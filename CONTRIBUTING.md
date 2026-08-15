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

## The live suite: when it runs, and who sees a red result

**Cadence:** daily 05:15 UTC, plus on demand via *Actions → Live-Tests → Run
workflow*. See [`.github/workflows/live.yml`](.github/workflows/live.yml).

**Who sees it:** a red run opens an issue titled `Live-Tests gegen data.sbb.ch rot …` with the
`upstream` label, and comments on the existing one instead of opening a second.
A run that goes green again closes it.

**Three answers, not two.** `scripts/classify_live_run.py` reads the JUnit XML rather than
the exit code and separates `clear` (ran, green), `finding` (ran, something
fell) and `unknown` (did not run — install failed, nothing collected,
everything skipped). An `unknown` never closes an issue: closing would claim a
comparison that never happened.

**A red live run does not necessarily mean *our* bug.** It means the contract
with the source has changed, or the source is down. Both belong seen; only the
first belongs fixed. Please read the run before disabling the job — that is how
this check dies, and it is the only one in the repository that can contradict a
wrong assumption about data.sbb.ch. Every other test asserts against a fixture, and
the fixture was written from the same assumption as the code.

## License

MIT – see [LICENSE](LICENSE)
