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
    padding: 14px 18px;
    margin: 8px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.meal-name { color: #e2e8f0; font-size: 0.95rem; }
.meal-kcal { color: #f5c518; font-size: 1.05rem; font-weight: 500; }
.progress-container {
    background: rgba(255,255,255,0.08);
    border-radius: 50px;
    height: 18px;
    overflow: hidden;
    margin: 12px 0 6px 0;
    box-shadow: inset 0 2px 6px rgba(0,0,0,0.3);
}
.progress-bar { height: 100%; border-radius: 50px; }
.stat-box {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 18px;
    text-align: center;
}
.stat-value { font-size: 2rem; font-weight: 700; font-family: 'Playfair Display', serif; }
.stat-label { font-size: 0.78rem; color: #718096; letter-spacing: 0.08em; text-transform: uppercase; margin-top: 4px; }
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
    m = re.search(r'(\d+)\s*(?:plasterek|plasterki|plasterków)', t)
    if m: return int(m.group(1)) * 40
    return 80  # domyślnie 1 kromka

# ---------------------------------------------------------------
# Groq API (Zamiast Gemini)
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
    Zwróć tylko i wyłącznie czysty JSON."""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    response = requests.post(url, headers=headers, json=payload, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Błąd Groq ({response.status_code}): {response.text}")

    data = response.json()
    res_text = data['choices'][0]['message']['content'].strip()
    start = res_text.find('{')
    end = res_text.rfind('}') + 1
    return json.loads(res_text[start:end])

# ---------------------------------------------------------------
# Sesja
# ---------------------------------------------------------------
if "meals" not in st.session_state:
    st.session_state.meals = []
if "daily_date" not in st.session_state:
    st.session_state.daily_date = date.today()

if st.session_state.daily_date != date.today():
    st.session_state.meals = []
    st.session_state.daily_date = date.today()

LIMIT = 2000

# ---------------------------------------------------------------
# UI
# ---------------------------------------------------------------
st.markdown('<div class="main-title">🍽️ Licznik Kalorii</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Wpisz co zjadłeś — Groq AI policzy resztę</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    if "GROQ_API_KEY" in st.secrets:
        api_key = st.secrets["GROQ_API_KEY"]
        st.success("✅ Klucz Groq wczytany")
    else:
        api_key = st.text_input("Klucz Groq API", type="password", placeholder="gsk_...")

# Statystyki
total = sum(m["calories"] for m in st.session_state.meals)
remaining = LIMIT - total
pct = min(total / LIMIT, 1.0)
bar_color = "#48bb78" if pct < 0.5 else ("#ed8936" if pct < 0.8 else "#fc5c65")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#f5c518">{total}</div><div class="stat-label">Spożyte kcal</div></div>', unsafe_allow_html=True)
with col2:
    color = "#48bb78" if remaining >= 0 else "#fc5c65"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{abs(remaining)}</div><div class="stat-label">{"Pozostało" if remaining >= 0 else "Przekroczono"}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#a0aec0">{LIMIT}</div><div class="stat-label">Limit kcal</div></div>', unsafe_allow_html=True)

st.markdown(f'<div class="progress-container"><div class="progress-bar" style="width:{pct*100}%; background:{bar_color};"></div></div>', unsafe_allow_html=True)

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co zjadłeś/aś?", placeholder="np. jajecznica z 3 jaj, masło, 2 kromki chleba...")
    submitted = st.form_submit_button("➕ Dodaj posiłek", use_container_width=True)

if submitted and food_input.strip():
    text = food_input.strip()
    if detect_bread(text):
        grams = parse_bread_grams(text)
        kcal = round(BREAD_KCAL_PER_100G * grams / 100)
        st.session_state.meals.append({"name": f"🍞 Chleb własny ({grams}g)", "calories": kcal})
        st.rerun()
    elif not api_key:
        st.warning("⚠️ Brak klucza Groq API!")
    else:
        with st.spinner("🤔 Groq liczy kalorie..."):
            try:
                result = get_calories_groq(text, api_key)
                st.session_state.meals.append({"name": result["name"], "calories": int(result["calories"])})
                st.rerun()
            except Exception as e:
                st.error(f"Błąd: {e}")

# Lista posiłków
if st.session_state.meals:
    for i, meal in enumerate(st.session_state.meals):
        c1, c2 = st.columns([6, 1])
        with c1: st.markdown(f'<div class="meal-card"><span>🍴 {meal["name"]}</span><span style="color:#f5c518">{meal["calories"]} kcal</span></div>', unsafe_allow_html=True)
        with c2: 
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.meals.pop(i)
                st.rerun()
    if st.button("🗑️ Wyczyść dzień"):
        st.session_state.meals = []
        st.rerun()

st.markdown('<div style="text-align:center;color:#718096;font-size:0.8rem;margin-top:2rem;">AI: Llama 3 (Groq) · Limit: 2000 kcal</div>', unsafe_allow_html=True)
