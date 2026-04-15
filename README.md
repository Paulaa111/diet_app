# 🍽️ Licznik Kalorii AI

Aplikacja Streamlit do śledzenia kalorii — wpisujesz co zjadłeś po polsku, AI szacuje kalorie i pokazuje ile zostało do limitu 2000 kcal.

## ✨ Funkcje

- 🤖 AI (Google Gemini Flash) rozpoznaje kalorie z opisu po polsku
- 🍞 Wbudowany własny chleb z otrębami i twarogiem — **działa BEZ klucza API!**
- 📊 Pasek postępu (zielony → pomarańczowy → czerwony)
- 🗑️ Usuwanie posiłków, reset dnia
- 🔄 Automatyczny reset o północy

## 🍞 Kalorie chleba z otrębami (wbudowane)

| | Waga | Kalorie |
|---|---|---|
| 100g | 100g | 211 kcal |
| 1 plasterek | 40g | 84 kcal |
| 1 kromka | 80g | 169 kcal |

## 🚀 Uruchomienie lokalne

```bash
git clone https://github.com/TWOJ_NICK/licznik-kalorii.git
cd licznik-kalorii
pip install -r requirements.txt
streamlit run app.py
```

Klucz Gemini wpisz w panelu bocznym aplikacji (lub dodaj do `.streamlit/secrets.toml`).

## 🔑 Klucz Gemini API (darmowy!)

1. Wejdź na https://aistudio.google.com
2. Kliknij **Get API key** → **Create API key**
3. Wklej klucz w panelu bocznym aplikacji

## ☁️ Deploy na Streamlit Cloud (darmowy)

1. Wgraj kod na GitHub
2. Wejdź na https://share.streamlit.io → połącz repo
3. Kliknij **Deploy** — klucz API wpisuje się w panelu bocznym przy użyciu

## 📝 Przykłady wpisów

- `2 kromki chleba z otrębami` ← działa bez klucza!
- `miska płatków owsianych z bananem i miodem`
- `schabowy z ziemniakami i surówką`
- `jogurt naturalny 150g, garść orzechów`
- `3 jajka sadzone, 2 tosty`
