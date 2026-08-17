"""Die ruff-Version steht an genau einer Stelle — und bleibt dort.

Sie stand an dreien: `ruff==0.16.1` im `[dev]`-Extra, noch einmal in
`[tool.hatch.envs.default] dependencies`, und ein drittes Mal als
`rev: v0.16.1` in `.pre-commit-config.yaml`. Alle drei nannten dieselbe
Version — aber nichts erzwang das.

Jeder Rueckfall ist still: Er macht kein Gate rot, er laesst es lediglich mit
einer anderen Version laufen als der, gegen die anderswo geprueft wird. Wer
den Pin oben anhebt und eine der anderen Stellen vergisst, faehrt
`hatch run lint` oder `pre-commit` gegen eine Version, die die CI nicht
kennt — und merkt es erst, wenn die CI Befunde meldet, die lokal nicht
auftauchten.

Vier Zusicherungen, in aufsteigender Reichweite:

1. Das `dev`-Extra pinnt exakt, genau einmal.
2. Kein Workflow installiert ruff selbst und ueberstimmt den Pin damit.
3. Die hatch-Umgebung zaehlt ihre Abhaengigkeiten nicht eigenstaendig auf,
   sondern zieht das Extra ueber `features`.
4. `.pre-commit-config.yaml` bringt keine eigene Versionsangabe mit.
"""

from __future__ import annotations

import pathlib
import re
import tomllib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"

# Formen, in denen ein Schritt ein Paket eigenstaendig installiert. Die erste
# Fassung dieses Tests kannte nur `pip install ruff` und liess damit
# `pip install --upgrade ruff==…`, `pip install "ruff==…"`, `uv tool install`
# und `uv run --with ruff==…` durch — allesamt Formen, die den Pin genauso
# ueberstimmen. Aufgefallen ist das in einem Codex-Review, nicht hier.
_INSTALL_FORM = re.compile(
    r"(?:pip3?\s+install|python\s+-m\s+pip\s+install|uv\s+pip\s+install"
    r"|uv\s+tool\s+install|uv\s+add|pipx\s+install|--with)\b"
)
# ruff als eigenes Paket-Argument. Anfuehrungszeichen sind erlaubt, ein
# vorangehendes Wort-, Pfad- oder Bindestrich-Zeichen nicht: sonst zaehlten
# `ruff-lsp` und `scripts/ruff_helper.py` mit.
_RUFF_PAKET = re.compile(r"""(?<![\w./-])["']?ruff(?![\w-])""")


def _installiert_ruff(zeile: str) -> bool:
    """Installiert diese Zeile ruff als benanntes Paket?

    `pip install -e ".[dev]"` zieht ruff ebenfalls herein — das ist aber der
    richtige Weg und darf nicht anschlagen. Entscheidend ist deshalb, ob nach
    dem Install-Befehl ein eigenes Argument `ruff` steht.
    """
    treffer = _INSTALL_FORM.search(zeile)
    return bool(treffer) and bool(_RUFF_PAKET.search(zeile[treffer.end() :]))


def _workflow_dateien() -> list[pathlib.Path]:
    """Beide Endungen: GitHub laedt `*.yml` UND `*.yaml`."""
    return sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")])


def _dev_abhaengigkeiten() -> list[str]:
    daten = tomllib.loads((_ROOT / "pyproject.toml").read_text())
    return daten["project"]["optional-dependencies"]["dev"]


def test_ruff_ist_exakt_gepinnt() -> None:
    """Eine Spanne laesst lokalen Lauf und CI verschiedene Versionen fahren."""
    specs = [s for s in _dev_abhaengigkeiten() if re.match(r"^ruff\b", s)]
    assert len(specs) == 1, f"genau ein ruff-Specifier erwartet, gefunden: {specs}"
    assert re.fullmatch(r"ruff==\d+\.\d+\.\d+", specs[0]), (
        f"ruff muss als ruff==X.Y.Z gepinnt sein, gefunden {specs[0]!r}."
    )


def test_der_pin_ist_die_einzige_versionsquelle() -> None:
    """Kein Workflow darf ruff selbst installieren."""
    for workflow in _workflow_dateien():
        # Kommentarzeilen raus, damit ein erklaerender Hinweis auf den
        # verbotenen Befehl den Test nicht selbst ausloest.
        zeilen = [z for z in workflow.read_text().splitlines() if not z.lstrip().startswith("#")]
        treffer = [z.strip() for z in zeilen if _installiert_ruff(z)]
        assert not treffer, (
            f"{workflow.name} installiert ruff direkt ({treffer}). Dieser Schritt "
            "laeuft nach dem dev-Install und ueberstimmt den Pin in pyproject."
        )


def test_der_erkenner_kennt_die_gaengigen_installationsformen() -> None:
    """Der Scan oben ist nur so gut wie das, was er als Install erkennt.

    Ohne diese Tabelle ist `test_der_pin_ist_die_einzige_versionsquelle` gruen,
    weil es die Form nicht kennt — nicht, weil sie fehlt. Genau so war es: Die
    erste Fassung suchte woertlich nach `pip install ruff` und uebersah jede
    andere Schreibweise.
    """
    muss_treffen = [
        "run: pip install ruff==0.16.1",
        "run: pip install --upgrade ruff==0.16.1",
        'run: pip install "ruff==0.16.1"',
        "run: pip install 'ruff==0.16.1'",
        "run: pip3 install ruff==0.16.1",
        "run: python -m pip install ruff==0.16.1",
        "run: uv pip install ruff==0.16.1 --system",
        "run: uv tool install ruff==0.16.1",
        "run: uv add ruff==0.16.1",
        "run: pipx install ruff==0.16.1",
        "run: uv run --with ruff==0.16.1 ruff check src/",
        "run: pip install ruff",
        "run: pip install pytest ruff==0.16.1",
        "run: pip install ruff[extra]==0.16.1",
    ]
    darf_nicht_treffen = [
        'run: pip install -e ".[dev]"',
        'run: uv pip install -e ".[dev]" --system',
        "run: ruff check src/ tests/ scripts/",
        "run: ruff format --check src/ tests/",
        "run: pip install ruff-lsp",
        "run: pip install uv",
        "run: python -m pip install --upgrade pip",
        "run: pip install build hatchling",
        "run: uv run --with pip-audit pip-audit",
        "run: python scripts/ruff_helper.py",
        "run: pip install -r requirements.txt",
        "name: Lint mit ruff",
    ]
    uebersehen = [z for z in muss_treffen if not _installiert_ruff(z)]
    assert not uebersehen, f"Erkenner uebersieht: {uebersehen}"
    fehlalarm = [z for z in darf_nicht_treffen if _installiert_ruff(z)]
    assert not fehlalarm, f"Erkenner schlaegt faelschlich an: {fehlalarm}"


def test_der_workflow_scan_findet_ueberhaupt_etwas() -> None:
    """Sichert die Pruefung oben gegen ein leeres Verzeichnis ab."""
    workflows = _workflow_dateien()
    assert len(workflows) >= 2, f"Workflow-Scan findet fast nichts: {workflows}"
    assert any("ruff check" in w.read_text() for w in workflows), (
        "kein Workflow ruft ruff auf — der Scan sucht am falschen Ort"
    )


def test_hatch_umgebung_zaehlt_nicht_selbst_auf() -> None:
    """`[tool.hatch.envs.default]` muss das Extra ziehen, nicht kopieren.

    Vorher standen dort dieselben drei Pakete noch einmal, ruff-Pin
    inklusive. Zwei Listen, die uebereinstimmen sollen, ohne dass es etwas
    erzwingt — `hatch run lint` lief dann gegen eine andere Version als die
    CI, ohne dass ein Gate rot wurde.
    """
    daten = tomllib.loads((_ROOT / "pyproject.toml").read_text())
    env = daten.get("tool", {}).get("hatch", {}).get("envs", {}).get("default", {})
    eigene = env.get("dependencies", [])
    assert not eigene, (
        "[tool.hatch.envs.default] zaehlt eigene dependencies auf "
        f'({eigene}). Das dev-Extra stattdessen ueber features = ["dev"] ziehen.'
    )
    assert "dev" in env.get("features", []), (
        '[tool.hatch.envs.default] muss features = ["dev"] setzen, sonst fehlt der hatch-Umgebung ruff ganz.'
    )


def test_pre_commit_bringt_keine_zweite_version_mit() -> None:
    """Ein `rev:` fuer ruff waere ein zweiter Pin.

    `.pre-commit-config.yaml` kann `pyproject.toml` nicht lesen. Wer ruff
    ueber `ruff-pre-commit` einbindet, braucht dort zwangslaeufig ein `rev:`
    — also eine zweite Versionsangabe. Deshalb `repo: local` mit
    `language: system`: der Hook nimmt das ruff aus dem PATH, und
    `scripts/check_ruff_pin.py` prueft, dass das der Pin ist.

    Geprueft wird auf Textebene statt ueber einen YAML-Parser: `pyyaml` ist
    keine Abhaengigkeit dieses Repos, und ein Test, der nur mit einem
    zusaetzlichen Paket laeuft, ist einer, der in der CI stillschweigend
    uebersprungen werden koennte.
    """
    pfad = _ROOT / ".pre-commit-config.yaml"
    assert pfad.is_file(), "keine .pre-commit-config.yaml — dieser Test sucht am falschen Ort"

    zeilen = [z for z in pfad.read_text().splitlines() if not z.lstrip().startswith("#")]
    text = "\n".join(zeilen)

    fremd = [z.strip() for z in zeilen if re.search(r"repo:\s*http", z)]
    assert not fremd, (
        f"pre-commit bindet einen fremden repo ein ({fremd}). Der braucht ein "
        "`rev:` und damit eine zweite Versionsangabe."
    )
    revs = [z.strip() for z in zeilen if re.match(r"\s*rev:", z)]
    assert not revs, f"`rev:` in .pre-commit-config.yaml ist ein zweiter Pin: {revs}"
    versionen = re.findall(r"\bv?\d+\.\d+\.\d+\b", text)
    assert not versionen, (
        f"Versionsnummer in .pre-commit-config.yaml gefunden: {versionen}. "
        "Die Version gehoert ausschliesslich in den dev-Extra von pyproject.toml."
    )
    assert "scripts/check_ruff_pin.py" in text, (
        "Ohne den Pin-Guard nimmt `language: system` irgendein ruff aus dem "
        "PATH — genau die Luecke, die der eine Pin schliessen soll."
    )
