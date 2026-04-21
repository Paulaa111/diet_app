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

SHEET_NAME = "Dziennik Kalorii"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
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
        sheet = get_sheet()
        rows = sheet.get_all_records()
        meals = []
        for idx, r in enumerate(rows):
            meals.append({
                "id":        str(r.get("Data",""))+"_"+str(r.get("Pora",""))+"_"+str(r.get("Nazwa","")),
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
        st.error(f"❌ Błąd połączenia z Google Sheets: {e}")
        return []

def save_meal(meal_dict):
    try:
        sheet = get_sheet()
        days_pl = ["Poniedziałek","Wtorek","Środa","Czwartek","Piątek","Sobota","Niedziela"]
        row = [
            days_pl[date.today().weekday()],
            str(date.today()),
            meal_dict.get("time", ""),
            meal_dict.get("name", ""),
            meal_dict.get("calories", 0),
            round(meal_dict.get("protein", 0), 1),
            round(meal_dict.get("fat", 0), 1),
            round(meal_dict.get("carbs", 0), 1),
            "",
        ]
        sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        st.error(f"❌ Nie udało się zapisać: {e}")

def save_daily_summary(today_meals):
    try:
        sheet = get_sheet()
        total   = sum(m["calories"] for m in today_meals)
        total_p = sum(m.get("protein", 0) for m in today_meals)
        total_f = sum(m.get("fat", 0) for m in today_meals)
        total_c = sum(m.get("carbs", 0) for m in today_meals)
        first_row = min(m["_row"] for m in today_meals)
        summary_text = f"{total} kcal | B:{total_p:.0f}g T:{total_f:.0f}g W:{total_c:.0f}g"
        sheet.update_cell(first_row, 9, summary_text)
        for m in today_meals:
            if m["_row"] != first_row:
                sheet.update_cell(m["_row"], 9, "")
        return total
    except Exception as e:
        st.error(f"❌ Nie udało się zapisać podsumowania: {e}")
        return None

def delete_meal_by_row(row_number):
    try:
        get_sheet().delete_rows(row_number)
    except Exception as e:
        st.error(f"❌ Nie udało się usunąć wiersza: {e}")

# ---------------------------------------------------------------
# WYSZUKIWANIE W LOKALNEJ BAZIE database.py
# ---------------------------------------------------------------
def lookup_in_db(name_ai: str, amount_g: float) -> dict | None:
    """
    Szuka produktu w MY_FOOD_DB.
    Dwa poziomy dopasowania — celowo ostrożne żeby uniknąć fałszywych trafień:
      1. Dokładne dopasowanie klucza
      2. Klucz bazy zawiera się w nazwie AI LUB nazwa AI zawiera się w kluczu
         — ale TYLKO jeśli dopasowany fragment ma >= 2 słowa lub >= 8 znaków
    """
    name_lower = name_ai.lower().strip()

    # Poziom 1 — dokładne dopasowanie
    if name_lower in MY_FOOD_DB:
        db_val = MY_FOOD_DB[name_lower]
        factor = amount_g / 100
        return {
            "calories": round(db_val["kcal"] * factor),
            "protein":  round(db_val["p"] * factor, 1),
            "fat":      round(db_val["f"] * factor, 1),
            "carbs":    round(db_val["c"] * factor, 1),
            "source_label": f"🏠 Moja baza ({name_lower})",
        }

    # Poziom 2 — częściowe dopasowanie (ostrożne)
    best_key    = None
    best_length = 0

    for key in MY_FOOD_DB:
        matched_fragment = None

        if key in name_lower:
            matched_fragment = key
        elif name_lower in key:
            matched_fragment = name_lower

        if matched_fragment:
            words = matched_fragment.split()
            if len(words) >= 2 or len(matched_fragment) >= 8:
                if len(matched_fragment) > best_length:
                    best_length = len(matched_fragment)
                    best_key = key

    if not best_key:
        return None

    db_val = MY_FOOD_DB[best_key]
    factor = amount_g / 100
    return {
        "calories": round(db_val["kcal"] * factor),
        "protein":  round(db_val["p"] * factor, 1),
        "fat":      round(db_val["f"] * factor, 1),
        "carbs":    round(db_val["c"] * factor, 1),
        "source_label": f"🏠 Moja baza ({best_key})",
    }

# ---------------------------------------------------------------
# GEMINI — helpery
# ---------------------------------------------------------------
# Lista modeli — próbujemy po kolei gdy poprzedni jest niedostępny
GEMINI_MODELS = [
    "gemini-2.5-flash",       # główny
    "gemini-2.5-flash-lite",  # lżejszy fallback
    "gemini-2.0-flash",       # ostateczna rezerwa
]

def _gemini_url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def _gemini_headers(api_key: str) -> dict:
    """Zwraca nagłówki HTTP dla Gemini API (klucz w nagłówku, nie w URL)."""
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

def _gemini_post(payload: dict, api_key: str, timeout: int = 30) -> dict:
    """
    Wysyła żądanie do Gemini.
    Próbuje kolejno modele z GEMINI_MODELS.
    Obsługuje 429 (rate limit) i 503 (przeciążenie serwera).
    Przy 503 czeka dłużej (serwer jest przeciążony) i przechodzi do następnego modelu.
    """
    last_error = None
    for model in GEMINI_MODELS:
        for attempt in range(3):
            try:
                resp = requests.post(
                    _gemini_url(model),
                    headers=_gemini_headers(api_key),
                    json=payload,
                    timeout=timeout,
                )
                if resp.status_code == 429:
                    # Rate limit — czekaj i spróbuj ponownie ten sam model
                    time.sleep(2 ** attempt)
                    continue
                if resp.status_code == 503:
                    # Serwer przeciążony — krótka przerwa, potem następny model
                    time.sleep(3 * (attempt + 1))  # 3s, 6s, 9s
                    if attempt == 2:
                        break  # po 3 próbach przejdź do następnego modelu
                    continue
                if resp.status_code == 404:
                    # Model nie istnieje — od razu następny
                    last_error = f"Model {model} nie istnieje (404)"
                    break
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.Timeout:
                last_error = f"Timeout dla modelu {model}"
                time.sleep(2)
                break  # przejdź do następnego modelu
            except requests.exceptions.HTTPError as e:
                last_error = str(e)
                if resp.status_code in (400, 401, 403):
                    raise  # błędy autoryzacji — nie próbuj innych modeli
                break  # inny błąd HTTP — spróbuj następnego modelu
        else:
            # Wszystkie 3 próby dla tego modelu zakończyły się 429
            last_error = f"Rate limit dla modelu {model}"
    raise Exception(f"Gemini API niedostępne. Ostatni błąd: {last_error}")

# ---------------------------------------------------------------
# GEMINI — klasyfikacja składników
# ---------------------------------------------------------------

# Słownik domyślnych porcji — nadpisuje wartości z Gemini dla znanych produktów
# Zapobiega halucynacjom AI w gramaturach (np. "800g kromki chleba")
DEFAULT_PORTIONS = {
    "chleb z otrębami":               80,   # 1 kromka
    "mój chleb":                      80,
    "chleb twarogowy":                80,
    "chleb własny":                   80,
    "chleb żytni":                    80,
    "bułka pszenna":                 100,
    "finuu klasyczne":                10,   # 1 łyżeczka do smarowania
    "finuu lekkie":                   10,
    "masło ekstra":                   10,
    "oliwa z oliwek":                 10,
    "jajko kurze":                    60,   # 1 sztuka
    "jajko sadzone":                  60,
    "jogurt naturalny piątnica 2%":  150,
    "jogurt naturalny piątnica 0%":  150,
    "skyr naturalny":                150,
    "twaróg półtłusty":              100,
    "mleko 2%":                      200,
    "kawa czarna":                   150,
    "herbata":                       200,
}

def classify_with_gemini(food_description: str, api_key: str) -> list:
    prompt = (
        "Jesteś ekspertem ds. żywienia. Analizujesz opis posiłku po polsku.\n"
        "Zwróć TYLKO czysty JSON — tablicę obiektów, zero tekstu przed/po, zero markdown.\n\n"
        'Format: [{"item": "nazwa", "amount": 100, "source": "USDA", "eng_name": "name"}]\n\n'
        "KRYTYCZNE — pole \"amount\":\n"
        "- WYŁĄCZNIE liczba całkowita (gramy), zakres 5-500\n"
        '- NIE pisz jednostek: 80 TAK, "80g" NIE\n'
        "- 1 kromka chleba=80, 1 jajko=60, 1 lyzka=15, 1 lyzeczka=10,\n"
        "  1 szklanka=240, kubek=250, porcja zupy=350, jogurt kubeczek=150,\n"
        "  smarowanie chleba margaryną/masłem/finuu=10\n\n"
        "Zasady:\n"
        '- source="OFF" → markowe (Danone, Piątnica, Finuu, Zott, Oreo)\n'
        '- source="USDA" → surowce, warzywa, mięso, dania domowe\n'
        "- Kazdy skladnik = osobny obiekt\n"
        "- eng_name: po angielsku, max 3 slowa\n\n"
        "Mapowania nazw (uzyj DOKLADNIE tej nazwy w item):\n"
        '- moj chleb/chleb domowy/chleb twarogowy/chleb wlasny → "chleb z otrębami"\n'
        '- finuu/margaryna finuu → "finuu klasyczne" (lub "finuu lekkie")\n'
        '- jajko/jajka/jajeczko → "jajko kurze"\n'
        '- jajko sadzone → "jajko sadzone"\n\n'
        f"Opis posilku: {food_description}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 512},
    }
    raw_json = _gemini_post(payload, api_key)
    raw = raw_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    start, end = raw.find("["), raw.rfind("]") + 1
    items_list = json.loads(raw[start:end])

    # DEBUG — pokaż co Gemini zwrócił (można usunąć po naprawieniu błędów)
    st.sidebar.markdown("**🔎 DEBUG — Gemini zwrócił:**")
    for it in items_list:
        st.sidebar.code(f"item: '{it.get('item')}' | amount: {it.get('amount')}")

    # Nadpisz amount domyślną porcją dla znanych produktów
    # (zabezpieczenie przed halucynacjami Gemini w gramaturach)
    for it in items_list:
        name_l = it.get("item", "").lower().strip()
        if name_l in DEFAULT_PORTIONS:
            st.sidebar.caption(f"✅ Nadpisuję amount: {name_l} → {DEFAULT_PORTIONS[name_l]}g")
            it["amount"] = DEFAULT_PORTIONS[name_l]
        else:
            st.sidebar.caption(f"⚠️ Brak w DEFAULT_PORTIONS: '{name_l}'")

    return items_list

# ---------------------------------------------------------------
# GEMINI — fallback kalkulator dla pojedynczego składnika
# ---------------------------------------------------------------
def gemini_estimate_single(item_name: str, amount_g: float, api_key: str) -> dict | None:
    prompt = (
        f"Podaj wartości odżywcze dla: {item_name}, porcja {amount_g}g. "
        f"Zwróć TYLKO czysty JSON (bez tekstu, bez markdown): "
        f'{{"calories": 0, "protein": 0, "fat": 0, "carbs": 0}}'
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 100},
    }
    try:
        raw_json = _gemini_post(payload, api_key, timeout=15)
        raw = raw_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        start, end = raw.find("{"), raw.rfind("}") + 1
        data = json.loads(raw[start:end])
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
# Open Food Facts
# ---------------------------------------------------------------
def fetch_from_off(query: str, amount_g: float) -> dict | None:
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10,
            "sort_by": "unique_scans_n",
            "fields": "product_name,nutriments",
        }
        resp = requests.get(url, params=params, timeout=12)
        resp.raise_for_status()
        products = resp.json().get("products", [])
        if not products:
            return None
        best, best_score = None, -1
        for p in products:
            n = p.get("nutriments", {})
            kcal_100 = n.get("energy-kcal_100g")
            if not kcal_100 and n.get("energy_100g"):
                kcal_100 = n["energy_100g"] / 4.184
            if not kcal_100 or kcal_100 <= 0:
                continue
            score = sum([
                n.get("proteins_100g") is not None,
                n.get("fat_100g") is not None,
                n.get("carbohydrates_100g") is not None,
            ])
            if score > best_score:
                best_score = score
                best = (p, n, kcal_100)
        if not best:
            return None
        p, n, kcal_100 = best
        factor = amount_g / 100
        return {
            "calories": round(kcal_100 * factor),
            "protein":  round((n.get("proteins_100g") or 0) * factor, 1),
            "fat":      round((n.get("fat_100g") or 0) * factor, 1),
            "carbs":    round((n.get("carbohydrates_100g") or 0) * factor, 1),
            "source_label": f"🔵 OFF: {p.get('product_name','?')[:30]}",
        }
    except Exception:
        return None

# ---------------------------------------------------------------
# USDA FoodData Central
# ---------------------------------------------------------------
def fetch_from_usda(eng_name: str, amount_g: float, usda_key: str = "DEMO_KEY") -> dict | None:
    try:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        for data_type in ["SR Legacy,Foundation", "Branded"]:
            params = {
                "query":    eng_name,
                "dataType": data_type,
                "pageSize": 5,
                "api_key":  usda_key,
            }
            resp = requests.get(url, params=params, timeout=12)
            resp.raise_for_status()
            foods = resp.json().get("foods", [])
            for food in foods:
                nutrients = {}
                for n in food.get("foodNutrients", []):
                    if not isinstance(n, dict):
                        continue
                    name = n.get("nutrientName")
                    value = n.get("value")
                    if name and isinstance(value, (int, float)):
                        nutrients[name] = value

                kcal = (
                    nutrients.get("Energy") or
                    nutrients.get("Energy (Atwater General Factors)") or
                    nutrients.get("Energy (Atwater Specific Factors)") or 0
                )
                if kcal > 0:
                    factor = amount_g / 100
                    return {
                        "calories": round(kcal * factor),
                        "protein":  round(nutrients.get("Protein", 0) * factor, 1),
                        "fat":      round(nutrients.get("Total lipid (fat)", 0) * factor, 1),
                        "carbs":    round(nutrients.get("Carbohydrate, by difference", 0) * factor, 1),
                        "source_label": f"🟠 USDA: {food.get('description','?')[:30]}",
                    }
        return None
    except Exception:
        return None

# ---------------------------------------------------------------
# PARSOWANIE LOKALNE — bez AI, dla znanych produktów
# ---------------------------------------------------------------

# Słowa kluczowe → nazwa w bazie
KEYWORD_MAP = {
    "mój chleb":        "chleb z otrębami",
    "mojego chleba":    "chleb z otrębami",
    "moje chleba":      "chleb z otrębami",
    "chleb twarogowy":  "chleb z otrębami",
    "chleba twarogowego": "chleb z otrębami",
    "chlebie twarogowym": "chleb z otrębami",
    "chleb własny":     "chleb z otrębami",
    "chleb domowy":     "chleb z otrębami",
    "chleb z otrębami": "chleb z otrębami",
    "finuu klasyczne":  "finuu klasyczne",
    "finuu lekkie":     "finuu lekkie",
    "finuu":            "finuu klasyczne",
    "jajko sadzone":    "jajko sadzone",
    "jajka sadzone":    "jajko sadzone",
    "jajko kurze":      "jajko kurze",
    "jajko":            "jajko kurze",
    "jajka":            "jajko kurze",
    "skyr":             "skyr naturalny",
    "piątnica 2%":      "jogurt naturalny piątnica 2%",
    "piątnica 0%":      "jogurt naturalny piątnica 0%",
    "piątnica":         "jogurt naturalny piątnica 2%",
    "twaróg":           "twaróg półtłusty",
    "masło":            "masło ekstra",
    "kawa":             "kawa czarna",
    "herbata":          "herbata",
    "mleko":            "mleko 2%",
}

def parse_locally(food_description: str) -> list | None:
    """
    Próbuje rozpoznać składniki bez Gemini.
    Zwraca listę itemów lub None jeśli nie rozpozna wszystkiego.
    """
    text = food_description.lower().strip()
    found = []

    # Wyciągnij liczbę z początku (np. "2 jajka" → 2)
    def extract_count(text):
        m = re.match(r"^(\d+)\s+", text)
        return int(m.group(1)) if m else 1

    # Sprawdź każde słowo kluczowe
    matched_any = False
    remaining = text

    # Sortuj od najdłuższego do najkrótszego żeby "jajko sadzone" trafiło przed "jajko"
    for keyword in sorted(KEYWORD_MAP.keys(), key=len, reverse=True):
        if keyword in remaining:
            db_name = KEYWORD_MAP[keyword]
            portion = DEFAULT_PORTIONS.get(db_name, 100)
            # Sprawdź czy jest liczba przed słowem kluczowym
            pattern = r"(\d+)\s*(?:kromk[aię]|sztuk[aię]|szt\.?)?" + re.escape(keyword)
            m = re.search(pattern, remaining)
            count = int(m.group(1)) if m else 1
            amount = portion * count
            found.append({
                "item": db_name,
                "amount": amount,
                "source": "LOCAL",
                "eng_name": db_name,
            })
            remaining = remaining.replace(keyword, "", 1).strip()
            matched_any = True

    return found if matched_any else None


# ---------------------------------------------------------------
# ORKIESTRACJA — pełny pipeline
# ---------------------------------------------------------------
def get_nutrition_hybrid(food_description: str, api_key: str, usda_key: str) -> dict:
    # Najpierw spróbuj lokalnie (szybko, bez AI, bezbłędnie)
    items = parse_locally(food_description)
    if not items:
        # Fallback na Gemini gdy lokalne parsowanie nic nie znalazło
        items = classify_with_gemini(food_description, api_key)

    total = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    sources_used   = []
    fallback_items = []

    MAX_GRAMS = {
        "chleb":      300,
        "masło":       30,
        "finuu":       30,
        "margaryna":   30,
        "olej":        30,
        "oliwa":       30,
        "sól":         10,
        "cukier":      30,
        "miód":        30,
        "dżem":        40,
        "jogurt":     300,
        "mleko":      300,
        "ser":        100,
        "jajko":      180,
        "default":   1000,
    }

    def sanitize_amount(name: str, amount: float) -> float:
        name_l = name.lower()
        for keyword, max_g in MAX_GRAMS.items():
            if keyword == "default":
                continue
            if keyword in name_l:
                if amount > max_g:
                    return max_g
                return amount
        return min(amount, MAX_GRAMS["default"])

    for item in items:
        name_ai  = item.get("item", "").lower()
        # Bezpieczne parsowanie amount — Gemini czasem zwraca "80g" zamiast 80
        raw_amount = item.get("amount", 100)
        try:
            # Usuń wszystkie nie-liczbowe znaki ("80g" → "80", "1.5" → "1.5")
            amount_clean = re.sub(r"[^0-9.]", "", str(raw_amount))
            amount = float(amount_clean) if amount_clean else 100.0
        except (ValueError, TypeError):
            amount = 100.0
        amount = sanitize_amount(name_ai, amount)
        source   = item.get("source", "USDA")
        eng_name = item.get("eng_name", name_ai)

        result = None

        # 1️⃣ Własna baza — zawsze pierwsza
        result = lookup_in_db(name_ai, amount)

        # 2️⃣ API zewnętrzne — tylko gdy brak w bazie
        if not result:
            if source == "OFF":
                result = fetch_from_off(name_ai, amount)
                if not result:
                    result = fetch_from_usda(eng_name, amount, usda_key)
            else:
                result = fetch_from_usda(eng_name, amount, usda_key)
                if not result:
                    result = fetch_from_off(name_ai, amount)

        # 3️⃣ Ostateczny fallback — Gemini szacuje
        if not result:
            result = gemini_estimate_single(name_ai, amount, api_key)

        if result:
            total["calories"] += result["calories"]
            total["protein"]  += result["protein"]
            total["fat"]      += result["fat"]
            total["carbs"]    += result["carbs"]
            sources_used.append(f"{name_ai} ({amount:.0f}g) → {result['source_label']}")
        else:
            fallback_items.append(f"{name_ai} ({amount:.0f}g) — brak danych")

    return {
        "name":         food_description[:60],
        "calories":     total["calories"],
        "protein":      round(total["protein"], 1),
        "fat":          round(total["fat"], 1),
        "carbs":        round(total["carbs"], 1),
        "sources_used": sources_used,
        "fallback":     fallback_items,
    }

# ---------------------------------------------------------------
# STYLIZACJA
# ---------------------------------------------------------------
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

# ---------------------------------------------------------------
# UI
# ---------------------------------------------------------------
st.markdown('<div class="main-title">🥑 Dziennik Makro</div>', unsafe_allow_html=True)

history     = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]

total_kcal = sum(m["calories"] for m in today_meals)
total_p    = sum(m.get("protein", 0) for m in today_meals)
total_f    = sum(m.get("fat", 0) for m in today_meals)
total_c    = sum(m.get("carbs", 0) for m in today_meals)

c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_kcal}</div><div class="stat-label">Kcal</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6b8e23">{total_p:.0f}g</div><div class="stat-label">Białko</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#bc6c25">{total_f:.0f}g</div><div class="stat-label">Tłuszcz</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#4299e1">{total_c:.0f}g</div><div class="stat-label">Węgle</div></div>', unsafe_allow_html=True)
with c5:
    rem   = LIMIT_KCAL - total_kcal
    color = "#6b8e23" if rem >= 0 else "#e53e3e"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{rem}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    api_key  = st.secrets.get("GEMINI_API_KEY", "") or st.text_input("Klucz Gemini API", type="password")
    usda_key = st.secrets.get("USDA_API_KEY", "DEMO_KEY")
    st.markdown("---")
    st.markdown("**Źródła danych (kolejność):**")
    st.markdown("1️⃣ 🏠 **Moja baza** — database.py")
    st.markdown("2️⃣ 🔵 **Open Food Facts** — marki")
    st.markdown("3️⃣ 🟠 **USDA** — surowce")
    st.markdown("4️⃣ 🤖 **Gemini** — ostateczny fallback")
    st.markdown("---")
    st.markdown("**Model:** gemini-2.5-flash")
    st.markdown("**Arkusz:** Dziennik Kalorii")
    if st.button("🔄 Odśwież dane"):
        st.cache_resource.clear()
        st.rerun()

# FORMULARZ
with st.form("meal_form", clear_on_submit=True):
    col_in, col_sel = st.columns([3, 1])
    with col_in:
        food_input = st.text_input(
            "Co dziś zjadłaś?",
            placeholder="np. jogurt piątnica 150g, 2 jajka sadzone, pierogi ruskie 200g…"
        )
    with col_sel:
        meal_time = st.selectbox("Pora", ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

if submitted and food_input:
    with st.spinner("🔍 Analizuję składniki…"):
        try:
            result = get_nutrition_hybrid(food_input, api_key, usda_key)
            new_meal = {
                "name":     result["name"],
                "calories": result["calories"],
                "protein":  result["protein"],
                "fat":      result["fat"],
                "carbs":    result["carbs"],
                "time":     meal_time,
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
                for f_item in result["fallback"]:
                    st.caption(f"⚠️ {f_item}")
            st.rerun()
        except Exception as e:
            st.error(f"Błąd: {e}")

# LISTA POSIŁKÓW
st.markdown('<div class="section-header">Dzisiejsze Menu</div>', unsafe_allow_html=True)
if today_meals:
    for cat in ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"]:
        cat_meals = [m for m in today_meals if m["time"] == cat]
        if cat_meals:
            st.write(f"**{cat}**")
            for m in cat_meals:
                c1, c2 = st.columns([8, 1])
                with c1:
                    st.markdown(
                        f'<div class="meal-card"><span>{m["name"]}</span>'
                        f'<span class="meal-stats">{m["calories"]} kcal | '
                        f'B:{m["protein"]:.0f}g T:{m["fat"]:.0f}g W:{m["carbs"]:.0f}g'
                        f'</span></div>',
                        unsafe_allow_html=True
                    )
                with c2:
                    if st.button("🗑️", key=f"del_{m['_row']}"):
                        delete_meal_by_row(m["_row"])
                        st.cache_resource.clear()
                        st.rerun()
else:
    st.info("Dodaj swój pierwszy posiłek powyżej!")

# PODSUMOWANIE DNIA
if today_meals:
    st.write("")
    col_sum, col_info = st.columns([2, 5])
    with col_sum:
        if st.button("📊 Zapisz podsumowanie dnia do arkusza", use_container_width=True):
            with st.spinner("Zapisuję…"):
                total = save_daily_summary(today_meals)
                if total is not None:
                    st.cache_resource.clear()
                    st.success(f"✅ Suma dnia: **{total} kcal** — zapisana w kolumnie 'Suma dnia'.")
    with col_info:
        first_meal = min(today_meals, key=lambda m: m["_row"])
        if first_meal.get("suma_dnia"):
            st.info(f"📋 Ostatnie podsumowanie: **{first_meal['suma_dnia']}**")
        else:
            st.caption("💡 Kliknij gdy skończyłaś dodawać posiłki.")

# PODSUMOWANIE TYGODNIA
st.write("")
st.markdown('<div class="section-header">Podsumowanie Tygodnia</div>', unsafe_allow_html=True)
if history:
    week_data = {}
    for i in range(6, -1, -1):
        d     = date.today() - timedelta(days=i)
        d_str = str(d)
        day_sum = sum(m["calories"] for m in history if m["date"] == d_str)
        week_data[d.strftime("%d.%m")] = day_sum
    st.bar_chart(week_data)
    avg_kcal = sum(week_data.values()) / 7
    st.write(f"Średnie kalorie z ostatnich 7 dni: **{avg_kcal:.0f} kcal**")
