# Hintavahti

Seuraa verkkokauppojen tuotteiden hintoja ja ilmoittaa kun hinta laskee.
Käyttöliittymä avautuu suoraan Home Assistantin sivupalkkiin (Ingress).
Jokaisella käyttäjällä on oma välilehti omille linkeilleen ja
ilmoitussähköpostille. Hinnat voidaan myös tuoda Home Assistantiin
sensoreina MQTT:n kautta.

## Asennus

1. Asetukset → Apuohjelmat (Add-ons) → Add-on Store → oikea yläkulma →
   **Repositories** → lisää tämän repositorion URL.
2. Asenna **Hintavahti** ja käynnistä se.
3. Avaa käyttöliittymä sivupalkin **Hintavahti**-kohdasta.

## Asetukset

| Asetus | Selitys |
|---|---|
| `check_interval_hours` | Kuinka usein kaikki hinnat tarkistetaan (tunteina). |
| `request_delay_seconds` | Viive pyyntöjen välillä tarkistuskierroksella. |
| `playwright_enabled` | Salli sivujen renderöinti selaimella (JS-sivut). |
| `log_level` | Lokitaso: debug / info / warning / error. |
| `smtp_*` | Sähköpostipalvelimen tiedot ilmoituksia varten (valinnainen). |
| `mqtt_enabled` | Julkaise tuotteet HA-sensoreina MQTT:n kautta. |
| `mqtt_*` | MQTT-brokerin tiedot. Jää tyhjäksi → haetaan Mosquitto-add-onilta. |

### Sähköposti

Jätä `smtp_host` tyhjäksi, jos et halua sähköposteja — hinnanlaskut näkyvät
silti käyttöliittymässä ja lokissa. Gmailille: `smtp_host: smtp.gmail.com`,
`smtp_port: 587`, käyttäjänä sähköpostiosoite ja salasanana **sovellussalasana**.

### Home Assistant -sensorit (MQTT)

1. Asenna ja käynnistä **Mosquitto broker** -add-on.
2. Aseta tähän add-oniin `mqtt_enabled: true`. Jätä `mqtt_host` tyhjäksi —
   broker haetaan automaattisesti Supervisorilta.
3. Jokainen tuote ilmestyy laitteen **Hintavahti** alle sensorina, jonka tila
   on nykyinen hinta. Sensorin attribuutteina ovat mm. alin hinta,
   tavoitehinta ja linkki.

Sensoreita voi käyttää automaatioissa, esim. ilmoitus puhelimeen kun
`sensor.hintavahti_1` laskee alle halutun rajan.

### Ilman MQTT:tä

Hinnat saa myös REST-rajapinnasta: `GET /api/sensors` palauttaa listan
tuotteista hintoineen. Tätä voi lukea HA:n RESTful-sensorilla.

## Hintojen tunnistus

Hinta etsitään tässä järjestyksessä: oma CSS-valitsin → sivun JSON-LD-tuotetieto
→ kaupan valmis valitsin (osa suomalaisista kaupoista) → yleiset meta-tagit.
Jos hinta latautuu vasta JavaScriptillä, rastita tuotteelle **Renderöi sivu
selaimella (JS)**.

Käytä kohtuullisia tarkistusvälejä, jotta et kuormita kauppojen sivustoja.
