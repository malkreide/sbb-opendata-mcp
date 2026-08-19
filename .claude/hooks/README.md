# SessionStart-Hook: Klon-Aktualität

`klon-aktualitaet.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter dem Standard-Branch des Remotes liegt. Liegt er
nicht zurück, schweigt er.

## Grund

Ein veralteter Klon hat am 3.8.2026 **zweimal** eine rote CI erzeugt, deren
Ursache nicht im Diff stand: Die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte. Gesucht wurde
daraufhin in den falschen Dateien — im eigenen Diff, der in Ordnung war.

Die Prüfung kostet eine Sekunde und ersetzt diese Fehlersuche. Das ist der
ganze Handel: eine Sekunde pro Sessionstart gegen eine Fehlersuche, die
strukturell am falschen Ort ansetzt, weil die Fehlermeldung auf Code zeigt,
den man gerade geschrieben hat.

## Erste Regel: er blockiert nie

Kein Netz, kein Remote, detached HEAD, flatterndes DNS, fehlendes `git` —
jeder dieser Fälle geht still durch, mit Exit-Code 0 und ohne Ausgabe.

Das ist keine Nachlässigkeit, sondern die wichtigste Eigenschaft. Ein Hook,
der bei Netzproblemen die Arbeit anhält, wird nach dem zweiten Mal
abgeschaltet und schützt danach gar nichts. Ein Hook, der bei Netzproblemen
schweigt, verliert eine einzelne Warnung. Die beiden Fehler sind nicht
gleich viel wert.

Durchgesetzt wird das dreifach, weil eine Zusicherung, die nur aus
sorgfältigem Code besteht, beim nächsten Edit still fällt:

1. `trap 'exit 0' EXIT` — auch ein unvorhergesehener Fehlerpfad endet mit 0.
2. Jeder einzelne Schritt hat ein explizites `|| exit 0`.
3. Beide Netzaufrufe teilen sich eine harte Zeitschranke.

Zusätzlich setzt der Hook `GIT_TERMINAL_PROMPT=0` und `BatchMode=yes`: Ein
git, das interaktiv nach Zugangsdaten fragt, ist genau das Blockieren, das
hier ausgeschlossen sein soll — die Zeitschranke finge es zwar ab, aber erst
nach voller Wartezeit.

## Zeitschranke

`CLAUDE_KLON_CHECK_TIMEOUT` (Default 5) begrenzt die **gesamte** Prüfung, nicht
den einzelnen Aufruf. Der Unterschied fiel beim Nachmessen auf: Mit einer
Schranke je Aufruf summierten sich die beiden Netzaufrufe (`ls-remote`,
`fetch`) gegen ein schwarzes Loch als Remote auf 8,0 Sekunden — beide liefen
die volle Wartezeit aus. Nachgemessen mit dem Gesamtbudget: 5,0 s bei Default,
2,0 s bei `CLAUDE_KLON_CHECK_TIMEOUT=2`, und 5,0 s bei einem unsinnigen Wert
wie `abc`, der sonst auf „unbegrenzt" hinausliefe.

Fehlt `timeout` (macOS ohne coreutils), übernimmt ein Watchdog in bash. Ohne
Zeitschranke laufen zu lassen wäre der eine Fall, in dem der Hook doch hängen
kann.

## Der Standard-Branch wird ermittelt, nicht angenommen

`git ls-remote --symref origin HEAD` fragt den Remote, wie sein
Standard-Branch heißt. Drei Server im Portfolio (`openlex-mcp`,
`swiss-courts-mcp`, `swisstopo-mcp`) nennen ihn `master`; ein fest
verdrahtetes `origin/main` scheitert dort mit «couldn't find remote ref main».
Wer das für ein Netzproblem hält, arbeitet weiter auf genau dem veralteten
Klon, vor dem dieser Hook warnt — so ist schon einmal ein Branch 15 Commits
alt geworden.

Kündigt ein älterer Server kein symref an, zählt ersatzweise der beim Klonen
gesetzte lokale Zeiger `refs/remotes/origin/HEAD`. Schwächer, weil er bei
einer Umbenennung des Standard-Branches veraltet — aber immer noch ermittelt
statt geraten.

## Warum detached HEAD schweigt

Der Vergleich wäre dort rechenbar, aber ein ausgechecktes Tag oder ein
laufendes `git bisect` liegt naturgemäß hinter dem Standard-Branch. Die
Meldung wäre dort kein Befund, sondern Rauschen — und eine Meldung, die immer
dasteht, wird nicht mehr gelesen. Aus demselben Grund schweigt er bei
Rückstand 0.

## Gegenprobe

`tests/test_session_start_hook.py` hält beide Hälften fest — das Schweigen in
den Ausfallfällen und die Meldung, wenn tatsächlich Commits fehlen. Die Tests
bauen echte git-Repositories in einem Temp-Verzeichnis und sprechen über
Dateipfad-Remotes miteinander: kein Netz, damit sie nicht rot werden, weil
gerade eine Quelle stört.

Ohne die erste Hälfte wäre „blockiert nie" eine Behauptung. Ohne die zweite
wäre ein Hook, der aus Versehen immer schweigt, ununterscheidbar von einem,
der funktioniert — er wäre grün und nutzlos.

Jede Zusicherung wurde einzeln neutralisiert, und es fiel genau der
zugehörige Test:

| neutralisiert | fällt |
|---|---|
| Schweigen bei Rückstand 0 | `test_aktueller_klon_schweigt` |
| Standard-Branch fest auf `main` | `test_standard_branch_master_wird_ermittelt_nicht_angenommen` |
| Detached-HEAD-Wache | `test_detached_head` |
| Zeitschranke | beide Zeitschranken-Tests (Lauf 8,5 s → 182 s) |
| `trap 'exit 0' EXIT` | beide Tests in `ExitNullGarantieTest` |
| Grund in der Meldung | `test_meldung_nennt_den_grund` |

Zwei Dinge fielen erst dabei auf, und beide wären still geblieben:

- Der `trap` war zunächst **nicht** widerlegbar. Ihn zu entfernen machte
  keinen einzigen Test rot, weil jeder Schritt zusätzlich sein eigenes
  `|| exit 0` hat und diese Wachen vorher greifen. `ExitNullGarantieTest`
  leitet deshalb aus dem echten Hook eine Variante ab, deren letzte
  Anweisung scheitert — dort trägt der `trap` messbar: mit ihm Exit 0, ohne
  ihn Exit 1.
- Genau dieser Test prüfte zunächst nichts: `str.replace(…, 1)` traf die
  Erwähnung des `trap` im Kommentarkopf statt der Anweisung darunter. Die
  Variante war mit dem Original identisch und der Test grün. Aufgefallen ist
  das nur, weil die Gegenprobe das erwartete Rot nicht lieferte — die
  Ersetzung ist jetzt mit `^…$` an die Anweisung verankert.
