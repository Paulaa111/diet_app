import streamlit as st
import json
import os
from datetime import date, datetime, timedelta

# --- Konfiguracja strony ---
st.set_page_config(page_title="Mój Dziennik Jedzenia", page_icon="🥑", layout="wide")

# --- Funkcje zapisu danych ---
DATA_FILE = "history_meals_v2.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_meal(meal_dict):
    history = load_data()
    meal_dict["date"] = str(date.today())
    meal_dict["id"] = datetime.now().timestamp()
    history.append(meal_dict)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def delete_meal_from_file(meal_id):
    history = load_data()
    history = [m for m in history if m.get("id") != meal_id]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

# --- STYLIZACJA (DUŻE LICZBY I CIEPŁE KOLORY) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
.stApp { background-color: #fdfaf5; color: #4a4a4a; font-family: 'Quicksand', sans-serif; }

.main-title { font-size: 3.5rem; font-weight: 700; color: #6b8e23; text-align: center; margin-bottom: 0.2rem; }
.subtitle { text-align: center; color: #8c7b6c; font-size: 1.2rem; margin-bottom: 2rem; }

.stat-box {
    background: white; border-radius: 20px; padding: 20px; text-align: center;
    box-shadow: 0 10px 20px rgba(139, 123, 108, 0.1); border-bottom: 5px solid #e0d7cd;
}
.stat-value { font-size: 3.2rem; font-weight: 800; line-height: 1; margin-bottom: 5px; }
.stat-label { font-size: 0.9rem; color: #a69080; text-transform: uppercase; font-weight: 700; }

.meal-card {
    background: white; border-radius: 12px; padding: 15px; margin: 10px 0;
    display: flex; justify-content: space-between; align-items: center; border: 1px solid #f0ede9;
}
.section-header { color: #6b8e23; font-size: 1.5rem; font-weight: 700; margin-top: 30px; border-bottom: 2px solid #e9e2d8; }
.meal-info { font-weight: 600; font-size: 1.1rem; }
.meal-stats { background: #f1f3eb; color: #6b8e23; padding: 5px 12px; border-radius: 10px; font-weight: 700; }

div.stButton > button:first-child { background-color: #d4a373; color: white; border-radius: 12px; font-weight: 700; height: 3em; }
</style>
""", unsafe_allow_html=True)

# --- Logika AI i Chleba ---
BREAD_KCAL_PER_100G = 211
BREAD_PROTEIN_PER_100G = 12 # Twój chleb ma dużo białka!

def detect_bread(text: str) -> bool:
    keywords = ["chleb z otrębami", "chleb otręby", "chleb twarogowy", "chleb własny", "mój chleb"]
    return any(kw in text.lower() for kw in keywords)

def parse_bread_grams(text: str) -> int:
    import re
    m = re.search(r'(\d+)\s*g', text.lower())
    if m: return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:kromk|plaster)', text.lower())
    if m: return int(m.group(1)) * 80
    return 80

def get_nutrition_groq(food_description: str, api_key: str) -> dict:
    import requests
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = f"""Oszacuj kalorie i białko dla: {food_description}. 
    Zwróć TYLKO czysty JSON: {{"name": "nazwa", "calories": 100, "protein": 10}}"""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    res_text = response.json()['choices'][0]['message']['content'].strip()
    start, end = res_text.find('{'), res_text.rfind('}') + 1
    return json.loads(res_text[start:end])

# --- UI GŁÓWNE ---
st.markdown('<div class="main-title">🥑 Mój Dziennik</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Cel: 1500 kcal | Białko: >100g</div>', unsafe_allow_html=True)

history = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]

LIMIT_KCAL = 1500
GOAL_PROTEIN = 100

total_today_kcal = sum(m["calories"] for m in today_meals)
total_today_protein = sum(m.get("protein", 0) for m in today_meals)
remaining_kcal = LIMIT_KCAL - total_today_kcal

# CZTERY DUŻE STATYSTYKI
col1, col2, col3, col4 = st.columns(4)
with col1: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#8b7b6c">{total_today_kcal}</div><div class="stat-label">Kcal Zjedzone</div></div>', unsafe_allow_html=True)
with col2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6b8e23">{remaining_kcal}</div><div class="stat-label">Kcal Zostało</div></div>', unsafe_allow_html=True)
with col3: 
    p_color = "#6b8e23" if total_today_protein >= GOAL_PROTEIN else "#bc6c25"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{p_color}">{total_today_protein}g</div><div class="stat-label">Białko</div></div>', unsafe_allow_html=True)
with col4: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#a69080">{LIMIT_KCAL}</div><div class="stat-label">Limit Kcal</div></div>', unsafe_allow_html=True)

# Formularz
with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Klucz Groq API", type="password")

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co dziś jemy?", placeholder="np. 2 jajka i chleb z otrębami...")
    meal_time = st.selectbox("Pora posiłku", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

if submitted and food_input.strip():
    txt = food_input.strip()
    try:
        if detect_bread(txt):
            g = parse_bread_grams(txt)
            kcal = round(BREAD_KCAL_PER_100G * g / 100)
            prot = round(BREAD_PROTEIN_PER_100G * g / 100)
            new_meal = {"name": f"🍞 Chleb własny ({g}g)", "calories": kcal, "protein": prot, "time": meal_time}
        else:
            res = get_nutrition_groq(txt, api_key)
            new_meal = {"name": res["name"], "calories": int(res["calories"]), "protein": int(res.get("protein", 0)), "time": meal_time}
        
        save_meal(new_meal)
        st.rerun()
    except Exception as e: st.error(f"Błąd: {e}")

# --- LISTA POSIŁKÓW ---
if today_meals:
    st.markdown("### 📋 Dzisiejsze menu")
    for cat in ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"]:
        cat_meals = [m for m in today_meals if m["time"] == cat]
        if cat_meals:
            st.markdown(f'<div class="section-header">{cat}</div>', unsafe_allow_html=True)
            for m in cat_meals:
                c1, c2 = st.columns([6, 1])
                with c1: st.markdown(f'<div class="meal-card"><span class="meal-info">{m["name"]}</span><span class="meal-stats">{m["calories"]} kcal | {m.get("protein", 0)}g B</span></div>', unsafe_allow_html=True)
                with c2: 
                    if st.button("🗑️", key=str(m.get("id"))):
                        delete_meal_from_file(m.get("id"))
                        st.rerun()

# --- WYKRES TYGODNIOWY ---
st.write("---")
st.markdown("### 📊 Kalorie w ostatnim tygodniu")
if history:
    week_data = {}
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i))
        week_data[d.strftime("%d.%m")] = sum(m["calories"] for m in history if m["date"] == str(d))
    st.bar_chart(week_data)
