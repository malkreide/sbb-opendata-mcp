#!/usr/bin/env bash
#
# SessionStart-Hook: meldet, wie viele Commits der ausgecheckte Stand hinter
# dem Standard-Branch des Remotes liegt. Bei 0 schweigt er.
#
# GRUND. Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt,
# deren Ursache nicht im Diff stand: Die fehlenden Commits waren jeweils genau
# die, die das Gate einfuehrten, an dem der Branch scheiterte. Gesucht wurde
# daraufhin in den falschen Dateien. Die Pruefung kostet eine Sekunde und
# ersetzt diese Fehlersuche.
#
# ERSTE REGEL: Dieser Hook blockiert die Session NIEMALS. Kein Netz, kein
# Remote, detached HEAD, flatterndes DNS, fehlendes git — jeder dieser Faelle
# geht still durch. Ein Hook, der bei Netzproblemen die Arbeit anhaelt, wird
# nach dem zweiten Mal abgeschaltet und schuetzt danach gar nichts. Ein Hook,
# der bei Netzproblemen schweigt, verliert eine einzelne Warnung.
#
# Durchgesetzt wird das dreifach, weil eine Zusicherung, die nur aus
# sorgfaeltigem Code besteht, beim naechsten Edit still faellt:
#   1. `trap 'exit 0' EXIT` — auch ein unvorhergesehener Fehlerpfad endet mit 0.
#   2. Jeder Schritt hat ein explizites `|| exit 0`.
#   3. Beide Netzaufrufe laufen unter einer harten Zeitschranke.
#
# tests/test_session_start_hook.py haelt beides fest: das Schweigen in den
# Ausfallfaellen und die Meldung, wenn tatsaechlich Commits fehlen.

# Egal welcher Pfad hier endet — die Session sieht 0.
trap 'exit 0' EXIT

# Sekunden fuer die GESAMTE Pruefung, nicht je Aufruf. Das ist der
# Unterschied, der beim Nachmessen auffiel: Mit einer Schranke je Aufruf
# summierten sich die beiden Netzaufrufe (ls-remote, fetch) gegen einen
# schwarzen Loch als Remote auf 8,0 Sekunden — beide liefen die volle
# Wartezeit aus. Der Sessionstart soll aber insgesamt nur wenige Sekunden
# warten, nicht wenige Sekunden mal Anzahl Aufrufe.
ZEITSCHRANKE="${CLAUDE_KLON_CHECK_TIMEOUT:-5}"
# Eine kaputt gesetzte Variable darf den Hook nicht ins Unbegrenzte schicken.
case "$ZEITSCHRANKE" in
  '' | *[!0-9]*) ZEITSCHRANKE=5 ;;
esac
[ "$ZEITSCHRANKE" -gt 0 ] || ZEITSCHRANKE=5

# `SECONDS` zaehlt ab hier; `rest` gibt das noch verbliebene Budget.
SECONDS=0
rest() {
  uebrig=$((ZEITSCHRANKE - SECONDS))
  [ "$uebrig" -ge 1 ] || uebrig=0
  printf '%s' "$uebrig"
}

# git darf unter keinen Umstaenden interaktiv nach Zugangsdaten fragen: ein
# wartender Prompt ist genau das Blockieren, das hier ausgeschlossen sein
# soll. Die Zeitschranke faenge es zwar ab, aber erst nach voller Wartezeit.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=true
export SSH_ASKPASS=true
export GIT_OPTIONAL_LOCKS=0
# Nur setzen, wenn der Aufrufer nichts eigenes mitbringt — sonst ueberschreibt
# der Hook eine bewusst gesetzte SSH-Konfiguration.
if [ -z "${GIT_SSH_COMMAND:-}" ]; then
  export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=${ZEITSCHRANKE}"
fi

# `timeout` ist auf macOS ohne coreutils nicht da. Fehlt es, uebernimmt ein
# Watchdog in bash die Aufgabe: ohne Zeitschranke laufen zu lassen waere der
# eine Fall, in dem der Hook doch haengen kann.
if command -v timeout >/dev/null 2>&1; then
  ZEIT_BIN="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  ZEIT_BIN="gtimeout"
else
  ZEIT_BIN=""
fi

mit_zeitschranke() {
  budget="$(rest)"
  # Budget schon aufgebraucht: gar nicht erst anfangen.
  [ "$budget" -gt 0 ] || return 124
  if [ -n "$ZEIT_BIN" ]; then
    "$ZEIT_BIN" "${budget}s" "$@"
    return $?
  fi
  "$@" &
  watchdog_pid=$!
  gewartet=0
  while kill -0 "$watchdog_pid" 2>/dev/null; do
    if [ "$gewartet" -ge "$budget" ]; then
      kill -TERM "$watchdog_pid" 2>/dev/null
      wait "$watchdog_pid" 2>/dev/null
      return 124
    fi
    sleep 1
    gewartet=$((gewartet + 1))
  done
  wait "$watchdog_pid"
}

command -v git >/dev/null 2>&1 || exit 0

# $CLAUDE_PROJECT_DIR setzt Claude Code; der Fallback macht den Hook von Hand
# aufrufbar, was der Test ausnutzt.
PROJEKT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJEKT" ]; then
  PROJEKT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
fi
cd "$PROJEKT" 2>/dev/null || exit 0

git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# Detached HEAD geht still durch. Der Vergleich waere zwar rechenbar, aber ein
# ausgecheckter Tag oder ein laufendes `git bisect` liegt naturgemaess hinter
# dem Standard-Branch — dort ist die Meldung kein Befund, sondern Rauschen.
git symbolic-ref --quiet HEAD >/dev/null 2>&1 || exit 0
git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || exit 0

git remote get-url origin >/dev/null 2>&1 || exit 0

# Der Standard-Branch wird ERMITTELT, nicht als `main` angenommen. Drei Server
# im Portfolio (openlex-mcp, swiss-courts-mcp, swisstopo-mcp) heissen ihn
# `master`; ein fest verdrahtetes origin/main scheitert dort mit «couldn't find
# remote ref main». Wer das fuer ein Netzproblem haelt, arbeitet weiter auf
# genau dem veralteten Klon, vor dem dieser Hook warnt — so ist schon einmal
# ein Branch 15 Commits alt geworden.
SYMREF="$(mit_zeitschranke git ls-remote --symref origin HEAD 2>/dev/null)" || SYMREF=""
STANDARD="$(printf '%s\n' "$SYMREF" | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' | head -n1)"

# Aeltere Server kuendigen kein symref an. Dann zaehlt der beim Klonen
# gesetzte lokale Zeiger — schwaecher, weil er bei einer Umbenennung des
# Standard-Branches veraltet, aber immer noch ermittelt statt geraten.
if [ -z "$STANDARD" ]; then
  STANDARD="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)" || STANDARD=""
  STANDARD="${STANDARD#origin/}"
fi
[ -n "$STANDARD" ] || exit 0

mit_zeitschranke git fetch --quiet origin "$STANDARD" >/dev/null 2>&1 || exit 0

RUECKSTAND="$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)" || exit 0
# Nur Ziffern gelten. Alles andere heisst, dass der Vergleich nicht zustande
# kam — und ein nicht zustande gekommener Vergleich ist kein Befund.
case "$RUECKSTAND" in
  '' | *[!0-9]*) exit 0 ;;
esac

# Bei 0 schweigt er. Ohne diese Zeile stuende bei jedem Sessionstart eine
# Meldung da, die nichts verlangt — und eine Meldung, die immer da steht,
# wird nicht mehr gelesen.
[ "$RUECKSTAND" -gt 0 ] || exit 0

if [ "$RUECKSTAND" -eq 1 ]; then
  COMMITS="1 Commit"
else
  COMMITS="$RUECKSTAND Commits"
fi

cat <<MELDUNG
[Klon-Aktualitaet] Der ausgecheckte Stand liegt $COMMITS hinter origin/$STANDARD.

  git merge FETCH_HEAD     # oder: git rebase origin/$STANDARD

Grund: Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff
steht — die fehlenden Commits sind erfahrungsgemaess genau die, die das Gate
einfuehren, an dem der Branch scheitert.
MELDUNG

exit 0
