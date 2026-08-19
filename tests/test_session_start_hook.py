#!/usr/bin/env python3
"""Tests fuer .claude/hooks/klon-aktualitaet.sh — der Hook blockiert nie.

Der Hook meldet beim Sessionstart, wie viele Commits der ausgecheckte Stand
hinter dem Standard-Branch liegt. Sein Nutzen ist eine einzelne Warnung; seine
wichtigste Eigenschaft ist, dass er die Session unter keinen Umstaenden
anhaelt. Ein Hook, der bei Netzproblemen die Arbeit blockiert, wird nach dem
zweiten Mal abgeschaltet und schuetzt danach gar nichts.

«Blockiert nie» ist ohne Test eine Behauptung — und zwar eine, die still
faellt: Ein Hook, der in einem Ausfallfall haengt oder mit != 0 endet, macht
kein Gate rot. Er faellt dem Nutzer beim naechsten Sessionstart auf die
Fuesse, nicht der CI.

Zwei Haelften, und nur beide zusammen greifen:

| Test                  | haelt                                  | faengt                       |
|-----------------------|----------------------------------------|------------------------------|
| `SchweigenTest`       | jeder Ausfallfall endet still mit 0     | ein Hook, der blockiert      |
| `MeldungTest`         | Rueckstand wird gemeldet                | ein Hook, der immer schweigt |

Ohne die zweite Haelfte waere ein Hook, der aus Versehen nie etwas sagt,
ununterscheidbar von einem, der funktioniert — gruen und nutzlos.

Kein Netz: Die Repositories liegen im Temp-Verzeichnis und sprechen ueber
Dateipfad-Remotes miteinander. Ein Test, der rot wird, weil gerade eine
Quelle stoert, wird ignoriert statt gelesen.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_HOOK = _ROOT / ".claude" / "hooks" / "klon-aktualitaet.sh"
_SETTINGS = _ROOT / ".claude" / "settings.json"
# Die ANWEISUNG, nicht ihre Erwaehnung: `trap 'exit 0' EXIT` steht im Hook
# auch im Kommentarkopf. Die erste Fassung dieses Tests ersetzte per
# `str.replace(..., 1)` und traf damit den Kommentar — der `trap` blieb stehen,
# die Variante verhielt sich wie das Original, und der Test haette nie etwas
# widerlegt. Aufgefallen ist das nur, weil die Gegenprobe das erwartete
# Rot nicht lieferte.
_TRAP_ANWEISUNG = re.compile(r"^trap 'exit 0' EXIT$", re.MULTILINE)

# Reproduzierbar unabhaengig von der Umgebung des Ausfuehrenden: weder eine
# globale gitconfig (init.defaultBranch!) noch eine fehlende Identitaet duerfen
# das Ergebnis bestimmen.
_GIT_UMGEBUNG = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
    "GIT_TERMINAL_PROMPT": "0",
    "HOME": "/nonexistent-home-fuer-den-test",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
}


def _git(*args: str, cwd: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        env=dict(_GIT_UMGEBUNG),
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


class HookLauf:
    """Ein Hook-Lauf: Exit-Code und Ausgabe."""

    def __init__(
        self,
        projekt: pathlib.Path,
        timeout_s: str | None = None,
        hook: pathlib.Path | None = None,
    ):
        umgebung = dict(_GIT_UMGEBUNG)
        umgebung["CLAUDE_PROJECT_DIR"] = str(projekt)
        if timeout_s is not None:
            umgebung["CLAUDE_KLON_CHECK_TIMEOUT"] = timeout_s
        # `timeout=` hier ist die Reissleine des Tests, nicht die des Hooks:
        # Haengt der Hook trotz eigener Zeitschranke, soll der Test das als
        # Fehlschlag melden statt selbst haengenzubleiben.
        fertig = subprocess.run(
            ["bash", str(hook or _HOOK)],
            env=umgebung,
            capture_output=True,
            text=True,
            timeout=90,
        )
        self.code = fertig.returncode
        self.ausgabe = fertig.stdout
        self.fehler = fertig.stderr


@unittest.skipUnless(shutil.which("git"), "git nicht verfuegbar")
class HookBasis(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def fernrepo(self, standard_branch: str) -> pathlib.Path:
        """Ein bares Repo, dessen HEAD auf `standard_branch` zeigt.

        Bewusst ueber `symbolic-ref` statt `git init -b`: Der Standard-Branch
        ist der Gegenstand dieses Tests und darf nicht davon abhaengen, was
        die git-Version des Ausfuehrenden als Default waehlt.
        """
        fern = self.tmp / f"fern-{standard_branch}.git"
        _git("init", "--quiet", "--bare", str(fern), cwd=self.tmp)
        _git("symbolic-ref", "HEAD", f"refs/heads/{standard_branch}", cwd=fern)
        return fern

    def befuellen(self, fern: pathlib.Path, branch: str) -> pathlib.Path:
        arbeit = self.tmp / f"arbeit-{branch}"
        _git("clone", "--quiet", str(fern), str(arbeit), cwd=self.tmp)
        _git("checkout", "--quiet", "-b", branch, cwd=arbeit)
        (arbeit / "datei.txt").write_text("start\n", encoding="utf-8")
        _git("add", "-A", cwd=arbeit)
        _git("commit", "--quiet", "-m", "start", cwd=arbeit)
        _git("push", "--quiet", "origin", branch, cwd=arbeit)
        return arbeit

    def vorspulen(self, arbeit: pathlib.Path, branch: str, anzahl: int) -> None:
        for i in range(anzahl):
            (arbeit / "datei.txt").write_text(f"stand {i}\n", encoding="utf-8")
            _git("commit", "--quiet", "-am", f"commit {i}", cwd=arbeit)
        _git("push", "--quiet", "origin", branch, cwd=arbeit)

    def szenario(self, branch: str, rueckstand: int) -> pathlib.Path:
        """Ein Klon, der um `rueckstand` Commits hinter `branch` liegt."""
        fern = self.fernrepo(branch)
        arbeit = self.befuellen(fern, branch)
        klon = self.tmp / f"klon-{branch}-{rueckstand}"
        _git("clone", "--quiet", str(fern), str(klon), cwd=self.tmp)
        if rueckstand:
            self.vorspulen(arbeit, branch, rueckstand)
        return klon


class MeldungTest(HookBasis):
    """Liegt der Klon zurueck, sagt der Hook es — sonst ist er nutzlos."""

    def test_rueckstand_wird_gemeldet(self):
        lauf = HookLauf(self.szenario("main", 3))
        self.assertEqual(lauf.code, 0)
        self.assertIn("3 Commits", lauf.ausgabe)
        self.assertIn("origin/main", lauf.ausgabe)

    def test_standard_branch_master_wird_ermittelt_nicht_angenommen(self):
        """Der Fall, der schon einmal einen Branch 15 Commits alt werden liess.

        Drei Server im Portfolio (openlex-mcp, swiss-courts-mcp, swisstopo-mcp)
        nennen ihren Standard-Branch `master`. Ein Hook, der `main` fest
        verdrahtet, schweigt dort fuer immer — und zwar genau so still wie im
        gewollten Fall «alles aktuell», also ununterscheidbar davon.
        """
        lauf = HookLauf(self.szenario("master", 4))
        self.assertEqual(lauf.code, 0)
        self.assertIn("4 Commits", lauf.ausgabe)
        self.assertIn("origin/master", lauf.ausgabe)
        self.assertNotIn("origin/main", lauf.ausgabe)

    def test_ein_einzelner_commit_im_singular(self):
        lauf = HookLauf(self.szenario("main", 1))
        self.assertIn("1 Commit hinter", lauf.ausgabe)
        self.assertNotIn("1 Commits", lauf.ausgabe)

    def test_meldung_nennt_den_grund(self):
        """Ohne den Grund ist die Meldung eine Aufforderung ohne Begruendung."""
        lauf = HookLauf(self.szenario("main", 2))
        self.assertIn("rote CI", lauf.ausgabe)


class SchweigenTest(HookBasis):
    """Jeder dieser Faelle geht still durch: Exit 0, keine Ausgabe."""

    def pruefe_still(self, projekt: pathlib.Path, timeout_s: str | None = None) -> None:
        lauf = HookLauf(projekt, timeout_s=timeout_s)
        self.assertEqual(lauf.code, 0, f"Exit {lauf.code}, stderr: {lauf.fehler}")
        self.assertEqual(lauf.ausgabe.strip(), "", f"unerwartete Ausgabe: {lauf.ausgabe!r}")

    def test_aktueller_klon_schweigt(self):
        """Bei 0 schweigt er. Eine Meldung, die immer dasteht, wird nicht gelesen."""
        self.pruefe_still(self.szenario("main", 0))

    def test_kein_remote(self):
        projekt = self.tmp / "ohne-remote"
        _git("init", "--quiet", str(projekt), cwd=self.tmp)
        (projekt / "a.txt").write_text("a\n", encoding="utf-8")
        _git("add", "-A", cwd=projekt)
        _git("commit", "--quiet", "-m", "eins", cwd=projekt)
        self.pruefe_still(projekt)

    def test_kein_git_repository(self):
        projekt = self.tmp / "kein-repo"
        projekt.mkdir()
        self.pruefe_still(projekt)

    def test_verzeichnis_existiert_nicht(self):
        self.pruefe_still(self.tmp / "gibt-es-nicht")

    def test_repo_ohne_commit(self):
        projekt = self.tmp / "leer"
        _git("init", "--quiet", str(projekt), cwd=self.tmp)
        self.pruefe_still(projekt)

    def test_detached_head(self):
        """Ein ausgechecktes Tag oder `git bisect` liegt naturgemaess zurueck.

        Dort waere die Meldung kein Befund, sondern Rauschen.
        """
        klon = self.szenario("main", 3)
        _git("checkout", "--quiet", "--detach", "HEAD", cwd=klon)
        self.pruefe_still(klon)

    def test_remote_existiert_nicht(self):
        klon = self.szenario("main", 3)
        _git("remote", "set-url", "origin", str(self.tmp / "weg.git"), cwd=klon)
        self.pruefe_still(klon)

    def test_unerreichbarer_remote_haelt_die_zeitschranke_ein(self):
        """Flatterndes DNS: unerreichbar, aber nicht sofort abweisend.

        Ein nicht existierender Pfad scheitert augenblicklich und beweist die
        Zeitschranke deshalb nicht. Eine nicht routbare Adresse laesst git
        warten — genau der Fall, in dem ein Hook ohne Schranke den
        Sessionstart anhaelt.
        """
        klon = self.szenario("main", 3)
        _git("remote", "set-url", "origin", "git://10.255.255.1/x.git", cwd=klon)
        self.pruefe_still(klon, timeout_s="2")

    def test_unsinnige_zeitschranke_laeuft_nicht_unbegrenzt(self):
        """Eine kaputt gesetzte Variable darf kein unbegrenztes Warten bedeuten."""
        klon = self.szenario("main", 3)
        _git("remote", "set-url", "origin", "git://10.255.255.1/x.git", cwd=klon)
        self.pruefe_still(klon, timeout_s="abc")


class ExitNullGarantieTest(HookBasis):
    """`trap 'exit 0' EXIT` ist die letzte Absicherung — und sie traegt wirklich.

    Beim Gegenproben fiel auf, dass ein blosses Entfernen des `trap` keinen
    einzigen Test rot macht: Jeder Schritt hat zusaetzlich sein eigenes
    `|| exit 0`, und diese Wachen greifen vorher. Der `trap` sah damit aus wie
    eine Zusicherung, war aber eine Behauptung — genau die Sorte, die beim
    naechsten Edit still faellt, weil kein Gate sie haelt.

    Dieser Test macht sie widerlegbar. Er leitet aus dem echten Hook eine
    Variante ab, deren letzte Anweisung scheitert — ein unvorhergesehener
    Fehlerpfad, wie ihn ein spaeterer Edit einbauen kann — und laesst sie
    einen Lauf fahren, der bis ans Ende kommt (also einen mit Rueckstand, wo
    keine der Wachen vorher zieht).

    Nachgemessen: mit `trap` endet die Variante mit 0, ohne ihn mit 1.
    Loescht jemand den `trap` aus dem Hook, faellt dieser Test.
    """

    def _variante(self, name: str, mit_trap: bool) -> pathlib.Path:
        quelle = _HOOK.read_text(encoding="utf-8")
        abgeleitet = re.sub(r"\nexit 0\n\Z", "\nfalse\n", quelle)
        self.assertNotEqual(abgeleitet, quelle, "Hook endet nicht mehr auf `exit 0` — Test angleichen")
        if not mit_trap:
            abgeleitet, ersetzt = _TRAP_ANWEISUNG.subn("true", abgeleitet)
            self.assertEqual(ersetzt, 1, "genau eine trap-Anweisung erwartet")
        pfad = self.tmp / name
        pfad.write_text(abgeleitet, encoding="utf-8")
        return pfad

    def test_trap_faengt_einen_unvorhergesehenen_fehlerpfad(self):
        klon = self.szenario("main", 2)
        mit = HookLauf(klon, hook=self._variante("mit-trap.sh", mit_trap=True))
        self.assertEqual(mit.code, 0)

    def test_ohne_trap_kaeme_der_fehlerpfad_durch(self):
        """Die Gegenprobe zur vorigen Zusicherung, als Test statt als Notiz.

        Faellt sie, faengt der Fehlerpfad schon woanders — dann prueft der
        Test darueber nichts mehr und beide gehoeren nachgezogen.
        """
        klon = self.szenario("main", 2)
        ohne = HookLauf(klon, hook=self._variante("ohne-trap.sh", mit_trap=False))
        self.assertNotEqual(ohne.code, 0)


class RegistrierungTest(unittest.TestCase):
    """Ein Hook, den settings.json nicht aufruft, laeuft nie."""

    def test_hook_ist_ausfuehrbar(self):
        self.assertTrue(_HOOK.exists(), f"{_HOOK} fehlt")
        self.assertTrue(_HOOK.stat().st_mode & 0o111, "Hook ist nicht ausfuehrbar")

    def test_settings_registriert_genau_diesen_hook(self):
        daten = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        eintraege = daten["hooks"]["SessionStart"]
        befehle = [h["command"] for gruppe in eintraege for h in gruppe["hooks"]]
        self.assertIn("$CLAUDE_PROJECT_DIR/.claude/hooks/klon-aktualitaet.sh", befehle)

    def test_settings_ist_striktes_json(self):
        """Kommentare wuerden den Hook still abschalten, statt zu meckern."""
        json.loads(_SETTINGS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
