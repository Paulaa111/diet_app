import streamlit as st
import json
import os
from datetime import date, datetime, timedelta

# --- Konfiguracja strony ---
st.set_page_config(page_title="Mój Dziennik Jedzenia", page_icon="🥑", layout="centered")

# --- Funkcje zapisu danych (TRWAŁOŚĆ) ---
DATA_FILE = "meals_history.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_meal(meal_dict):
    history = load_data()
    # Dodajemy aktualną datę do posiłku
    meal_dict["date"] = str(date.today())
    history.append(meal_dict)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

# --- Style CSS (Organic Style) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
.stApp { background-color: #fdfaf5; color: #4a4a4a; font-family: 'Quicksand', sans-serif; }
.main-title { font-size: 2.5rem; font-weight: 700; color: #6b8e23; text-align: center; }
.stat-box { background: white; border-radius: 15px; padding: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }
.meal-card { background: white; border-radius: 10px; padding: 10px 15px; margin: 5px 0; display: flex; justify-content: space-between; border-left: 5px solid #6b8e23; }
</style>
""", unsafe_allow_html=True)

# --- Logika AI i Chleba ---
# (Tutaj pozostają Twoje funkcje: detect_bread, parse_bread_grams, get_calories_groq)
# [Dla zwięzłości pomijam definicje tych funkcji, ale one muszą zostać w kodzie]

# --- UI GŁÓWNE ---
st.markdown('<div class="main-title">🥑 Dziennik & Podsumowanie</div>', unsafe_allow_html=True)

# Pobieramy dane z pliku
history = load_data()
today_str = str(date.today())
today_meals = [m for m in history if m["date"] == today_str]

# Statystyki dnia
LIMIT = 2000
total_today = sum(m["calories"] for m in today_meals)
remaining = LIMIT - total_today

col1, col2, col3 = st.columns(3)
with col1: st.markdown(f'<div class="stat-box"><b>{total_today}</b><br><small>Dzisiaj</small></div>', unsafe_allow_html=True)
with col2: st.markdown(f'<div class="stat-box"><b style="color:#6b8e23">{remaining}</b><br><small>Zostało</small></div>', unsafe_allow_html=True)
with col3: 
    # Podsumowanie tygodnia (proste liczenie)
    last_7_days = [datetime.now().date() - timedelta(days=i) for i in range(7)]
    week_total = sum(m["calories"] for m in history if datetime.strptime(m["date"], "%Y-%m-%d").date() in last_7_days)
    st.markdown(f'<div class="stat-box"><b>{week_total}</b><br><small>Ostatnie 7 dni</small></div>', unsafe_allow_html=True)

# Formularz
with st.sidebar:
    st.header("⚙️ Ustawienia")
    # (Tutaj Twój kod do API Key)
    api_key = st.secrets.get("GROQ_API_KEY") or st.text_input("Klucz Groq", type="password")

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co zjadłaś?")
    meal_time = st.selectbox("Pora", ["Śniadanie", "Obiad", "Kolacja", "Inne"])
    submitted = st.form_submit_button("DODAJ")

if submitted and food_input:
    # ... Logika sprawdzania chleba lub AI ...
    # Wynik zapisujemy do 'new_meal'
    # PRZYKŁAD: 
    # new_meal = {"name": "Test", "calories": 200, "time": meal_time}
    
    # ZAPISUJEMY TRWALE:
    # save_meal(new_meal)
    # st.rerun()
    pass # (Tutaj wstaw swoją pełną logikę z poprzedniego kroku)

# --- SEKCJA PODSUMOWANIA TYGODNIA ---
st.markdown("### 📊 Podsumowanie tygodnia")
if history:
    # Grupowanie danych po dacie
    days_data = {}
    for i in range(6, -1, -1):
        day = (date.today() - timedelta(days=i)).isoformat()
        days_data[day] = sum(m["calories"] for m in history if m["date"] == day)
    
    # Wyświetlenie prostego wykresu Streamlit
    st.bar_chart(days_data)
    
    with st.expander("Zobacz historię wszystkich dni"):
        st.table(history)
