# Muutosloki

Hintavahti-add-onin versiohistoria.

## 2.2.0 (2026-06-17)
Lisätty rate limiting "Tarkista nyt" -endpointille (`slowapi`): sama IP voi käynnistää hintatarkistuksen enintään kerran 30 sekunnissa per tuote. Ylimäärinen pyyntö palauttaa HTTP 429. Lisätty yksikkötestit (`pytest`) scraper.py:n hintaparsinnalle (63 testiä kattaen eri numeroformaatit, CSS-valitsimet, JSON-LD ja meta-tagit) sekä notifier.py:n apufunktioille. Korjattu myös bugi: kapea sitova välilyönti (U+202F, virallinen suomalainen tuhaterotin) ei tunnistunut hinnaksi – lisätty tuki `parse_price`-funktioon.

## 2.1.7 (2026-06-15)
Muutettu hinnan tunnistusjärjestys scraper.py:ssä: kauppakohtaiset CSS-presetit tarkistetaan nyt ennen JSON-LD:tä ja meta-tageja. Näin tarjoushinnat (kuten Motonetin kampanjahinnat) löytyvät oikein ilman manuaalista valitsinta.

## 2.1.6 (2026-06-15)
Päivitetty motonet.fi-presetti: tarjoushinta haetaan nyt `.MuiTypography-root.MuiTypography-h3.mui-sv4qni`-valitsimella ennen normaalihinnan valitsinta. Huom: MUI:n hash-luokka voi muuttua sivustopäivityksen yhteydessä.

## 2.1.5 (2026-06-15)
Lisätty nettiauto.com kauppakohtaisiin CSS-valitsimiin (presets.py). Valitsin: `.details-page-header__item-price-main`.

## 2.1.4 (2026-06-15)
Korjattu Tokmannin hintatunnistus: `.product-info-price .price` on nyt ensimmäinen ehdokas presets.py:ssä. Aiempi järjestys johti väärään hintaan meta-tagin kautta.

## 2.1.3 (2026-06-15)
Lisätty k-ruoka.fi kauppakohtaisiin CSS-valitsimiin (presets.py). Huom: K-Ruoka näyttää hinnan vasta kun kauppa on valittu, joten hintaa ei välttämättä saada ilman erillistä kaupanvalintaa.

## 2.1.2 (2026-06-15)
Korjattu: sähköpostin lähetys kaatui rikkomattomaan välilyöntiin (U+00A0) SMTP-tunnuksessa tai -salasanassa, tyypillisesti Gmailin sovellussalasanaa kopioitaessa. Tunnukset siivotaan nyt ennen kirjautumista. Korjattu myös url-kenttä config.yaml- ja repository.yaml-tiedostoissa.

## 2.1.1 (2026-06-15)
Korjattu: rikkomattomat ja näkymättömät välilyönnit siivotaan sähköpostin osoitteista, otsikosta ja rungosta ennen lähetystä.

## 2.1.0 (2026-06-15)
Lisätty aikavyöhykkeen mukaiset kellonajat (timezone-asetus, oletus Europe/Helsinki) ja Testaa sähköposti -nappi. Uusi päätepiste GET /api/config.

## 2.0.1 (2026-06-15)
Korjattu: add-onin buildi kaatui riviin playwright install --with-deps. Pohjaimage vaihdettu viralliseen Playwright-imageen.

## 2.0.0 (2026-06-15)
Lisätty: paketointi Home Assistant -add-oniksi (Ingress, options), Playwright/Chromium-renderöinti, kauppakohtaiset CSS-valitsimet, HA-sensorit MQTT discoveryllä ja REST-rajapinta GET /api/sensors.

## 1.0.0 (2026-06-15)
Ensimmäinen versio: FastAPI + SQLite, useat välilehdet, hinnan tunnistus (JSON-LD/meta), ajastettu tarkistus, hintahistoria ja sähköposti-ilmoitukset.
