import streamlit as st
import json
import requests
import re
from datetime import date, timedelta

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
BREAD_VALS = {"kcal": 211, "protein": 12, "fat": 5, "carbs": 25}
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
# KROK 1 — GROQ: klasyfikacja i parsowanie tekstu użytkownika
# ---------------------------------------------------------------
def classify_with_groq(food_description: str, api_key: str) -> list:
    """
    Groq analizuje tekst i zwraca listę składników z klasyfikacją źródła:
    OFF  = produkty markowe  → Open Food Facts
    USDA = surowce / dania domowe → USDA FoodData Central
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    system_prompt = """Jesteś ekspertem ds. żywienia. Dostajesz opis posiłku po polsku.
Zwróć TYLKO czysty JSON (tablica, bez żadnego tekstu przed/po):
[
  {
    "item": "polska nazwa produktu",
    "amount": <liczba gramów jako liczba, domyślnie 100 jeśli nie podano>,
    "source": "OFF" | "USDA",
    "eng_name": "angielska nazwa do wyszukiwania w API"
  }
]

Zasady klasyfikacji źródła:
- source="OFF"  → produkty markowe (Danone, Oreo, Activia, Zott, konkretna marka) LUB produkty przetworzone z etykietą sklepową
- source="USDA" → surowce, dania domowe, warzywa, owoce, mięso, nabiał bez marki, dania gotowane
- Każdy składnik/produkt to osobny obiekt w tablicy
- amount zawsze w gramach (1 kromka=80g, 1 plasterek=40g, 1 jajko=60g, 1 szklanka=240g, 1 łyżka=15g, 1 łyżeczka=5g)"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": food_description}
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    # Wyciągnij JSON nawet jeśli Groq doda jakiś tekst wokół
    start, end = raw.find("["), raw.rfind("]") + 1
    return json.loads(raw[start:end])

# ---------------------------------------------------------------
# KROK 2A — Open Food Facts
# ---------------------------------------------------------------
def fetch_from_off(query: str, amount_g: float) -> dict | None:
    """
    Szuka produktu w Open Food Facts.
    Zwraca makro przeliczone na amount_g lub None jeśli nie znalazło.
    """
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 5,
            "fields": "product_name,nutriments",
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        products = data.get("products", [])
        if not products:
            return None

        # Weź pierwszy produkt z kompletem makro
        for p in products:
            n = p.get("nutriments", {})
            kcal = n.get("energy-kcal_100g") or n.get("energy_100g", 0)
            if kcal:
                # Przelicz kcal z kJ jeśli trzeba
                if not n.get("energy-kcal_100g") and n.get("energy_100g"):
                    kcal = n["energy_100g"] / 4.184
                factor = amount_g / 100
                return {
                    "calories": round(kcal * factor),
                    "protein":  round(n.get("proteins_100g", 0) * factor, 1),
                    "fat":      round(n.get("fat_100g", 0) * factor, 1),
                    "carbs":    round(n.get("carbohydrates_100g", 0) * factor, 1),
                    "source_label": f"OFF:{p.get('product_name','?')[:30]}",
                }
        return None
    except Exception:
        return None

# ---------------------------------------------------------------
# KROK 2B — USDA FoodData Central
# ---------------------------------------------------------------
def fetch_from_usda(eng_name: str, amount_g: float) -> dict | None:
    """
    Szuka składnika w USDA FoodData Central (nie wymaga klucza API dla Foundation Foods).
    Zwraca makro przeliczone na amount_g lub None jeśli nie znalazło.
    """
    try:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {
            "query": eng_name,
            "dataType": "SR Legacy,Foundation,Branded",
            "pageSize": 5,
            "api_key": "DEMO_KEY",  # DEMO_KEY działa do ~30 req/min — wystarczy
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        foods = data.get("foods", [])
        if not foods:
            return None

        food = foods[0]
        nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}

        kcal    = nutrients.get("Energy", 0)
        protein = nutrients.get("Protein", 0)
        fat     = nutrients.get("Total lipid (fat)", 0)
        carbs   = nutrients.get("Carbohydrate, by difference", 0)

        factor = amount_g / 100
        return {
            "calories": round(kcal * factor),
            "protein":  round(protein * factor, 1),
            "fat":      round(fat * factor, 1),
            "carbs":    round(carbs * factor, 1),
            "source_label": f"USDA:{food.get('description','?')[:30]}",
        }
    except Exception:
        return None

# ---------------------------------------------------------------
# KROK 3 — Orkiestracja: suma po wszystkich składnikach
# ---------------------------------------------------------------
def get_nutrition_hybrid(food_description: str, api_key: str) -> dict:
    """
    Pełny pipeline:
    1. Groq klasyfikuje i parsuje składniki
    2. Dla każdego składnika odpowiednie API
    3. Sumuje makro
    Zwraca dict z name, calories, protein, fat, carbs + debug_info
    """
    items = classify_with_groq(food_description, api_key)

    total = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    sources_used = []
    fallback_items = []  # składniki których nie znaleziono w API

    for item in items:
        name      = item.get("item", "?")
        amount    = float(item.get("amount", 100))
        source    = item.get("source", "USDA")
        eng_name  = item.get("eng_name", name)

        result = None

        if source == "OFF":
            result = fetch_from_off(name, amount)
            if not result:
                # fallback: spróbuj USDA
                result = fetch_from_usda(eng_name, amount)

        else:  # USDA
            result = fetch_from_usda(eng_name, amount)
            if not result:
                # fallback: spróbuj OFF
                result = fetch_from_off(name, amount)

        if result:
            total["calories"] += result["calories"]
            total["protein"]  += result["protein"]
            total["fat"]      += result["fat"]
            total["carbs"]    += result["carbs"]
            sources_used.append(f"{name} ({amount:.0f}g) → {result['source_label']}")
        else:
            fallback_items.append(f"{name} ({amount:.0f}g) — brak danych")

    # Nazwa posiłku = oryginalny opis (skrócony)
    meal_name = food_description[:60] + ("…" if len(food_description) > 60 else "")

    return {
        "name":         meal_name,
        "calories":     total["calories"],
        "protein":      round(total["protein"], 1),
        "fat":          round(total["fat"], 1),
        "carbs":        round(total["carbs"], 1),
        "sources_used": sources_used,
        "fallback":     fallback_items,
    }

# ---------------------------------------------------------------
# POMOCNICZE — chleb własny
# ---------------------------------------------------------------
def detect_bread(text: str) -> bool:
    return any(kw in text.lower() for kw in [
        "chleb z otrębami", "chleb otręby", "chleb twarogowy", "chleb własny", "mój chleb"
    ])

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
.source-tag { font-size: 0.72rem; color: #a69080; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# UI — START
# ---------------------------------------------------------------
st.markdown('<div class="main-title">🥑 Dziennik Makro</div>', unsafe_allow_html=True)

history     = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]

total_kcal = sum(m["calories"] for m in today_meals)
total_p    = sum(m.get("protein", 0) for m in today_meals)
total_f    = sum(m.get("fat", 0) for m in today_meals)
total_c    = sum(m.get("carbs", 0) for m in today_meals)

# STATYSTYKI
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
    api_key = st.secrets.get("GROQ_API_KEY", "") or st.text_input("Klucz Groq API", type="password")
    st.markdown("---")
    st.markdown("**Źródła danych:**")
    st.markdown("🟢 **Groq** — klasyfikacja składników")
    st.markdown("🔵 **Open Food Facts** — produkty markowe")
    st.markdown("🟠 **USDA** — surowce i dania domowe")
    st.markdown("🍞 **Własna baza** — chleb z otrębami")
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
            placeholder="np. jogurt Danone 150g, 2 jajka sadzone, chleb z otrębami 80g…"
        )
    with col_sel:
        meal_time = st.selectbox("Pora", ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

if submitted and food_input:
    with st.spinner("🔍 Analizuję składniki i pobieram dane o wartościach odżywczych…"):
        try:
            # --- Chleb własny (bez API) ---
            if detect_bread(food_input):
                m_g = re.search(r"(\d+)\s*g", food_input.lower())
                g = int(m_g.group(1)) if m_g else 80
                new_meal = {
                    "name":     f"🍞 Chleb własny ({g}g)",
                    "calories": round(BREAD_VALS["kcal"] * g / 100),
                    "protein":  round(BREAD_VALS["protein"] * g / 100, 1),
                    "fat":      round(BREAD_VALS["fat"] * g / 100, 1),
                    "carbs":    round(BREAD_VALS["carbs"] * g / 100, 1),
                    "time":     meal_time,
                }
                save_meal(new_meal)
                st.cache_resource.clear()
                st.success(f"✅ {new_meal['name']} — **{new_meal['calories']} kcal** (dane własne)")
                st.rerun()

            # --- Hybrydowy pipeline ---
            else:
                result = get_nutrition_hybrid(food_input, api_key)
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

                # Pokaż skąd pobrano dane (expander, żeby nie zaśmiecać UI)
                if result["sources_used"]:
                    with st.expander("🔍 Skąd pobrano dane?"):
                        for s in result["sources_used"]:
                            st.caption(f"✔ {s}")
                        for f_item in result["fallback"]:
                            st.caption(f"⚠️ Nie znaleziono: {f_item} — pominięto")

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
                        f'<div class="meal-card">'
                        f'<span>{m["name"]}</span>'
                        f'<span class="meal-stats">'
                        f'{m["calories"]} kcal | B:{m["protein"]:.0f}g T:{m["fat"]:.0f}g W:{m["carbs"]:.0f}g'
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

# PRZYCISK PODSUMOWANIA DNIA
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
