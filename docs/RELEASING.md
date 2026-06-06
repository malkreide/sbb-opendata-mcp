# Releasing & Publishing to PyPI

`sbb-opendata-mcp` is published to [PyPI](https://pypi.org/project/sbb-opendata-mcp/)
automatically by the [`publish.yml`](../.github/workflows/publish.yml) workflow
whenever a GitHub Release is published. Publishing uses
[PyPI Trusted Publishing (OIDC)](https://docs.pypi.org/trusted-publishers/), so
**no API token or secret is stored in the repository**.

## One-time setup on PyPI

This only has to be done once (and again for TestPyPI if you want a staging
target).

1. Sign in at <https://pypi.org> (the maintainer account).
2. Go to **Account → Publishing → Add a new pending publisher**
   (or, if the project already exists, open the project → **Settings → Publishing**).
3. Register a **GitHub Actions** trusted publisher with these values:

   | Field            | Value                |
   |------------------|----------------------|
   | PyPI Project Name| `sbb-opendata-mcp`   |
   | Owner            | `malkreide`          |
   | Repository name  | `sbb-opendata-mcp`   |
   | Workflow name    | `publish.yml`        |
   | Environment name | `pypi`               |

4. (Recommended) In the GitHub repo, create an **Environment** named `pypi`
   under **Settings → Environments**. You can add required reviewers there so a
   human approves every publish.

That's it — the first release will create the project on PyPI automatically
(pending publisher), and subsequent releases will publish new versions.

## Cutting a release

1. Bump the version in **two** places (they must match):
   - `pyproject.toml` → `[project].version`
   - `src/sbb_opendata_mcp/__init__.py` → `__version__`
2. Update `CHANGELOG.md`.
3. Commit and merge to `main`.
4. Tag and push, then create a GitHub Release for that tag:

   ```bash
   git tag v0.3.0
   git push origin v0.3.0
   ```

   Then publish a Release from the tag in the GitHub UI (or with `gh release create v0.3.0 --generate-notes`).
5. The `Publish to PyPI` workflow runs automatically: it builds the sdist +
   wheel, validates metadata with `twine check`, and uploads to PyPI via OIDC.

## Building locally (sanity check)

```bash
python -m pip install --upgrade build twine
python -m build          # creates dist/*.whl and dist/*.tar.gz
python -m twine check dist/*
```

> Note: `twine check` requires `packaging>=24.2` to validate the modern
> (Metadata 2.4 / PEP 639) license fields this project uses. Older system
> `packaging` will report a false `license-expression` error — use a fresh
> virtualenv if you hit that.

## Manual publish (fallback)

If you ever need to publish without the workflow, you can use a
[PyPI API token](https://pypi.org/help/#apitoken):

```bash
python -m build
python -m twine upload dist/*   # username: __token__, password: <your-token>
```
