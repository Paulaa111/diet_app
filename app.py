import streamlit as st
import re
from datetime import date, timedelta
from database import MY_FOOD_DB

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------
st.set_page_config(page_title="Dziennik Makro", page_icon="🥑", layout="wide")

SHEET_NAME = "Dziennik Kalorii"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
LIMIT_KCAL = 1500

# ---------------------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------------------
@st.cache_resource
def get_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def load_data():
    try:
        rows = get_sheet().get_all_records()
        meals = []
        for idx, r in enumerate(rows):
            meals.append({
                "date": str(r.get("Data", "")),
                "time": str(r.get("Pora", "")),
                "name": str(r.get("Nazwa", "")),
                "calories": int(r.get("Kalorie", 0) or 0),
                "protein": float(r.get("Białko", 0) or 0),
                "fat": float(r.get("Tłuszcz", 0) or 0),
                "carbs": float(r.get("Węglowodany", 0) or 0),
                "suma_dnia": r.get("Suma dnia", ""),
                "_row": idx + 2,
            })
        return meals
    except Exception as e:
        st.error(f"❌ Błąd Google Sheets: {e}")
        return []

def save_meal(meal_dict):
    try:
        days_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
        get_sheet().append_row([
            days_pl[date.today().weekday()],
            str(date.today()),
            meal_dict.get("time", ""),
            meal_dict.get("name", ""),
            meal_dict.get("calories", 0),
            round(meal_dict.get("protein", 0), 1),
            round(meal_dict.get("fat", 0), 1),
            round(meal_dict.get("carbs", 0), 1),
            "",
        ], value_input_option="USER_ENTERED")
    except Exception as e:
        st.error(f"❌ Nie udało się zapisać: {e}")

def save_daily_summary(today_meals):
    try:
        sheet = get_sheet()
        total = sum(m["calories"] for m in today_meals)
        total_p = sum(m.get("protein", 0) for m in today_meals)
        total_f = sum(m.get("fat", 0) for m in today_meals)
        total_c = sum(m.get("carbs", 0) for m in today_meals)
        first_row = min(m["_row"] for m in today_meals)
        text = f"{total} kcal | B:{total_p:.0f}g T:{total_f:.0f}g W:{total_c:.0f}g"
        sheet.update_cell(first_row, 9, text)
        for m in today_meals:
            if m["_row"] != first_row:
                sheet.update_cell(m["_row"], 9, "")
        return total
    except Exception as e:
        st.error(f"❌ Błąd zapisu podsumowania: {e}")
        return None

def delete_meal_by_row(row_number):
    try:
        get_sheet().delete_rows(row_number)
    except Exception as e:
        st.error(f"❌ Błąd usuwania: {e}")

# ---------------------------------------------------------------
# ROZPOZNAWANIE SKŁADNIKÓW
# ---------------------------------------------------------------

# Jednostki miary -> gramy na 1 jednostkę
PORTIONS = {
    "kromka":    80,
    "kromki":    80,
    "kromek":    80,
    "łyżeczka":  5,
    "łyżeczki":  5,
    "łyżka":     15,
    "łyżki":     15,
    "łyżek":     15,
    "sztuka":    60,
    "sztuki":    60,
    "sztuk":     60,
    "g":         1,
    "gram":      1,
    "gramy":     1,
    "gramów":    1,
    "ml":        1,
}

# Aliasy nazw produktów -> klucz w bazie danych
ALIASES = {
    "mojego chleba":        "chleb z otrębami",
    "mój chleb":            "chleb z otrębami",
    "moje chleba":          "chleb z otrębami",
    "chleb":                "chleb z otrębami",
    "finuu":                "finuu klasyczne",
    "jajko":                "jajko kurze",
    "jajka":                "jajko kurze",
    "jaj":                  "jajko kurze",
    "jogurt":               "jogurt naturalny piątnica 2%",
    "twaróg":               "twaróg półtłusty",
    "masło":                "masło ekstra",
    "oliwa":                "oliwa z oliwek",
    "kasza":                "kasza gryczana",
    "ryż":                  "ryż biały",
}

def resolve_product(raw: str) -> str:
    """
    Zamienia surowy tekst na klucz w bazie MY_FOOD_DB.
    Kolejność: 1) bezpośrednie trafienie w bazie, 2) alias, 3) częściowe dopasowanie.
    """
    raw = raw.strip().lower()

    # 1. Dokładne trafienie w bazie
    if raw in MY_FOOD_DB:
        return raw

    # 2. Szukaj aliasów (od najdłuższego, żeby "mojego chleba" > "chleba")
    for alias in sorted(ALIASES.keys(), key=len, reverse=True):
        if alias in raw:
            return ALIASES[alias]

    # 3. Częściowe dopasowanie w kluczach bazy
    for key in MY_FOOD_DB:
        if key in raw or raw in key:
            return key

    # 4. Nie znaleziono
    return raw


def parse_meal(text: str):
    """
    Parsuje tekst wejściowy i zwraca listę (nazwa_produktu, gramy).

    Obsługuje:
      - "2 kromki chleba"         -> (chleb z otrębami, 160g)
      - "2 kromki mojego chleba"  -> (chleb z otrębami, 160g)
      - "150g ryżu"               -> (ryż biały, 150g)
      - "łyżka finuu"             -> (finuu klasyczne, 15g)
      - "jajko"                   -> (jajko kurze, 60g)
    """
    text_lower = text.lower()
    results = []
    used_spans = []

    unit_pattern = "|".join(re.escape(u) for u in PORTIONS.keys())

    # ----------------------------------------------------------------
    # Wzór A: liczba + jednostka + produkt
    # Przykład: "2 kromki mojego chleba", "150 g ryżu"
    # ----------------------------------------------------------------
    pattern_a = re.compile(
        r'(\d+(?:[.,]\d+)?)\s+(' + unit_pattern + r')\s+([a-ząćęłńóśźż ]+?)(?=\s+z\s+\d|\s+i\s+|\s*,|\s*$)',
        re.IGNORECASE | re.UNICODE
    )

    for m in pattern_a.finditer(text_lower):
        count = float(m.group(1).replace(",", "."))
        unit  = m.group(2).lower()
        raw   = m.group(3).strip()
        grams = PORTIONS[unit] * count
        product = resolve_product(raw)
        results.append((product, grams))
        used_spans.append((m.start(), m.end()))

    # ----------------------------------------------------------------
    # Wzór B: jednostka (bez liczby) + produkt
    # Przykład: "łyżka finuu", "kromka chleba"
    # ----------------------------------------------------------------
    pattern_b = re.compile(
        r'\b(' + unit_pattern + r')\s+([a-ząćęłńóśźż ]+?)(?=\s+z\s+\d|\s+i\s+|\s*,|\s*$)',
        re.IGNORECASE | re.UNICODE
    )

    for m in pattern_b.finditer(text_lower):
        # Pomiń jeśli ten fragment już pokryty przez wzór A
        if any(s <= m.start() < e for s, e in used_spans):
            continue
        # Upewnij się, że przed jednostką nie ma cyfry (bo wtedy wzór A powinien był trafić)
        before = text_lower[:m.start()].rstrip()
        if before and before[-1].isdigit():
            continue

        unit  = m.group(1).lower()
        raw   = m.group(2).strip()
        grams = PORTIONS[unit] * 1  # 1 jednostka
        product = resolve_product(raw)
        results.append((product, grams))
        used_spans.append((m.start(), m.end()))

    # ----------------------------------------------------------------
    # Wzór C: liczba + produkt (brak jednostki)
    # Przykład: "2 jajka", "3 jabłka"
    # ----------------------------------------------------------------
    pattern_c = re.compile(
        r'(\d+)\s+([a-ząćęłńóśźż ]+?)(?=\s+z\s+\d|\s+i\s+|\s*,|\s*$)',
        re.IGNORECASE | re.UNICODE
    )

    for m in pattern_c.finditer(text_lower):
        if any(s <= m.start() < e for s, e in used_spans):
            continue
        count = int(m.group(1))
        raw   = m.group(2).strip()
        product = resolve_product(raw)
        # Domyślna porcja jednej sztuki to 60g (można nadpisać przez bazę danych)
        grams = 60 * count
        results.append((product, grams))
        used_spans.append((m.start(), m.end()))

    # ----------------------------------------------------------------
    # Wzór D: sam produkt (bez liczby i jednostki)
    # Przykład: "finuu", "jajko"
    # ----------------------------------------------------------------
    if not results:
        product = resolve_product(text_lower)
        results.append((product, 60))  # domyślna porcja

    return results


def calculate_nutrition(product_name: str, grams: float):
    """Oblicza wartości odżywcze dla produktu na podstawie gramy."""
    data = MY_FOOD_DB.get(product_name)
    if not data:
        return None

    multiplier = grams / 100.0
    return {
        "calories": int(round(data["kcal"] * multiplier)),
        "protein":  round(data["p"] * multiplier, 1),
        "fat":      round(data["f"] * multiplier, 1),
        "carbs":    round(data["c"] * multiplier, 1),
    }

# ---------------------------------------------------------------
# STYLIZACJA
# ---------------------------------------------------------------
st.markdown("""
<style>
.stApp { background-color: #fdfaf5; }
.main-title { font-size: 3rem; font-weight: 700; color: #6b8e23; text-align: center; }
.stat-box { background: white; border-radius: 15px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.stat-value { font-size: 2rem; font-weight: 800; }
.stat-label { font-size: 0.8rem; color: #666; }
.meal-card { background: white; border-radius: 10px; padding: 10px; margin: 5px 0; display: flex; justify-content: space-between; align-items: center; }
.section-header { color: #6b8e23; font-size: 1.3rem; font-weight: 700; margin-top: 20px; border-bottom: 2px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# UI
# ---------------------------------------------------------------
st.markdown('<div class="main-title">🥑 Dziennik Makro</div>', unsafe_allow_html=True)

history = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]
total_kcal = sum(m["calories"] for m in today_meals)
total_p    = sum(m.get("protein", 0) for m in today_meals)
total_f    = sum(m.get("fat", 0) for m in today_meals)
total_c    = sum(m.get("carbs", 0) for m in today_meals)

c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_kcal}</div><div class="stat-label">Kcal</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_p:.0f}g</div><div class="stat-label">Białko</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_f:.0f}g</div><div class="stat-label">Tłuszcz</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_c:.0f}g</div><div class="stat-label">Węgle</div></div>', unsafe_allow_html=True)
with c5:
    rem = LIMIT_KCAL - total_kcal
    color = "#6b8e23" if rem >= 0 else "#e53e3e"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{rem}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    st.markdown("---")
    st.markdown("**Arkusz:** Dziennik Kalorii")
    if st.button("🔄 Odśwież dane"):
        st.cache_resource.clear()
        st.rerun()

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co dziś zjadłaś?",
        placeholder="np. 2 kromki mojego chleba z łyżką finuu")
    meal_time = st.selectbox("Pora", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

st.write("TEST:", parse_meal("2 kromki mojego chleba"))
st.write("TEST2:", parse_meal("łyżka finuu"))

if submitted and food_input:
    with st.spinner("🔍 Analizuję…"):
        items = parse_meal(food_input)

        total = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        details = []
        found_any = False

        for product_name, grams in items:
            nutrition = calculate_nutrition(product_name, grams)
            if nutrition:
                found_any = True
                total["calories"] += nutrition["calories"]
                total["protein"]  += nutrition["protein"]
                total["fat"]      += nutrition["fat"]
                total["carbs"]    += nutrition["carbs"]
                details.append(f"✅ **{product_name}**: {grams:.0f}g → {nutrition['calories']} kcal | B:{nutrition['protein']}g T:{nutrition['fat']}g W:{nutrition['carbs']}g")
            else:
                details.append(f"⚠️ **{product_name}**: brak w bazie danych")

        if not found_any:
            st.error("❌ Nie rozpoznano żadnego składnika. Spróbuj: '2 kromki chleba z łyżką finuu'")
        else:
            new_meal = {
                "name":     food_input[:50],
                "calories": total["calories"],
                "protein":  total["protein"],
                "fat":      total["fat"],
                "carbs":    total["carbs"],
                "time":     meal_time,
            }
            save_meal(new_meal)
            st.cache_resource.clear()
            st.success(f"✅ Zapisano: {total['calories']} kcal | B:{total['protein']:.0f}g T:{total['fat']:.0f}g W:{total['carbs']:.0f}g")
            with st.expander("📊 Szczegóły składników"):
                for d in details:
                    st.markdown(d)
            st.rerun()

# ---------------------------------------------------------------
# DZISIEJSZE MENU
# ---------------------------------------------------------------
st.markdown('<div class="section-header">Dzisiejsze Menu</div>', unsafe_allow_html=True)

if today_meals:
    for cat in ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"]:
        cat_meals = [m for m in today_meals if m["time"] == cat]
        if cat_meals:
            st.write(f"**{cat}**")
            for m in cat_meals:
                col1, col2 = st.columns([8, 1])
                with col1:
                    st.markdown(
                        f'<div class="meal-card">'
                        f'<span>{m["name"]}</span>'
                        f'<span>{m["calories"]} kcal | B:{m["protein"]:.0f}g T:{m["fat"]:.0f}g W:{m["carbs"]:.0f}g</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with col2:
                    if st.button("🗑️", key=f"del_{m['_row']}"):
                        delete_meal_by_row(m["_row"])
                        st.rerun()
else:
    st.info("Dodaj swój pierwszy posiłek powyżej!")

if today_meals:
    if st.button("📊 Zapisz podsumowanie dnia"):
        save_daily_summary(today_meals)
        st.success("✅ Podsumowanie zapisane!")

# ---------------------------------------------------------------
# PODSUMOWANIE TYGODNIA
# ---------------------------------------------------------------
st.markdown('<div class="section-header">Podsumowanie Tygodnia</div>', unsafe_allow_html=True)
if history:
    week_data = {}
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        week_data[d.strftime("%d.%m")] = sum(m["calories"] for m in history if m["date"] == str(d))
    st.bar_chart(week_data)
