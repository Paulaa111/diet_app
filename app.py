import streamlit as st
import re
import json
import requests
import time
from datetime import date, timedelta
from database import MY_FOOD_DB

import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------
st.set_page_config(page_title="Dziennik Makro", page_icon="🥑", layout="wide")

SHEET_NAME = "Dziennik Kalorii"
SCOPES     = ["https://www.googleapis.com/auth/spreadsheets",
               "https://www.googleapis.com/auth/drive"]
LIMIT_KCAL = 1500

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
            def _f(v):
                try: return float(str(v or 0).replace(",", "."))
                except: return 0.0
            meals.append({
                "date":      str(r.get("Data", "")),
                "time":      str(r.get("Pora", "")),
                "name":      str(r.get("Nazwa", "")),
                "calories":  int(_f(r.get("Kalorie", 0))),
                "protein":   _f(r.get("Białko", 0)),
                "fat":       _f(r.get("Tłuszcz", 0)),
                "carbs":     _f(r.get("Węglowodany", 0)),
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
        ], value_input_option="RAW")
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
# LOKALNA BAZA — aliasy i porcje
# ---------------------------------------------------------------

# Domyślna gramatura 1 sztuki / 1 jednostki produktu
DEFAULT_GRAMS = {
    "chleb z otrębami":             80,
    "chleb żytni":                  80,
    "bułka pszenna":               100,
    "finuu klasyczne":              10,
    "finuu lekkie":                 10,
    "masło ekstra":                 10,
    "oliwa z oliwek":               10,
    "jajko kurze":                  60,
    "jajko sadzone":                60,
    "jogurt naturalny piątnica 2%": 150,
    "jogurt naturalny piątnica 0%": 150,
    "jogurt zott primo":            150,
    "jogurt danone łagodny":        150,
    "skyr naturalny":               150,
    "twaróg półtłusty":             100,
    "mleko 2%":                     200,
    "kawa czarna":                  150,
    "herbata":                      200,
    "jabłko":                       150,
    "banan":                        120,
    "pomarańcza":                   150,
    # dania obiadowe — typowa porcja na talerzu
    "kotlet schabowy":              170,  # 1 kotlet
    "kotlet mielony":               150,
    "pierogi ruskie":               250,  # porcja ~5 szt
    "pierogi z mięsem":             250,
    "pierogi z owocami":            250,
    "kopytka":                      200,
    "naleśniki z serem":            200,
    "naleśniki z dżemem":           200,
    "placki ziemniaczane":          200,
    "gołąbki w sosie pomidorowym":  300,  # 2 gołąbki
    "gulasz wieprzowy":             250,
    "pizza margherita":             200,  # 2 kawałki ~100g każdy
    "pizza pepperoni":              200,
    "ziemniaki gotowane":           200,
    "ziemniaki z masłem":           200,
    "puree ziemniaczane":           200,
    "frytki":                       150,
    "ryż biały":                    150,
    "ryż brązowy":                  150,
    "kasza gryczana":               150,
    "kasza pęczak":                 150,
    "makaron":                      200,
    "kuskus":                       150,
    "ziemniaki opiekane":           200,
    # mięso i drób
    "pierś z kurczaka pieczona":    150,
    "kurczak w sosie śmietanowym":  250,
    "stek wołowy":                  200,
    "dorsz pieczony":               150,
    "ryba w panierce":              150,
    "leczo z kiełbasą":             300,
    # kiełbasy
    "kiełbasa zwyczajna":           100,
    "kiełbasa wiejska":             100,
    "kiełbasa szynkowa":            100,
    "kiełbasa krakowska sucha":     80,
    "kiełbasa biała parzona":       100,
    "parówki drobiowe":             80,
    "parówki z szynki":             80,
    "kabanosy wieprzowe":           60,
    "kaszanka":                     100,
    "pasztet pieczony":             80,
    # orzechy i inne
    "orzechy włoskie":              30,
    "orzechy laskowe":              30,
    "migdały":                      30,
    "masło orzechowe":              30,
    "awokado":                      150,
    "szpinak":                      100,
    "cukinia":                      150,
    "pomidor":                      120,
    "ogórek":                       150,
    "marchew":                      100,
    "brokuł":                       150,
    # napoje
    "sok pomarańczowy":             200,
    "piwo jasne":                   500,
    "wino czerwone wytrawne":       150,
    "wino białe wytrawne":          150,
    "wódka":                        50,
    # zupy
    "zupa pomidorowa":              350,
    "rosół":                        350,
    "żurek":                        350,
    "barszcz":                      300,
}

# Wszystkie warianty nazw → klucz w MY_FOOD_DB
ALIASES = {
    # chleb
    "chleb z otrębami":           "chleb z otrębami",
    "chleb z otrebami":           "chleb z otrębami",
    "mój chleb":                  "chleb z otrębami",
    "moj chleb":                  "chleb z otrębami",
    "mojego chleba":              "chleb z otrębami",
    "chleba mojego":              "chleb z otrębami",
    "moje chleba":                "chleb z otrębami",
    "chleb twarogowy":            "chleb z otrębami",
    "chleba twarogowego":         "chleb z otrębami",
    "chleb własny":               "chleb z otrębami",
    "chleb wlasny":               "chleb z otrębami",
    "chleb domowy":               "chleb z otrębami",
    "chleb":                      "chleb z otrębami",
    # tłuszcze
    "finuu klasyczne":            "finuu klasyczne",
    "finuu lekkie":               "finuu lekkie",
    "finuu":                      "finuu klasyczne",
    "masło ekstra":               "masło ekstra",
    "maslo ekstra":               "masło ekstra",
    "masło":                      "masło ekstra",
    "maslo":                      "masło ekstra",
    "oliwa z oliwek":             "oliwa z oliwek",
    "oliwa":                      "oliwa z oliwek",
    # jajka
    "jajko sadzone":              "jajko sadzone",
    "jajka sadzone":              "jajko sadzone",
    "jajko kurze":                "jajko kurze",
    "jajka kurze":                "jajko kurze",
    "jajko":                      "jajko kurze",
    "jajka":                      "jajko kurze",
    "jajeczko":                   "jajko kurze",
    # nabiał
    "jogurt naturalny piątnica 2%": "jogurt naturalny piątnica 2%",
    "jogurt naturalny piątnica 0%": "jogurt naturalny piątnica 0%",
    "jogurt piątnica 2%":           "jogurt naturalny piątnica 2%",
    "jogurt piątnica 0%":           "jogurt naturalny piątnica 0%",
    "piątnica 2%":                  "jogurt naturalny piątnica 2%",
    "piatnica 2%":                  "jogurt naturalny piątnica 2%",
    "piątnica 0%":                  "jogurt naturalny piątnica 0%",
    "piatnica 0%":                  "jogurt naturalny piątnica 0%",
    "piątnica":                     "jogurt naturalny piątnica 2%",
    "piatnica":                     "jogurt naturalny piątnica 2%",
    "jogurt zott":                  "jogurt zott primo",
    "zott":                         "jogurt zott primo",
    "jogurt danone":                "jogurt danone łagodny",
    "danone":                       "jogurt danone łagodny",
    "skyr naturalny":               "skyr naturalny",
    "skyr":                         "skyr naturalny",
    "twaróg półtłusty":             "twaróg półtłusty",
    "twarog polttlusty":            "twaróg półtłusty",
    "twaróg":                       "twaróg półtłusty",
    "twarog":                       "twaróg półtłusty",
    "mleko 2%":                     "mleko 2%",
    "mleko":                        "mleko 2%",
    # napoje
    "kawa czarna":                  "kawa czarna",
    "kawa":                         "kawa czarna",
    "herbata":                      "herbata",
    # owoce
    "jabłko":                       "jabłko",
    "jablko":                       "jabłko",
    "banan":                        "banan",
    "pomarańcza":                   "pomarańcza",
    "pomarancza":                   "pomarańcza",
    "truskawki":                    "truskawki",
    "borówki":                      "borówki",
    "borowki":                      "borówki",
    # ziemniaki — różne formy
    "ziemniaki z masłem":           "ziemniaki z masłem",
    "ziemniaki z maslem":           "ziemniaki z masłem",
    "ziemniaków z masłem":          "ziemniaki z masłem",
    "ziemniakow z maslem":          "ziemniaki z masłem",
    "ziemniaki opiekane":           "ziemniaki opiekane",
    "ziemniaki gotowane":           "ziemniaki gotowane",
    "puree":                        "puree ziemniaczane",
    "frytki":                       "frytki",
    # mięso i drób
    "pierś z kurczaka":             "pierś z kurczaka pieczona",
    "piers z kurczaka":             "pierś z kurczaka pieczona",
    "kurczak w sosie":              "kurczak w sosie śmietanowym",
    "stek":                         "stek wołowy",
    "dorsz":                        "dorsz pieczony",
    "ryba w panierce":              "ryba w panierce",
    "leczo":                        "leczo z kiełbasą",
    # kiełbasy
    "kiełbasa zwyczajna":           "kiełbasa zwyczajna",
    "kielbasaw zwyczajna":          "kiełbasa zwyczajna",
    "kiełbasa wiejska":             "kiełbasa wiejska",
    "kiełbasa szynkowa":            "kiełbasa szynkowa",
    "kiełbasa krakowska":           "kiełbasa krakowska sucha",
    "kielbasa krakowska":           "kiełbasa krakowska sucha",
    "kiełbasa biała":               "kiełbasa biała parzona",
    "kielbasa biala":               "kiełbasa biała parzona",
    "parówki z szynki":             "parówki z szynki",
    "parowki z szynki":             "parówki z szynki",
    "parówki drobiowe":             "parówki drobiowe",
    "parowki drobiowe":             "parówki drobiowe",
    "parówki":                      "parówki drobiowe",
    "parowki":                      "parówki drobiowe",
    "kabanosy":                     "kabanosy wieprzowe",
    "kaszanka":                     "kaszanka",
    "pasztet":                      "pasztet pieczony",
    # orzechy
    "orzechy włoskie":              "orzechy włoskie",
    "orzechy wloskie":              "orzechy włoskie",
    "orzechy laskowe":              "orzechy laskowe",
    "migdały":                      "migdały",
    "migdaly":                      "migdały",
    "masło orzechowe":              "masło orzechowe",
    "maslo orzechowe":              "masło orzechowe",
    # napoje i alkohole
    "sok pomarańczowy":             "sok pomarańczowy",
    "sok pomaranczowy":             "sok pomarańczowy",
    "sok":                          "sok pomarańczowy",
    "koktajl":                      "koktajl owocowy (na mleku)",
    "piwo":                         "piwo jasne",
    "wino czerwone":                "wino czerwone wytrawne",
    "wino białe":                   "wino białe wytrawne",
    "wino":                         "wino czerwone wytrawne",
    "wódka":                        "wódka",
    "wodka":                        "wódka",
    # warzywa
    "pomidor":                      "pomidor",
    "pomidora":                     "pomidor",
    "ogórek":                       "ogórek",
    "ogorek":                       "ogórek",
    "marchew":                      "marchew",
    "marchewka":                    "marchew",
    "cukinia":                      "cukinia",
    "cukinii":                      "cukinia",
    "brokuł":                       "brokuł",
    "brokul":                       "brokuł",
    "szpinak":                      "szpinak",
    "awokado":                      "awokado",
    # pieczywo
    "chleb żytni":                  "chleb żytni",
    "chleb zytni":                  "chleb żytni",
    "bułka":                        "bułka pszenna",
    "bulka":                        "bułka pszenna",
}

# Przeliczniki jednostek → gramy na 1 jednostkę
UNITS = {
    "g":           1,   "gram":       1,   "gramy":      1,   "gramów":     1,
    "ml":          1,
    "dag":        10,
    "kg":       1000,
    "łyżeczka":    5,   "łyżeczki":   5,   "lyżeczka":   5,
    "łyżka":      15,   "łyżki":     15,   "lyżka":     15,   "łyżek":     15,
    "kromka":     80,   "kromki":    80,   "kromek":    80,
    "plasterek":  40,   "plasterki": 40,   "plasterków": 40,
    "kawałek":    80,   "kawałki":   80,   "kawalek":   80,
    "sztuka":     60,   "sztuki":    60,   "sztuk":     60,   "szt":       60,
    "szklanka":  240,   "szklanki":  240,  "szklanek":  240,
    "kubek":     250,   "kubki":     250,
    "porcja":    200,   "porcje":    200,  "porcji":    200,
    "talerz":    300,   "miseczka":  200,  "garść":      30,
    "plasterek": 40,
}

# Odmiana przez przypadki — końcówki fleksyjne polskich słów
# "pizzy" -> "pizza", "kawałki" -> już w UNITS, "ziemniaków" -> "ziemniaki"
POLISH_STEMS = {
    "pizzy":         "pizza",
    "pizy":          "pizza",       # literówka
    "pizyy":         "pizza",       # literówka
    "margarity":     "margherita",  # literówka
    "margherity":    "margherita",
    "pepperoni":     "pepperoni",
    "ziemniaków":    "ziemniaki",
    "ziemniakow":    "ziemniaki",
    "ziemniaka":     "ziemniaki",
    "pierogi":       "pierogi ruskie",
    "pierogów":      "pierogi ruskie",
    "pierogow":      "pierogi ruskie",
    "schabowego":    "kotlet schabowy",
    "schabowe":      "kotlet schabowy",
    "schabowy":      "kotlet schabowy",
    "schabow":       "kotlet schabowy",
    "schabu":        "schab",
    "kotleta":       "kotlet schabowy",
    "kotlety":       "kotlet schabowy",
    "kotletów":      "kotlet schabowy",
    "mielonego":     "kotlet mielony",
    "mielone":       "kotlet mielony",
    "gulaszu":       "gulasz wieprzowy",
    "pieczeń":       "schab",
    "ziemniaka":     "ziemniaki gotowane",
    "ziemniaki":     "ziemniaki gotowane",
    "ziemniaków":    "ziemniaki gotowane",
    "ziemniakow":    "ziemniaki gotowane",
    "frytki":        "frytki",
    "frytek":        "frytki",
    "puree":         "puree ziemniaczane",
    "kopytka":       "kopytka",
    "kopytek":       "kopytka",
    "naleśniki":     "naleśniki z serem",
    "naleśnik":      "naleśniki z serem",
    "nalesniki":     "naleśniki z serem",
    "pierogi":       "pierogi ruskie",
    "pierogów":      "pierogi ruskie",
    "pierogow":      "pierogi ruskie",
    "gołąbki":       "gołąbki w sosie pomidorowym",
    "golabki":       "gołąbki w sosie pomidorowym",
    "gołąbka":       "gołąbki w sosie pomidorowym",
    "golabka":       "gołąbki w sosie pomidorowym",
    "ryżu":          "ryż biały",
    "ryzu":          "ryż biały",
    "makaronu":      "makaron",
    "kaszy":         "kasza gryczana",
    "marchewki":     "marchew",
    "marchewkę":     "marchew",
    "ogórka":        "ogórek",
    "ogorka":        "ogórek",
    "pomidora":      "pomidor",
    "papryki":       "papryka",
    "cebuli":        "cebula",
    "brokułu":       "brokuł",
    "brokulu":       "brokuł",
    "jabłka":        "jabłko",
    "jablka":        "jabłko",
    "banana":        "banan",
    "truskawek":     "truskawki",
    "borówek":            "borówki",
    "borowek":            "borówki",
    # ziemniaki z masłem
    "ziemniaki z masłem": "ziemniaki z masłem",
    "ziemniaków z masłem":"ziemniaki z masłem",
    # mięso
    "kurczaka":           "pierś z kurczaka pieczona",
    "piersi":             "pierś z kurczaka pieczona",
    "steka":              "stek wołowy",
    "dorsza":             "dorsz pieczony",
    # kiełbasy
    "kiełbasę":           "kiełbasa zwyczajna",
    "kielbasy":           "kiełbasa zwyczajna",
    "parówek":            "parówki drobiowe",
    "parowek":            "parówki drobiowe",
    "kabanosów":          "kabanosy wieprzowe",
    "kabanosow":          "kabanosy wieprzowe",
    "pasżtetu":           "pasztet pieczony",
    "pasztetu":           "pasztet pieczony",
    # warzywa
    "cukinii":            "cukinia",
    "szpinaku":           "szpinak",
    "awokado":            "awokado",
    "pomidora":           "pomidor",
    "pomidory":           "pomidor",
    # napoje
    "piwa":               "piwo jasne",
    "wina":               "wino czerwone wytrawne",
    "wódki":              "wódka",
    "wodki":              "wódka",
    # orzechy
    "orzechów":           "orzechy włoskie",
    "orzechow":           "orzechy włoskie",
    "migdałów":           "migdały",
    "migdalow":           "migdały",
}

def normalize_polish(text: str) -> str:
    """
    Zamienia polskie końcówki fleksyjne na mianownik.
    np. "2 kawałki pizzy margarity" -> "2 kawałki pizza margherita"
    """
    words = text.split()
    result = []
    for w in words:
        result.append(POLISH_STEMS.get(w, w))
    return " ".join(result)

def resolve_product(raw: str) -> str | None:
    """Zamienia surowy tekst na klucz w MY_FOOD_DB. Zwraca None jeśli nie znalazło."""
    raw = raw.strip().lower()

    # 1. Bezpośrednie trafienie w bazie
    if raw in MY_FOOD_DB:
        return raw

    # 2. Alias (od najdłuższego)
    for alias in sorted(ALIASES.keys(), key=len, reverse=True):
        if alias in raw:
            return ALIASES[alias]

    # 3. Normalizacja polskich końcówek + ponowne próby
    normalized = normalize_polish(raw)
    if normalized != raw:
        if normalized in MY_FOOD_DB:
            return normalized
        for alias in sorted(ALIASES.keys(), key=len, reverse=True):
            if alias in normalized:
                return ALIASES[alias]
        for key in sorted(MY_FOOD_DB.keys(), key=len, reverse=True):
            if key in normalized or normalized in key:
                return key

    # 4. Częściowe dopasowanie po pierwszym słowie
    # np. "pizzy margarity" -> pierwsze słowo "pizzy" -> stem "pizza" -> szukaj kluczy zaczynających się od "pizza"
    first_word = raw.split()[0] if raw.split() else raw
    first_normalized = POLISH_STEMS.get(first_word, first_word)
    for key in sorted(MY_FOOD_DB.keys(), key=len, reverse=True):
        if key.startswith(first_normalized):
            return key

    # 5. Ogólne częściowe dopasowanie
    for key in sorted(MY_FOOD_DB.keys(), key=len, reverse=True):
        if key in raw or raw in key:
            return key

    return None

def parse_meal_locally(text: str) -> tuple[list, list]:
    """
    Parsuje tekst i zwraca:
    - found: lista (db_key, gramy) dla produktów znalezionych w bazie
    - unknown: lista surowych tekstów których nie rozpoznano

    Separator składników: przecinek LUB ' i ' LUB ' oraz '
    Obsługuje:
      "2 kromki chleba"          → (chleb z otrębami, 160g)
      "łyżka finuu"              → (finuu klasyczne, 15g)
      "150g jogurtu piątnica"    → (jogurt naturalny piątnica 2%, 150g)
      "jajko"                    → (jajko kurze, 60g)
      "2 kawałki pizzy"          → unknown → idzie do Gemini
    """
    # Podziel na składniki po separatorach
    parts = re.split(r',|\bi\b|\boraz\b', text.lower())
    parts = [p.strip() for p in parts if p.strip()]

    found   = []
    unknown = []
    unit_pat = "|".join(re.escape(u) for u in sorted(UNITS.keys(), key=len, reverse=True))

    for part in parts:
        grams   = None
        product = None

        # Wzór A: liczba + jednostka + produkt  → "2 kromki mojego chleba"
        m = re.match(
            rf'^(\d+(?:[.,]\d+)?)\s+({unit_pat})\s+(.+)$',
            part, re.IGNORECASE | re.UNICODE
        )
        if m:
            count   = float(m.group(1).replace(",", "."))
            unit    = m.group(2).lower()
            raw     = m.group(3).strip()
            grams   = UNITS[unit] * count
            product = resolve_product(raw)

        # Wzór B: liczba + "g"/"ml" bezpośrednio (np. "150g jogurtu")
        if not product:
            m = re.match(
                r'^(\d+(?:[.,]\d+)?)\s*(g|ml|dag|kg)\s+(.+)$',
                part, re.IGNORECASE
            )
            if m:
                count   = float(m.group(1).replace(",", "."))
                unit    = m.group(2).lower()
                raw     = m.group(3).strip()
                grams   = UNITS[unit] * count
                product = resolve_product(raw)

        # Wzór C: jednostka (bez liczby) + produkt  → "łyżka finuu"
        if not product:
            m = re.match(
                rf'^({unit_pat})\s+(.+)$',
                part, re.IGNORECASE | re.UNICODE
            )
            if m:
                unit    = m.group(1).lower()
                raw     = m.group(2).strip()
                grams   = UNITS[unit] * 1
                product = resolve_product(raw)

        # Wzór D: liczba + produkt (bez jednostki)  → "2 jajka", "3 jabłka"
        if not product:
            m = re.match(r'^(\d+)\s+(.+)$', part, re.IGNORECASE | re.UNICODE)
            if m:
                count   = int(m.group(1))
                raw     = m.group(2).strip()
                product = resolve_product(raw)
                if product:
                    unit_g = DEFAULT_GRAMS.get(product, 100)
                    grams  = unit_g * count

        # Wzór E: sam produkt (bez liczby i jednostki)  → "finuu", "jajko"
        if not product:
            product = resolve_product(part)
            if product:
                grams = DEFAULT_GRAMS.get(product, 100)

        if product and product in MY_FOOD_DB:
            found.append((product, grams or DEFAULT_GRAMS.get(product, 100)))
        else:
            unknown.append(part)

    return found, unknown

# ---------------------------------------------------------------
# GEMINI — fallback dla nieznanych produktów
# ---------------------------------------------------------------
GEMINI_MODELS = ["gemini-1.5-flash", "gemini-2.0-flash"]

def _gemini_post(prompt: str, api_key: str, max_tokens: int = 512) -> str:
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
                    time.sleep(2); break
                resp.raise_for_status()
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                last_err = str(e); time.sleep(1); break
    raise Exception(f"Gemini niedostępne: {last_err}")

def gemini_estimate(items: list[str], api_key: str) -> list[dict]:
    """
    Wysyła listę nieznanych składników do Gemini.
    Zwraca listę słowników z kaloriami i makro.
    Naprawiona wersja: jawne przykłady żeby Gemini nie mylił porcji z wartościami na 100g.
    """
    if not items:
        return []

    items_text = "\n".join(f"- {it}" for it in items)

    prompt = f"""Jesteś polskim dietetykiem. Oblicz wartości odżywcze dla podanych składników.

ZWRÓĆ TYLKO czysty JSON — tablicę obiektów. Zero tekstu przed/po. Zero markdown.

Format każdego obiektu:
{{"item": "poprawna nazwa produktu", "grams": 150, "calories": 375, "protein": 12.0, "fat": 14.0, "carbs": 48.0}}

KRYTYCZNE ZASADY:
1. "grams" = rzeczywista gramatura porcji z opisu (np. "2 kawałki pizzy" = 2 × 125g = 250g)
2. "calories/protein/fat/carbs" = wartości dla TEJ gramatury, NIE na 100g
3. Jeśli brak gramatury — użyj typowej polskiej porcji
4. Popraw literówki w nazwach (np. "pizyy" = "pizza")
5. Każdy składnik = osobny obiekt w tablicy

PRZYKŁAD:
Wejście: "2 kawałki pizzy margherita"
Wyjście: [{{"item": "pizza margherita", "grams": 250, "calories": 625, "protein": 22.0, "fat": 22.5, "carbs": 80.0}}]

WERYFIKACJA: calories musi być > 50 dla każdej normalnej porcji jedzenia.

Składniki do obliczenia:
{items_text}"""

    try:
        raw  = _gemini_post(prompt, api_key)
        raw  = raw.replace("```json","").replace("```","").strip()
        s, e = raw.find("["), raw.rfind("]") + 1
        data = json.loads(raw[s:e])

        # Walidacja — odrzuć wyniki z absurdalnie małymi kaloriami
        validated = []
        for item in data:
            kcal  = float(item.get("calories", 0))
            grams = float(item.get("grams", 100))
            # Jeśli kalorie < 10 a gramatura > 50g — prawdopodobnie Gemini dał wartości na 1g zamiast porcję
            if kcal < 10 and grams > 50:
                # Przemnóż przez gramaturę (zakładamy że dał na 100g)
                factor = grams / 100
                item["calories"] = round(kcal * factor * 100)  # kcal było na 100g
                item["protein"]  = round(float(item.get("protein", 0)) * factor * 100, 1)
                item["fat"]      = round(float(item.get("fat", 0)) * factor * 100, 1)
                item["carbs"]    = round(float(item.get("carbs", 0)) * factor * 100, 1)
            validated.append(item)

        return validated
    except Exception as e:
        st.warning(f"⚠️ Gemini: {e}")
        return []

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

history     = load_data()
today_meals = [m for m in history if m["date"] == str(date.today())]
total_kcal  = sum(m["calories"] for m in today_meals)
total_p     = sum(m.get("protein", 0) for m in today_meals)
total_f     = sum(m.get("fat", 0) for m in today_meals)
total_c     = sum(m.get("carbs", 0) for m in today_meals)

c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f'<div class="stat-box"><div class="stat-value">{total_kcal}</div><div class="stat-label">Kcal</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6b8e23">{total_p:.0f}g</div><div class="stat-label">Białko</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#bc6c25">{total_f:.0f}g</div><div class="stat-label">Tłuszcz</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#4299e1">{total_c:.0f}g</div><div class="stat-label">Węgle</div></div>', unsafe_allow_html=True)
with c5:
    rem   = LIMIT_KCAL - total_kcal
    color = "#6b8e23" if rem >= 0 else "#e53e3e"
    st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:{color}">{rem}</div><div class="stat-label">Zostało</div></div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Ustawienia")
    api_key = st.secrets.get("GEMINI_API_KEY", "") or st.text_input("Klucz Gemini API", type="password")
    st.markdown("---")
    st.markdown("**Jak wpisywać:**")
    st.markdown("Oddzielaj składniki **przecinkiem** lub **' i '**")
    st.markdown("```\n2 kromki chleba, łyżka finuu\njajko sadzone, 150g jogurtu piątnica\n2 kawałki pizzy margherita\n```")
    st.markdown("---")
    st.markdown("**Źródła:**")
    st.markdown("1️⃣ 🏠 Moja baza — szybko i dokładnie")
    st.markdown("2️⃣ 🤖 Gemini — gdy brak w bazie")
    st.markdown("---")
    if st.button("🔄 Odśwież dane"):
        st.cache_resource.clear()
        st.rerun()

with st.form("meal_form", clear_on_submit=True):
    food_input = st.text_input(
        "Co dziś zjadłaś?",
        placeholder="np. 2 kromki chleba, łyżka finuu, jajko sadzone"
    )
    meal_time = st.selectbox("Pora", ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

if submitted and food_input:
    with st.spinner("🔍 Analizuję…"):

        # KROK 1: Parsuj lokalnie
        found, unknown = parse_meal_locally(food_input)

        total   = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        details = []

        # KROK 2: Policz kalorie z bazy lokalnej
        for db_key, grams in found:
            v = MY_FOOD_DB[db_key]
            f = grams / 100
            kcal = round(v["kcal"] * f)
            p    = round(v["p"] * f, 1)
            fat  = round(v["f"] * f, 1)
            c    = round(v["c"] * f, 1)
            total["calories"] += kcal
            total["protein"]  += p
            total["fat"]      += fat
            total["carbs"]    += c
            details.append(f"🏠 **{db_key}** ({grams:.0f}g) → {kcal} kcal | B:{p}g T:{fat}g W:{c}g")

        # KROK 3: Nieznane → Gemini
        if unknown and api_key:
            gemini_results = gemini_estimate(unknown, api_key)
            for g in gemini_results:
                kcal = int(g.get("calories", 0))
                p    = round(float(g.get("protein", 0)), 1)
                fat  = round(float(g.get("fat", 0)), 1)
                c    = round(float(g.get("carbs", 0)), 1)
                grams = float(g.get("grams", 100))
                name  = g.get("item", "?")
                total["calories"] += kcal
                total["protein"]  += p
                total["fat"]      += fat
                total["carbs"]    += c
                details.append(f"🤖 **{name}** ({grams:.0f}g) → {kcal} kcal | B:{p}g T:{fat}g W:{c}g")
        elif unknown and not api_key:
            for u in unknown:
                details.append(f"⚠️ **{u}** — brak w bazie, dodaj klucz Gemini w ustawieniach")

        if total["calories"] == 0 and not found:
            st.error("❌ Nie rozpoznano żadnego składnika. Użyj przecinka między produktami.")
        else:
            new_meal = {
                "name":     food_input[:50],
                "calories": total["calories"],
                "protein":  round(total["protein"], 1),
                "fat":      round(total["fat"], 1),
                "carbs":    round(total["carbs"], 1),
                "time":     meal_time,
            }
            save_meal(new_meal)
            st.cache_resource.clear()
            st.success(
                f"✅ **{total['calories']} kcal** | "
                f"B:{total['protein']:.0f}g T:{total['fat']:.0f}g W:{total['carbs']:.0f}g"
            )
            with st.expander("📊 Szczegóły składników"):
                for d in details:
                    st.markdown(d)
            st.rerun()

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
                        f'</span></div>', unsafe_allow_html=True)
                with c2:
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
                total_val = save_daily_summary(today_meals)
                if total_val is not None:
                    st.cache_resource.clear()
                    st.success(f"✅ Suma dnia: **{total_val} kcal** zapisana.")
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
