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
    font-size: 2.8rem;
    color: #f5c518;
    text-align: center;
    margin-bottom: 0.2rem;
    text-shadow: 0 0 30px rgba(245,197,24,0.3);
}
.subtitle {
    text-align: center;
    color: #a0aec0;
    font-size: 0.95rem;
    margin-bottom: 2rem;
    letter-spacing: 0.05em;
}
.meal-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(245,197,24,0.2);
    border-radius: 12px;
    padding: 10px 15px;
    margin: 5px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.meal-name { color: #e2e8f0; font-size: 0.9rem; }
.meal-kcal { color: #f5c518; font-size: 1rem; font-weight: 500; }
.section-header {
    color: #f5c518;
    border-bottom: 1px solid rgba(245,197,24,0.3);
    padding-bottom: 5px;
    margin-top: 20px;
    margin-bottom: 10px;
}
.stat-box {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 18px;
    text-align: center;
}
.stat-value { font-size: 2rem; font-weight: 700; font-family: 'Playfair Display', serif; }
.stat-label { font-size: 0.78rem; color: #718096; letter-spacing: 0.08em; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Wbudowany własny chleb
# ---------------------------------------------------------------
BREAD_KCAL_PER_100G = 211
BREAD_KEYWORDS = ["chleb z otrębami", "chleb otręby", "chleb twarogowy", "chleb własny", "mój chleb", "chleb z twarogiem"]

def detect_bread(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in BREAD_KEYWORDS)

def parse_bread_grams(text: str) -> int:
    import re
    t = text.lower()
    m = re.search(r'(\d+)\s*g(?:ram)?', t)
    if m: return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:kromk[aięi]|kromki)', t)
    if m: return int(m.group(1)) * 80
    return 80

# ---------------------------------------------------------------
# API Groq
# ---------------------------------------------------------------
def get_calories_groq(food_description: str, api_key: str) -> dict:
    import requests
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = f"""Jesteś ekspertem od dietetyki. Użytkownik napisał: "{food_description}".
    Oszacuj kalorie i podaj dane w formacie JSON:
    {{
      "name": "Nazwa dania po polsku",
      "calories": 100,
      "note": "Krótka uwaga"
    }}
    Zwróć TYLKO czysty JSON."""
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    data = response.json()
    res_text = data['choices'][0]['message']['content'].strip()
    start = res_text.find('{')
    end = res_text.rfind('}') + 1
    return json.loads(res_text[start:end])

# ---------------------------------------------------------------
# Sesja i logika
# ---------------------------------------------------------------
if "meals" not in st.session_state:
    st.session_state.meals = []
if "daily_date" not in st.session_state:
    st.session_state.daily_date = date.today()

LIMIT = 2000

# --- Sidebar (POPRAWIONY) ---
with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    if "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("✅ Klucz Groq aktywny")
    else:
        api_key = st.text_input("Klucz Groq API", type="password")

# --- UI Główne ---
st.markdown('<div class="main-title">🍽️ Licznik Kalorii</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Wpisz co zjadłeś — podzielone na posiłki</div>', unsafe_allow_html=True)

# Statystyki
total = sum(m["calories"] for m in st.session_state.meals)
remaining = LIMIT - total

col1, col2, col3 = st.columns(3)
with col1: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#f5c518">{total}</div><div class="stat-label">Spożyte</div></div>', unsafe_allow_html=True)
with col2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#48bb78">{remaining}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)
with col3: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#a0aec0">{LIMIT}</div><div class="stat-label">Limit</div></div>', unsafe_allow_html=True)

# Formularz dodawania
with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co zjadłeś/aś?", placeholder="np. jajecznica, banan...")
    meal_time = st.selectbox("Pora posiłku", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("➕ Dodaj do listy", use_container_width=True)

if submitted and food_input.strip():
    if detect_bread(food_input):
        grams = parse_bread_grams(food_input)
        kcal = round(BREAD_KCAL_PER_100G * grams / 100)
        st.session_state.meals.append({"name": f"🍞 Chleb własny ({grams}g)", "calories": kcal, "time": meal_time})
        st.rerun()
    elif api_key:
        with st.spinner("Liczenie..."):
            try:
                res = get_calories_groq(food_input, api_key)
                st.session_state.meals.append({"name": res["name"], "calories": int(res["calories"]), "time": meal_time})
                st.rerun()
            except Exception as e:
