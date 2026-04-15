import streamlit as st
import json
from datetime import date

# --- Konfiguracja strony ---
st.set_page_config(
    page_title="Licznik Kalorii",
    page_icon="🍏",
    layout="centered",
)

# --- NOWOCZESNY JASNY CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Plus+Jakarta+Sans:wght@700&display=swap');

/* Główny background - jasny, świeży gradient */
.stApp {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    color: #2d3748;
}

/* Czcionki */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Plus Jakarta Sans', sans-serif; }

/* Tytuł */
.main-title {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(90deg, #2b6cb0, #4299e1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 0.5rem;
}

.subtitle {
    text-align: center;
    color: #718096;
    font-size: 1rem;
    margin-bottom: 2.5rem;
}

/* Karty Statystyk - Glassmorphism */
.stat-box {
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 20px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 10px 25px rgba(0,0,0,0.05);
}

.stat-value {
    font-size: 2.2rem;
    font-weight: 800;
    color: #2b6cb0;
}

.stat-label {
    font-size: 0.75rem;
    color: #a0aec0;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 5px;
}

/* Posiłki */
.section-header {
    color: #2d3748;
    font-size: 1.2rem;
    font-weight: 700;
    margin-top: 25px;
    padding-left: 5px;
    border-left: 4px solid #4299e1;
    margin-bottom: 10px;
}

.meal-card {
    background: white;
    border-radius: 15px;
    padding: 12px 20px;
    margin: 8px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    transition: transform 0.2s;
}

.meal-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.05);
}

.meal-name { color: #4a5568; font-weight: 500; }
.meal-kcal { color: #2b6cb0; font-weight: 700; }

/* Przycisk formy */
div.stButton > button:first-child {
    background: linear-gradient(90deg, #4299e1, #3182ce);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 10px 20px;
    font-weight: 600;
    box-shadow: 0 4px 15px rgba(66, 153, 225, 0.3);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: white;
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

LIMIT = 2000

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    if "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("✅ Klucz aktywny")
    else:
        api_key = st.text_input("Klucz Groq API", type="password")

# --- UI GŁÓWNE ---
st.markdown('<div class="main-title">🍏 Mój Licznik</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Lekkie i nowoczesne śledzenie kalorii</div>', unsafe_allow_html=True)

total = sum(m["calories"] for m in st.session_state.meals)
remaining = LIMIT - total

col1, col2, col3 = st.columns(3)
with col1: st.markdown(f'<div class="stat-box"><div class="stat-value">{total}</div><div class="stat-label">Spożyte</div></div>', unsafe_allow_html=True)
with col2: 
    color = "#48bb78" if remaining >= 0 else "#f56565"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{remaining}</div><div class="stat-label">Pozostało</div></div>', unsafe_allow_html=True)
with col3: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#718096">{LIMIT}</div><div class="stat-label">Limit</div></div>', unsafe_allow_html=True)

st.write("") # Odstęp

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co dziś jemy?", placeholder="Wpisz posiłek...")
    meal_time = st.selectbox("Pora dnia", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

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
        st.error(f"Coś poszło nie tak: {e}")

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
    if st.button("Wyczyść dzisiejsze menu"):
        st.session_state.meals = []
        st.rerun()
