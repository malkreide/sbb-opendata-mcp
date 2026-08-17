#!/usr/bin/env python3
"""Prüft, dass das aufgerufene ruff die in pyproject.toml gepinnte Version ist.

Der Sinn eines lokalen Gates ist, dass es dasselbe Ergebnis liefert wie die CI.
Eine andere ruff-Version meldet Abweichungen, die niemand verursacht hat — und
verschweigt umgekehrt welche, die die CI dann rot machen. Beides kostet mehr
Zeit als es spart.

Die pre-commit-Hooks rufen ruff über ``language: system`` auf, also das, was im
PATH liegt. Das ist Absicht: so gibt es genau EINEN Pin, nämlich den in
pyproject.toml, und keine zweite Versionsangabe in .pre-commit-config.yaml, die
still auseinanderlaufen kann. Der Preis dafür ist, dass der PATH auch ein
fremdes ruff liefern kann — dieses Skript ist der Ausgleich.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


def pinned_version() -> str:
    """Liest ``ruff==X.Y.Z`` aus den dev-Extras. Einzige Quelle der Wahrheit."""
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev = data["project"]["optional-dependencies"]["dev"]
    for entry in dev:
        match = re.fullmatch(r"ruff==([0-9][^\s;]*)", entry.strip())
        if match:
            return match.group(1)
    raise SystemExit(
        "Kein exakter ruff-Pin (ruff==X.Y.Z) in [project.optional-dependencies].dev "
        f"von {PYPROJECT.name}. Ohne exakten Pin kann kein lokales Gate die CI "
        "reproduzieren — bitte den Pin wiederherstellen."
    )


def installed_version() -> str:
    if shutil.which("ruff") is None:
        raise SystemExit('ruff ist nicht im PATH. Dev-Umgebung installieren:\n    pip install -e ".[dev]"')
    out = subprocess.run(["ruff", "--version"], capture_output=True, text=True, check=True).stdout
    match = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", out)
    if not match:
        raise SystemExit(f"Version aus 'ruff --version' nicht lesbar: {out!r}")
    return match.group(1)


def main() -> int:
    want, have = pinned_version(), installed_version()
    if want != have:
        print(
            f"ruff-Version weicht ab: installiert {have}, gepinnt {want}.\n"
            "Die Gates würden lokal anders ausfallen als in der CI. Angleichen mit:\n"
            f'    pip install -e ".[dev]"   # oder: pip install "ruff=={want}"',
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
