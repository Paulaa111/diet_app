import streamlit as st
import json
import requests
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
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
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
        sheet = get_sheet()
        rows = sheet.get_all_records()
        meals = []
        for idx, r in enumerate(rows):
            meals.append({
                "id":        str(r.get("Data",""))+"_"+str(r.get("Pora",""))+"_"+str(r.get("Nazwa","")),
                "date":      str(r.get("Data", "")),
                "time":      str(r.get("Pora", "")),
                "name":      str(r.get("Nazwa", "")),
                "calories":  int(r.get("Kalorie", 0) or 0),
                "protein":   float(r.get("Białko", 0) or 0),
                "fat":       float(r.get("Tłuszcz", 0) or 0),
                "carbs":     float(r.get("Węglowodany", 0) or 0),
                "suma_dnia": r.get("Suma dnia", ""),
                "_row":      idx + 2,
            })
        return meals
    except Exception as e:
        st.error(f"❌ Błąd połączenia z Google Sheets: {e}")
        return []

def save_meal(meal_dict):
    try:
        sheet = get_sheet()
        days_pl = ["Poniedziałek","Wtorek","Środa","Czwartek","Piątek","Sobota","Niedziela"]
        row = [
            days_pl[date.today().weekday()],
            str(date.today()),
            meal_dict.get("time", ""),
            meal_dict.get("name", ""),
            meal_dict.get("calories", 0),
            round(meal_dict.get("protein", 0), 1),
            round(meal_dict.get("fat", 0), 1),
            round(meal_dict.get("carbs", 0), 1),
            "",
        ]
        sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        st.error(f"❌ Nie udało się zapisać: {e}")

def save_daily_summary(today_meals):
    try:
        sheet = get_sheet()
        total   = sum(m["calories"] for m in today_meals)
        total_p = sum(m.get("protein", 0) for m in today_meals)
        total_f = sum(m.get("fat", 0) for m in today_meals)
        total_c = sum(m.get("carbs", 0) for m in today_meals)
        first_row = min(m["_row"] for m in today_meals)
        summary_text = f"{total} kcal | B:{total_p:.0f}g T:{total_f:.0f}g W:{total_c:.0f}g"
        sheet.update_cell(first_row, 9, summary_text)
        for m in today_meals:
            if m["_row"] != first_row:
                sheet.update_cell(m["_row"], 9, "")
        return total
    except Exception as e:
        st.error(f"❌ Nie udało się zapisać podsumowania: {e}")
        return None

def delete_meal_by_row(row_number):
    try:
        get_sheet().delete_rows(row_number)
    except Exception as e:
        st.error(f"❌ Nie udało się usunąć wiersza: {e}")

# ---------------------------------------------------------------
# WYSZUKIWANIE W LOKALNEJ BAZIE database.py
# ---------------------------------------------------------------
def lookup_in_db(name_ai: str, amount_g: float) -> dict | None:
    """
    Szuka produktu w MY_FOOD_DB.
    Dwa poziomy dopasowania — celowo ostrożne żeby uniknąć fałszywych trafień:
      1. Dokładne dopasowanie klucza
      2. Klucz bazy zawiera się w nazwie AI LUB nazwa AI zawiera się w kluczu
         — ale TYLKO jeśli dopasowany fragment ma >= 2 słowa lub >= 8 znaków
           (żeby "chleb" nie łapał "chleb pszenny" jako "chleb z otrębami")
    Poziom 3 (wspólne słowa) usunięty — był przyczyną błędów.
    """
    name_lower = name_ai.lower().strip()

    # Poziom 1 — dokładne dopasowanie
    if name_lower in MY_FOOD_DB:
        db_val = MY_FOOD_DB[name_lower]
        factor = amount_g / 100
        return {
            "calories": round(db_val["kcal"] * factor),
            "protein":  round(db_val["p"] * factor, 1),
            "fat":      round(db_val["f"] * factor, 1),
            "carbs":    round(db_val["c"] * factor, 1),
            "source_label": f"🏠 Moja baza ({name_lower})",
        }

    # Poziom 2 — częściowe dopasowanie (ostrożne)
    best_key    = None
    best_length = 0  # im dłuższy dopasowany fragment, tym lepiej

    for key in MY_FOOD_DB:
        matched_fragment = None

        if key in name_lower:
            matched_fragment = key          # klucz bazy zawiera się w nazwie AI
        elif name_lower in key:
            matched_fragment = name_lower   # nazwa AI zawiera się w kluczu bazy

        if matched_fragment:
            # Akceptuj tylko jeśli fragment jest wystarczająco specyficzny:
            # przynajmniej 2 słowa LUB przynajmniej 8 znaków
            words = matched_fragment.split()
            if len(words) >= 2 or len(matched_fragment) >= 8:
                if len(matched_fragment) > best_length:
                    best_length = len(matched_fragment)
                    best_key = key

    if not best_key:
        return None

    db_val = MY_FOOD_DB[best_key]
    factor = amount_g / 100
    return {
        "calories": round(db_val["kcal"] * factor),
        "protein":  round(db_val["p"] * factor, 1),
        "fat":      round(db_val["f"] * factor, 1),
        "carbs":    round(db_val["c"] * factor, 1),
        "source_label": f"🏠 Moja baza ({best_key})",
    }

# ---------------------------------------------------------------
# GEMINI — klasyfikacja składników
# ---------------------------------------------------------------
def classify_with_gemini(food_description: str, api_key: str) -> list:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    prompt = f"""Jesteś ekspertem ds. żywienia. Dostajesz opis posiłku po polsku.
Zwróć TYLKO czysty JSON (tablica, bez żadnego tekstu przed/po, bez markdown):
[
  {{
    "item": "polska nazwa produktu (jak najbardziej szczegółowa)",
    "amount": <liczba gramów — TYLKO liczba, bez tekstu>,
    "source": "OFF lub USDA",
    "eng_name": "krótka angielska nazwa, max 3 słowa"
  }}
]

Zasady:
- source="OFF"  → produkty z konkretną marką (Danone, Zott, Activia, Piątnica, Finuu, Oreo itp.)
- source="USDA" → surowce, warzywa, owoce, mięso, nabiał bez marki, dania domowe
- Każdy składnik to OSOBNY obiekt w tablicy
- amount ZAWSZE w gramach (liczba całkowita):
    1 kromka = 80g
    1 plasterek = 40g
    1 jajko = 60g
    1 łyżka = 15g
    1 łyżeczka = 5g
    1 szklanka = 240g
    kubek = 250g
    porcja zupy = 350g
    filiżanka kawy = 150g
- NIE sumuj składników w jeden obiekt — każdy produkt osobno
- eng_name: konkretny np. "natural yogurt", "chicken breast", "boiled potato"

SPECJALNE MAPOWANIA — zawsze używaj dokładnie tej nazwy w polu "item":
- "mój chleb", "kromka mojego chleba", "chleb twarogowy", "chleb własny", "chleb domowy" → item = "chleb z otrębami"
- "finuu", "margaryna finuu" → item = "finuu klasyczne" (chyba że napisano "lekkie" → "finuu lekkie")
- "jajko", "jajka", "jajeczko" (bez przymiotnika) → item = "jajko kurze"
- "jajko sadzone", "jajka sadzone" → item = "jajko sadzone"

Opis posiłku: {food_description}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512}
    }
    resp = requests.post(url, json=payload, timeout=20)
    resp.raise_for_status()
    raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    start, end = raw.find("["), raw.rfind("]") + 1
    return json.loads(raw[start:end])

# ---------------------------------------------------------------
# GEMINI — fallback kalkulator dla pojedynczego składnika
# ---------------------------------------------------------------
def gemini_estimate_single(item_name: str, amount_g: float, api_key: str) -> dict | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    prompt = (
        f"Podaj wartości odżywcze dla: {item_name}, porcja {amount_g}g. "
        f"Zwróć TYLKO czysty JSON (bez tekstu, bez markdown): "
        f'{{"calories": 0, "protein": 0, "fat": 0, "carbs": 0}}'
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 100}
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        start, end = raw.find("{"), raw.rfind("}") + 1
        data = json.loads(raw[start:end])
        return {
            "calories": int(data.get("calories", 0)),
            "protein":  round(float(data.get("protein", 0)), 1),
            "fat":      round(float(data.get("fat", 0)), 1),
            "carbs":    round(float(data.get("carbs", 0)), 1),
            "source_label": "🤖 Gemini~szacunek",
        }
    except Exception:
        return None

# ---------------------------------------------------------------
# Open Food Facts
# ---------------------------------------------------------------
def fetch_from_off(query: str, amount_g: float) -> dict | None:
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
            "sort_by": "unique_scans_n",
            "fields": "product_name,nutriments",
        }
        resp = requests.get(url, params=params, timeout=12)
        resp.raise_for_status()
        products = resp.json().get("products", [])
        if not products:
            return None
        best, best_score = None, -1
        for p in products:
            n = p.get("nutriments", {})
            kcal_100 = n.get("energy-kcal_100g")
            if not kcal_100 and n.get("energy_100g"):
                kcal_100 = n["energy_100g"] / 4.184
            if not kcal_100 or kcal_100 <= 0:
                continue
            score = sum([
                n.get("proteins_100g") is not None,
                n.get("fat_100g") is not None,
                n.get("carbohydrates_100g") is not None,
            ])
            if score > best_score:
                best_score = score
                best = (p, n, kcal_100)
        if not best:
            return None
        p, n, kcal_100 = best
        factor = amount_g / 100
        return {
            "calories": round(kcal_100 * factor),
            "protein":  round((n.get("proteins_100g") or 0) * factor, 1),
            "fat":      round((n.get("fat_100g") or 0) * factor, 1),
            "carbs":    round((n.get("carbohydrates_100g") or 0) * factor, 1),
            "source_label": f"🔵 OFF: {p.get('product_name','?')[:30]}",
        }
    except Exception:
        return None

# ---------------------------------------------------------------
# USDA FoodData Central
# ---------------------------------------------------------------
def fetch_from_usda(eng_name: str, amount_g: float, usda_key: str = "DEMO_KEY") -> dict | None:
    try:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        for data_type in ["SR Legacy,Foundation", "Branded"]:
            params = {
                "query":    eng_name,
                "dataType": data_type,
                "pageSize": 5,
                "api_key":  usda_key,
            }
            resp = requests.get(url, params=params, timeout=12)
            resp.raise_for_status()
            foods = resp.json().get("foods", [])
            for food in foods:
                # Bezpieczne budowanie słownika — pomijamy wpisy bez nazwy lub z wartością niebędącą liczbą
                nutrients = {}
                for n in food.get("foodNutrients", []):
                    if not isinstance(n, dict):
                        continue
                    name = n.get("nutrientName")
                    value = n.get("value")
                    if name and isinstance(value, (int, float)):
                        nutrients[name] = value

                kcal = (
                    nutrients.get("Energy") or
                    nutrients.get("Energy (Atwater General Factors)") or
                    nutrients.get("Energy (Atwater Specific Factors)") or 0
                )
                if kcal > 0:
                    factor = amount_g / 100
                    return {
                        "calories": round(kcal * factor),
                        "protein":  round(nutrients.get("Protein", 0) * factor, 1),
                        "fat":      round(nutrients.get("Total lipid (fat)", 0) * factor, 1),
                        "carbs":    round(nutrients.get("Carbohydrate, by difference", 0) * factor, 1),
                        "source_label": f"🟠 USDA: {food.get('description','?')[:30]}",
                    }
        return None
    except Exception:
        return None

# ---------------------------------------------------------------
# ORKIESTRACJA — pełny pipeline
# ---------------------------------------------------------------
def get_nutrition_hybrid(food_description: str, api_key: str, usda_key: str) -> dict:
    items = classify_with_gemini(food_description, api_key)

    total = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    sources_used   = []
    fallback_items = []

    # Rozsądne limity gramatur na 1 porcję (zapobiega absurdalnym wartościom od Groqa)
    MAX_GRAMS = {
        "chleb":      300,   # max 3-4 kromki
        "masło":       30,   # max 2 łyżki
        "finuu":       30,   # max 2 łyżki
        "margaryna":   30,
        "olej":        30,
        "oliwa":       30,
        "sól":         10,
        "cukier":      30,
        "miód":        30,
        "dżem":        40,
        "jogurt":     300,
        "mleko":      300,
        "ser":        100,
        "jajko":      180,   # max 3 jajka
        "default":   1000,   # domyślny limit
    }

    def sanitize_amount(name: str, amount: float) -> float:
        """Koryguje absurdalne gramatury — AI czasem zwraca np. 800g chleba."""
        name_l = name.lower()
        for keyword, max_g in MAX_GRAMS.items():
            if keyword == "default":
                continue
            if keyword in name_l:
                if amount > max_g:
                    return max_g
                return amount
        # Domyślnie: nic powyżej 1kg nie ma sensu dla 1 porcji
        return min(amount, MAX_GRAMS["default"])

    for item in items:
        name_ai  = item.get("item", "").lower()
        amount   = sanitize_amount(name_ai, float(item.get("amount", 100)))
        source   = item.get("source", "USDA")
        eng_name = item.get("eng_name", name_ai)

        result = None

        # 1️⃣ Własna baza — zawsze pierwsza
        result = lookup_in_db(name_ai, amount)

        # 2️⃣ API zewnętrzne — tylko gdy brak w bazie
        if not result:
            if source == "OFF":
                result = fetch_from_off(name_ai, amount)
                if not result:
                    result = fetch_from_usda(eng_name, amount, usda_key)
            else:
                result = fetch_from_usda(eng_name, amount, usda_key)
                if not result:
                    result = fetch_from_off(name_ai, amount)

        # 3️⃣ Ostateczny fallback — Groq szacuje
        if not result:
            result = gemini_estimate_single(name_ai, amount, api_key)

        if result:
            total["calories"] += result["calories"]
            total["protein"]  += result["protein"]
            total["fat"]      += result["fat"]
            total["carbs"]    += result["carbs"]
            sources_used.append(f"{name_ai} ({amount:.0f}g) → {result['source_label']}")
        else:
            fallback_items.append(f"{name_ai} ({amount:.0f}g) — brak danych")

    return {
        "name":         food_description[:60],
        "calories":     total["calories"],
        "protein":      round(total["protein"], 1),
        "fat":          round(total["fat"], 1),
        "carbs":        round(total["carbs"], 1),
        "sources_used": sources_used,
        "fallback":     fallback_items,
    }

# ---------------------------------------------------------------
# STYLIZACJA
# ---------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
.stApp { background-color: #fdfaf5; color: #4a4a4a; font-family: 'Quicksand', sans-serif; }
.main-title { font-size: 3rem; font-weight: 700; color: #6b8e23; text-align: center; margin-top: -30px; }
.stat-box {
    background: white; border-radius: 15px; padding: 15px; text-align: center;
    box-shadow: 0 8px 16px rgba(139,123,108,0.1); border-bottom: 4px solid #e0d7cd;
}
.stat-value { font-size: 2.2rem; font-weight: 800; line-height: 1; margin-bottom: 5px; }
.stat-label { font-size: 0.8rem; color: #a69080; text-transform: uppercase; font-weight: 700; }
.meal-card {
    background: white; border-radius: 12px; padding: 12px; margin: 5px 0;
    display: flex; justify-content: space-between; align-items: center; border: 1px solid #f0ede9;
}
.meal-stats { background: #f1f3eb; color: #6b8e23; padding: 5px 12px; border-radius: 10px; font-weight: 700; font-size: 0.85rem; }
.section-header { color: #6b8e23; font-size: 1.3rem; font-weight: 700; margin-top: 20px; border-bottom: 2px solid #e9e2d8; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# UI
# ---------------------------------------------------------------
st.markdown('<div class="main-title">🥑 Dziennik Makro</div>', unsafe_allow_html=True)

history     = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]

total_kcal = sum(m["calories"] for m in today_meals)
total_p    = sum(m.get("protein", 0) for m in today_meals)
total_f    = sum(m.get("fat", 0) for m in today_meals)
total_c    = sum(m.get("carbs", 0) for m in today_meals)

c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_kcal}</div><div class="stat-label">Kcal</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6b8e23">{total_p:.0f}g</div><div class="stat-label">Białko</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#bc6c25">{total_f:.0f}g</div><div class="stat-label">Tłuszcz</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#4299e1">{total_c:.0f}g</div><div class="stat-label">Węgle</div></div>', unsafe_allow_html=True)
with c5:
    rem   = LIMIT_KCAL - total_kcal
    color = "#6b8e23" if rem >= 0 else "#e53e3e"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{rem}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    api_key  = st.secrets.get("GEMINI_API_KEY", "") or st.text_input("Klucz Gemini API", type="password")
    usda_key = st.secrets.get("USDA_API_KEY", "DEMO_KEY")
    st.markdown("---")
    st.markdown("**Źródła danych (kolejność):**")
    st.markdown("1️⃣ 🏠 **Moja baza** — database.py")
    st.markdown("2️⃣ 🔵 **Open Food Facts** — marki")
    st.markdown("3️⃣ 🟠 **USDA** — surowce")
    st.markdown("4️⃣ 🤖 **Gemini** — ostateczny fallback")
    st.markdown("---")
    st.markdown("**Arkusz:** Dziennik Kalorii")
    if st.button("🔄 Odśwież dane"):
        st.cache_resource.clear()
        st.rerun()

# FORMULARZ
with st.form("meal_form", clear_on_submit=True):
    col_in, col_sel = st.columns([3, 1])
    with col_in:
        food_input = st.text_input(
            "Co dziś zjadłaś?",
            placeholder="np. jogurt piątnica 150g, 2 jajka sadzone, pierogi ruskie 200g…"
        )
    with col_sel:
        meal_time = st.selectbox("Pora", ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

if submitted and food_input:
    with st.spinner("🔍 Analizuję składniki…"):
        try:
            result = get_nutrition_hybrid(food_input, api_key, usda_key)
            new_meal = {
                "name":     result["name"],
                "calories": result["calories"],
                "protein":  result["protein"],
                "fat":      result["fat"],
                "carbs":    result["carbs"],
                "time":     meal_time,
            }
            save_meal(new_meal)
            st.cache_resource.clear()
            st.success(
                f"✅ **{result['name']}** — "
                f"**{result['calories']} kcal** | "
                f"B:{result['protein']:.0f}g T:{result['fat']:.0f}g W:{result['carbs']:.0f}g"
            )
            with st.expander("🔍 Skąd pobrano dane?"):
                for s in result["sources_used"]:
                    st.caption(f"✔ {s}")
                for f_item in result["fallback"]:
                    st.caption(f"⚠️ {f_item}")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd: {e}")

# LISTA POSIŁKÓW
st.markdown('<div class="section-header">Dzisiejsze Menu</div>', unsafe_allow_html=True)
if today_meals:
    for cat in ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"]:
        cat_meals = [m for m in today_meals if m["time"] == cat]
        if cat_meals:
            st.write(f"**{cat}**")
            for m in cat_meals:
                c1, c2 = st.columns([8, 1])
                with c1:
                    st.markdown(
                        f'<div class="meal-card"><span>{m["name"]}</span>'
                        f'<span class="meal-stats">{m["calories"]} kcal | '
                        f'B:{m["protein"]:.0f}g T:{m["fat"]:.0f}g W:{m["carbs"]:.0f}g'
                        f'</span></div>',
                        unsafe_allow_html=True
                    )
                with c2:
                    if st.button("🗑️", key=f"del_{m['_row']}"):
                        delete_meal_by_row(m["_row"])
                        st.cache_resource.clear()
                        st.rerun()
else:
    st.info("Dodaj swój pierwszy posiłek powyżej!")

# PODSUMOWANIE DNIA
if today_meals:
    st.write("")
    col_sum, col_info = st.columns([2, 5])
    with col_sum:
        if st.button("📊 Zapisz podsumowanie dnia do arkusza", use_container_width=True):
            with st.spinner("Zapisuję…"):
                total = save_daily_summary(today_meals)
                if total is not None:
                    st.cache_resource.clear()
                    st.success(f"✅ Suma dnia: **{total} kcal** — zapisana w kolumnie 'Suma dnia'.")
    with col_info:
        first_meal = min(today_meals, key=lambda m: m["_row"])
        if first_meal.get("suma_dnia"):
            st.info(f"📋 Ostatnie podsumowanie: **{first_meal['suma_dnia']}**")
        else:
            st.caption("💡 Kliknij gdy skończyłaś dodawać posiłki.")

# PODSUMOWANIE TYGODNIA
st.write("")
st.markdown('<div class="section-header">Podsumowanie Tygodnia</div>', unsafe_allow_html=True)
if history:
    week_data = {}
    for i in range(6, -1, -1):
        d     = date.today() - timedelta(days=i)
        d_str = str(d)
        day_sum = sum(m["calories"] for m in history if m["date"] == d_str)
        week_data[d.strftime("%d.%m")] = day_sum
    st.bar_chart(week_data)
    avg_kcal = sum(week_data.values()) / 7
    st.write(f"Średnie kalorie z ostatnich 7 dni: **{avg_kcal:.0f} kcal**")
