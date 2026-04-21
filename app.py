import streamlit as st
import json
import requests
import time
import re
from datetime import date, timedelta
from database import MY_FOOD_DB

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------
st.set_page_config(page_title="Dziennik Makro", page_icon="🥑", layout="wide")

SHEET_NAME  = "Dziennik Kalorii"
SCOPES      = ["https://www.googleapis.com/auth/spreadsheets",
               "https://www.googleapis.com/auth/drive"]
LIMIT_KCAL  = 1500

# ---------------------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------------------
@st.cache_resource
def get_sheet():
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds  = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def load_data():
    try:
        rows  = get_sheet().get_all_records()
        meals = []
        for idx, r in enumerate(rows):
            meals.append({
                "date":      str(r.get("Data", "")),
                "time":      str(r.get("Pora", "")),
                "name":      str(r.get("Nazwa", "")),
                "calories":  int(r.get("Kalorie", 0) or 0),
                "protein":   float(r.get("Białko", 0) or 0),
                "fat":       float(r.get("Tłuszcz", 0) or 0),
                "carbs":     float(r.get("Węglowodany", 0) or 0),
                "suma_dnia": r.get("Suma dnia", ""),
                "_row":      idx + 2,
            })
        return meals
    except Exception as e:
        st.error(f"❌ Błąd Google Sheets: {e}")
        return []

def save_meal(meal_dict):
    try:
        days_pl = ["Poniedziałek","Wtorek","Środa","Czwartek","Piątek","Sobota","Niedziela"]
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
        sheet     = get_sheet()
        total     = sum(m["calories"] for m in today_meals)
        total_p   = sum(m.get("protein", 0) for m in today_meals)
        total_f   = sum(m.get("fat", 0) for m in today_meals)
        total_c   = sum(m.get("carbs", 0) for m in today_meals)
        first_row = min(m["_row"] for m in today_meals)
        text      = f"{total} kcal | B:{total_p:.0f}g T:{total_f:.0f}g W:{total_c:.0f}g"
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
# LOKALNA BAZA — słownik aliasów → klucz w MY_FOOD_DB
# ---------------------------------------------------------------
ALIASES = {
    # chleb
    "chleb z otrębami":          "chleb z otrębami",
    "chleb z otrebami":          "chleb z otrębami",
    "mój chleb":                 "chleb z otrębami",
    "moj chleb":                 "chleb z otrębami",
    "mojego chleba":             "chleb z otrębami",
    "chleb twarogowy":           "chleb z otrębami",
    "chleba twarogowego":        "chleb z otrębami",
    "chlebem twarogowym":        "chleb z otrębami",
    "chleb własny":              "chleb z otrębami",
    "chleb wlasny":              "chleb z otrębami",
    "chleb domowy":              "chleb z otrębami",
    "chleb żytni":               "chleb żytni",
    "chleb zytni":               "chleb żytni",
    "kromka chleba":             "chleb z otrębami",
    "kromki chleba":             "chleb z otrębami",
    # tłuszcze
    "finuu klasyczne":           "finuu klasyczne",
    "finuu lekkie":              "finuu lekkie",
    "finuu":                     "finuu klasyczne",
    "masło ekstra":              "masło ekstra",
    "maslo ekstra":              "masło ekstra",
    "masło":                     "masło ekstra",
    "maslo":                     "masło ekstra",
    # jajka
    "jajko sadzone":             "jajko sadzone",
    "jajka sadzone":             "jajko sadzone",
    "jajko kurze":               "jajko kurze",
    "jajka kurze":               "jajko kurze",
    "jajko":                     "jajko kurze",
    "jajka":                     "jajko kurze",
    "jajeczko":                  "jajko kurze",
    # nabiał
    "jogurt naturalny piątnica 2%": "jogurt naturalny piątnica 2%",
    "jogurt naturalny piątnica 0%": "jogurt naturalny piątnica 0%",
    "piątnica 2%":               "jogurt naturalny piątnica 2%",
    "piatnica 2%":               "jogurt naturalny piątnica 2%",
    "piątnica 0%":               "jogurt naturalny piątnica 0%",
    "piatnica 0%":               "jogurt naturalny piątnica 0%",
    "piątnica":                  "jogurt naturalny piątnica 2%",
    "piatnica":                  "jogurt naturalny piątnica 2%",
    "skyr naturalny":            "skyr naturalny",
    "skyr":                      "skyr naturalny",
    "twaróg półtłusty":          "twaróg półtłusty",
    "twarog półtłusty":          "twaróg półtłusty",
    "twaróg":                    "twaróg półtłusty",
    "twarog":                    "twaróg półtłusty",
    "mleko 2%":                  "mleko 2%",
    "mleko":                     "mleko 2%",
    # napoje
    "kawa czarna":               "kawa czarna",
    "kawa":                      "kawa czarna",
    "herbata":                   "herbata",
}

# Domyślna gramatura dla JEDNEJ sztuki/jednostki (w gramach)
UNIT_GRAMS = {
    "chleb z otrębami":          80,   # 1 kromka
    "chleb żytni":               80,   # 1 kromka
    "bułka pszenna":            100,   # 1 sztuka
    "finuu klasyczne":           10,   # 1 łyżeczka
    "finuu lekkie":              10,   # 1 łyżeczka
    "masło ekstra":              10,   # 1 łyżeczka
    "jajko kurze":               60,   # 1 sztuka
    "jajko sadzone":             60,   # 1 sztuka
    "jogurt naturalny piątnica 2%": 150,  # 1 kubeczek
    "jogurt naturalny piątnica 0%": 150,  # 1 kubeczek
    "skyr naturalny":           150,   # 1 kubeczek
    "twaróg półtłusty":         100,   # standardowa porcja
    "mleko 2%":                 200,   # 1 szklanka
    "kawa czarna":              150,   # 1 kubek
    "herbata":                  200,   # 1 szklanka
}

def parse_locally(text: str) -> list:
    """
    Rozpoznaje składniki z tekstu BEZ AI.
    Zwraca listę itemów z prawidłowo wyliczoną gramaturą.
    """
    found   = []
    used_up = set()
    t = text.lower()

    # Sortuj aliasy od najdłuższych do najkrótszych
    for alias in sorted(ALIASES.keys(), key=len, reverse=True):
        pos = t.find(alias)
        if pos == -1:
            continue
        if any(pos <= u < pos + len(alias) for u in used_up):
            continue

        db_key = ALIASES[alias]
        unit_g = UNIT_GRAMS.get(db_key, 100)

        # Szukaj jawnej gramatury: "150g jogurtu"
        # Sprawdź w okolicy aliasu (10 znaków przed i 10 po)
        search_start = max(0, pos - 10)
        search_end = min(len(t), pos + len(alias) + 10)
        context = t[search_start:search_end]
        
        gram_match = re.search(r"(\d+)\s*g\b", context)
        if gram_match:
            amount = float(gram_match.group(1))
        else:
            # Szukaj liczby sztuk PRZED aliasem
            before_alias = t[max(0, pos-20):pos]
            # Wzorzec dla liczby + jednostki (kromki, sztuki, itp.)
            count_match = re.search(r"(\d+)\s*(?:kromk[aię]|kromkę|kromki|sztuk[aię]|szt\.?\s*|sztuki|sztukę)?\s*$", before_alias)
            
            if count_match:
                count = int(count_match.group(1))
            else:
                # Szukaj samej liczby
                simple_count = re.search(r"(\d+)\s*$", before_alias)
                count = int(simple_count.group(1)) if simple_count else 1
            
            amount = unit_g * count

        # Zabezpieczenie przed absurdalnymi wartościami
        amount = max(5.0, min(amount, 2000.0))

        found.append({
            "item":     db_key,
            "amount":   amount,
            "source":   "LOCAL",
            "eng_name": db_key,
        })
        
        for i in range(pos, pos + len(alias)):
            used_up.add(i)

    return found

# ---------------------------------------------------------------
# GEMINI — helper do wysyłania zapytań
# ---------------------------------------------------------------
GEMINI_MODELS = ["gemini-1.5-flash", "gemini-2.0-flash"]

def _gemini_post(prompt: str, api_key: str, max_tokens: int = 512) -> str:
    """Wysyła prompt do Gemini, zwraca surowy tekst odpowiedzi."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": max_tokens},
    }
    last_err = "brak odpowiedzi"
    for model in GEMINI_MODELS:
        url = (f"https://generativelanguage.googleapis.com/v1beta"
               f"/models/{model}:generateContent?key={api_key}")
        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=25)
                if resp.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                if resp.status_code in (404, 503):
                    time.sleep(2)
                    break
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                last_err = str(e)
                time.sleep(1)
    raise Exception(f"Gemini niedostępne: {last_err}")

def _parse_json_list(raw: str) -> list:
    raw = raw.replace("```json", "").replace("```", "").strip()
    s, e = raw.find("["), raw.rfind("]") + 1
    return json.loads(raw[s:e])

def _parse_json_dict(raw: str) -> dict:
    raw = raw.replace("```json", "").replace("```", "").strip()
    s, e = raw.find("{"), raw.rfind("}") + 1
    return json.loads(raw[s:e])

# ---------------------------------------------------------------
# GEMINI — klasyfikacja
# ---------------------------------------------------------------
def classify_with_gemini(food_description: str, api_key: str) -> list:
    prompt = (
        "Jesteś ekspertem ds. żywienia. Przeanalizuj opis posiłku po polsku.\n"
        "Zwróć TYLKO czysty JSON — tablicę, zero tekstu, zero markdown.\n\n"
        'Format każdego obiektu: {"item":"nazwa po polsku","amount":100,"source":"USDA","eng_name":"english name"}\n\n'
        "ZASADY:\n"
        "- Każdy składnik = osobny obiekt\n"
        '- source="OFF" → konkretna marka (Danone, Zott, Oreo)\n'
        '- source="USDA" → surowce, warzywa, mięso, dania domowe\n'
        "- amount = gramy jako liczba całkowita, zakres 5-800\n"
        "  Przeliczniki: 1 kromka=80, 1 jajko=60, 1 łyżka=15, 1 łyżeczka=5,\n"
        "  1 szklanka=240, kubek=250, porcja zupy=350, jogurt kubeczek=150\n"
        "- NIE uwzględniaj produktów które już rozpoznałeś jako tłuszcz do smarowania\n\n"
        f"Opis: {food_description}"
    )
    raw = _gemini_post(prompt, api_key)
    return _parse_json_list(raw)

# ---------------------------------------------------------------
# GEMINI — szacowanie kalorii
# ---------------------------------------------------------------
def gemini_estimate_single(item_name: str, amount_g: float, api_key: str) -> dict | None:
    prompt = (
        f"Wartości odżywcze: {item_name}, porcja {amount_g:.0f}g.\n"
        'Zwróć TYLKO JSON: {"calories":0,"protein":0,"fat":0,"carbs":0}'
    )
    try:
        raw  = _gemini_post(prompt, api_key, max_tokens=80)
        data = _parse_json_dict(raw)
        return {
            "calories": int(data.get("calories", 0)),
            "protein":  round(float(data.get("protein", 0)), 1),
            "fat":      round(float(data.get("fat", 0)), 1),
            "carbs":    round(float(data.get("carbs", 0)), 1),
            "source_label": "🤖 Gemini~szacunek",
        }
    except Exception:
        return None

# ---------------------------------------------------------------
# BAZA LOKALNA
# ---------------------------------------------------------------
def lookup_in_db(db_key: str, amount_g: float) -> dict | None:
    """Szuka dokładnie po kluczu w MY_FOOD_DB."""
    v = MY_FOOD_DB.get(db_key)
    if not v:
        resolved = ALIASES.get(db_key.lower())
        if resolved:
            v = MY_FOOD_DB.get(resolved)
    if not v:
        return None
    
    # Oblicz mnożnik - baza jest na 100g
    multiplier = amount_g / 100.0
    
    return {
        "calories": int(round(v["kcal"] * multiplier)),
        "protein": round(v["p"] * multiplier, 1),
        "fat": round(v["f"] * multiplier, 1),
        "carbs": round(v["c"] * multiplier, 1),
        "source_label": f"🏠 Moja baza ({db_key})",
    }

# ---------------------------------------------------------------
# OPEN FOOD FACTS
# ---------------------------------------------------------------
def fetch_from_off(query: str, amount_g: float) -> dict | None:
    try:
        resp = requests.get("https://world.openfoodfacts.org/cgi/search.pl", params={
            "search_terms": query, "search_simple": 1, "action": "process",
            "json": 1, "page_size": 10, "sort_by": "unique_scans_n",
            "fields": "product_name,nutriments",
        }, timeout=12)
        resp.raise_for_status()
        products = resp.json().get("products", [])
        best, best_score = None, -1
        for p in products:
            n        = p.get("nutriments", {})
            kcal_100 = n.get("energy-kcal_100g") or (n.get("energy_100g", 0) / 4.184)
            if not kcal_100 or kcal_100 <= 0:
                continue
            score = sum([n.get("proteins_100g") is not None,
                         n.get("fat_100g") is not None,
                         n.get("carbohydrates_100g") is not None])
            if score > best_score:
                best_score, best = score, (p, n, kcal_100)
        if not best:
            return None
        p, n, kcal_100 = best
        f = amount_g / 100
        return {
            "calories": round(kcal_100 * f),
            "protein":  round((n.get("proteins_100g") or 0) * f, 1),
            "fat":      round((n.get("fat_100g") or 0) * f, 1),
            "carbs":    round((n.get("carbohydrates_100g") or 0) * f, 1),
            "source_label": f"🔵 OFF: {p.get('product_name','?')[:30]}",
        }
    except Exception:
        return None

# ---------------------------------------------------------------
# USDA
# ---------------------------------------------------------------
def fetch_from_usda(eng_name: str, amount_g: float,
                    usda_key: str = "DEMO_KEY") -> dict | None:
    try:
        for data_type in ["SR Legacy,Foundation", "Branded"]:
            resp = requests.get("https://api.nal.usda.gov/fdc/v1/foods/search", params={
                "query": eng_name, "dataType": data_type,
                "pageSize": 5, "api_key": usda_key,
            }, timeout=12)
            resp.raise_for_status()
            for food in resp.json().get("foods", []):
                nutrients = {}
                for n in food.get("foodNutrients", []):
                    if isinstance(n, dict):
                        nm, val = n.get("nutrientName"), n.get("value")
                        if nm and isinstance(val, (int, float)):
                            nutrients[nm] = val
                kcal = (nutrients.get("Energy") or
                        nutrients.get("Energy (Atwater General Factors)") or
                        nutrients.get("Energy (Atwater Specific Factors)") or 0)
                if kcal > 0:
                    f = amount_g / 100
                    return {
                        "calories": round(kcal * f),
                        "protein":  round(nutrients.get("Protein", 0) * f, 1),
                        "fat":      round(nutrients.get("Total lipid (fat)", 0) * f, 1),
                        "carbs":    round(nutrients.get("Carbohydrate, by difference", 0) * f, 1),
                        "source_label": f"🟠 USDA: {food.get('description','?')[:30]}",
                    }
        return None
    except Exception:
        return None

# ---------------------------------------------------------------
# ORKIESTRACJA - GŁÓWNA FUNKCJA
# ---------------------------------------------------------------
def get_nutrition_hybrid(food_description: str, api_key: str, usda_key: str) -> dict:
    # Krok 1: Rozpoznaj lokalnie
    local_items = parse_locally(food_description)
    local_keys = {it["item"] for it in local_items}

    # Krok 2: Gemini dla nierozpoznanych składników
    gemini_items = []
    temp = food_description.lower()
    for alias in ALIASES:
        temp = temp.replace(alias, "")
    has_unknown = bool(re.sub(r"[\d\s,gz./]", "", temp).strip())

    if has_unknown and api_key:
        try:
            all_gemini = classify_with_gemini(food_description, api_key)
            gemini_items = [it for it in all_gemini
                            if it.get("item", "").lower() not in local_keys
                            and ALIASES.get(it.get("item", "").lower()) not in local_keys]
        except Exception as e:
            st.warning(f"⚠️ Gemini niedostępny: {e}. Używam tylko lokalnej bazy.")

    items = local_items + gemini_items

    # Jeśli nic nie znaleziono, spróbuj całość przez Gemini
    if not items and api_key:
        try:
            items = classify_with_gemini(food_description, api_key)
        except Exception:
            pass

    total = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    sources_used = []
    fallback_items = []

    for item in items:
        name_ai = item.get("item", "").lower().strip()
        raw_amt = item.get("amount", 100)
        
        # Pobierz gramaturę
        try:
            amount = float(re.sub(r"[^0-9.]", "", str(raw_amt)) or "100")
        except Exception:
            amount = 100.0
        
        # Zabezpieczenie - ale z większym limitem (dla 2 kromek chleba = 160g)
        amount = max(5.0, min(amount, 2000.0))

        source = item.get("source", "USDA")
        eng_name = item.get("eng_name", name_ai)

        # 1️⃣ Własna baza
        result = lookup_in_db(name_ai, amount)

        # 2️⃣ API zewnętrzne
        if not result:
            if source == "OFF":
                result = fetch_from_off(name_ai, amount) or fetch_from_usda(eng_name, amount, usda_key)
            else:
                result = fetch_from_usda(eng_name, amount, usda_key) or fetch_from_off(name_ai, amount)

        # 3️⃣ Gemini szacuje
        if not result and api_key:
            result = gemini_estimate_single(name_ai, amount, api_key)

        if result:
            total["calories"] += result["calories"]
            total["protein"] += result["protein"]
            total["fat"] += result["fat"]
            total["carbs"] += result["carbs"]
            sources_used.append(f"{name_ai} ({amount:.0f}g) → {result['source_label']}")
        else:
            fallback_items.append(f"{name_ai} ({amount:.0f}g) — brak danych")

    return {
        "name": food_description[:60],
        "calories": total["calories"],
        "protein": round(total["protein"], 1),
        "fat": round(total["fat"], 1),
        "carbs": round(total["carbs"], 1),
        "sources_used": sources_used,
        "fallback": fallback_items,
    }

# ---------------------------------------------------------------
# STYLIZACJA
# ---------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');
.stApp { background-color: #fdfaf5; color: #4a4a4a; font-family: 'Quicksand', sans-serif; }
.main-title { font-size: 3rem; font-weight: 700; color: #6b8e23; text-align: center; margin-top: -30px; }
.stat-box { background: white; border-radius: 15px; padding: 15px; text-align: center;
    box-shadow: 0 8px 16px rgba(139,123,108,0.1); border-bottom: 4px solid #e0d7cd; }
.stat-value { font-size: 2.2rem; font-weight: 800; line-height: 1; margin-bottom: 5px; }
.stat-label { font-size: 0.8rem; color: #a69080; text-transform: uppercase; font-weight: 700; }
.meal-card { background: white; border-radius: 12px; padding: 12px; margin: 5px 0;
    display: flex; justify-content: space-between; align-items: center; border: 1px solid #f0ede9; }
.meal-stats { background: #f1f3eb; color: #6b8e23; padding: 5px 12px; border-radius: 10px;
    font-weight: 700; font-size: 0.85rem; }
.section-header { color: #6b8e23; font-size: 1.3rem; font-weight: 700; margin-top: 20px;
    border-bottom: 2px solid #e9e2d8; }
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
with c2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6b8e23">{total_p:.0f}g</div><div class="stat-label">Białko</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#bc6c25">{total_f:.0f}g</div><div class="stat-label">Tłuszcz</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#4299e1">{total_c:.0f}g</div><div class="stat-label">Węgle</div></div>', unsafe_allow_html=True)
with c5:
    rem = LIMIT_KCAL - total_kcal
    color = "#6b8e23" if rem >= 0 else "#e53e3e"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{rem}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    api_key = st.secrets.get("GEMINI_API_KEY", "") or st.text_input("Klucz Gemini API", type="password")
    usda_key = st.secrets.get("USDA_API_KEY", "DEMO_KEY")
    st.markdown("---")
    st.markdown("**Źródła (kolejność):**")
    st.markdown("1️⃣ 🏠 Moja baza")
    st.markdown("2️⃣ 🔵 Open Food Facts")
    st.markdown("3️⃣ 🟠 USDA")
    st.markdown("4️⃣ 🤖 Gemini~szacunek")
    st.markdown("---")
    st.markdown("**Arkusz:** Dziennik Kalorii")
    if st.button("🔄 Odśwież dane"):
        st.cache_resource.clear()
        st.rerun()

with st.form("meal_form", clear_on_submit=True):
    col_in, col_sel = st.columns([3, 1])
    with col_in:
        food_input = st.text_input("Co dziś zjadłaś?",
            placeholder="np. 2 kromki mojego chleba z finuu, jajko sadzone, jogurt piątnica…")
    with col_sel:
        meal_time = st.selectbox("Pora", ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

if submitted and food_input:
    with st.spinner("🔍 Analizuję…"):
        try:
            result = get_nutrition_hybrid(food_input, api_key, usda_key)
            new_meal = {
                "name": result["name"],
                "calories": result["calories"],
                "protein": result["protein"],
                "fat": result["fat"],
                "carbs": result["carbs"],
                "time": meal_time,
            }
            save_meal(new_meal)
            st.cache_resource.clear()
            st.success(
                f"✅ **{result['name']}** — "
                f"**{result['calories']} kcal** | "
                f"B:{result['protein']:.0f}g T:{result['fat']:.0f}g W:{result['carbs']:.0f}g"
            )
            with st.expander("🔍 Skąd pobrano dane?"):
                for s in result["sources_used"]:
                    st.caption(f"✔ {s}")
                for fi in result["fallback"]:
                    st.caption(f"⚠️ {fi}")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd: {e}")

st.markdown('<div class="section-header">Dzisiejsze Menu</div>', unsafe_allow_html=True)
if today_meals:
    for cat in ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"]:
        cat_meals = [m for m in today_meals if m["time"] == cat]
        if cat_meals:
            st.write(f"**{cat}**")
            for m in cat_meals:
                col1, col2 = st.columns([8, 1])
                with col1:
                    st.markdown(
                        f'<div class="meal-card"><span>{m["name"]}</span>'
                        f'<span class="meal-stats">{m["calories"]} kcal | '
                        f'B:{m["protein"]:.0f}g T:{m["fat"]:.0f}g W:{m["carbs"]:.0f}g'
                        f'</span></div>', unsafe_allow_html=True)
                with col2:
                    if st.button("🗑️", key=f"del_{m['_row']}"):
                        delete_meal_by_row(m["_row"])
                        st.cache_resource.clear()
                        st.rerun()
else:
    st.info("Dodaj swój pierwszy posiłek powyżej!")

if today_meals:
    st.write("")
    col_sum, col_info = st.columns([2, 5])
    with col_sum:
        if st.button("📊 Zapisz podsumowanie dnia do arkusza", use_container_width=True):
            with st.spinner("Zapisuję…"):
                total = save_daily_summary(today_meals)
                if total is not None:
                    st.cache_resource.clear()
                    st.success(f"✅ Suma dnia: **{total} kcal** zapisana.")
    with col_info:
        first_meal = min(today_meals, key=lambda m: m["_row"])
        if first_meal.get("suma_dnia"):
            st.info(f"📋 Ostatnie podsumowanie: **{first_meal['suma_dnia']}**")
        else:
            st.caption("💡 Kliknij gdy skończyłaś dodawać posiłki.")

st.write("")
st.markdown('<div class="section-header">Podsumowanie Tygodnia</div>', unsafe_allow_html=True)
if history:
    week_data = {}
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        week_data[d.strftime("%d.%m")] = sum(
            m["calories"] for m in history if m["date"] == str(d))
    st.bar_chart(week_data)
    st.write(f"Średnia z 7 dni: **{sum(week_data.values())/7:.0f} kcal**")
