---
name: bump-version
description: Release a new cuttlefish version from the CHANGELOG's Unreleased section.
argument-hint: "[X.Y.Z]"
disable-model-invocation: true
---

# Bump version

Release the work collected under `## [Unreleased]` in `CHANGELOG.md` as a new version. The target version is `$ARGUMENTS` (no leading `v`).

## 1. Pre-flight

Stop and tell the user rather than continuing if any of these fail:

- `git status --short` is empty (a release commit must contain only the bump).
- The `## [Unreleased]` section in `CHANGELOG.md` has at least one entry.
- `uv run python -m pytest -q` passes.

## 2. Pick the version

- If `$ARGUMENTS` names a version, use it. It must be greater than the current `version` in `pyproject.toml`, and `git tag -l vX.Y.Z` must be empty.
- If no version was given, propose the next **patch** (`0.1.11` → `0.1.12`). The project is pre-1.0 and has released features as patch bumps so far. Confirm with the user before going on.

## 3. Update CHANGELOG.md

Follow the existing Keep a Changelog layout exactly:

- Rename the heading `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`, using today's date. Don't add a new empty Unreleased section.
- In the link references at the bottom of the file, add a line for the new version above the previous newest one, then remove any `[Unreleased]: …` line:

  ```
  [X.Y.Z]: https://github.com/acaibowlz/cuttlefish/compare/vPREV...vX.Y.Z
  ```

  `PREV` is the version that was in `pyproject.toml` before the bump.

## 4. Update the version and lockfile

- Set `version = "X.Y.Z"` in the `[project]` table of `pyproject.toml`. That's the only place the version lives, because `cuttlefish.__version__` reads it from the package metadata.
- Run `uv sync`. It updates the `cuttlefish-ssg` entry in `uv.lock`.
- Check that `uv run ctf --version` prints `ctf X.Y.Z`.

## 5. Commit and tag

The commit must contain only `CHANGELOG.md`, `pyproject.toml` and `uv.lock`:

```bash
git add CHANGELOG.md pyproject.toml uv.lock
git commit -m "chore: bump version to vX.Y.Z" -m "Co-Authored-By: <attribution line from the system reminder>"
git tag -a vX.Y.Z -m vX.Y.Z
```

Tags are annotated, with the tag name as the message, to match the earlier `v0.1.x` tags.

## 6. Push

Push without asking; running this skill is the go-ahead.

- `git fetch origin` and check that `main` is not behind `origin/main` (`git rev-list --count main..origin/main` is `0`). If it is behind, stop and tell the user. Don't rebase a tagged release commit.
- Push the branch first, then the tag, so the tag never points at a commit the remote doesn't have:

  ```bash
  git push origin main
  git push origin vX.Y.Z
  ```

- Check that `git ls-remote --tags origin vX.Y.Z` lists the tag.

## 7. Publish

Run `bash scripts/release.sh` from the repo root. It clears `dist/`, builds with `uv build`, and publishes to PyPI with the `PYPI_TOKEN` from `.env`. If it fails, stop and show the output. Don't retry: PyPI never accepts the same version twice, so a partial upload needs a look before anything else.

## 8. Report

Show `git log --oneline -1`, the pushed tag, and the PyPI URL: `https://pypi.org/project/cuttlefish-ssg/X.Y.Z/`.
