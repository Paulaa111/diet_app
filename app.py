import streamlit as st
import json
import google.generativeai as genai # Dodaj ten import na górze kodu!
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
.bread-info {
    background: rgba(245,197,24,0.08);
    border: 1px solid rgba(245,197,24,0.35);
    border-radius: 10px;
    padding: 12px 16px;
    margin: 6px 0;
    font-size: 0.85rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Wbudowany własny chleb
# Cały bochenek ~950g = ~2003 kcal → 211 kcal/100g
# 1 kromka ~80g = ~169 kcal
# 1 plasterek ~40g = ~84 kcal
# ---------------------------------------------------------------
BREAD_KCAL_PER_100G = 211
BREAD_KEYWORDS = [
    "chleb z otrębami", "chleb otręby", "chleb twarogowy",
    "chleb własny", "mój chleb", "chleb z twarogiem"
]

def detect_bread(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in BREAD_KEYWORDS)

def parse_bread_grams(text: str) -> int:
    import re
    t = text.lower()
    m = re.search(r'(\d+)\s*g(?:ram)?', t)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*(?:kromk[aięi]|kromki)', t)
    if m:
        return int(m.group(1)) * 80
    m = re.search(r'(\d+)\s*(?:plasterek|plasterki|plasterków)', t)
    if m:
        return int(m.group(1)) * 40
    if "kawałek" in t or "kawalek" in t:
        return 80
    return 80  # domyślnie 1 kromka

# ---------------------------------------------------------------
# Gemini API
# ---------------------------------------------------------------
def get_calories_gemini(food_description: str, api_key: str) -> dict:
    # Konfiguracja - biblioteka sama dobierze właściwe v1 lub v1beta
    genai.configure(api_key=api_key)
    
    # Próbujemy użyć wersji flash, która jest najstabilniejsza
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""Jesteś ekspertem od dietetyki. Użytkownik napisał co zjadł: "{food_description}"
    Oszacuj kalorie. Odpowiedz WYŁĄCZNIE w formacie JSON:
    {{
      "name": "Nazwa dania",
      "calories": 100,
      "note": "Krótka informacja"
    }}"""
    
    # Wywołanie nową metodą
    response = model.generate_content(prompt)
    
    # Wyciąganie tekstu (biblioteka sama czyści śmieci z odpowiedzi)
    res_text = response.text.strip()
    
    # Na wypadek gdyby AI dodało ```json ... ```
    if "```json" in res_text:
        res_text = res_text.split("```json")[1].split("```")[0].strip()
    elif "```" in res_text:
        res_text = res_text.split("```")[1].strip()
        
    return json.loads(res_text)

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
st.markdown('<div class="subtitle">Wpisz co zjadłeś — AI policzy resztę</div>', unsafe_allow_html=True)

# Sidebar
# W sekcji Sidebar zamień st.text_input na to:
with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    
    # Sprawdź czy klucz jest w Secrets, jeśli nie - pozwól wpisać ręcznie
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Klucz API wczytany z Secrets")
    else:
        api_key = st.text_input(
            "Klucz Gemini API",
            type="password",
            placeholder="AIza...",
            help="Wklej klucz lub dodaj go do secrets.toml"
        )


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
    label = "Pozostało kcal" if remaining >= 0 else "Przekroczono"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{abs(remaining)}</div><div class="stat-label">{label}</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#a0aec0">{LIMIT}</div><div class="stat-label">Limit kcal</div></div>', unsafe_allow_html=True)

st.markdown(f"""
<div class="progress-container">
    <div class="progress-bar" style="width:{pct*100:.1f}%; background:linear-gradient(90deg,{bar_color},{bar_color}cc);"></div>
</div>
<div style="text-align:right;color:#718096;font-size:0.82rem;margin-bottom:1.5rem;">{pct*100:.0f}% dziennego limitu</div>
""", unsafe_allow_html=True)

# Formularz
with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input(
        "Co zjadłeś/aś?",
        placeholder="np. 2 kromki chleba z otrębami, jogurt naturalny, banan..."
    )
    submitted = st.form_submit_button("➕ Dodaj posiłek", use_container_width=True)

if submitted and food_input.strip():
    text = food_input.strip()

    if detect_bread(text):
        grams = parse_bread_grams(text)
        kcal = round(BREAD_KCAL_PER_100G * grams / 100)
        st.session_state.meals.append({
            "name": f"🍞 Chleb z otrębami i twarogiem ({grams}g)",
            "calories": kcal,
        })
        st.success(f"✅ **Chleb z otrębami ({grams}g)** — **{kcal} kcal**")
        st.caption("ℹ️ Kalorie z własnego przepisu (211 kcal/100g) — bez użycia API.")
        st.rerun()

    elif not api_key:
        st.warning("⚠️ Wpisz klucz Gemini API w panelu po lewej. Chleb z otrębami działa bez klucza!")

    else:
        with st.spinner("🤔 Pytam Gemini o kalorie..."):
            try:
                result = get_calories_gemini(text, api_key)
                st.session_state.meals.append({
                    "name": result["name"],
                    "calories": int(result["calories"]),
                })
                st.success(f'✅ **{result["name"]}** — **{result["calories"]} kcal**')
                if result.get("note"):
                    st.caption(f"ℹ️ {result['note']}")
                st.rerun()
            except Exception as e:
                st.error(f"Błąd Gemini API: {e}")

# Lista posiłków
if st.session_state.meals:
    st.markdown("### 📋 Dzisiejsze posiłki")
    for i, meal in enumerate(st.session_state.meals):
        c1, c2 = st.columns([6, 1])
        with c1:
            st.markdown(f'<div class="meal-card"><span class="meal-name">🍴 {meal["name"]}</span><span class="meal-kcal">{meal["calories"]} kcal</span></div>', unsafe_allow_html=True)
        with c2:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.meals.pop(i)
                st.rerun()

    st.markdown("---")
    if remaining < 0:
        st.error(f"⚠️ Przekroczono limit o **{abs(remaining)} kcal**!")
    elif remaining < 200:
        st.warning(f"🔶 Zostało tylko **{remaining} kcal** — ostrożnie!")
    else:
        st.info(f"✅ Możesz jeszcze zjeść ok. **{remaining} kcal**")

    if st.button("🗑️ Wyczyść cały dzień"):
        st.session_state.meals = []
        st.rerun()
else:
    st.markdown('<div style="text-align:center;padding:3rem 0;color:#4a5568"><div style="font-size:3rem">🍽️</div><div style="margin-top:0.5rem">Nie dodałeś jeszcze żadnego posiłku.</div></div>', unsafe_allow_html=True)

st.markdown('<div style="text-align:center;color:#2d3748;font-size:0.78rem;margin-top:3rem">AI: Google Gemini Flash · Limit: 2000 kcal/dzień</div>', unsafe_allow_html=True)
