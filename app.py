import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import requests
from datetime import date, datetime

# --- 1. KONFIGURACJA STRONY I CSS ---
st.set_page_config(page_title="Mój Dziennik 1500 kcal", page_icon="🥑", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
.stApp { background-color: #fdfaf5; color: #4a4a4a; font-family: 'Quicksand', sans-serif; }

.main-title { font-size: 3rem; font-weight: 700; color: #6b8e23; text-align: center; margin-top: -30px; }
.subtitle { text-align: center; color: #8c7b6c; font-size: 1.1rem; margin-bottom: 2rem; }

/* Kafelki statystyk */
.stat-box {
    background: white; border-radius: 20px; padding: 20px; text-align: center;
    box-shadow: 0 10px 20px rgba(139, 123, 108, 0.05); border-bottom: 5px solid #e0d7cd;
}
.stat-value { font-size: 2.8rem; font-weight: 800; line-height: 1; margin-bottom: 5px; }
.stat-label { font-size: 0.8rem; color: #a69080; text-transform: uppercase; font-weight: 700; }

/* Karty posiłków */
.meal-card {
    background: white; border-radius: 12px; padding: 12px 20px; margin: 8px 0;
    display: flex; justify-content: space-between; align-items: center; border: 1px solid #f0ede9;
}
.meal-info-name { font-weight: 700; color: #4a4a4a; font-size: 1.1rem; }
.meal-stats-label { background: #f1f3eb; color: #6b8e23; padding: 4px 10px; border-radius: 8px; font-weight: 700; font-size: 0.9rem; }

.section-header { color: #6b8e23; font-size: 1.5rem; font-weight: 700; margin-top: 25px; border-bottom: 2px solid #e9e2d8; }

/* Przycisk */
div.stButton > button:first-child {
    background-color: #d4a373; color: white; border-radius: 12px; font-weight: 700; border: none; width: 100%;
}
</style>
""", unsafe_allow_html=True)

# --- 2. FUNKCJE TECHNICZNE (GOOGLE & AI) ---

def connect_to_gsheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open("Dziennik Kalorii").sheet1

def get_polish_day():
    dni = {0: "Poniedziałek", 1: "Wtorek", 2: "Środa", 3: "Czwartek", 4: "Piątek", 5: "Sobota", 6: "Niedziela"}
    return dni[date.today().weekday()]

def get_nutrition_ai(food_desc, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = f"""Oszacuj kalorie, białko, tłuszcze i węgle dla: {food_desc}. 
    Zwróć TYLKO czysty JSON: {{"name": "...", "kcal": 100, "p": 10, "f": 5, "c": 20}}"""
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    res = requests.post(url, headers=headers, json=payload, timeout=15).json()
    content = res['choices'][0]['message']['content'].strip()
    return json.loads(content[content.find('{'):content.rfind('}')+1])

def delete_from_gsheets(meal_name, meal_time, meal_date):
    try:
        sheet = connect_to_gsheets()
        all_rows = sheet.get_all_values()
        for i, row in enumerate(all_rows):
            # Kolumny: 0:Dzień, 1:Data, 2:Pora, 3:Nazwa
            if row[1] == meal_date and row[2] == meal_time and row[3] == meal_name:
                sheet.delete_rows(i + 1)
                return True
        return False
    except Exception as e:
        st.error(f"Błąd usuwania: {e}")
        return False

# --- 3. LOGIKA I UI ---

st.markdown('<div class="main-title">🥑 Mój Dziennik</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Cel: 1500 kcal | Białko: >100g</div>', unsafe_allow_html=True)

# Pobieranie danych do statystyk
try:
    sheet = connect_to_gsheets()
    all_data = sheet.get_all_records()
    today_str = str(date.today())
    today_meals = [row for row in all_data if str(row.get('Data')) == today_str]
except Exception as e:
    st.sidebar.error("Błąd połączenia z Arkuszem Google")
    today_meals = []

# Obliczenia makro
LIMIT_KCAL = 1500
total_kcal = sum(int(row.get('Kalorie', 0)) for row in today_meals)
total_p = sum(int(row.get('Białko', 0)) for row in today_meals)
total_f = sum(int(row.get('Tłuszcz', 0)) for row in today_meals)
total_c = sum(int(row.get('Węgle', 0)) for row in today_meals)

# PANEL STATYSTYK (GÓRA)
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#8b7b6c">{total_kcal}</div><div class="stat-label">Kcal Zjedzone</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6b8e23">{LIMIT_KCAL - total_kcal}</div><div class="stat-label">Kcal Zostało</div></div>', unsafe_allow_html=True)
with c3: 
    p_color = "#6b8e23" if total_p >= 100 else "#bc6c25"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{p_color}">{total_p}g</div><div class="stat-label">Białko (Cel 100g)</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#a69080">{total_f}g / {total_c}g</div><div class="stat-label">Tłuszcz / Węgle</div></div>', unsafe_allow_html=True)

# FORMULARZ DODAWANIA
st.sidebar.markdown("### ⚙️ Ustawienia")
api_key = st.sidebar.text_input("Klucz Groq API", type="password")

with st.form("meal_form", clear_on_submit=True):
    f1, f2 = st.columns([3, 1])
    with f1: food_input = st.text_input("Co zjadłaś?", placeholder="np. 2 jajka i chleb własny 80g")
    with f2: meal_time = st.selectbox("Pora", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("DODAJ I ZAPISZ W ARKUSZU")

if submitted and food_input and api_key:
    try:
        with st.spinner("AI analizuje, Google zapisuje..."):
            data = get_nutrition_ai(food_input, api_key)
            new_row = [get_polish_day(), today_str, meal_time, data['name'], data['kcal'], data['p'], data['f'], data['c']]
            sheet.append_row(new_row)
            st.rerun()
    except Exception as e:
        st.error(f"Błąd: {e}")

# LISTA POSIŁKÓW DNIA Z PRZYCISKIEM USUWANIA
if today_meals:
    st.markdown('<div class="section-header">Dzisiejsze Menu</div>', unsafe_allow_html=True)
    for m in today_meals:
        col_info, col_del = st.columns([7, 1])
        with col_info:
            st.markdown(f"""
            <div class="meal-card">
                <span class="meal-info-name">{m['Nazwa']}</span>
                <span class="meal-stats-label">{m['Kalorie']} kcal | B:{m['Białko']}g T:{m['Tłuszcz']}g W:{m['Węgle']}g</span>
            </div>
            """, unsafe_allow_html=True)
        with col_del:
            # Usuwanie po nazwie, porze i dacie
            if st.button("🗑️", key=f"del_{m['Nazwa']}_{m['Pora']}"):
                with st.spinner("Usuwanie..."):
                    if delete_from_gsheets(m['Nazwa'], m['Pora'], today_str):
                        st.rerun()

# WYKRES TYGODNIOWY
if all_data:
    st.markdown('<div class="section-header">Podsumowanie Tygodnia</div>', unsafe_allow_html=True)
    df = pd.DataFrame(all_data)
    # Grupowanie ostatnich 7 dni
    last_7 = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        day_sum = sum(int(row.get('Kalorie', 0)) for row in all_data if str(row.get('Data')) == d)
        last_7.append({"Dzień": d[-5:], "Kcal": day_sum})
    
    chart_df = pd.DataFrame(last_7)
    st.bar_chart(data=chart_df, x="Dzień", y="Kcal")
