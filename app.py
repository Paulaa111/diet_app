import streamlit as st
import re
from datetime import date, timedelta
from database import MY_FOOD_DB

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------
st.set_page_config(page_title="Dziennik Makro", page_icon="🥑", layout="wide")

SHEET_NAME = "Dziennik Kalorii"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
LIMIT_KCAL = 1500

# ---------------------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------------------
@st.cache_resource
def get_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def load_data():
    try:
        rows = get_sheet().get_all_records()
        meals = []
        for idx, r in enumerate(rows):
            meals.append({
                "date": str(r.get("Data", "")),
                "time": str(r.get("Pora", "")),
                "name": str(r.get("Nazwa", "")),
                "calories": int(r.get("Kalorie", 0) or 0),
                "protein": float(r.get("Białko", 0) or 0),
                "fat": float(r.get("Tłuszcz", 0) or 0),
                "carbs": float(r.get("Węglowodany", 0) or 0),
                "suma_dnia": r.get("Suma dnia", ""),
                "_row": idx + 2,
            })
        return meals
    except Exception as e:
        st.error(f"❌ Błąd Google Sheets: {e}")
        return []

def save_meal(meal_dict):
    try:
        days_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
        get_sheet().append_row([
            days_pl[date.today().weekday()],
            str(date.today()),
            meal_dict.get("time", ""),
            meal_dict.get("name", ""),
            meal_dict.get("calories", 0),
            round(meal_dict.get("protein", 0), 1),
            round(meal_dict.get("fat", 0), 1),
            round(meal_dict.get("carbs", 0), 1),
            "",
        ], value_input_option="USER_ENTERED")
    except Exception as e:
        st.error(f"❌ Nie udało się zapisać: {e}")

def save_daily_summary(today_meals):
    try:
        sheet = get_sheet()
        total = sum(m["calories"] for m in today_meals)
        total_p = sum(m.get("protein", 0) for m in today_meals)
        total_f = sum(m.get("fat", 0) for m in today_meals)
        total_c = sum(m.get("carbs", 0) for m in today_meals)
        first_row = min(m["_row"] for m in today_meals)
        text = f"{total} kcal | B:{total_p:.0f}g T:{total_f:.0f}g W:{total_c:.0f}g"
        sheet.update_cell(first_row, 9, text)
        for m in today_meals:
            if m["_row"] != first_row:
                sheet.update_cell(m["_row"], 9, "")
        return total
    except Exception as e:
        st.error(f"❌ Błąd zapisu podsumowania: {e}")
        return None

def delete_meal_by_row(row_number):
    try:
        get_sheet().delete_rows(row_number)
    except Exception as e:
        st.error(f"❌ Błąd usuwania: {e}")

# ---------------------------------------------------------------
# PROSTE ROZPOZNAWANIE - BEZ ŻADNYCH ZAWIŁOŚCI
# ---------------------------------------------------------------

# Gramatura 1 sztuki (w gramach)
PORTIONS = {
    "kromka": 80,
    "kromki": 80,
    "łyżeczka": 10,
    "łyżka": 15,
    "sztuka": 60,
    "sztuki": 60,
}

# Aliasy produktów
PRODUCTS = {
    "chleb": "chleb z otrębami",
    "mojego chleba": "chleb z otrębami",
    "mój chleb": "chleb z otrębami",
    "finuu": "finuu klasyczne",
}

def parse_meal(text):
    """Proste parsowanie - zwraca listę (produkt, gramy)"""
    text = text.lower()
    results = []
    
    # Szukaj wzorca: "liczba kromki produkt" lub "liczba produkt"
    # Przykład: "2 kromki mojego chleba" lub "2 chleb"
    
    # Wzór 1: liczba + jednostka + produkt
    pattern1 = r'(\d+)\s+(kromk[aię]|kromki|łyżeczk[aię]|łyżk[aię]|sztuk[aię])\s+(.+?)(?:\s+z\s+|\s*$)'
    # Wzór 2: liczba + produkt (bez jednostki)
    pattern2 = r'(\d+)\s+(.+?)(?:\s+z\s+|\s*$)'
    
    # Szukaj wszystkich dopasowań
    for match in re.finditer(pattern1, text):
        count = int(match.group(1))
        unit = match.group(2)
        product = match.group(3).strip()
        
        # Sprawdź czy produkt jest w aliasach
        for alias, real_name in PRODUCTS.items():
            if alias in product:
                product_name = real_name
                break
        else:
            product_name = product
        
        grams = PORTIONS.get(unit, 80) * count
        results.append((product_name, grams))
        
        # Usuń przetworzony fragment
        text = text.replace(match.group(0), "")
    
    # Szukaj bez jednostki
    for match in re.finditer(pattern2, text):
        count = int(match.group(1))
        product = match.group(2).strip()
        
        # Sprawdź czy produkt jest w aliasach
        for alias, real_name in PRODUCTS.items():
            if alias in product:
                product_name = real_name
                break
        else:
            product_name = product
        
        # Domyślna porcja - 1 sztuka
        grams = 80 * count
        results.append((product_name, grams))
    
    return results

def calculate_nutrition(product_name, grams):
    """Oblicza wartości odżywcze dla produktu"""
    # Pobierz z bazy
    data = MY_FOOD_DB.get(product_name)
    if not data:
        return None
    
    # Mnożnik - baza na 100g
    multiplier = grams / 100.0
    
    return {
        "calories": int(round(data["kcal"] * multiplier)),
        "protein": round(data["p"] * multiplier, 1),
        "fat": round(data["f"] * multiplier, 1),
        "carbs": round(data["c"] * multiplier, 1),
    }

# ---------------------------------------------------------------
# STYLIZACJA
# ---------------------------------------------------------------
st.markdown("""
<style>
.stApp { background-color: #fdfaf5; }
.main-title { font-size: 3rem; font-weight: 700; color: #6b8e23; text-align: center; }
.stat-box { background: white; border-radius: 15px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.stat-value { font-size: 2rem; font-weight: 800; }
.stat-label { font-size: 0.8rem; color: #666; }
.meal-card { background: white; border-radius: 10px; padding: 10px; margin: 5px 0; display: flex; justify-content: space-between; align-items: center; }
.section-header { color: #6b8e23; font-size: 1.3rem; font-weight: 700; margin-top: 20px; border-bottom: 2px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# UI
# ---------------------------------------------------------------
st.markdown('<div class="main-title">🥑 Dziennik Makro</div>', unsafe_allow_html=True)

history = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]
total_kcal = sum(m["calories"] for m in today_meals)
total_p = sum(m.get("protein", 0) for m in today_meals)
total_f = sum(m.get("fat", 0) for m in today_meals)
total_c = sum(m.get("carbs", 0) for m in today_meals)

c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_kcal}</div><div class="stat-label">Kcal</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_p:.0f}g</div><div class="stat-label">Białko</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_f:.0f}g</div><div class="stat-label">Tłuszcz</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_c:.0f}g</div><div class="stat-label">Węgle</div></div>', unsafe_allow_html=True)
with c5:
    rem = LIMIT_KCAL - total_kcal
    color = "#6b8e23" if rem >= 0 else "#e53e3e"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{rem}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    st.markdown("---")
    st.markdown("**Arkusz:** Dziennik Kalorii")
    if st.button("🔄 Odśwież dane"):
        st.cache_resource.clear()
        st.rerun()

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input("Co dziś zjadłaś?",
        placeholder="np. 2 kromki mojego chleba z finuu")
    meal_time = st.selectbox("Pora", ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

if submitted and food_input:
    with st.spinner("🔍 Analizuję…"):
        # Parsuj
        items = parse_meal(food_input)
        
        if not items:
            st.error("❌ Nie rozpoznano składników. Spróbuj: '2 kromki chleba z finuu'")
        else:
            total = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
            details = []
            
            for product_name, grams in items:
                nutrition = calculate_nutrition(product_name, grams)
                if nutrition:
                    total["calories"] += nutrition["calories"]
                    total["protein"] += nutrition["protein"]
                    total["fat"] += nutrition["fat"]
                    total["carbs"] += nutrition["carbs"]
                    details.append(f"{product_name}: {grams}g → {nutrition['calories']} kcal")
                else:
                    details.append(f"⚠️ {product_name}: brak w bazie")
            
            # Zapisz
            new_meal = {
                "name": food_input[:50],
                "calories": total["calories"],
                "protein": total["protein"],
                "fat": total["fat"],
                "carbs": total["carbs"],
                "time": meal_time,
            }
            save_meal(new_meal)
            st.cache_resource.clear()
            
            st.success(f"✅ {food_input[:50]} — {total['calories']} kcal | B:{total['protein']:.0f}g T:{total['fat']:.0f}g W:{total['carbs']:.0f}g")
            with st.expander("📊 Szczegóły"):
                for d in details:
                    st.write(d)
            st.rerun()

st.markdown('<div class="section-header">Dzisiejsze Menu</div>', unsafe_allow_html=True)

if today_meals:
    for cat in ["Śniadanie", "II Śniadanie", "Obiad", "Kolacja", "Przekąska"]:
        cat_meals = [m for m in today_meals if m["time"] == cat]
        if cat_meals:
            st.write(f"**{cat}**")
            for m in cat_meals:
                col1, col2 = st.columns([8, 1])
                with col1:
                    st.markdown(f'<div class="meal-card"><span>{m["name"]}</span><span>{m["calories"]} kcal | B:{m["protein"]:.0f}g T:{m["fat"]:.0f}g W:{m["carbs"]:.0f}g</span></div>', unsafe_allow_html=True)
                with col2:
                    if st.button("🗑️", key=f"del_{m['_row']}"):
                        delete_meal_by_row(m["_row"])
                        st.rerun()
else:
    st.info("Dodaj swój pierwszy posiłek powyżej!")

if today_meals:
    if st.button("📊 Zapisz podsumowanie dnia"):
        save_daily_summary(today_meals)
        st.success("✅ Podsumowanie zapisane!")

st.markdown('<div class="section-header">Podsumowanie Tygodnia</div>', unsafe_allow_html=True)
if history:
    week_data = {}
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        week_data[d.strftime("%d.%m")] = sum(m["calories"] for m in history if m["date"] == str(d))
    st.bar_chart(week_data)
