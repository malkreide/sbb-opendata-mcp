# CLAUDE.md

## Teil 1 — Konventionen (portfolio-weit)

### Vor der Arbeit

Klon-Aktualität prüfen: `git fetch origin main && git rev-list --count HEAD..origin/main`
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

PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.

Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

## Teil 2 — dieses Repo

### ruff-Version: an drei Stellen, immer dieselbe

`.github/workflows/ci.yml`, `.pre-commit-config.yaml` und `pyproject.toml`
(`[dev]` und `[tool.hatch.envs.default]`) nennen alle `0.16.1`. Beim Anheben
alle drei Dateien anfassen — sonst meldet ruff lokal Abweichungen, die niemand
verursacht hat, oder es meldet lokal nichts und die CI wird rot.

`pre-commit install` einmal pro Klon, dann fahren die Gates von selbst mit.

### Gate-Befehle (wörtlich aus `ci.yml`, Reihenfolge = CI; Matrix 3.11/3.12/3.13)

```sh
pip install -e ".[dev]"
PYTHONPATH=src pytest tests/ -m "not live"
pip install ruff==0.16.1
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
| `unknown` | Suite lief **nicht** (Install kaputt, Marke umbenannt, alles übersprungen) |

`unknown` ist der Fall, der ohne Klassifikator verlorengeht: pytest endet mit
0, wenn jeder Test übersprungen wurde. Ein Job, der das als grün bucht,
schliesst ein offenes Issue mit einem Vergleich, den es nie gab.

GitHub schaltet geplante Workflows nach 60 Tagen ohne Repo-Aktivität ab. Bei
einem ruhenden Repo ist ein grünes `live.yml` also unter Umständen gar keine
Aussage, sondern ein Workflow, der nicht mehr läuft.
