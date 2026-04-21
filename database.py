# database.py - Kompletna baza produktów dla Twojej aplikacji

MY_FOOD_DB = {
    # --- NABIAŁ ---
    "jogurt naturalny piątnica 2%": {"kcal": 63, "p": 4.3, "f": 2.0, "c": 7.0},
    "jogurt naturalny piątnica 0%": {"kcal": 52, "p": 5.5, "f": 0.0, "c": 7.5},
    "jogurt zott primo": {"kcal": 67, "p": 4.8, "f": 3.1, "c": 4.0},
    "jogurt danone łagodny": {"kcal": 69, "p": 4.5, "f": 3.0, "c": 5.4},
    "skyr naturalny": {"kcal": 64, "p": 12.0, "f": 0.0, "c": 4.0},
    "twaróg półtłusty": {"kcal": 133, "p": 18.0, "f": 4.7, "c": 3.7},
    "mleko 2%": {"kcal": 50, "p": 3.4, "f": 2.0, "c": 4.8},

    # --- TŁUSZCZE ---
    "finuu klasyczne": {"kcal": 666, "p": 0.3, "f": 74.0, "c": 0.6},
    "finuu lekkie": {"kcal": 360, "p": 0.1, "f": 40.0, "c": 0.1},
    "masło ekstra": {"kcal": 748, "p": 0.7, "f": 82.0, "c": 0.7},
    "oliwa z oliwek": {"kcal": 884, "p": 0.0, "f": 100.0, "c": 0.0},

    # --- JAJA ---
    "jajko kurze": {"kcal": 139, "p": 12.5, "f": 9.7, "c": 0.6}, # na 100g (ok. 2 sztuki)
    "jajko sadzone": {"kcal": 196, "p": 13.0, "f": 15.0, "c": 0.8},

    # --- OBIADY (DANIE GŁÓWNE) ---
    "gołąbki w sosie pomidorowym": {"kcal": 120, "p": 6.0, "f": 7.0, "c": 9.0},
    "stek wołowy": {"kcal": 250, "p": 25.0, "f": 17.0, "c": 0.0},
    "leczo z kiełbasą": {"kcal": 115, "p": 6.0, "f": 8.0, "c": 5.5},
    "kotlet schabowy": {"kcal": 320, "p": 20.0, "f": 18.0, "c": 15.0},
    "kotlet mielony": {"kcal": 280, "p": 18.0, "f": 22.0, "c": 5.0},
    "pierś z kurczaka pieczona": {"kcal": 150, "p": 31.0, "f": 2.5, "c": 0.0},
    "kurczak w sosie śmietanowym": {"kcal": 180, "p": 15.0, "f": 12.0, "c": 4.0},
    "gulasz wieprzowy": {"kcal": 150, "p": 12.0, "f": 9.0, "c": 6.0},
    "ryba w panierce": {"kcal": 230, "p": 15.0, "f": 12.0, "c": 15.0},
    "dorsz pieczony": {"kcal": 90, "p": 20.0, "f": 0.7, "c": 0.0},

    # --- OBIADY (MĄCZNE) ---
    "pierogi ruskie": {"kcal": 200, "p": 6.0, "f": 5.0, "c": 33.0},
    "pierogi z mięsem": {"kcal": 220, "p": 9.0, "f": 7.0, "c": 30.0},
    "pierogi z owocami": {"kcal": 190, "p": 5.0, "f": 3.0, "c": 36.0},
    "kopytka": {"kcal": 160, "p": 3.5, "f": 0.5, "c": 35.0},
    "naleśniki z serem": {"kcal": 210, "p": 9.0, "f": 7.0, "c": 28.0},
    "naleśniki z dżemem": {"kcal": 185, "p": 4.0, "f": 4.5, "c": 32.0},
    "placuszki z cukinii": {"kcal": 145, "p": 4.0, "f": 9.0, "c": 14.0},
    "placki ziemniaczane": {"kcal": 260, "p": 3.0, "f": 15.0, "c": 28.0},
    "pizza margherita": {"kcal": 250, "p": 10.0, "f": 9.0, "c": 32.0},
    "pizza pepperoni": {"kcal": 290, "p": 12.0, "f": 14.0, "c": 28.0},

    # --- DODATKI DO OBIADU ---
    "ziemniaki gotowane": {"kcal": 77, "p": 2.0, "f": 0.1, "c": 17.0},
    "ziemniaki z masłem": {"kcal": 110, "p": 2.0, "f": 4.0, "c": 17.0},
    "puree ziemniaczane": {"kcal": 120, "p": 2.2, "f": 5.0, "c": 16.0},
    "ziemniaki opiekane": {"kcal": 140, "p": 2.5, "f": 5.0, "c": 22.0},
    "frytki": {"kcal": 290, "p": 3.4, "f": 15.0, "c": 35.0},
    "ryż biały": {"kcal": 130, "p": 2.7, "f": 0.3, "c": 28.0}, # gotowany
    "ryż brązowy": {"kcal": 111, "p": 2.6, "f": 0.9, "c": 23.0}, # gotowany
    "kasza gryczana": {"kcal": 120, "p": 4.5, "f": 1.0, "c": 24.0}, # gotowana
    "kasza pęczak": {"kcal": 125, "p": 3.5, "f": 0.5, "c": 26.0},
    "kuskus": {"kcal": 112, "p": 3.8, "f": 0.2, "c": 23.0},

    # --- WARZYWA ---
    "pomidor": {"kcal": 18, "p": 0.9, "f": 0.2, "c": 3.9},
    "ogórek": {"kcal": 15, "p": 0.7, "f": 0.1, "c": 2.9},
    "marchew": {"kcal": 41, "p": 0.9, "f": 0.2, "c": 9.6},
    "cukinia": {"kcal": 17, "p": 1.2, "f": 0.3, "c": 3.1},
    "brokuł": {"kcal": 34, "p": 2.8, "f": 0.4, "c": 6.6},
    "szpinak": {"kcal": 23, "p": 2.9, "f": 0.4, "c": 3.6},

    # --- OWOCE ---
    "jabłko": {"kcal": 52, "p": 0.3, "f": 0.2, "c": 14.0},
    "banan": {"kcal": 89, "p": 1.1, "f": 0.3, "c": 23.0},
    "truskawki": {"kcal": 32, "p": 0.7, "f": 0.3, "c": 7.7},
    "borówki": {"kcal": 57, "p": 0.7, "f": 0.3, "c": 14.5},
    "awokado": {"kcal": 160, "p": 2.0, "f": 15.0, "c": 9.0},

    # --- ORZECHY ---
    "orzechy włoskie": {"kcal": 654, "p": 15.0, "f": 65.0, "c": 14.0},
    "orzechy laskowe": {"kcal": 628, "p": 15.0, "f": 61.0, "c": 17.0},
    "migdały": {"kcal": 579, "p": 21.0, "f": 50.0, "c": 22.0},
    "masło orzechowe": {"kcal": 588, "p": 25.0, "f": 50.0, "c": 20.0},

    # --- NAPOJE ---
    "kawa czarna": {"kcal": 2, "p": 0.1, "f": 0.0, "c": 0.0},
    "herbata": {"kcal": 1, "p": 0.0, "f": 0.0, "c": 0.2},
    "sok pomarańczowy": {"kcal": 45, "p": 0.7, "f": 0.2, "c": 10.4},
    "koktajl owocowy (na mleku)": {"kcal": 70, "p": 3.0, "f": 1.5, "c": 12.0},

    # --- ALKOHOLE ---
    "piwo jasne": {"kcal": 43, "p": 0.5, "f": 0.0, "c": 3.6},
    "wino czerwone wytrawne": {"kcal": 85, "p": 0.1, "f": 0.0, "c": 2.6},
    "wino białe wytrawne": {"kcal": 82, "p": 0.1, "f": 0.0, "c": 2.4},
    "wódka": {"kcal": 231, "p": 0.0, "f": 0.0, "c": 0.0},

    # --- PIECZYWO ---
    "chleb z otrębami": {"kcal": 211, "p": 12.0, "f": 5.0, "c": 25.0},
    "chleb żytni": {"kcal": 259, "p": 8.5, "f": 3.3, "c": 48.0},
    "bułka pszenna": {"kcal": 272, "p": 8.0, "f": 1.5, "c": 55.0},

    # --- KIEŁBASY I WĘDLINY PODROBOWE ---
    "kiełbasa zwyczajna": {"kcal": 210, "p": 17.0, "f": 16.0, "c": 1.0},
    "kiełbasa wiejska": {"kcal": 300, "p": 16.0, "f": 25.0, "c": 1.0},
    "kiełbasa szynkowa": {"kcal": 130, "p": 18.0, "f": 6.0, "c": 1.0}, # Najchudsza opcja!
    "kiełbasa krakowska sucha": {"kcal": 320, "p": 25.0, "f": 24.0, "c": 2.0},
    "kiełbasa biała surowa": {"kcal": 270, "p": 14.0, "f": 24.0, "c": 1.0},
    "kiełbasa biała parzona": {"kcal": 230, "p": 14.0, "f": 18.0, "c": 1.0},
    "parówki z szynki": {"kcal": 260, "p": 13.0, "f": 22.0, "c": 1.5},
    "parówki drobiowe": {"kcal": 210, "p": 12.0, "f": 17.0, "c": 2.0},
    "kabanosy wieprzowe": {"kcal": 480, "p": 25.0, "f": 40.0, "c": 4.0},
    "kaszanka": {"kcal": 210, "p": 10.0, "f": 15.0, "c": 9.0},
    "pasztet pieczony": {"kcal": 350, "p": 14.0, "f": 30.0, "c": 4.0},
}
