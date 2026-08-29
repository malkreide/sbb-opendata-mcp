# CLAUDE.md

## Teil 1 — Konventionen (portfolio-weit)

### Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen:

```bash
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.

Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

### Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.

Zwei Fallen, die beide grün blieben:

- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
  echte Zeit nicht widerlegen.
- `monkeypatch.setattr(modul.asyncio, "sleep", ...)` greift ins Modul
  `asyncio` selbst und entschärft die Mechanik im ganzen Prozess. Patche
  einen Modul-Alias (`_sleep = asyncio.sleep`), nicht das fremde Modul.

Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

### Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.

**Ein 4xx ist kein Nein.** Am 29.8.2026 antwortete `past-publications` in
`swiss-procurement-mcp` auf jede Publikation mit Losen mit HTTP 400. Daraus war
geschlossen worden, die Quelle verweigere diese Auskunft; der Befund stand
datiert im Fixture-Nachweis, ein Test bestätigte ihn, alles blieb grün. Die
Spec desselben Endpunkts führt einen als *optional* deklarierten Parameter
`lotId` — für Publikationen mit Losen ist er Pflicht. Mit ihm antwortet
dieselbe Publikation mit 200. Ein Projekt trug sieben Vorgängerpublikationen,
die der Server als «Quelle nicht erreichbar» wegwarf.

Drei Handgriffe daraus:

- **Die Parameterliste der Spec durchgehen, bevor ein Statuscode eingeordnet
  wird.** «Optional» heisst dort oft «optional für die Mehrheit».
- **Einer deterministischen Absage keinen Wiederholungsrat geben.** «Nicht
  erreichbar, bitte später erneut» ist bei einem 400 falsch und liest sich für
  das Modell wie eine Störung. Den Status mitführen und den fehlenden
  Parameter benennen — den Status, nicht den Antwortkörper.
- **Beide Antworten aufzeichnen, mit und ohne den Parameter.** Eine
  Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar war;
  dass nur der 400er aufgezeichnet war, ist der Grund, warum der falsche
  Befund nicht auffiel.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

### Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Zwischen erster und letzter Limit-Meldung liegen **25 h 15 min**. Das ist der
Abstand zweier Fehlschläge, nicht die Dauer einer Sperre. Wer ihn Untergrenze
nennt, hat die durchgehende Erschöpfung schon vorausgesetzt, die er belegen
soll: Öffnete sich das Fenster zwischendurch und schloss es sich durch neue
Auslöser wieder, waren es zwei kurze Sperren und nie eine von 25 Stunden.
Untergrenze einer *einzelnen* Sperre sind die 25 h 15 min nur unter genau dieser
Annahme — und die ist unbelegt.

Nach oben trägt die Rechnung dagegen. Die längste mit den Beobachtungen
verträgliche Sperre reicht vom letzten Erfolg um 08:41 bis zur abweichenden
Meldung um 08:22, also **47 h 41 min**; länger kann keine einzelne gewesen sein.
Wer stattdessen ab der ersten Limit-Meldung rechnet, unterschlägt die 67
Minuten, in denen das Kontingent schon weg gewesen sein kann, und nennt die
Spanne zwischen zwei Beobachtungen eine Obergrenze.

Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor der abweichenden
Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Vier** Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann schreibt er einen gewöhnlichen Issue-Kommentar:

  ```
  Codex Review: Didn't find any major issues. Swish!
  ```

  Der Schlusssatz wechselt bei jedem Lauf («Delightful!», «Keep it up!»,
  «More of your lovely PRs please.»); stabil ist nur der Satz davor. Der
  Infokasten, den Codex unter jeden Review setzt, behauptet weiterhin eine
  Reaktion («otherwise it will react with 👍») — am 23.8. kam in sechs Repos
  die Meldung und in keinem die Reaktion. Der Kasten ist keine Quelle.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Für das Repo fehlt eine Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch ein
Review-Objekt **oder** eine Befundlos-Meldung. Wer nur das Objekt gelten lässt,
zählt jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm
ein, den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe); ein Review **ohne** Befund und die
beiden Ausfallmeldungen — Kontingent wie Environment — sind gewöhnliche
Issue-Kommentare und trennen sich nur im Text. Beim Draft gibt es überhaupt
nichts, weil Codex nicht anläuft; ein kommentarloser Draft ist deshalb kein
Beleg, sondern ein nicht durchgeführter Test.

Das sind verschiedene Abfragen — `get_reviews` fürs Objekt, `get_comments` für
alles andere; wer nur eine nimmt, übersieht den Rest. Genau so ist die
Limit-Meldung zuerst durchgerutscht.

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Befundlos-, die Kontingent- **oder** die Environment-Meldung sein — drei
gegensätzliche Bedeutungen unter derselben Zahl. Den Text lesen, nicht die Zahl.
Und einen unbekannten vierten Text wörtlich zitieren, statt ihn in eine der
bekannten Schubladen zu zwingen: Dieser Abschnitt musste schon einmal von drei
auf vier Gründe wachsen, und die 👍-Reaktion stand hier zwei Fassungen lang als
Tatsache.

Und ein befundloser Lauf ist kein Freispruch. Am 23.8. lief derselbe Text durch
42 Reviews: 36 meldeten denselben P2-Befund, 6 die Befundlos-Meldung — gleiche
Eingabe, gegenteiliges Urteil, alles in denselben neun Minuten. Ein sauberer
Lauf sagt damit etwas über den Lauf, nicht über den Text. Wer sein Häkchen
daran hängt, hängt es an einen Münzwurf.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die Lücke oben
schliesst das Fünf-Stunden-Fenster nicht aus: Es kann sich zwischendurch
geöffnet und durch neue Auslöser wieder erschöpft haben. Das auszuschliessen
bräuchte den Nachweis, dass in der ganzen Spanne kein einziger Review durchlief
— den gibt es nicht, weil nur Fehlschläge beobachtet wurden. Eine lange Reihe
von Fehlschlägen belegt eine lange Reihe von Fehlschlägen, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Die Meldung sagt es selbst («for this repo»), und am
23.8. war es genau so: In `swiss-public-data-mcp` fehlte sie, dort kam kein
Review; in den übrigen Repos lief Codex am selben Morgen durch. Eine
Environment fürs Konto genügt also nicht — wer eine anlegt und den Rest für
erledigt hält, mergt weiter Ungeprüftes.

### Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt:

```bash
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Teil 2 — dieses Repo

**ruff: eine Quelle — und zwar wörtlich eine.** Der Pin `0.16.3` steht
ausschliesslich im `[dev]`-Extra von `pyproject.toml`. `ci.yml` installiert
nur dieses Extra, `[tool.hatch.envs.default]` zieht es über
`features = ["dev"]`, und die pre-commit-Hooks rufen das ruff aus dem `PATH`
statt ein eigenes `rev:` mitzubringen. Anheben also genau dort — sonst
nirgends.

Bis zu diesem Commit waren es **drei** Stellen: das `[dev]`-Extra, eine eigene
`dependencies`-Liste in `[tool.hatch.envs.default]` und `rev: v0.16.3` in
`.pre-commit-config.yaml`. Alle drei nannten dieselbe Version, erzwungen wurde
das von nichts — und jeder Rückfall wäre still: Er macht kein Gate rot, er
lässt lokal nur eine andere Version prüfen als die, gegen die die CI prüft.

`tests/test_werkzeug_versionen.py` hält das jetzt fest, statt es zu behaupten.
Sechs Zusicherungen, jede einzeln gegengeprobt: exakter Pin genau einmal, kein
Workflow installiert ruff selbst, die hatch-Umgebung zählt nicht selbst auf,
`.pre-commit-config.yaml` nennt keine Version. Der Test läuft im bestehenden
pytest-Gate; ein neuer CI-Schritt war dafür nicht nötig.

`language: system` macht eine Lücke auf — der `PATH` kann ein fremdes ruff
liefern. Dagegen läuft `scripts/check_ruff_pin.py` als **erster** Hook: schlägt
er fehl, sind die Ergebnisse der beiden ruff-Hooks darunter für die CI nicht
aussagekräftig. Nachgemessen: mit einem ruff `0.15.8` früher im `PATH` meldet
er «Version weicht ab» und bricht ab.

`pip install -e ".[dev]" && pre-commit install` einmal pro Klon, dann fahren
die Gates von selbst mit.

`scripts/check_version_sync.py` prüft hier nur die Paketversion, nicht den
ruff-Pin: seine Ausgabe nennt keine ruff-Zeile. (Die Fassung in
`swiss-electricity-mcp` und `bakom-mcp` kann das — hier übernimmt das der
Test statt des Skripts.)

### Gate-Befehle (wörtlich aus `ci.yml`, Reihenfolge = CI; Matrix 3.11/3.12/3.13)

```sh
pip install -e ".[dev]"
PYTHONPATH=src pytest tests/ -m "not live"
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python scripts/check_version_sync.py
```

### Live-Tests (DRIFT-005)

`ci.yml` schliesst die `@pytest.mark.live`-Tests mit `-m "not live"` aus — ein
PR soll nicht rot werden, weil die Quelle gerade stört. Gefahren werden sie von
`live.yml`, täglich 05:15 UTC und per `workflow_dispatch`. Von Hand:

```sh
PYTHONPATH=src pytest tests/ -m live
```

Der Feld-Vertrag hat zwei Hälften, und nur beide zusammen greifen:

| Test | hält | fängt |
|---|---|---|
| `TestFieldContract` (offline) | Server gegen `dataset_fields.json` | falsches Feld im Server |
| `test_live_the_recording_still_matches_the_source` | Aufzeichnung gegen die Quelle | veraltete Aufzeichnung |

Eine Aufzeichnung kann ihre eigene Veralterung nicht bemerken. Ohne die zweite
Hälfte bleiben beim Feldnamen-Wechsel der Quelle alle Offline-Tests grün,
während die Werkzeuge HTTP 400 kassieren — der Zustand vom 3.8.2026. Beide
Hälften lesen dieselbe Liste (`fields_the_server_uses()`); als zwei Kopien
würden ausgerechnet sie auseinanderlaufen.

Wird es rot, gilt Teil 1: erst die Quelle abfragen, dann einordnen. Meldet der
Test «Aufzeichnung überholt», ist die Antwort `python scripts/record_fixtures.py`
— und danach ein Blick, ob der Server die verschwundenen Felder benutzt.

Ein roter Lauf erzeugt ein Issue mit Label `upstream` und stabilem Titel;
wird die Suite wieder grün, schliesst es sich selbst. Über auf oder zu
entscheidet nicht der Exit-Code, sondern `scripts/classify_live_run.py` —
denn ein Live-Lauf hat drei Antworten, nicht zwei:

| | heisst |
|---|---|
| `clear` | Suite lief, alles grün — nur hier geht ein Issue zu |
| `finding` | Suite lief, etwas fiel — Issue auf |
| `unknown` | Suite lief **nicht** (Install kaputt, Marke umbenannt, alles übersprungen) — und ebenso: die Quelle hat nicht geantwortet |

`unknown` ist der Fall, der ohne Klassifikator verlorengeht: pytest endet mit
0, wenn jeder Test übersprungen wurde. Ein Job, der das als grün bucht,
schliesst ein offenes Issue mit einem Vergleich, den es nie gab.

Die dritte Antwort hat zwei Wege hinein, und der zweite wurde lange übersehen.
Am 26.8.2026 lief `test_live_search_waedenswil` ins 30-s-Zeitlimit; der Lauf
wurde `finding` und Issue #48 behauptete, der Vertrag habe sich geändert.
Nachgemessen am Tag darauf, gleiche Anfrage: sechs Läufe, 0.44–0.80 s, HTTP 200.
Der Docstring des Klassifikators nannte «ein Timeout» schon als `unknown` — nur
kam ein Timeout *innerhalb* eines Tests nie dort an, sondern als Fehlschlag.

**Keine Antwort ist kein Befund.** Timeout, Verbindungsabbruch, 429 und 5xx
heissen: Die Quelle hat nichts gesagt, und über den Feld-Vertrag folgt daraus
weder das eine noch das andere. `live_attempt()` wiederholt sie dreimal und
überspringt danach mit `SOURCE_UNAVAILABLE` im Grund; der Klassifikator liest
den Marker und antwortet `unknown`.

Die Grenze ist die ganze Sache: **HTTP 400 und 404 sind Antworten** und bleiben
Fehlschläge. 400 ist genau die vom 3.8.2026, als die Quelle einen Feldnamen
wechselte. Verschluckt diese Mechanik sie, verschluckt sie den Fehler,
dessentwegen die Live-Suite existiert — deshalb ist die Gegenprobe dazu
(`test_a_findings_status_is_never_swallowed`) wichtiger als die Mechanik selbst.

Und ein Skip heisst nicht immer dasselbe: «Vorbedingung nicht erfüllt» ist eine
Entscheidung im Test und lässt den Rest des Laufs gültig, «Quelle weg» heisst,
dass dieser Teil nicht verglichen wurde. Wer beide gleich behandelt, muss sich
zwischen zwei Fehlern entscheiden — jede bewusste Vorbedingung zum Ausfall
erklären, oder einen echten Ausfall grün buchen. Der Marker trennt sie; beide
Richtungen sind gegengeprobt.

Ein Nebenbefund derselben Simulation, und er zeigt, wozu sie taugt: Fünf Tests
übersprangen, `test_live_list_datasets` lief grün durch — das Werkzeug trug die
Basis-URL als **zweites Literal** und zeigte als einziges nicht dorthin, wohin
`BASE_URL` zeigt. Zwei Kopien derselben Adresse fallen nicht auf, solange beide
gleich lauten, und beim Umzug fällt die zweite still aus, weil die alte Adresse
ja antwortet.

GitHub schaltet geplante Workflows nach 60 Tagen ohne Repo-Aktivität ab. Bei
einem ruhenden Repo ist ein grünes `live.yml` also unter Umständen gar keine
Aussage, sondern ein Workflow, der nicht mehr läuft.
