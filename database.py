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
    "serek łaciaty do smarowania": {"kcal": 145, "p": 9.0, "f": 11.0, "c": 2.5},
    "mozzarella": {"kcal": 280, "p": 18.0, "f": 22.0, "c": 2.0},

    # --- TŁUSZCZE ---
    "finuu klasyczne": {"kcal": 666, "p": 0.3, "f": 74.0, "c": 0.6},
    "finuu lekkie": {"kcal": 360, "p": 0.1, "f": 40.0, "c": 0.1},
    "masło ekstra": {"kcal": 748, "p": 0.7, "f": 82.0, "c": 0.7},
    "oliwa z oliwek": {"kcal": 884, "p": 0.0, "f": 100.0, "c": 0.0},

    # --- JAJA ---
    "jajko kurze": {"kcal": 139, "p": 12.5, "f": 9.7, "c": 0.6},   # na 100g (~2 sztuki)
    "jajko gotowane": {"kcal": 155, "p": 13.0, "f": 11.0, "c": 1.1},
    "jajko sadzone": {"kcal": 196, "p": 13.0, "f": 15.0, "c": 0.8},
    "jajecznica z 1 jajka":  {"kcal": 388, "p": 21.8, "f": 30.7, "c": 1.3},
    "jajecznica z 2 jajek":  {"kcal": 388, "p": 21.8, "f": 30.7, "c": 1.3},
    "jajecznica z 3 jajek":  {"kcal": 388, "p": 21.8, "f": 30.7, "c": 1.3},
    "jajecznica z 4 jajek":  {"kcal": 388, "p": 21.8, "f": 30.7, "c": 1.3},

    # --- ŚNIADANIA ---
    "owsianka na wodzie": {"kcal": 68, "p": 2.4, "f": 1.4, "c": 12.0},   # gotowana
    "owsianka na mleku": {"kcal": 95, "p": 4.0, "f": 3.0, "c": 13.5},    # gotowana
    "płatki owsiane": {"kcal": 350, "p": 13.0, "f": 7.0, "c": 58.0},     # suche
    "musli bez cukru": {"kcal": 370, "p": 10.0, "f": 7.0, "c": 65.0},
    "granola": {"kcal": 410, "p": 8.0, "f": 15.0, "c": 63.0},

    # --- NAPOJE ---
    "kawa czarna": {"kcal": 2, "p": 0.1, "f": 0.0, "c": 0.0},
    "kawa z mlekiem": {"kcal": 22, "p": 1.5, "f": 0.8, "c": 2.1},        # ~50ml mleka 2%
    "herbata": {"kcal": 1, "p": 0.0, "f": 0.0, "c": 0.2},
    "herbata z miodem": {"kcal": 35, "p": 0.0, "f": 0.0, "c": 9.0},      # łyżeczka miodu
    "sok pomarańczowy": {"kcal": 45, "p": 0.7, "f": 0.2, "c": 10.4},
    "koktajl owocowy (na mleku)": {"kcal": 70, "p": 3.0, "f": 1.5, "c": 12.0},
    "miód": {"kcal": 304, "p": 0.3, "f": 0.0, "c": 82.0},

    # --- ALKOHOLE ---
    "piwo jasne": {"kcal": 43, "p": 0.5, "f": 0.0, "c": 3.6},
    "wino czerwone wytrawne": {"kcal": 85, "p": 0.1, "f": 0.0, "c": 2.6},
    "wino białe wytrawne": {"kcal": 82, "p": 0.1, "f": 0.0, "c": 2.4},
    "wódka": {"kcal": 231, "p": 0.0, "f": 0.0, "c": 0.0},

    # --- PRZEKĄSKI I SŁODYCZE ---
    "migdały": {"kcal": 579, "p": 21.0, "f": 50.0, "c": 22.0},
    "batonik proteinowy": {"kcal": 370, "p": 30.0, "f": 10.0, "c": 40.0},  # średnia
    "czekolada mleczna": {"kcal": 535, "p": 7.0, "f": 30.0, "c": 59.0},
    "czekolada gorzka": {"kcal": 546, "p": 5.0, "f": 32.0, "c": 60.0},

    # --- CIASTA I DESERY ---
    "kremówka": {"kcal": 310, "p": 4.5, "f": 18.0, "c": 34.0},
    "wuzetka": {"kcal": 380, "p": 5.0, "f": 22.0, "c": 42.0},
    "szarlotka": {"kcal": 280, "p": 3.5, "f": 12.0, "c": 40.0},
    "ciastko kruche": {"kcal": 480, "p": 6.0, "f": 24.0, "c": 62.0},
    "biszkopty": {"kcal": 385, "p": 7.0, "f": 6.0, "c": 76.0},

    # --- LODY ---
    "lody waniliowe": {"kcal": 200, "p": 3.5, "f": 10.0, "c": 25.0},       # 1 gałka ~80g
    "lody czekoladowe": {"kcal": 215, "p": 3.5, "f": 11.0, "c": 27.0},
    "lody truskawkowe": {"kcal": 185, "p": 3.0, "f": 8.0, "c": 27.0},
    "lody owocowe sorbetowe": {"kcal": 130, "p": 0.5, "f": 0.2, "c": 32.0},
    "drumstick lody": {"kcal": 255, "p": 4.0, "f": 13.0, "c": 32.0},       # 1 sztuka ~100g

    # --- MIĘSO I DRÓB ---
    "gołąbki w sosie pomidorowym": {"kcal": 120, "p": 6.0, "f": 7.0, "c": 9.0},
    "stek wołowy": {"kcal": 250, "p": 25.0, "f": 17.0, "c": 0.0},
    "leczo z kiełbasą": {"kcal": 115, "p": 6.0, "f": 8.0, "c": 5.5},
    "kotlet schabowy": {"kcal": 280, "p": 18.0, "f": 20.0, "c": 10.0},
    "kotlet mielony": {"kcal": 280, "p": 18.0, "f": 22.0, "c": 5.0},
    "pierś z kurczaka pieczona": {"kcal": 150, "p": 31.0, "f": 2.5, "c": 0.0},
    "udko z kurczaka pieczone": {"kcal": 215, "p": 26.0, "f": 12.0, "c": 0.0},
    "drumstick kurczak": {"kcal": 195, "p": 24.0, "f": 11.0, "c": 0.0},    # podudzie
    "kurczak pieczony cały": {"kcal": 190, "p": 27.0, "f": 9.0, "c": 0.0},
    "kurczak w sosie śmietanowym": {"kcal": 180, "p": 15.0, "f": 12.0, "c": 4.0},
    "gulasz wieprzowy": {"kcal": 150, "p": 12.0, "f": 9.0, "c": 6.0},
    "boczek wędzony": {"kcal": 541, "p": 14.0, "f": 53.0, "c": 1.0},
    "boczek pieczony": {"kcal": 458, "p": 17.0, "f": 43.0, "c": 0.0},
    "ryba w panierce": {"kcal": 230, "p": 15.0, "f": 12.0, "c": 15.0},
    "dorsz pieczony": {"kcal": 90, "p": 20.0, "f": 0.7, "c": 0.0},
    "tuńczyk w oleju": {"kcal": 190, "p": 25.0, "f": 10.0, "c": 0.0},
    "tuńczyk w wodzie": {"kcal": 116, "p": 26.0, "f": 1.0, "c": 0.0},
    "łosoś pieczony": {"kcal": 206, "p": 20.0, "f": 13.0, "c": 0.0},

    # --- WĘDLINY I SZYNKI ---
    "szynka wieprzowa gotowana": {"kcal": 107, "p": 17.0, "f": 4.0, "c": 1.0},
    "szynka drobiowa": {"kcal": 95, "p": 16.0, "f": 3.0, "c": 1.5},
    "szynka konserwowa": {"kcal": 130, "p": 15.0, "f": 7.0, "c": 2.0},
    "szynka parmeńska": {"kcal": 250, "p": 25.0, "f": 16.0, "c": 1.0},
    "polędwica sopocka": {"kcal": 110, "p": 18.0, "f": 4.0, "c": 1.0},
    "kiełbasa zwyczajna": {"kcal": 210, "p": 17.0, "f": 16.0, "c": 1.0},
    "kiełbasa wiejska": {"kcal": 300, "p": 16.0, "f": 25.0, "c": 1.0},
    "kiełbasa szynkowa": {"kcal": 130, "p": 18.0, "f": 6.0, "c": 1.0},
    "kiełbasa krakowska sucha": {"kcal": 320, "p": 25.0, "f": 24.0, "c": 2.0},
    "kiełbasa biała surowa": {"kcal": 270, "p": 14.0, "f": 24.0, "c": 1.0},
    "kiełbasa biała parzona": {"kcal": 230, "p": 14.0, "f": 18.0, "c": 1.0},
    "parówki z szynki": {"kcal": 260, "p": 13.0, "f": 22.0, "c": 1.5},
    "parówki drobiowe": {"kcal": 210, "p": 12.0, "f": 17.0, "c": 2.0},
    "kabanosy wieprzowe": {"kcal": 480, "p": 25.0, "f": 40.0, "c": 4.0},
    "kaszanka": {"kcal": 210, "p": 10.0, "f": 15.0, "c": 9.0},
    "pasztet pieczony": {"kcal": 350, "p": 14.0, "f": 30.0, "c": 4.0},

    # --- MAKARONY (gotowane) ---
    "makaron spaghetti": {"kcal": 157, "p": 5.8, "f": 0.9, "c": 31.0},
    "makaron penne": {"kcal": 157, "p": 5.8, "f": 0.9, "c": 31.0},
    "makaron tagliatelle": {"kcal": 157, "p": 5.8, "f": 0.9, "c": 31.0},
    "makaron pełnoziarnisty": {"kcal": 140, "p": 5.5, "f": 1.1, "c": 28.0},
    "makaron durum": {"kcal": 157, "p": 6.0, "f": 0.9, "c": 31.0},
    "makaron jajeczny": {"kcal": 165, "p": 6.5, "f": 1.5, "c": 32.0},
    "makaron ryżowy": {"kcal": 109, "p": 2.0, "f": 0.2, "c": 25.0},

    # --- ZUPY ---
    "rosół drobiowy": {"kcal": 25, "p": 2.5, "f": 1.0, "c": 1.5},
    "zupa pomidorowa": {"kcal": 55, "p": 2.0, "f": 2.0, "c": 8.0},
    "zupa pomidorowa z ryżem": {"kcal": 75, "p": 2.5, "f": 2.0, "c": 12.0},
    "żurek": {"kcal": 80, "p": 4.0, "f": 4.5, "c": 7.0},
    "barszcz czerwony": {"kcal": 35, "p": 1.5, "f": 0.5, "c": 7.0},
    "barszcz biały": {"kcal": 90, "p": 5.0, "f": 4.0, "c": 9.0},
    "zupa jarzynowa": {"kcal": 45, "p": 2.0, "f": 1.5, "c": 7.0},
    "zupa grzybowa": {"kcal": 60, "p": 2.5, "f": 2.5, "c": 8.0},
    "zupa grochowa": {"kcal": 95, "p": 6.0, "f": 3.0, "c": 12.0},
    "zupa ogórkowa": {"kcal": 50, "p": 2.0, "f": 2.0, "c": 7.0},
    "zupa kapuśniak": {"kcal": 65, "p": 4.0, "f": 3.0, "c": 7.0},
    "zupa fasolowa": {"kcal": 90, "p": 5.0, "f": 3.0, "c": 12.0},
    "krupnik": {"kcal": 80, "p": 3.5, "f": 2.5, "c": 12.0},
    "zupa cebulowa": {"kcal": 60, "p": 2.0, "f": 2.5, "c": 8.0},

    # --- OBIADY (MĄCZNE) ---
    "pierogi ruskie": {"kcal": 200, "p": 6.0, "f": 5.0, "c": 33.0},
    "pierogi z mięsem": {"kcal": 220, "p": 9.0, "f": 7.0, "c": 30.0},
    "pierogi z owocami": {"kcal": 190, "p": 5.0, "f": 3.0, "c": 36.0},
    "kopytka": {"kcal": 160, "p": 3.5, "f": 0.5, "c": 35.0},
    "naleśniki z serem": {"kcal": 210, "p": 9.0, "f": 7.0, "c": 28.0},
    "naleśniki z dżemem": {"kcal": 185, "p": 4.0, "f": 4.5, "c": 32.0},
    "placuszki z cukinii": {"kcal": 145, "p": 4.0, "f": 9.0, "c": 14.0},
    "placki ziemniaczane": {"kcal": 260, "p": 3.0, "f": 15.0, "c": 28.0},
    "pizza margherita": {"kcal": 260, "p": 10.0, "f": 10.0, "c": 33.0},
    "pizza pepperoni": {"kcal": 300, "p": 13.0, "f": 15.0, "c": 28.0},

    # --- DODATKI DO OBIADU ---
    "ziemniaki gotowane": {"kcal": 77, "p": 2.0, "f": 0.1, "c": 17.0},
    "ziemniaki z masłem": {"kcal": 110, "p": 2.0, "f": 4.0, "c": 17.0},
    "puree ziemniaczane": {"kcal": 120, "p": 2.2, "f": 5.0, "c": 16.0},
    "ziemniaki opiekane": {"kcal": 140, "p": 2.5, "f": 5.0, "c": 22.0},
    "frytki": {"kcal": 290, "p": 3.4, "f": 15.0, "c": 35.0},
    "ryż biały": {"kcal": 130, "p": 2.7, "f": 0.3, "c": 28.0},           # gotowany
    "ryż brązowy": {"kcal": 111, "p": 2.6, "f": 0.9, "c": 23.0},         # gotowany
    "kasza gryczana": {"kcal": 120, "p": 4.5, "f": 1.0, "c": 24.0},      # gotowana
    "kasza pęczak": {"kcal": 125, "p": 3.5, "f": 0.5, "c": 26.0},
    "kuskus": {"kcal": 112, "p": 3.8, "f": 0.2, "c": 23.0},

    # --- WARZYWA ---
    "pomidor": {"kcal": 18, "p": 0.9, "f": 0.2, "c": 3.9},
    "ogórek": {"kcal": 15, "p": 0.7, "f": 0.1, "c": 2.9},
    "marchew": {"kcal": 41, "p": 0.9, "f": 0.2, "c": 9.6},
    "cukinia": {"kcal": 17, "p": 1.2, "f": 0.3, "c": 3.1},
    "brokuł": {"kcal": 34, "p": 2.8, "f": 0.4, "c": 6.6},
    "szpinak": {"kcal": 23, "p": 2.9, "f": 0.4, "c": 3.6},
    "cebula": {"kcal": 40, "p": 1.1, "f": 0.1, "c": 9.3},
    "czosnek": {"kcal": 149, "p": 6.4, "f": 0.5, "c": 33.0},
    "papryka czerwona": {"kcal": 31, "p": 1.0, "f": 0.3, "c": 6.0},
    "papryka zielona": {"kcal": 20, "p": 0.9, "f": 0.2, "c": 4.6},
    "papryka marynowana": {"kcal": 25, "p": 0.8, "f": 0.2, "c": 5.5},
    "kapusta biała": {"kcal": 25, "p": 1.3, "f": 0.1, "c": 6.0},
    "kapusta kiszona": {"kcal": 19, "p": 1.0, "f": 0.1, "c": 4.3},
    "kalafior": {"kcal": 25, "p": 1.9, "f": 0.3, "c": 5.0},
    "bakłażan": {"kcal": 25, "p": 1.0, "f": 0.2, "c": 6.0},
    "fasolka szparagowa": {"kcal": 31, "p": 1.8, "f": 0.2, "c": 7.0},
    "sałata lodowa": {"kcal": 14, "p": 0.9, "f": 0.1, "c": 2.9},
    "rukola": {"kcal": 25, "p": 2.6, "f": 0.7, "c": 3.7},
    "burak": {"kcal": 43, "p": 1.6, "f": 0.2, "c": 10.0},
    "seler korzeniowy": {"kcal": 42, "p": 1.5, "f": 0.3, "c": 9.0},
    "pietruszka korzeń": {"kcal": 55, "p": 2.3, "f": 0.6, "c": 12.0},
    "koper": {"kcal": 43, "p": 3.5, "f": 1.1, "c": 7.0},
    "kukurydza konserwowa": {"kcal": 86, "p": 3.2, "f": 1.2, "c": 17.0},
    "groszek konserwowy": {"kcal": 77, "p": 5.0, "f": 0.4, "c": 14.0},
    "pieczarki": {"kcal": 22, "p": 3.1, "f": 0.3, "c": 3.3},

    # --- OWOCE ---
    "jabłko": {"kcal": 52, "p": 0.3, "f": 0.2, "c": 14.0},
    "banan": {"kcal": 89, "p": 1.1, "f": 0.3, "c": 23.0},
    "truskawki": {"kcal": 32, "p": 0.7, "f": 0.3, "c": 7.7},
    "borówki": {"kcal": 57, "p": 0.7, "f": 0.3, "c": 14.5},
    "awokado": {"kcal": 160, "p": 2.0, "f": 15.0, "c": 9.0},
    "gruszka": {"kcal": 57, "p": 0.4, "f": 0.1, "c": 15.0},
    "pomarańcza": {"kcal": 47, "p": 0.9, "f": 0.1, "c": 12.0},
    "mandarynka": {"kcal": 53, "p": 0.8, "f": 0.3, "c": 13.0},
    "kiwi": {"kcal": 61, "p": 1.1, "f": 0.5, "c": 15.0},
    "ananas": {"kcal": 50, "p": 0.5, "f": 0.1, "c": 13.0},
    "winogrona": {"kcal": 69, "p": 0.7, "f": 0.2, "c": 18.0},
    "arbuz": {"kcal": 30, "p": 0.6, "f": 0.2, "c": 8.0},
    "melon": {"kcal": 34, "p": 0.8, "f": 0.2, "c": 8.0},
    "maliny": {"kcal": 52, "p": 1.2, "f": 0.7, "c": 12.0},
    "jeżyny": {"kcal": 43, "p": 1.4, "f": 0.5, "c": 10.0},

    # --- ORZECHY ---
    "orzechy włoskie": {"kcal": 654, "p": 15.0, "f": 65.0, "c": 14.0},
    "orzechy laskowe": {"kcal": 628, "p": 15.0, "f": 61.0, "c": 17.0},
    "migdały": {"kcal": 579, "p": 21.0, "f": 50.0, "c": 22.0},
    "masło orzechowe": {"kcal": 588, "p": 25.0, "f": 50.0, "c": 20.0},
    "nerkowce": {"kcal": 553, "p": 18.0, "f": 44.0, "c": 30.0},
    "pistacje": {"kcal": 562, "p": 20.0, "f": 45.0, "c": 28.0},
    "orzeszki ziemne": {"kcal": 567, "p": 26.0, "f": 49.0, "c": 16.0},

    # --- PIECZYWO ---
    "chleb z otrębami": {"kcal": 211, "p": 12.0, "f": 5.0, "c": 25.0},
    "chleb żytni": {"kcal": 259, "p": 8.5, "f": 3.3, "c": 48.0},
    "bułka pszenna": {"kcal": 272, "p": 8.0, "f": 1.5, "c": 55.0},
    "mój chleb": {"kcal": 211, "p": 12.0, "f": 5.0, "c": 25.0},
    "chleb twarogowy": {"kcal": 211, "p": 12.0, "f": 5.0, "c": 25.0},
    "chleb własny": {"kcal": 211, "p": 12.0, "f": 5.0, "c": 25.0},
    "bagietka": {"kcal": 270, "p": 9.0, "f": 1.5, "c": 55.0},
    "tortilla pszenna": {"kcal": 300, "p": 8.0, "f": 7.0, "c": 50.0},
    "chleb tostowy": {"kcal": 265, "p": 8.5, "f": 3.5, "c": 50.0},

    # --- DODATKI ---
    "cukier biały": {"kcal": 400, "p": 0.0, "f": 0.0, "c": 100.0},
    "cukier trzcinowy": {"kcal": 397, "p": 0.0, "f": 0.0, "c": 99.0},
    "ksylitol": {"kcal": 240, "p": 0.0, "f": 0.0, "c": 99.0},
    "erytrytol": {"kcal": 0, "p": 0.0, "f": 0.0, "c": 100.0},
}
