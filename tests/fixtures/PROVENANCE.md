# Herkunft der Fixtures

**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**

Aufgezeichnet am **2026-08-08** von `data.sbb.ch`, unveraendert bis
auf die je Datei dokumentierte Auswahl.

Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht
mehr zu unterscheiden — die Datei sieht gleich aus, und niemand weiss,
ob sie den Stand von gestern zeigt oder den von vor drei
Schema-Wechseln. Das Datum macht diesen Abstand zu einer lesbaren Zahl.

## `dataset_fields.json` ist kein Datenauszug, sondern der Vertrag

Die Explore-v2.1-API deklariert je Datensatz, welche Felder es gibt.
Ein `select` oder `order_by` auf ein Feld, das dort fehlt, beantwortet
sie mit **HTTP 400** — nicht mit weniger Spalten. Der Unterschied ist
der ganze Punkt: Ein fehlendes Feld faellt nicht als Luecke auf,
sondern als Ausfall, und der Nutzer liest «API-Anfrage
fehlgeschlagen». `tests/test_server.py` haelt deshalb jeden Feldnamen,
den der Server verwendet, gegen diese Aufzeichnung.

**Es sind Ausschnitte, keine Vollabzuege**, und die Auswahlregel steht
je Datei dabei. Eine Fixture belegt damit die *Form* der Antwort und
einen datierten Ausschnitt ihres Inhalts — nicht den Bestand. Aussagen
ueber Vollstaendigkeit gehoeren in Live-Tests (`pytest -m live`).

## `dataset_fields.json`

- **Quelle:** `https://data.sbb.ch/api/explore/v2.1/catalog/datasets/<dataset>`
- **Aufgezeichnet:** 2026-08-08
- **Auswahl:** die deklarierten Feldnamen (`fields[].name`) je Datensatz, den der Server benutzt — vollstaendig. Gegen diese Liste haelt der Test jedes `select` und jedes `order_by`; ein Feld, das hier fehlt, beantwortet die Quelle mit HTTP 400 und nicht mit weniger Spalten
- **Groesse:** 2540 B
- **SHA-256:** `c89c8eae4e125b5dc9cd9030c1b6d4fc2c8e46f4d2ff6faf9f679d1eab5beb39`

## `catalog.json`

- **Quelle:** `https://data.sbb.ch/api/explore/v2.1/catalog/datasets?limit=100&order_by=title+asc`
- **Aufgezeichnet:** 2026-08-08
- **Auswahl:** die ersten 12 von 61 Katalogeintraegen, je auf die vier Angaben gekuerzt, die das Werkzeug liest (`dataset_id`, `metas.default.title`, `metas.default.records_count`, `metas.dcat.accrualperiodicity`); `total_count` unveraendert. Der Sortierschluessel gehoert zur Aufzeichnung: `metas.default.title` kennt der Katalog-Endpunkt NICHT, `title` schon
- **Groesse:** 3199 B
- **SHA-256:** `233def1f44bf85dc327c9c59f485446ae3273d2008bd3cfbad0c34121353506e`

## `stations_search.json`

- **Quelle:** `https://data.sbb.ch/api/explore/v2.1/catalog/datasets/dienststellen-gemass-opentransportdataswiss/records`
- **Aufgezeichnet:** 2026-08-08
- **Auswahl:** Suche nach 'Wädenswil', 20 von 54 Treffern. Die Auswahl ist die Anfrage des Servers selbst, mit seiner eigenen Feldliste — nur so belegt die Fixture, dass die Feldnamen stimmen
- **Groesse:** 8399 B
- **SHA-256:** `40d3c82d0e137ac43ac65cbcfd6852232887f6c2296798a23544de7ee521b7d0`

## `stations_expired.json`

- **Quelle:** `https://data.sbb.ch/api/explore/v2.1/catalog/datasets/dienststellen-gemass-opentransportdataswiss/records`
- **Aufgezeichnet:** 2026-08-08
- **Auswahl:** 3 Eintraege mit echtem Ablaufdatum (von 15). Nach Merkmal ausgewaehlt, nicht nach Position: Fast alle Eintraege tragen den Fuellwert 9999-12-31, und «die ersten N» haetten ausgerechnet die unauffaelligen getroffen
- **Groesse:** 1290 B
- **SHA-256:** `6212599457c380b0d7abdc6a57bcb1675313e09c256ed9bcc8bf93ad86b097e5`

## `passenger_frequency.json`

- **Quelle:** `https://data.sbb.ch/api/explore/v2.1/catalog/datasets/passagierfrequenz/records`
- **Aufgezeichnet:** 2026-08-08
- **Auswahl:** die 6 juengsten Zeilen (order_by wie im Server) von 5724
- **Groesse:** 3525 B
- **SHA-256:** `980d43dff49b9f4de91a24d311d7fd8d1fd359cae5cbfc443712962e310a30e3`

## `rail_disruptions.json`

- **Quelle:** `https://data.sbb.ch/api/explore/v2.1/catalog/datasets/rail-traffic-information/records`
- **Aufgezeichnet:** 2026-08-08
- **Auswahl:** die 6 juengsten Meldungen von 5849
- **Groesse:** 6839 B
- **SHA-256:** `6ccd850e78530671fedf8e246ba123600cd63f6a128962cb81bf66e16b95dfd3`
