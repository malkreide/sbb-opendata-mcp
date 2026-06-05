# Contributing

[🇩🇪 Deutsche Version](CONTRIBUTING.de.md)

Thank you for your interest in this project! Contributions are welcome.

## How can I contribute?

**Report bugs:** Create an [Issue](../../issues) with a clear description, reproduction steps, and expected vs. actual output.

**Suggest features:** Describe the use case, ideally with a reference to Swiss rail / open-data context (passenger frequency, construction projects, accessibility, station comparisons, etc.).

**Contribute code:**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Write tests for your changes
5. Run linter: `ruff check src/ tests/`
6. Commit with clear message: `git commit -m "feat: add elevator availability tool"`
7. Create a Pull Request

## Code Standards

- Python 3.11+, Ruff for linting
- Docstrings in English (for international compatibility)
- Comments and error messages may be in German or English
- All MCP tools must set `readOnlyHint: True` (read-only access)
- Pydantic models for all tool inputs
- Any value flowing into an ODSQL `where` clause must be validated (regex) or escaped via `_odsql_quote()`

## Testing

No API key is required — all data comes from the public [data.sbb.ch](https://data.sbb.ch) portal.

```bash
# Unit tests (no network required)
PYTHONPATH=src pytest tests/ -m "not live"

# Live API smoke tests (require network access to data.sbb.ch)
PYTHONPATH=src pytest tests/ -m live
```

## License

MIT – see [LICENSE](LICENSE)
