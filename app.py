import streamlit as st
import json
from datetime import date

# --- Konfiguracja strony ---
st.set_page_config(
    page_title="Mój Dziennik Jedzenia",
    page_icon="🥑",
    layout="centered",
)

# --- STYL ORGANICZNY (Ciepłe beże, zieleń szałwiowa) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');

/* Tło w kolorze ciepłego piasku/kremu */
.stApp {
    background-color: #fdfaf5;
    color: #4a4a4a;
}

/* Czcionka bardziej zaokrąglona i przyjazna */
html, body, [class*="css"] { font-family: 'Quicksand', sans-serif; }

/* Nagłówek w kolorze oliwkowym/szałwiowym */
.main-title {
    font-size: 2.8rem;
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

/* Statystyki - ciepłe, papierowe karty */
.stat-box {
    background: #ffffff;
    border-radius: 15px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(139, 123, 108, 0.1);
    border-bottom: 4px solid #e0d7cd;
}

.stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: #8b7b6c;
}

.stat-label {
    font-size: 0.8rem;
    color: #a69080;
    text-transform: uppercase;
    font-weight: 600;
}

/* Posiłki - zielone akcenty */
.section-header {
    color: #6b8e23;
    font-size: 1.3rem;
    font-weight: 700;
    margin-top: 30px;
    border-bottom: 2px solid #e9e2d8;
    padding-bottom: 5px;
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

.meal-name { color: #5d5d5d; font-weight: 600; }
.meal-kcal { 
    background: #f1f3eb;
    color: #6b8e23;
    padding: 4px 10px;
    border-radius: 8px;
    font-weight: 700;
}

/* Przyciski - terakota / ciepły brąz */
div.stButton > button:first-child {
    background-color: #d4a373;
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px;
    font-weight: 700;
    transition: all 0.3s;
}

div.stButton > button:first-child:hover {
    background-color: #bc8a5f;
    transform: scale(1.02);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #f7f3ed;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Logika Chleba
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

# --- API Groq ---
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

# --- Sesja ---
if "meals" not in st.session_state:
    st.session_state.meals = []

LIMIT = 1500

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    if "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("✅ Klucz aktywny")
    else:
        api_key = st.text_input("Klucz Groq API", type="password")

# --- UI GŁÓWNE ---
st.markdown('<div class="main-title">🥑 Mój Dziennik</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Zdrowy styl życia krok po kroku</div>', unsafe_allow_html=True)

total = sum(m["calories"] for m in st.session_state.meals)
remaining = LIMIT - total

col1, col2, col3 = st.columns(3)
with col1: st.markdown(f'<div class="stat-box"><div class="stat-value">{total}</div><div class="stat-label">Zjedzono</div></div>', unsafe_allow_html=True)
with col2: 
    color = "#6b8e23" if remaining >= 0 else "#bc6c25"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{remaining}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)
with col3: st.markdown(f'<div class="stat-box"><div class="stat-value">{LIMIT}</div><div class="stat-label">Cel</div></div>', unsafe_allow_html=True)

st.write("")

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co dobrego zjadłaś?", placeholder="np. sałatka z fetą...")
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
        
        st.session_state.meals.append(new_meal)
        st.rerun()
    except Exception as e:
        st.error(f"Mały problem: {e}")

# --- LISTA POSIŁKÓW ---
if st.session_state.meals:
    categories = ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"]
    for cat in categories:
        cat_meals = [m for m in st.session_state.meals if m["time"] == cat]
        if cat_meals:
            st.markdown(f'<div class="section-header">{cat}</div>', unsafe_allow_html=True)
            for m in cat_meals:
                st.markdown(f'<div class="meal-card"><span class="meal-name">{m["name"]}</span><span class="meal-kcal">{m["calories"]} kcal</span></div>', unsafe_allow_html=True)
    
    st.write("")
    if st.button("Zacznij nowy dzień"):
        st.session_state.meals = []
        st.rerun()
