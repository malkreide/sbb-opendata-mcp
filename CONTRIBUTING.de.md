# Beitragen

[🇬🇧 English Version](CONTRIBUTING.md)

Vielen Dank für Ihr Interesse an diesem Projekt! Beiträge sind willkommen.

## Wie kann ich beitragen?

**Fehler melden:** Erstellen Sie ein [Issue](../../issues) mit einer klaren Beschreibung des Problems, Schritten zur Reproduktion und der erwarteten vs. tatsächlichen Ausgabe.

**Feature vorschlagen:** Beschreiben Sie den Use Case, idealerweise mit einem Bezug zum Schweizer Bahn-/Open-Data-Kontext (Passagierfrequenz, Bauprojekte, Barrierefreiheit, Bahnhofvergleiche etc.).

**Code beitragen:**

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feature/mein-feature`
3. Installieren Sie die Dev-Abhängigkeiten: `pip install -e ".[dev]"`
4. Schreiben Sie Tests für Ihre Änderungen
5. Lint prüfen: `ruff check src/ tests/`
6. Commit mit aussagekräftiger Nachricht: `git commit -m "feat: Aufzugsverfügbarkeit ergänzen"`
7. Pull Request erstellen

## Code-Standards

- Python 3.11+, Ruff für Linting
- Docstrings auf Englisch (für internationale Kompatibilität)
- Kommentare und Fehlermeldungen dürfen Deutsch oder Englisch sein
- Alle MCP-Tools müssen `readOnlyHint: True` setzen (nur lesender Zugriff)
- Pydantic-Modelle für alle Tool-Inputs
- Jeder Wert, der in eine ODSQL-`where`-Klausel fliesst, muss validiert (Regex) oder über `_odsql_quote()` escaped werden

## Tests

Es ist **kein API-Key erforderlich** – alle Daten stammen vom öffentlichen Portal [data.sbb.ch](https://data.sbb.ch).

```bash
# Unit-Tests (ohne Netzwerk)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-API-Smoke-Tests (benötigen Netzwerkzugriff auf data.sbb.ch)
PYTHONPATH=src pytest tests/ -m live
```

## Lizenz

MIT – siehe [LICENSE](LICENSE)
