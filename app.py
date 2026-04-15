import streamlit as st
import json
import os
from datetime import date, datetime, timedelta

# --- Konfiguracja strony ---
st.set_page_config(page_title="Mój Dziennik Jedzenia", page_icon="🥑", layout="wide")

# --- Funkcje zapisu danych ---
DATA_FILE = "history_meals_v3.json"

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

# --- STYLIZACJA ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
.stApp { background-color: #fdfaf5; color: #4a4a4a; font-family: 'Quicksand', sans-serif; }

.main-title { font-size: 3rem; font-weight: 700; color: #6b8e23; text-align: center; }
.stat-box {
    background: white; border-radius: 15px; padding: 15px; text-align: center;
    box-shadow: 0 8px 16px rgba(139, 123, 108, 0.1); border-bottom: 4px solid #e0d7cd;
}
.stat-value { font-size: 2.2rem; font-weight: 800; line-height: 1; margin-bottom: 5px; }
.stat-label { font-size: 0.8rem; color: #a69080; text-transform: uppercase; font-weight: 700; }

.meal-card {
    background: white; border-radius: 12px; padding: 15px; margin: 8px 0;
    display: flex; justify-content: space-between; align-items: center; border: 1px solid #f0ede9;
}
.meal-stats { background: #f1f3eb; color: #6b8e23; padding: 5px 12px; border-radius: 10px; font-weight: 700; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# --- Logika AI i Chleba ---
BREAD_VALS = {"kcal": 211, "protein": 12, "fat": 5, "carbs": 25}

def detect_bread(text: str) -> bool:
    return any(kw in text.lower() for kw in ["chleb z otrębami", "chleb otręby", "chleb twarogowy", "chleb własny"])

def get_nutrition_groq(food_description: str, api_key: str) -> dict:
    import requests
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = f"""Oszacuj kalorie, białko, tłuszcze i węglowodany dla: {food_description}. 
    Zwróć TYLKO czysty JSON: {{"name": "...", "calories": 100, "protein": 10, "fat": 5, "carbs": 20}}"""
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    res_text = response.json()['choices'][0]['message']['content'].strip()
    start, end = res_text.find('{'), res_text.rfind('}') + 1
    return json.loads(res_text[start:end])

# --- UI ---
st.markdown('<div class="main-title">🥑 Dziennik Makro</div>', unsafe_allow_html=True)

history = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]

LIMIT_KCAL = 1500
total_kcal = sum(m["calories"] for m in today_meals)
total_p = sum(m.get("protein", 0) for m in today_meals)
total_f = sum(m.get("fat", 0) for m in today_meals)
total_c = sum(m.get("carbs", 0) for m in today_meals)

# PIĘĆ DUŻYCH STATYSTYK
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_kcal}</div><div class="stat-label">Kcal</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6b8e23">{total_p}g</div><div class="stat-label">Białko</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#bc6c25">{total_f}g</div><div class="stat-label">Tłuszcz</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#4299e1">{total_c}g</div><div class="stat-label">Węgle</div></div>', unsafe_allow_html=True)
with c5: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#a69080">{LIMIT_KCAL - total_kcal}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co zjedzone?")
    meal_time = st.selectbox("Pora", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("DODAJ")

if submitted and food_input:
    try:
        if detect_bread(food_input):
            import re
            m = re.search(r'(\d+)\s*g', food_input.lower())
            g = int(m.group(1)) if m else 80
            new_meal = {
                "name": f"🍞 Chleb własny ({g}g)",
                "calories": round(BREAD_VALS["kcal"] * g / 100),
                "protein": round(BREAD_VALS["protein"] * g / 100),
                "fat": round(BREAD_VALS["fat"] * g / 100),
                "carbs": round(BREAD_VALS["carbs"] * g / 100),
                "time": meal_time
            }
        else:
            api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Klucz", type="password")
            res = get_nutrition_groq(food_input, api_key)
            new_meal = {
                "name": res["name"],
                "calories": int(res["calories"]),
                "protein": int(res.get("protein", 0)),
                "fat": int(res.get("fat", 0)),
                "carbs": int(res.get("carbs", 0)),
                "time": meal_time
            }
        save_meal(new_meal)
        st.rerun()
    except Exception as e: st.error(f"Błąd: {e}")

# LISTA
for cat in ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"]:
    meals = [m for m in today_meals if m["time"] == cat]
    if meals:
        st.markdown(f"#### {cat}")
        for m in meals:
            c1, c2 = st.columns([6, 1])
            with c1: st.markdown(f'<div class="meal-card"><span>{m["name"]}</span><span class="meal-stats">{m["calories"]} kcal | B:{m["protein"]}g T:{m["fat"]}g W:{m["carbs"]}g</span></div>', unsafe_allow_html=True)
            with c2: 
                if st.button("🗑️", key=str(m.get("id"))):
                    delete_meal_from_file(m.get("id"))
                    st.rerun()
