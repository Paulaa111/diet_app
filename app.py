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
    # --- pieczywo ---
    "chleb z otrębami":             80,
    "chleb żytni":                  80,
    "bułka pszenna":               100,
    "bagietka":                    100,
    "tortilla pszenna":             60,
    "chleb tostowy":                30,   # 1 kromka
    # --- tłuszcze ---
    "finuu klasyczne":              10,
    "finuu lekkie":                 10,
    "masło ekstra":                 10,
    "oliwa z oliwek":               10,
    # --- jajka ---
    "jajko kurze":                  60,
    "jajko sadzone":                60,
    "jajko gotowane":               60,
    # --- nabiał ---
    "jogurt naturalny piątnica 2%": 150,
    "jogurt naturalny piątnica 0%": 150,
    "jogurt zott primo":            150,
    "jogurt danone łagodny":        150,
    "skyr naturalny":               150,
    "twaróg półtłusty":             100,
    "mleko 2%":                     200,
    "serek łaciaty do smarowania":   30,
    "mozzarella":                   125,
    # --- śniadania ---
    "owsianka na wodzie":           250,
    "owsianka na mleku":            250,
    "płatki owsiane":                60,
    "musli bez cukru":               60,
    "granola":                       50,
    # --- napoje ---
    "kawa czarna":                  150,
    "kawa z mlekiem":               200,
    "herbata":                      200,
    "herbata z miodem":             200,
    "sok pomarańczowy":             200,
    "koktajl owocowy (na mleku)":   300,
    "miód":                          10,
    # --- alkohole ---
    "piwo jasne":                   500,
    "wino czerwone wytrawne":       150,
    "wino białe wytrawne":          150,
    "wódka":                         50,
    # --- owoce ---
    "jabłko":                       150,
    "banan":                        120,
    "pomarańcza":                   150,
    "mandarynka":                    80,
    "gruszka":                      150,
    "kiwi":                          80,
    "truskawki":                    150,
    "borówki":                      100,
    "maliny":                       100,
    "jeżyny":                       100,
    "winogrona":                    100,
    "arbuz":                        250,
    "melon":                        200,
    "ananas":                       150,
    "awokado":                      150,
    # --- warzywa ---
    "pomidor":                      120,
    "ogórek":                       150,
    "marchew":                      100,
    "cukinia":                      150,
    "brokuł":                       150,
    "szpinak":                      100,
    "cebula":                        80,
    "papryka czerwona":             150,
    "papryka zielona":              150,
    "papryka marynowana":           100,
    "kapusta biała":                150,
    "kapusta kiszona":              100,
    "kalafior":                     150,
    "bakłażan":                     200,
    "fasolka szparagowa":           150,
    "sałata lodowa":                 80,
    "rukola":                        50,
    "burak":                        100,
    "pieczarki":                    100,
    "kukurydza konserwowa":          80,
    "groszek konserwowy":            80,
    # --- orzechy ---
    "orzechy włoskie":               30,
    "orzechy laskowe":               30,
    "migdały":                       30,
    "masło orzechowe":               30,
    "nerkowce":                      30,
    "pistacje":                      30,
    "orzeszki ziemne":               30,
    # --- mięso i drób ---
    "pierś z kurczaka pieczona":    150,
    "udko z kurczaka pieczone":     200,
    "drumstick kurczak":            150,
    "kurczak pieczony cały":        250,
    "kurczak w sosie śmietanowym":  250,
    "kotlet schabowy":              170,
    "kotlet mielony":               150,
    "stek wołowy":                  200,
    "gulasz wieprzowy":             250,
    "boczek wędzony":               50,
    "boczek pieczony":              80,
    "gołąbki w sosie pomidorowym":  150,
    "leczo z kiełbasą":             300,
    "dorsz pieczony":               150,
    "ryba w panierce":              150,
    "tuńczyk w oleju":              100,
    "tuńczyk w wodzie":             100,
    "łosoś pieczony":               150,
    # --- wędliny ---
    "szynka wieprzowa gotowana":     60,
    "szynka drobiowa":               60,
    "szynka konserwowa":             60,
    "szynka parmeńska":              40,
    "polędwica sopocka":             60,
    "kiełbasa zwyczajna":           100,
    "kiełbasa wiejska":             100,
    "kiełbasa szynkowa":            100,
    "kiełbasa krakowska sucha":      80,
    "kiełbasa biała surowa":        120,
    "kiełbasa biała parzona":       120,
    "parówki z szynki":              80,
    "parówki drobiowe":              80,
    "kabanosy wieprzowe":            60,
    "kaszanka":                     100,
    "pasztet pieczony":              80,
    # --- makarony (gotowane) ---
    "makaron spaghetti":            200,
    "makaron penne":                200,
    "makaron tagliatelle":          200,
    "makaron pełnoziarnisty":       200,
    "makaron durum":                200,
    "makaron jajeczny":             200,
    "makaron ryżowy":               200,
    # --- zupy ---
    "rosół drobiowy":               350,
    "zupa pomidorowa":              350,
    "zupa pomidorowa z ryżem":      350,
    "żurek":                        350,
    "barszcz czerwony":             300,
    "barszcz biały":                300,
    "zupa jarzynowa":               350,
    "zupa grzybowa":                350,
    "zupa grochowa":                350,
    "zupa ogórkowa":                350,
    "zupa kapuśniak":               350,
    "zupa fasolowa":                350,
    "krupnik":                      350,
    "zupa cebulowa":                350,
    # --- obiady mączne ---
    "pierogi ruskie":               250,
    "pierogi z mięsem":             250,
    "pierogi z owocami":            250,
    "kopytka":                      200,
    "naleśniki z serem":            200,
    "naleśniki z dżemem":           200,
    "placuszki z cukinii":          200,
    "placki ziemniaczane":          200,
    "pizza margherita":             200,
    "pizza pepperoni":              200,
    # --- dodatki ---
    "ziemniaki gotowane":           200,
    "ziemniaki z masłem":           200,
    "puree ziemniaczane":           200,
    "ziemniaki opiekane":           200,
    "frytki":                       150,
    "ryż biały":                    150,
    "ryż brązowy":                  150,
    "kasza gryczana":               150,
    "kasza pęczak":                 150,
    "kuskus":                       150,
    # --- przekąski i słodycze ---
    "batonik proteinowy":            60,
    "czekolada mleczna":             40,
    "czekolada gorzka":              40,
    # --- ciasta i desery ---
    "kremówka":                     100,
    "wuzetka":                      100,
    "szarlotka":                    120,
    "ciastko kruche":                30,
    "biszkopty":                     10,
    # --- lody ---
    "lody waniliowe":                80,
    "lody czekoladowe":              80,
    "lody truskawkowe":              80,
    "lody owocowe sorbetowe":        80,
    "drumstick lody":               100,
}

# Wszystkie warianty nazw → klucz w MY_FOOD_DB
ALIASES = {
    # --- chleb ---
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
    "chleb żytni":                "chleb żytni",
    "chleb zytni":                "chleb żytni",
    "bułka":                      "bułka pszenna",
    "bulka":                      "bułka pszenna",
    "bagietka":                   "bagietka",
    "tortilla":                   "tortilla pszenna",
    "tost":                       "chleb tostowy",
    "tosty":                      "chleb tostowy",
    "chleb tostowy":              "chleb tostowy",
    # --- tłuszcze ---
    "finuu klasyczne":            "finuu klasyczne",
    "finuu lekkie":               "finuu lekkie",
    "finuu":                      "finuu klasyczne",
    "masło ekstra":               "masło ekstra",
    "maslo ekstra":               "masło ekstra",
    "masło":                      "masło ekstra",
    "maslo":                      "masło ekstra",
    "oliwa z oliwek":             "oliwa z oliwek",
    "oliwa":                      "oliwa z oliwek",
    # --- jajka ---
    "jajko sadzone":              "jajko sadzone",
    "jajka sadzone":              "jajko sadzone",
    "jajko gotowane":             "jajko gotowane",
    "jajka gotowane":             "jajko gotowane",
    "jajko kurze":                "jajko kurze",
    "jajka kurze":                "jajko kurze",
    "jajko":                      "jajko kurze",
    "jajka":                      "jajko kurze",
    "jajeczko":                   "jajko kurze",
    # --- nabiał ---
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
    "zott primo":                   "jogurt zott primo",
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
    "serek łaciaty":                "serek łaciaty do smarowania",
    "serek laciaty":                "serek łaciaty do smarowania",
    "serek":                        "serek łaciaty do smarowania",
    "mozzarella":                   "mozzarella",
    # --- śniadania ---
    "owsianka na wodzie":           "owsianka na wodzie",
    "owsianka na mleku":            "owsianka na mleku",
    "owsianka":                     "owsianka na mleku",
    "płatki owsiane":               "płatki owsiane",
    "platki owsiane":               "płatki owsiane",
    "płatki":                       "płatki owsiane",
    "platki":                       "płatki owsiane",
    "musli bez cukru":              "musli bez cukru",
    "musli":                        "musli bez cukru",
    "müsli":                        "musli bez cukru",
    "granola":                      "granola",
    # --- napoje ---
    "kawa czarna":                  "kawa czarna",
    "kawa z mlekiem":               "kawa z mlekiem",
    "kawa":                         "kawa czarna",
    "herbata":                      "herbata",
    "herbata z miodem":             "herbata z miodem",
    "miód":                         "miód",
    "miod":                         "miód",
    "sok pomarańczowy":             "sok pomarańczowy",
    "sok pomaranczowy":             "sok pomarańczowy",
    "sok":                          "sok pomarańczowy",
    "koktajl owocowy":              "koktajl owocowy (na mleku)",
    "koktajl":                      "koktajl owocowy (na mleku)",
    # --- alkohole ---
    "piwo jasne":                   "piwo jasne",
    "piwo":                         "piwo jasne",
    "wino czerwone wytrawne":       "wino czerwone wytrawne",
    "wino czerwone":                "wino czerwone wytrawne",
    "wino białe wytrawne":          "wino białe wytrawne",
    "wino białe":                   "wino białe wytrawne",
    "wino biale":                   "wino białe wytrawne",
    "wino":                         "wino czerwone wytrawne",
    "wódka":                        "wódka",
    "wodka":                        "wódka",
    "kieliszek wina białego":       "wino białe wytrawne",
    "kieliszek wina czerwonego":    "wino czerwone wytrawne",
    "kieliszek wina":               "wino czerwone wytrawne",
    # --- owoce ---
    "jabłko":                       "jabłko",
    "jablko":                       "jabłko",
    "banan":                        "banan",
    "pomarańcza":                   "pomarańcza",
    "pomarancza":                   "pomarańcza",
    "mandarynka":                   "mandarynka",
    "gruszka":                      "gruszka",
    "kiwi":                         "kiwi",
    "truskawki":                    "truskawki",
    "borówki":                      "borówki",
    "borowki":                      "borówki",
    "maliny":                       "maliny",
    "jeżyny":                       "jeżyny",
    "jezyny":                       "jeżyny",
    "winogrona":                    "winogrona",
    "arbuz":                        "arbuz",
    "melon":                        "melon",
    "ananas":                       "ananas",
    "awokado":                      "awokado",
    # --- warzywa ---
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
    "cebula":                       "cebula",
    "papryka czerwona":             "papryka czerwona",
    "papryka zielona":              "papryka zielona",
    "papryka marynowana":           "papryka marynowana",
    "papryka":                      "papryka czerwona",
    "kapusta biała":                "kapusta biała",
    "kapusta biala":                "kapusta biała",
    "kapusta kiszona":              "kapusta kiszona",
    "kapusta":                      "kapusta biała",
    "kalafior":                     "kalafior",
    "bakłażan":                     "bakłażan",
    "baklażan":                     "bakłażan",
    "fasolka szparagowa":           "fasolka szparagowa",
    "fasolka":                      "fasolka szparagowa",
    "sałata":                       "sałata lodowa",
    "salata":                       "sałata lodowa",
    "rukola":                       "rukola",
    "burak":                        "burak",
    "pieczarki":                    "pieczarki",
    "pieczarka":                    "pieczarki",
    "kukurydza":                    "kukurydza konserwowa",
    "groszek":                      "groszek konserwowy",
    # --- orzechy ---
    "orzechy włoskie":              "orzechy włoskie",
    "orzechy wloskie":              "orzechy włoskie",
    "orzechy laskowe":              "orzechy laskowe",
    "migdały":                      "migdały",
    "migdaly":                      "migdały",
    "masło orzechowe":              "masło orzechowe",
    "maslo orzechowe":              "masło orzechowe",
    "nerkowce":                     "nerkowce",
    "pistacje":                     "pistacje",
    "orzeszki ziemne":              "orzeszki ziemne",
    "orzeszki":                     "orzeszki ziemne",
    # --- mięso i drób ---
    "pierś z kurczaka pieczona":    "pierś z kurczaka pieczona",
    "pierś z kurczaka":             "pierś z kurczaka pieczona",
    "piers z kurczaka":             "pierś z kurczaka pieczona",
    "udko z kurczaka pieczone":     "udko z kurczaka pieczone",
    "udko z kurczaka":              "udko z kurczaka pieczone",
    "udko kurczaka":                "udko z kurczaka pieczone",
    "udko":                         "udko z kurczaka pieczone",
    "drumstick kurczak":            "drumstick kurczak",
    "podudzie kurczaka":            "drumstick kurczak",
    "kurczak pieczony":             "kurczak pieczony cały",
    "kurczak w sosie":              "kurczak w sosie śmietanowym",
    "stek wołowy":                  "stek wołowy",
    "stek wolowy":                  "stek wołowy",
    "stek":                         "stek wołowy",
    "gulasz wieprzowy":             "gulasz wieprzowy",
    "gulasz":                       "gulasz wieprzowy",
    "kotlet schabowy":              "kotlet schabowy",
    "schabowy":                     "kotlet schabowy",
    "schab":                        "kotlet schabowy",
    "kotlet mielony":               "kotlet mielony",
    "mielony":                      "kotlet mielony",
    "boczek wędzony":               "boczek wędzony",
    "boczek wedzony":               "boczek wędzony",
    "boczek pieczony":              "boczek pieczony",
    "boczek":                       "boczek wędzony",
    "gołąbki w sosie pomidorowym":  "gołąbki w sosie pomidorowym",
    "gołąbki":                      "gołąbki w sosie pomidorowym",
    "golabki":                      "gołąbki w sosie pomidorowym",
    "leczo z kiełbasą":             "leczo z kiełbasą",
    "leczo":                        "leczo z kiełbasą",
    "dorsz pieczony":               "dorsz pieczony",
    "dorsz":                        "dorsz pieczony",
    "ryba w panierce":              "ryba w panierce",
    "tuńczyk w oleju":              "tuńczyk w oleju",
    "tunczyk w oleju":              "tuńczyk w oleju",
    "tuńczyk w wodzie":             "tuńczyk w wodzie",
    "tunczyk w wodzie":             "tuńczyk w wodzie",
    "tuńczyk":                      "tuńczyk w wodzie",
    "tunczyk":                      "tuńczyk w wodzie",
    "łosoś pieczony":               "łosoś pieczony",
    "losos pieczony":               "łosoś pieczony",
    "łosoś":                        "łosoś pieczony",
    "losos":                        "łosoś pieczony",
    # --- wędliny ---
    "szynka wieprzowa gotowana":    "szynka wieprzowa gotowana",
    "szynka wieprzowa":             "szynka wieprzowa gotowana",
    "szynka drobiowa":              "szynka drobiowa",
    "szynka konserwowa":            "szynka konserwowa",
    "szynka parmeńska":             "szynka parmeńska",
    "prosciutto":                   "szynka parmeńska",
    "szynka":                       "szynka wieprzowa gotowana",
    "polędwica sopocka":            "polędwica sopocka",
    "poledwica sopocka":            "polędwica sopocka",
    "polędwica":                    "polędwica sopocka",
    "kiełbasa zwyczajna":           "kiełbasa zwyczajna",
    "kiełbasa wiejska":             "kiełbasa wiejska",
    "kiełbasa szynkowa":            "kiełbasa szynkowa",
    "kiełbasa krakowska sucha":     "kiełbasa krakowska sucha",
    "kiełbasa krakowska":           "kiełbasa krakowska sucha",
    "kielbasa krakowska":           "kiełbasa krakowska sucha",
    "krakowska":                    "kiełbasa krakowska sucha",
    "kiełbasa biała surowa":        "kiełbasa biała surowa",
    "kiełbasa biała parzona":       "kiełbasa biała parzona",
    "kiełbasa biała":               "kiełbasa biała parzona",
    "kielbasa biala":               "kiełbasa biała parzona",
    "biała kiełbasa":               "kiełbasa biała parzona",
    "kiełbasa":                     "kiełbasa zwyczajna",
    "parówki z szynki":             "parówki z szynki",
    "parowki z szynki":             "parówki z szynki",
    "parówki drobiowe":             "parówki drobiowe",
    "parowki drobiowe":             "parówki drobiowe",
    "parówki":                      "parówki drobiowe",
    "parowki":                      "parówki drobiowe",
    "kabanosy wieprzowe":           "kabanosy wieprzowe",
    "kabanosy":                     "kabanosy wieprzowe",
    "kaszanka":                     "kaszanka",
    "pasztet pieczony":             "pasztet pieczony",
    "pasztet":                      "pasztet pieczony",
    "szynki parmeńskiej":           "szynka parmeńska",
    "polędwicy sopockiej":          "polędwica sopocka",
    "mozzarelli":                   "mozzarella",
    "30g mozzarelli":               "mozzarella",
    # --- makarony ---
    "makaron spaghetti":            "makaron spaghetti",
    "spaghetti":                    "makaron spaghetti",
    "makaron penne":                "makaron penne",
    "penne":                        "makaron penne",
    "makaron tagliatelle":          "makaron tagliatelle",
    "tagliatelle":                  "makaron tagliatelle",
    "makaron pełnoziarnisty":       "makaron pełnoziarnisty",
    "makaron pelnoziarnisty":       "makaron pełnoziarnisty",
    "makaron durum":                "makaron durum",
    "makaron jajeczny":             "makaron jajeczny",
    "makaron ryżowy":               "makaron ryżowy",
    "makaron ryzowy":               "makaron ryżowy",
    "makaron":                      "makaron spaghetti",
    # --- zupy ---
    "rosół drobiowy":               "rosół drobiowy",
    "rosół":                        "rosół drobiowy",
    "rosol":                        "rosół drobiowy",
    "zupa pomidorowa z ryżem":      "zupa pomidorowa z ryżem",
    "zupa pomidorowa":              "zupa pomidorowa",
    "pomidorowa":                   "zupa pomidorowa",
    "żurek":                        "żurek",
    "zurek":                        "żurek",
    "barszcz czerwony":             "barszcz czerwony",
    "barszcz biały":                "barszcz biały",
    "barszcz bialy":                "barszcz biały",
    "barszcz":                      "barszcz czerwony",
    "zupa jarzynowa":               "zupa jarzynowa",
    "jarzynowa":                    "zupa jarzynowa",
    "zupa grzybowa":                "zupa grzybowa",
    "grzybowa":                     "zupa grzybowa",
    "zupa grochowa":                "zupa grochowa",
    "grochowa":                     "zupa grochowa",
    "zupa ogórkowa":                "zupa ogórkowa",
    "ogórkowa":                     "zupa ogórkowa",
    "zupa kapuśniak":               "zupa kapuśniak",
    "kapuśniak":                    "zupa kapuśniak",
    "kapusniak":                    "zupa kapuśniak",
    "zupa fasolowa":                "zupa fasolowa",
    "fasolowa":                     "zupa fasolowa",
    "krupnik":                      "krupnik",
    "zupa cebulowa":                "zupa cebulowa",
    "cebulowa":                     "zupa cebulowa",
    # --- obiady mączne ---
    "pierogi ruskie":               "pierogi ruskie",
    "pierogi z mięsem":             "pierogi z mięsem",
    "pierogi z owocami":            "pierogi z owocami",
    "pierogi":                      "pierogi ruskie",
    "kopytka":                      "kopytka",
    "naleśniki z serem":            "naleśniki z serem",
    "naleśniki z dżemem":          "naleśniki z dżemem",
    "naleśniki":                    "naleśniki z serem",
    "nalesniki":                    "naleśniki z serem",
    "placuszki z cukinii":          "placuszki z cukinii",
    "placuszki":                    "placuszki z cukinii",
    "placki ziemniaczane":          "placki ziemniaczane",
    "placki":                       "placki ziemniaczane",
    "pizza margherita":             "pizza margherita",
    "pizza pepperoni":              "pizza pepperoni",
    "pizza":                        "pizza margherita",
    # --- dodatki ---
    "ziemniaki z masłem":           "ziemniaki z masłem",
    "ziemniaki z maslem":           "ziemniaki z masłem",
    "ziemniaki opiekane":           "ziemniaki opiekane",
    "ziemniaki gotowane":           "ziemniaki gotowane",
    "ziemniaki":                    "ziemniaki gotowane",
    "puree ziemniaczane":           "puree ziemniaczane",
    "puree":                        "puree ziemniaczane",
    "frytki":                       "frytki",
    "ryż biały":                    "ryż biały",
    "ryż brązowy":                  "ryż brązowy",
    "ryż brazowy":                  "ryż brązowy",
    "ryż":                          "ryż biały",
    "ryz":                          "ryż biały",
    "kasza gryczana":               "kasza gryczana",
    "kasza pęczak":                 "kasza pęczak",
    "kasza":                        "kasza gryczana",
    "kuskus":                       "kuskus",
    # --- przekąski i słodycze ---
    "batonik proteinowy":           "batonik proteinowy",
    "batonik":                      "batonik proteinowy",
    "czekolada mleczna":            "czekolada mleczna",
    "czekolada gorzka":             "czekolada gorzka",
    "czekolada":                    "czekolada mleczna",
    # --- ciasta i desery ---
    "kremówka":                     "kremówka",
    "kremowka":                     "kremówka",
    "wuzetka":                      "wuzetka",
    "wuzetki":                      "wuzetka",
    "szarlotka":                    "szarlotka",
    "ciastko kruche":               "ciastko kruche",
    "ciastko":                      "ciastko kruche",
    "biszkopty":                    "biszkopty",
    "biszkopt":                     "biszkopty",
    # --- lody ---
    "lody waniliowe":               "lody waniliowe",
    "lody czekoladowe":             "lody czekoladowe",
    "lody truskawkowe":             "lody truskawkowe",
    "lody owocowe sorbetowe":       "lody owocowe sorbetowe",
    "sorbet":                       "lody owocowe sorbetowe",
    "drumstick lody":               "drumstick lody",
    "lody":                         "lody waniliowe",
}

# Odmiana przez przypadki — końcówki fleksyjne polskich słów
POLISH_STEMS = {
    "pizzy":              "pizza",
    "pizy":               "pizza",
    "pizyy":              "pizza",
    "margarity":          "margherita",
    "margherity":         "margherita",
    "pepperoni":          "pepperoni",
    "ziemniaków":         "ziemniaki",
    "ziemniakow":         "ziemniaki",
    "ziemniaka":          "ziemniaki",
    "pierogów":           "pierogi ruskie",
    "pierogow":           "pierogi ruskie",
    "schabowego":         "kotlet schabowy",
    "schabowe":           "kotlet schabowy",
    "schabowy":           "kotlet schabowy",
    "schabow":            "kotlet schabowy",
    "schabu":             "kotlet schabowy",
    "kotleta":            "kotlet schabowy",
    "kotlety":            "kotlet schabowy",
    "kotletów":           "kotlet schabowy",
    "mielonego":          "kotlet mielony",
    "mielone":            "kotlet mielony",
    "gulaszu":            "gulasz wieprzowy",
    "frytki":             "frytki",
    "frytek":             "frytki",
    "kopytek":            "kopytka",
    "naleśniki":          "naleśniki z serem",
    "naleśnik":           "naleśniki z serem",
    "nalesniki":          "naleśniki z serem",
    "gołąbki":            "gołąbki w sosie pomidorowym",
    "golabki":            "gołąbki w sosie pomidorowym",
    "gołąbka":            "gołąbki w sosie pomidorowym",
    "golabka":            "gołąbki w sosie pomidorowym",
    "ryżu":               "ryż biały",
    "ryzu":               "ryż biały",
    "makaronu":           "makaron spaghetti",
    "kaszy":              "kasza gryczana",
    "marchewki":          "marchew",
    "marchewkę":          "marchew",
    "ogórka":             "ogórek",
    "ogorka":             "ogórek",
    "pomidora":           "pomidor",
    "pomidory":           "pomidor",
    "papryki":            "papryka czerwona",
    "cebuli":             "cebula",
    "brokułu":            "brokuł",
    "brokulu":            "brokuł",
    "jabłka":             "jabłko",
    "jablka":             "jabłko",
    "banana":             "banan",
    "truskawek":          "truskawki",
    "borówek":            "borówki",
    "borowek":            "borówki",
    "malin":              "maliny",
    "jeżyn":              "jeżyny",
    "winogron":           "winogrona",
    "kurczaka":           "pierś z kurczaka pieczona",
    "piersi":             "pierś z kurczaka pieczona",
    "steka":              "stek wołowy",
    "dorsza":             "dorsz pieczony",
    "łososia":            "łosoś pieczony",
    "lososia":            "łosoś pieczony",
    "tuńczyka":           "tuńczyk w wodzie",
    "tunczyka":           "tuńczyk w wodzie",
    "boczku":             "boczek wędzony",
    "kiełbasę":           "kiełbasa zwyczajna",
    "kielbasy":           "kiełbasa zwyczajna",
    "parówek":            "parówki drobiowe",
    "parowek":            "parówki drobiowe",
    "kabanosów":          "kabanosy wieprzowe",
    "kabanosow":          "kabanosy wieprzowe",
    "pasztetu":           "pasztet pieczony",
    "cukinii":            "cukinia",
    "szpinaku":           "szpinak",
    "awokado":            "awokado",
    "orzechów":           "orzechy włoskie",
    "orzechow":           "orzechy włoskie",
    "migdałów":           "migdały",
    "migdalow":           "migdały",
    "piwa":               "piwo jasne",
    "wina":               "wino czerwone wytrawne",
    "wódki":              "wódka",
    "wodki":              "wódka",
    "owsianki":           "owsianka na mleku",
    "płatków":            "płatki owsiane",
    "platków":            "płatki owsiane",
    "granoli":            "granola",
    "musli":              "musli bez cukru",
    "müsli":              "musli bez cukru",
    "kawy":               "kawa czarna",
    "herbaty":            "herbata",
    "miodu":              "miód",
    "soku":               "sok pomarańczowy",
    "kremówki":           "kremówka",
    "kremowki":           "kremówka",
    "wuzetki":            "wuzetka",
    "szarlotki":          "szarlotka",
    "lodów":              "lody waniliowe",
    "lodow":              "lody waniliowe",
}

# Przeliczniki jednostek → gramy na 1 jednostkę
UNITS = {
    "g":           1,   "gram":       1,   "gramy":      1,   "gramów":     1,
    "ml":          1,
    "dag":        10,
    "kg":       1000,
    "łyżeczka":    5,   "łyżeczki":   5,   "lyżeczka":   5,
    "łyżka":      15,   "łyżki":     15,   "lyżka":     15,   "łyżek":     15,
    "kromka":     40,   "kromki":    40,   "kromek":    40,
    "plasterek":  40,   "plasterki": 40,   "plasterków": 40,
    "kawałek":    80,   "kawałki":   80,   "kawalek":   80,
    "sztuka":     60,   "sztuki":    60,   "sztuk":     60,   "szt":       60,
    "szklanka":  240,   "szklanki":  240,  "szklanek":  240,
    "kubek":     250,   "kubki":     250,
    "porcja":    200,   "porcje":    200,  "porcji":    200,
    "talerz":    300,   "miseczka":  200,  "garść":      30,
    "gałka":      80,   "gałki":     80,   "galka":     80,
    "kieliszek":  150,   "kieliszki":  150,
}

def normalize_polish(text: str) -> str:
    words = text.split()
    result = []
    for w in words:
        result.append(POLISH_STEMS.get(w, w))
    return " ".join(result)

def resolve_product(raw: str) -> str | None:
    raw = raw.strip().lower()

    if raw in MY_FOOD_DB:
        return raw

    for alias in sorted(ALIASES.keys(), key=len, reverse=True):
        if alias in raw:
            return ALIASES[alias]

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

    first_word = raw.split()[0] if raw.split() else raw
    first_normalized = POLISH_STEMS.get(first_word, first_word)
    for key in sorted(MY_FOOD_DB.keys(), key=len, reverse=True):
        if key.startswith(first_normalized):
            return key

    for key in sorted(MY_FOOD_DB.keys(), key=len, reverse=True):
        if key in raw or raw in key:
            return key

    return None

def parse_meal_locally(text: str) -> tuple[list, list]:
    parts = re.split(r',|\bi\b|\boraz\b', text.lower())
    parts = [p.strip() for p in parts if p.strip()]

    found   = []
    unknown = []
    unit_pat = "|".join(re.escape(u) for u in sorted(UNITS.keys(), key=len, reverse=True))

    for part in parts:
        grams   = None
        product = None

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

        if not product:
            m = re.match(r'^(\d+)\s+(.+)$', part, re.IGNORECASE | re.UNICODE)
            if m:
                count   = int(m.group(1))
                raw     = m.group(2).strip()
                product = resolve_product(raw)
                if product:
                    unit_g = DEFAULT_GRAMS.get(product, 100)
                    grams  = unit_g * count

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

        validated = []
        for item in data:
            kcal  = float(item.get("calories", 0))
            grams = float(item.get("grams", 100))
            if kcal < 10 and grams > 50:
                factor = grams / 100
                item["calories"] = round(kcal * factor * 100)
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
    st.markdown("```\n2 kromki chleba, łyżka finuu\nowsianka na mleku, banan\n3 kawałki łososia\n```")
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
        placeholder="np. owsianka na mleku, banan, łyżka miodu"
    )
    meal_time = st.selectbox("Pora", ["Śniadanie","II Śniadanie","Obiad","Kolacja","Przekąska"])
    submitted = st.form_submit_button("DODAJ POSIŁEK", use_container_width=True)

if submitted and food_input:
    with st.spinner("🔍 Analizuję…"):

        found, unknown = parse_meal_locally(food_input)

        total   = {"calories": 0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
        details = []

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
