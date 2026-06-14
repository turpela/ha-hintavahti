# Hintavahti

Itse hostattava hintaseuranta Home Assistantille. Seuraa verkkokauppojen
tuotteiden hintoja, ilmoittaa sähköpostilla kun hinta laskee, ja tuo hinnat
Home Assistantiin sensoreina. Käyttöliittymä avautuu suoraan HA:n sivupalkkiin.

## Ominaisuudet

- Useita käyttäjiä omilla välilehdillä, kullakin oma ilmoitussähköposti
- Tuotelinkkien lisäys, muokkaus ja poisto
- Hinnan automaattitunnistus (JSON-LD, meta-tagit) + valmiit CSS-valitsimet
  monille suomalaisille kaupoille + oma valitsin tarvittaessa
- **Playwright/Chromium-renderöinti** sivuille, joilla hinta latautuu JS:llä
- Ajastettu tarkistus + "Tarkista nyt" -nappi, hintahistoria ja sparkline
- Sähköposti-ilmoitus hinnan laskiessa tai tavoitehinnan alittuessa
- **Home Assistant -sensorit** MQTT discoveryllä (tai REST-rajapinta `/api/sensors`)
- Ingress: UI HA:n sivupalkissa ilman porttien avaamista

## Asennus Home Assistant -add-onina (suositus)

1. Lataa tämä hakemisto GitHubiin (tai omaan repositorioon).
2. HA: Asetukset → Apuohjelmat → Add-on Store → ⋮ → **Repositories** →
   lisää repon URL.
3. Asenna **Hintavahti**, säädä asetukset (Configuration-välilehti) ja käynnistä.
4. Avaa UI sivupalkin **Hintavahti**-kohdasta.

Asetukset ja HA-sensoreiden (MQTT) ohjeet: ks. [`hintavahti/DOCS.md`](hintavahti/DOCS.md).

## Standalone (ilman HA:ta)

```bash
docker compose up -d --build
```
UI: `http://<palvelin>:8000`. Asetukset annetaan ympäristömuuttujina
`docker-compose.yml`-tiedostossa. Tietokanta tallentuu kansioon `./data`.

Ilman Dockeria:
```bash
cd hintavahti
pip install -r requirements.txt
playwright install --with-deps chromium   # vain jos käytät JS-renderöintiä
DATABASE_URL="sqlite:///./data/pricetracker.db" \
  uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Rakenne

```
hintavahti/                  # add-on repository (lisää tämä HA:han)
├── repository.yaml
├── docker-compose.yml       # standalone-vaihtoehto
└── hintavahti/              # itse add-on (slug)
    ├── config.yaml          # add-on-manifesti (asetukset, Ingress, MQTT)
    ├── Dockerfile           # python + Playwright/Chromium
    ├── DOCS.md
    ├── requirements.txt
    └── app/
        ├── main.py          # API, tarkistus, ajastin, MQTT-julkaisu
        ├── config.py        # asetukset: options.json / env
        ├── database.py      # mallit + kevyt migraatio
        ├── scraper.py       # haku (httpx/Playwright) + tunnistus
        ├── presets.py       # kauppakohtaiset CSS-valitsimet
        ├── notifier.py      # sähköposti
        ├── ha_mqtt.py       # HA-sensorit (MQTT discovery)
        └── static/index.html
```

## Huomioita

- Playwright tukee arkkitehtuureja amd64 ja aarch64 (esim. Raspberry Pi 4/5
  64-bit, x86). Vanha 32-bit armv7 ei ole tuettu.
- Add-on rakentuu virallisen Playwright-imagen päälle, jossa Chromium on
  valmiiksi asennettuna. Image on tämän vuoksi iso (~1–2 GB) ja ensimmäinen
  asennus kestää hetken.
- Kauppojen sivut muuttuvat ajoittain; jos jonkin kaupan hinta lakkaa
  löytymästä, päivitä valitsin `app/presets.py`-tiedostoon tai anna tuotteelle
  oma CSS-valitsin.
- Tarkoitettu henkilökohtaiseen käyttöön kohtuullisin tarkistusvälein.
