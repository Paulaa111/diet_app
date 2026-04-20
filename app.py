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
                "id":       str(r.get("Data",""))+"_"+str(r.get("Pora",""))+"_"+str(r.get("Nazwa","")),
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
# KROK 1 — GROQ: Parser
# ---------------------------------------------------------------
def classify_with_groq(food_description: str, api_key: str) -> list:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    system_prompt = """Jesteś ekspertem ds. żywienia i parserem JSON. 
Zwróć TYLKO tablicę JSON, bez komentarzy.
Zasady:
1. source="OFF" dla produktów konkretnych marek (np. Mlekovita, Zott, Danone). Pole 'item' musi być po polsku.
2. source="USDA" dla składników bazowych (np. pierś z kurczaka, ziemniaki). Pole 'eng_name' musi być po angielsku.
3. Jeśli użytkownik podał ilość w sztukach, przelicz na gramy: 1 jajko=60g, 1 jabłko=180g, 1 kromka=40g.

Format:
[{"item": "polska nazwa", "amount": 150, "source": "OFF" | "USDA", "eng_name": "english name"}]"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": food_description}
        ],
        "temperature": 0.1,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    start, end = raw.find("["), raw.rfind("]") + 1
    return json.loads(raw[start:end])

# ---------------------------------------------------------------
# KROK 2A — Open Food Facts (Markowe)
# ---------------------------------------------------------------
def fetch_from_off(query: str, amount_g: float) -> dict | None:
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 3,
            "sort_by": "unique_scans_n",
            "fields": "product_name,nutriments",
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        products = data.get("products", [])
        if not products: return None

        for p in products:
            n = p.get("nutriments", {})
            kcal = n.get("energy-kcal_100g") or n.get("energy_100g")
            if kcal:
                if n.get("energy_100g") and not n.get("energy-kcal_100g"):
                    kcal = n["energy_100g"] / 4.184
                factor = amount_g / 100
                return {
                    "calories": round(kcal * factor),
                    "protein":  round(n.get("proteins_100g", 0) * factor, 1),
                    "fat":      round(n.get("fat_100g", 0) * factor, 1),
                    "carbs":    round(n.get("carbohydrates_100g", 0) * factor, 1),
                    "source_label": f"OFF: {p.get('product_name','?')[:20]}",
                }
        return None
    except: return None

# ---------------------------------------------------------------
# KROK 2B — USDA (Surowce)
# ---------------------------------------------------------------
def fetch_from_usda(eng_name: str, amount_g: float) -> dict | None:
    try:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {
            "query": eng_name,
            "dataType": "Foundation,SR Legacy",
            "pageSize": 3,
            "api_key": "DEMO_KEY",
        }
        resp = requests.get(url, params=params, timeout=10)
        foods = resp.json().get("foods", [])
        if not foods: return None

        food = foods[0]
        nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}
        
        # Klucze USDA bywają różne, sprawdzamy najczęstsze
        kcal = nutrients.get("Energy", nutrients.get("Energy (kcal)", 0))
        prot = nutrients.get("Protein", 0)
        fat  = nutrients.get("Total lipid (fat)", 0)
        carb = nutrients.get("Carbohydrate, by difference", 0)

        factor = amount_g / 100
        return {
            "calories": round(kcal * factor),
            "protein":  round(prot * factor, 1),
            "fat":      round(fat * factor, 1),
            "carbs":    round(carb * factor, 1),
            "source_label": f"USDA: {food.get('description','?')[:20]}",
        }
    except: return None

# ---------------------------------------------------------------
# KROK 3 — Hybryda
# ---------------------------------------------------------------
def get_nutrition_hybrid(food_description: str, api_key: str) -> dict:
    items = classify_with_groq(food_description, api_key)
    total = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    sources = []
    
    for it in items:
        res = None
        amt = float(it.get("amount", 100))
        if it.get("source") == "OFF":
            res = fetch_from_off(it["item"], amt)
            if not res: res = fetch_from_usda(it["eng_name"], amt)
        else:
            res = fetch_from_usda(it["eng_name"], amt)
            if not res: res = fetch_from_off(it["item"], amt)
        
        if res:
            total["calories"] += res["calories"]
            total["protein"]  += res["protein"]
            total["fat"]      += res["fat"]
            total["carbs"]    += res["carbs"]
            sources.append(res["source_label"])
            
    return {
        "name": food_description[:50],
        "calories": total["calories"],
        "protein": round(total["protein"], 1),
        "fat": round(total["fat"], 1),
        "carbs": round(total["carbs"], 1),
        "sources_used": sources
    }

# ---------------------------------------------------------------
# RESZTA INTERFEJSU (UI)
# ---------------------------------------------------------------
def detect_bread(text: str) -> bool:
    return any(kw in text.lower() for kw in ["chleb własny", "chleb otręby", "chleb z otrębami"])

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
.stApp { background-color: #fdfaf5; color: #4a4a4a; font-family: 'Quicksand', sans-serif; }
.main-title { font-size: 3rem; font-weight: 700; color: #6b8e23; text-align: center; margin-top: -30px; }
.stat-box { background: white; border-radius: 15px; padding: 15px; text-align: center; box-shadow: 0 8px 16px rgba(0,0,0,0.05); }
.stat-value { font-size: 2rem; font-weight: 800; }
.meal-card { background: white; border-radius: 12px; padding: 12px; margin: 5px 0; display: flex; justify-content: space-between; border: 1px solid #f0ede9; }
.meal-stats { background: #f1f3eb; color: #6b8e23; padding: 4px 10px; border-radius: 8px; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🥑 Dziennik Makro</div>', unsafe_allow_html=True)

history = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]

# Statystyki górne
total_kcal = sum(m["calories"] for m in today_meals)
total_p = sum(m["protein"] for m in today_meals)
total_f = sum(m["fat"] for m in today_meals)
total_c = sum(m["carbs"] for m in today_meals)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="stat-box"><div class="stat-value">{total_kcal}</div><div>Kcal</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6b8e23">{total_p:.1f}g</div><div>Białko</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#bc6c25">{total_f:.1f}g</div><div>Tłuszcz</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#4299e1">{total_c:.1f}g</div><div>Węgle</div></div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Ustawienia")
    api_key = st.secrets.get("GROQ_API_KEY", "") or st.text_input("Klucz Groq", type="password")

# Formularz
with st.form("meal_form", clear_on_submit=True):
    f_in = st.text_input("Co zjadłaś?", placeholder="np. Jogurt Mlekovita 150g, 2 jajka...")
    m_time = st.selectbox("Pora", ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"])
    btn = st.form_submit_button("DODAJ")

if btn and f_in:
    with st.spinner("Szukam w bazach..."):
        try:
            if detect_bread(f_in):
                m_g = re.search(r"(\d+)\s*g", f_in.lower())
                g = int(m_g.group(1)) if m_g else 80
                res = {
                    "name": f"🍞 Chleb własny ({g}g)",
                    "calories": round(BREAD_VALS["kcal"] * g / 100),
                    "protein": round(BREAD_VALS["protein"] * g / 100, 1),
                    "fat": round(BREAD_VALS["fat"] * g / 100, 1),
                    "carbs": round(BREAD_VALS["carbs"] * g / 100, 1),
                    "time": m_time
                }
            else:
                data = get_nutrition_hybrid(f_in, api_key)
                res = {**data, "time": m_time}
            
            save_meal(res)
            st.cache_resource.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Coś poszło nie tak: {e}")

# Lista
if today_meals:
    for m in today_meals:
        c1, c2 = st.columns([9, 1])
        with c1:
            st.markdown(f'<div class="meal-card"><span>{m["name"]} ({m["time"]})</span><span class="meal-stats">{m["calories"]} kcal</span></div>', unsafe_allow_html=True)
        with c2:
            if st.button("🗑️", key=f"del_{m['_row']}"):
                delete_meal_by_row(m["_row"])
                st.cache_resource.clear()
                st.rerun()
