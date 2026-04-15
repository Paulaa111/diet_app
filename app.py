import streamlit as st
import json
from datetime import date

# --- Konfiguracja strony ---
st.set_page_config(
    page_title="Licznik Kalorii",
    page_icon="🍽️",
    layout="centered",
)

# --- Style CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1, h2, h3 { font-family: 'Playfair Display', serif; }
.stApp {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    min-height: 100vh;
}
.main-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.8rem; color: #f5c518; text-align: center;
    margin-bottom: 0.2rem; text-shadow: 0 0 30px rgba(245,197,24,0.3);
}
.subtitle {
    text-align: center; color: #a0aec0; font-size: 0.95rem;
    margin-bottom: 2rem; letter-spacing: 0.05em;
}
.meal-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(245,197,24,0.2);
    border-radius: 12px; padding: 10px 15px; margin: 5px 0;
    display: flex; justify-content: space-between; align-items: center;
}
.section-header {
    color: #f5c518; border-bottom: 1px solid rgba(245,197,24,0.3);
    padding-bottom: 5px; margin-top: 20px; margin-bottom: 10px; font-weight: bold;
}
.stat-box {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px; padding: 18px; text-align: center;
}
.stat-value { font-size: 2rem; font-weight: 700; font-family: 'Playfair Display', serif; }
.stat-label { font-size: 0.78rem; color: #718096; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- Logika Chleba ---
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

# --- UI ---
st.markdown('<div class="main-title">🍽️ Licznik Kalorii</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Wpisz co zjadłeś — podzielone na posiłki</div>', unsafe_allow_html=True)

total = sum(m["calories"] for m in st.session_state.meals)
remaining = LIMIT - total

col1, col2, col3 = st.columns(3)
with col1: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#f5c518">{total}</div><div class="stat-label">Spożyte</div></div>', unsafe_allow_html=True)
with col2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#48bb78">{remaining}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)
with col3: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#a0aec0">{LIMIT}</div><div class="stat-label">Limit</div></div>', unsafe_allow_html=True)

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co zjadłeś/aś?")
    meal_time = st.selectbox("Pora posiłku", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("➕ Dodaj", use_container_width=True)

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
        st.error(f"Błąd: {e}")

# --- WYŚWIETLANIE LISTY (Tego brakowało!) ---
if st.session_state.meals:
    st.markdown("### 📋 Twoje menu")
    categories = ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"]
    for cat in categories:
        cat_meals = [m for m in st.session_state.meals if m["time"] == cat]
        if cat_meals:
            st.markdown(f'<div class="section-header">{cat}</div>', unsafe_allow_html=True)
            for i, m in enumerate(st.session_state.meals):
                if m["time"] == cat:
                    st.markdown(f'<div class="meal-card"><span>{m["name"]}</span><span style="color:#f5c518">{m["calories"]} kcal</span></div>', unsafe_allow_html=True)
    
    if st.button("🗑️ Wyczyść dzień"):
        st.session_state.meals = []
        st.rerun()
