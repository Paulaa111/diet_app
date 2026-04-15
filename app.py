import streamlit as st
import json
import os
from datetime import date, datetime, timedelta

# --- Konfiguracja strony ---
st.set_page_config(
    page_title="Mój Dziennik Jedzenia",
    page_icon="🥑",
    layout="centered",
)

# --- Funkcje zapisu danych (TRWAŁOŚĆ) ---
DATA_FILE = "history_meals.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_meal(meal_dict):
    history = load_data()
    meal_dict["date"] = str(date.today())
    # Dodajemy unikalny ID, żeby łatwiej było usuwać
    meal_dict["id"] = datetime.now().timestamp()
    history.append(meal_dict)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def delete_meal_from_file(meal_id):
    history = load_data()
    history = [m for m in history if m.get("id") != meal_id]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

# --- STYLIZACJA (DUŻE LICZBY I ORYGINALNY TYTUŁ) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');

.stApp { background-color: #fdfaf5; color: #4a4a4a; font-family: 'Quicksand', sans-serif; }

/* PRZYWRÓCONY WIELKI TYTUŁ */
.main-title {
    font-size: 3rem;
    font-weight: 700;
    color: #6b8e23;
    text-align: center;
    margin-bottom: 0.2rem;
}

.subtitle {
    text-align: center;
    color: #8c7b6c;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}

/* POWIĘKSZONE STATYSTYKI */
.stat-box {
    background: white;
    border-radius: 20px;
    padding: 25px;
    text-align: center;
    box-shadow: 0 10px 20px rgba(139, 123, 108, 0.1);
    border-bottom: 5px solid #e0d7cd;
}

.stat-value {
    font-size: 3rem; /* POWRÓT DO DUŻEGO ROZMIARU */
    font-weight: 800;
    line-height: 1;
    margin-bottom: 5px;
}

.stat-label {
    font-size: 0.9rem;
    color: #a69080;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 1px;
}

.meal-card {
    background: white;
    border-radius: 12px;
    padding: 15px;
    margin: 10px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid #f0ede9;
}

.section-header {
    color: #6b8e23;
    font-size: 1.4rem;
    font-weight: 700;
    margin-top: 30px;
    border-bottom: 2px solid #e9e2d8;
}

.meal-kcal { 
    background: #f1f3eb;
    color: #6b8e23;
    padding: 5px 12px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 1.1rem;
}

div.stButton > button:first-child {
    background-color: #d4a373;
    color: white;
    border-radius: 12px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Logika AI i Chleba
# ---------------------------------------------------------------
BREAD_KCAL_PER_100G = 211
BREAD_KEYWORDS = ["chleb z otrębami", "chleb otręby", "chleb twarogowy", "chleb własny", "mój chleb", "chleb z twarogiem"]

def detect_bread(text: str) -> bool:
    return any(kw in text.lower() for kw in BREAD_KEYWORDS)

def parse_bread_grams(text: str) -> int:
    import re
    t = text.lower()
    m = re.search(r'(\d+)\s*g', t)
    if m: return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:kromk|plaster)', t)
    if m: return int(m.group(1)) * 80
    return 80

def get_calories_groq(food_description: str, api_key: str) -> dict:
    import requests
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = f"Oszacuj kalorie dla: {food_description}. Zwróć TYLKO JSON: {{\"name\": \"...\", \"calories\": 100}}"
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
st.markdown('<div class="subtitle">Zdrowy styl życia krok po kroku</div>', unsafe_allow_html=True)

# Załaduj historię
history = load_data()
today_str = str(date.today())
today_meals = [m for m in history if m["date"] == today_str]

# NOWY LIMIT: 1500 kcal
LIMIT = 1500 
total_today = sum(m["calories"] for m in today_meals)
remaining = LIMIT - total_today

# DUŻE STATYSTYKI
col1, col2, col3 = st.columns(3)
with col1: 
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#8b7b6c">{total_today}</div><div class="stat-label">Zjedzono</div></div>', unsafe_allow_html=True)
with col2: 
    color = "#6b8e23" if remaining >= 0 else "#bc6c25"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{remaining}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)
with col3: 
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#a69080">{LIMIT}</div><div class="stat-label">Limit</div></div>', unsafe_allow_html=True)

st.write("")

# Formularz
with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    if "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("✅ Klucz aktywny")
    else:
        api_key = st.text_input("Klucz Groq API", type="password")

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co dobrego zjadłaś?", placeholder="np. jajecznica z 3 jaj...")
    meal_time = st.selectbox("Pora posiłku", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("DODAJ DO DZIENNIKA", use_container_width=True)

if submitted and food_input.strip():
    txt = food_input.strip()
    try:
        if detect_bread(txt):
            g = parse_bread_grams(txt)
            kcal = round(BREAD_KCAL_PER_100G * g / 100)
            new_meal = {"name": f"🍞 Chleb własny ({g}g)", "calories": kcal, "time": meal_time}
        else:
            res = get_calories_groq(txt, api_key)
            new_meal = {"name": res["name"], "calories": int(res["calories"]), "time": meal_time}
        
        save_meal(new_meal)
        st.rerun()
    except Exception as e:
        st.error(f"Problem: {e}")

# --- LISTA POSIŁKÓW DNIA ---
if today_meals:
    st.markdown("### 📋 Dzisiejszy jadłospis")
    categories = ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"]
    for cat in categories:
        cat_meals = [m for m in today_meals if m["time"] == cat]
        if cat_meals:
            st.markdown(f'<div class="section-header">{cat}</div>', unsafe_allow_html=True)
            for m in cat_meals:
                col_m, col_d = st.columns([6, 1])
                with col_m:
                    st.markdown(f'<div class="meal-card"><span class="meal-name">{m["name"]}</span><span class="meal-kcal">{m["calories"]} kcal</span></div>', unsafe_allow_html=True)
                with col_d:
                    if st.button("🗑️", key=f"del_{m.get('id')}"):
                        delete_meal_from_file(m.get('id'))
                        st.rerun()

# --- PODSUMOWANIE TYGODNIA ---
st.write("---")
st.markdown("### 📊 Podsumowanie tygodnia")
if history:
    # Grupowanie ostatnich 7 dni
    week_data = {}
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i))
        d_str = str(d)
        day_sum = sum(m["calories"] for m in history if m["date"] == d_str)
        # Formatowanie daty na wykresie (np. 15.04)
        week_data[d.strftime("%d.%m")] = day_sum
    
    st.bar_chart(week_data)
