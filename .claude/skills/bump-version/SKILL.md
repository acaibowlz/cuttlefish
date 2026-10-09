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

## 6. Report

Show `git log --oneline -1` and `git tag -l vX.Y.Z`. **Don't push.** Tell the user the command they can run when ready: `git push && git push origin vX.Y.Z`.
