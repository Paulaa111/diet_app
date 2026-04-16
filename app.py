import streamlit as st
import json
import requests
import re
from datetime import date, datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

# --- Konfiguracja strony ---
st.set_page_config(page_title="Dziennik Makro", page_icon="🥑", layout="wide")

# --- GOOGLE SHEETS ---
SHEET_NAME = "Dziennik Kalorii"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_sheet():
    """Połącz z Google Sheets (wynik jest cache'owany)."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    # Streamlit czasem zamienia \n na literalne \\n — naprawiamy:
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

def load_data():
    """Wczytaj wszystkie wiersze z arkusza jako listę słowników."""
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        meals = []
        for idx, r in enumerate(rows):
            meals.append({
                "id":        str(r.get("Data", "")) + "_" + str(r.get("Pora", "")) + "_" + str(r.get("Nazwa", "")),
                "date":      str(r.get("Data", "")),
                "time":      str(r.get("Pora", "")),
                "name":      str(r.get("Nazwa", "")),
                "calories":  int(r.get("Kalorie", 0) or 0),
                "protein":   float(r.get("Białko", 0) or 0),
                "fat":       float(r.get("Tłuszcz", 0) or 0),
                "carbs":     float(r.get("Węglowodany", 0) or 0),
                "suma_dnia": r.get("Suma dnia", ""),
                "_row":      idx + 2,  # +2 bo wiersz 1 = nagłówek
            })
        return meals
    except Exception as e:
        st.error(f"❌ Błąd połączenia z Google Sheets: {e}")
        return []

def save_meal(meal_dict):
    """Dodaj jeden wiersz na dole arkusza (9 kolumn, Suma dnia pusta)."""
    try:
        sheet = get_sheet()
        today = str(date.today())
        days_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
        day_name = days_pl[date.today().weekday()]
        row = [
            day_name,
            today,
            meal_dict.get("time", ""),
            meal_dict.get("name", ""),
            meal_dict.get("calories", 0),
            meal_dict.get("protein", 0),
            meal_dict.get("fat", 0),
            meal_dict.get("carbs", 0),
            "",  # Suma dnia — pusta przy dodawaniu posiłku
        ]
        sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        st.error(f"❌ Nie udało się zapisać do arkusza: {e}")

def save_daily_summary(today_meals: list):
    """
    Znajdź pierwszy wiersz dzisiejszego dnia w arkuszu
    i wpisz sumę kalorii do kolumny 'Suma dnia' (kolumna I = nr 9).
    Jeśli suma już była wpisana — nadpisuje.
    """
    try:
        sheet = get_sheet()
        total = sum(m["calories"] for m in today_meals)
        total_p = sum(m.get("protein", 0) for m in today_meals)
        total_f = sum(m.get("fat", 0) for m in today_meals)
        total_c = sum(m.get("carbs", 0) for m in today_meals)

        # Znajdź numer pierwszego wiersza dzisiejszego dnia
        first_row = min(m["_row"] for m in today_meals)

        # Kolumna I (9) = "Suma dnia" — wpisujemy czytelny tekst
        summary_text = f"{total} kcal | B:{total_p:.0f}g T:{total_f:.0f}g W:{total_c:.0f}g"
        sheet.update_cell(first_row, 9, summary_text)

        # Wyczyść kolumnę I dla pozostałych wierszy tego dnia (żeby nie było duplikatów)
        for m in today_meals:
            if m["_row"] != first_row:
                sheet.update_cell(m["_row"], 9, "")

        return total
    except Exception as e:
        st.error(f"❌ Nie udało się zapisać podsumowania: {e}")
        return None

def delete_meal_by_row(row_number: int):
    """Usuń wiersz o podanym numerze z arkusza."""
    try:
        sheet = get_sheet()
        sheet.delete_rows(row_number)
    except Exception as e:
        st.error(f"❌ Nie udało się usunąć wiersza: {e}")

# --- STYLIZACJA ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
.stApp { background-color: #fdfaf5; color: #4a4a4a; font-family: 'Quicksand', sans-serif; }
.main-title { font-size: 3rem; font-weight: 700; color: #6b8e23; text-align: center; margin-top: -30px; }
.stat-box {
    background: white; border-radius: 15px; padding: 15px; text-align: center;
    box-shadow: 0 8px 16px rgba(139,123,108,0.1); border-bottom: 4px solid #e0d7cd;
}
.stat-value { font-size: 2.2rem; font-weight: 800; line-height: 1; margin-bottom: 5px; }
.stat-label { font-size: 0.8rem; color: #a69080; text-transform: uppercase; font-weight: 700; }
.meal-card {
    background: white; border-radius: 12px; padding: 12px; margin: 5px 0;
    display: flex; justify-content: space-between; align-items: center; border: 1px solid #f0ede9;
}
.meal-stats { background: #f1f3eb; color: #6b8e23; padding: 5px 12px; border-radius: 10px; font-weight: 700; font-size: 0.85rem; }
.section-header { color: #6b8e23; font-size: 1.3rem; font-weight: 700; margin-top: 20px; border-bottom: 2px solid #e9e2d8; }
</style>
""", unsafe_allow_html=True)

# --- Chleb własny ---
BREAD_VALS = {"kcal": 211, "protein": 12, "fat": 5, "carbs": 25}

def detect_bread(text: str) -> bool:
    return any(kw in text.lower() for kw in [
        "chleb z otrębami", "chleb otręby", "chleb twarogowy", "chleb własny", "mój chleb"
    ])

# --- Groq API ---
def get_nutrition_groq(food_description: str, api_key: str) -> dict:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    prompt = f"""Oszacuj kalorie, białko, tłuszcze i węglowodany dla: {food_description}.
Zwróć TYLKO czysty JSON: {{"name": "...", "calories": 100, "protein": 10, "fat": 5, "carbs": 20}}"""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    res_text = response.json()["choices"][0]["message"]["content"].strip()
    start, end = res_text.find("{"), res_text.rfind("}") + 1
    return json.loads(res_text[start:end])

# ---------------------------------------------------------------
# UI
# ---------------------------------------------------------------
st.markdown('<div class="main-title">🥑 Dziennik Makro</div>', unsafe_allow_html=True)

# Wczytaj dane
history = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]

LIMIT_KCAL = 1500
total_kcal = sum(m["calories"] for m in today_meals)
total_p    = sum(m.get("protein", 0) for m in today_meals)
total_f    = sum(m.get("fat", 0) for m in today_meals)
total_c    = sum(m.get("carbs", 0) for m in today_meals)

# STATYSTYKI
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_kcal}</div><div class="stat-label">Kcal</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6b8e23">{total_p:.0f}g</div><div class="stat-label">Białko</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#bc6c25">{total_f:.0f}g</div><div class="stat-label">Tłuszcz</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#4299e1">{total_c:.0f}g</div><div class="stat-label">Węgle</div></div>', unsafe_allow_html=True)
with c5:
    rem = LIMIT_KCAL - total_kcal
    color = "#6b8e23" if rem >= 0 else "#e53e3e"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{rem}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    api_key = st.secrets.get("GROQ_API_KEY", "") or st.text_input("Klucz Groq API", type="password")
    st.markdown("---")
    st.markdown("**Arkusz:** Dziennik Kalorii")
    if st.button("🔄 Odśwież dane"):
        st.cache_resource.clear()
        st.rerun()

# FORMULARZ
with st.form("meal_form", clear_on_submit=True):
    col_in, col_sel = st.columns([3, 1])
    with col_in:
        food_input = st.text_input("Co dziś zjadłaś?", placeholder="np. 2 kromki chleba z otrębami, jajka sadzone...")
    with col_sel:
        meal_time = st.selectbox("Pora", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

if submitted and food_input:
    with st.spinner("Analizuję..."):
        try:
            if detect_bread(food_input):
                m = re.search(r"(\d+)\s*g", food_input.lower())
                g = int(m.group(1)) if m else 80
                new_meal = {
                    "name":     f"🍞 Chleb własny ({g}g)",
                    "calories": round(BREAD_VALS["kcal"] * g / 100),
                    "protein":  round(BREAD_VALS["protein"] * g / 100, 1),
                    "fat":      round(BREAD_VALS["fat"] * g / 100, 1),
                    "carbs":    round(BREAD_VALS["carbs"] * g / 100, 1),
                    "time":     meal_time,
                }
            else:
                res = get_nutrition_groq(food_input, api_key)
                new_meal = {
                    "name":     res["name"],
                    "calories": int(res["calories"]),
                    "protein":  float(res.get("protein", 0)),
                    "fat":      float(res.get("fat", 0)),
                    "carbs":    float(res.get("carbs", 0)),
                    "time":     meal_time,
                }
            save_meal(new_meal)
            st.cache_resource.clear()  # wymuś odświeżenie cache
            st.rerun()
        except Exception as e:
            st.error(f"Błąd: {e}")

# LISTA POSIŁKÓW
st.markdown('<div class="section-header">Dzisiejsze Menu</div>', unsafe_allow_html=True)
if today_meals:
    for cat in ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"]:
        cat_meals = [m for m in today_meals if m["time"] == cat]
        if cat_meals:
            st.write(f"**{cat}**")
            for m in cat_meals:
                c1, c2 = st.columns([8, 1])
                with c1:
                    st.markdown(
                        f'<div class="meal-card">'
                        f'<span>{m["name"]}</span>'
                        f'<span class="meal-stats">{m["calories"]} kcal | '
                        f'B:{m["protein"]:.0f}g T:{m["fat"]:.0f}g W:{m["carbs"]:.0f}g</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with c2:
                    if st.button("🗑️", key=f"del_{m['_row']}"):
                        delete_meal_by_row(m["_row"])
                        st.cache_resource.clear()
                        st.rerun()
else:
    st.info("Dodaj swój pierwszy posiłek powyżej!")


# PRZYCISK PODSUMOWANIA DNIA
if today_meals:
    st.write("")
    col_sum, col_info = st.columns([2, 5])
    with col_sum:
        if st.button("📊 Zapisz podsumowanie dnia do arkusza", use_container_width=True):
            with st.spinner("Zapisuję podsumowanie..."):
                total = save_daily_summary(today_meals)
                if total is not None:
                    st.cache_resource.clear()
                    st.success(f"✅ Zapisano! Suma dnia: **{total} kcal** — widoczna w kolumnie 'Suma dnia' przy pierwszym posiłku.")
    with col_info:
        first_meal = min(today_meals, key=lambda m: m["_row"])
        if first_meal.get("suma_dnia"):
            st.info(f"📋 Ostatnio zapisane podsumowanie: **{first_meal['suma_dnia']}**")
        else:
            st.caption("💡 Kliknij gdy skończyłaś dodawać posiłki — suma trafi do kolumny I w arkuszu.")
# PODSUMOWANIE TYGODNIA
st.write("")
st.markdown('<div class="section-header">Podsumowanie Tygodnia</div>', unsafe_allow_html=True)

if history:
    week_data = {}
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        d_str = str(d)
        day_sum = sum(m["calories"] for m in history if m["date"] == d_str)
        week_data[d.strftime("%d.%m")] = day_sum

    st.bar_chart(week_data)
    avg_kcal = sum(week_data.values()) / 7
    st.write(f"Średnie kalorie z ostatnich 7 dni: **{avg_kcal:.0f} kcal**")
