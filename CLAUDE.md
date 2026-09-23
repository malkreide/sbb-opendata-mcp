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

**Und ein 403 ist gar keine Auskunft.** Am 29.8.2026 sollten für 42 Repos die
Dependabot-Labels nachgemessen werden. Alle 13 Abfragen des ersten Stapels
kamen zurück als:

```
Failed to find label: API rate limit already exceeded for user ID 8864492.
```

Der gefährliche Teil steht vorn: Das Werkzeug verpackt eine Sperre als
Fund-Fehlschlag. Wer die Zeile überfliegt oder nur auf ein leeres Ergebnis
prüft, zählt 39 Repos als «Label fehlt» und hat seine eigene Erschöpfung
gemessen. Das Limit hängt am Konto, nicht am Repo — derselbe Vormittag hatte
es mit 42 eröffneten und 42 gemergten PRs verbraucht.

Das ist der Absatz darüber, andersherum gelesen: dort war ein 400 eine echte,
wiederholbare Antwort und galt als Störung; hier ist eine Störung als Antwort
verpackt. Entscheidend ist nie der Statuscode, sondern ob die Quelle überhaupt
geantwortet hat.

- **Positivkontrolle im selben Repo.** Ein «nicht gefunden» wird erst dadurch
  zur Messung, dass eine gleichzeitige Abfrage etwas findet.
- **Die Messung entlang der Sperre teilen.** `raw.githubusercontent.com` ist
  ein CDN und nicht die REST-API. Um 11:19:27 UTC lieferte es für
  `register-mcp` HTTP 200, während die Label-Abfrage desselben Repos in
  derselben Minute die Sperre meldete. Alle 42 `dependabot.yml` kamen so
  durch, während die Label-Hälfte stand.
- **Am Token vorbei geht es nicht.** Beide Umwege enden am Agent-Proxy, und
  jeder mit einer eigenen irreführenden Begründung. `api.github.com` ohne
  Zugangsdaten:

  ```
  GitHub access is not enabled for this session. An org admin must connect
  the Claude GitHub App for this organization.
  ```

  Das ist keine Aussage über die Organisation, sondern das, was ohne Token
  kommt. Wer ihr folgt, sucht einen Admin für ein Problem, das keiner hat.
  Die HTML-Seite `github.com/<owner>/<repo>/labels` fällt ebenfalls, aber
  anders:

  ```
  This GitHub API path is not available: sessions are bound to their
  configured repositories. Use repository-scoped endpoints
  (repos/{owner}/{repo}/...).
  ```

  Der Proxy behandelt also auch `github.com` als API-Pfad; die zweite Meldung
  klingt nach einem Scope-Problem und ist doch nur dieselbe Sackgasse. Den
  Token aus der Umgebung in einen curl-Header zu setzen, blockiert der
  Klassifikator. Ob es überhaupt hülfe, ist offen: die Sperre nennt ein
  Nutzerkonto, und ob der Token zu diesem gehört, wurde nie geprüft.
- **Die Sperre gilt nicht dem Dienst, sondern dem Zugangspfad.** Unmittelbar
  nachdem eine Abfrage der Checks eines PR sauber durchlief, meldete die
  Label-Abfrage weiter die Sperre. Von einem blockierten Werkzeug also nicht
  auf «GitHub ist zu» schliessen — und umgekehrt eine gelungene Abfrage nicht
  als Entwarnung für die gesperrte nehmen.

Wann die Sperre fällt, geben diese Beobachtungen nicht her. Die Meldung nennt
keinen Zeitpunkt, und die `X-RateLimit`-Kopfzeilen sind hinter dem Proxy nicht
zu sehen. Belegt sind drei gesperrte Zeitpunkte — 11:14, 11:16 und 11:19 UTC.
Wer daraus eine Dauer macht, hat sie erfunden.

**Dieselbe Falle bei einer Konfigurationsoption: die Vorgabe lesen, bevor man
einen Schlüssel für wirkungslos hält.** Am 29.8.2026 fielen die
`labels:`-Zeilen aus den `dependabot.yml` des Portfolios, begründet mit
«Dependabot legt Labels nicht an». Eine Messung danach zeigte, dass
`dependencies` in 36 von 42 Repos sehr wohl existiert, 35 davon mit GitHubs
Standardbeschreibung. Das las sich zuerst wie ein Beleg, dass die Aktion
falsch war.

Die Optionsreferenz kehrt es um:

```
Dependabot creates these default labels automatically, as necessary in
your repository.

If you define more than one package manager, an additional label for the
ecosystem or language is added to each pull request.

The labels specified are used instead of the default labels.
```

Ohne `labels:` vergibt Dependabot also `dependencies` — und, sobald mehr als
ein Paketmanager deklariert ist, zusätzlich ein Ökosystem-Label — und legt sie
selbst an; eine eigene Liste **ersetzt** diesen Satz, und «if any of these
labels is not defined in the repository, it is ignored». Die Zeile war nicht
wirkungslos — sie tauschte einen sich selbst pflegenden Vorgabesatz gegen eine
starre Liste.

**Die Bedingung nicht weglassen.** Bei nur einem Paketmanager steht das
Ökosystem-Label gar nicht zu; wer es dort trotzdem erwartet, schreibt genau
den Fehlbefund auf, gegen den dieser Abschnitt geschrieben ist — der Abschnitt
liefe an sich selbst vorbei. Im Portfolio deklariert jede `dependabot.yml`
zwei (`pip` und `github-actions`), die Bedingung ist hier also überall
erfüllt; anderswo nicht unbedingt. Aufgefallen ist die fehlende Bedingung
nicht beim Schreiben, sondern durch einen Codex-Review auf
`swiss-environment-mcp` PR #113 — vierzehn Sekunden vor dem Merge desselben
PR.

Was das kostet, ist an `openlex-mcp` gemessen: zwei Ökosysteme deklariert,
also stünden `dependencies` **und** ein Ökosystem-Label zu; vorhanden ist nur
das erste, `github-actions` und `github_actions` fehlen beide (Kontrolle `bug`
vorhanden). `register-mcp` ist die Gegenprobe: dort existieren alle vier
deklarierten Namen mit handgeschriebener Beschreibung, die Liste ist gewollt
und vollständig.

**Dreimal falsch eingeordnet, in drei Richtungen.** Erst die Zeile für bloss
wirkungslos gehalten. Dann die gefundenen Labels für einen Widerspruch. Dann,
auf denselben Fund gestützt, einen richtigen PR geschlossen mit dem Argument,
das Label existiere ja — obwohl es existiert, *weil* die Vorgabe es anlegt.
Der dritte Fehler ist der teuerste, weil er wie eine Messung aussah.

Was die Messung **nicht** hergibt: wer die 36 Labels angelegt hat. Die
Referenz sagt, Dependabot tue es; die Objekt-IDs liegen aber so dicht
beieinander, dass sie eher aus einem Stapellauf stammen. Beides passt zum
Befund, keines ist belegt — die Herkunft blieb ungemessen.

Beim Aufräumen gilt deshalb dieselbe Frage wie bei `lotId`: Was ist die
*Vorgabe*, wenn man das Ding weglässt — nicht bloss, ob der aktuelle Wert
etwas bewirkt.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

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
