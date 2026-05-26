# UV Hatch Maturin Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the repository to a UV workspace, build pure Python packages with Hatchling, build the Rust/PyO3 client with Maturin, and keep Git subdirectory installs buildable.

**Architecture:** The repository root becomes a non-package UV workspace that coordinates the three existing package directories. `s3torchconnector` keeps its published dependency on `s3torchconnectorclient == 1.5.0`, while UV workspace sources resolve that dependency locally during development. Package subdirectories become self-contained PEP 517 projects so `uv pip install git+...#subdirectory=...` can build them directly.

**Tech Stack:** UV, Hatchling, Maturin, PyO3, Cargo, cibuildwheel, GitHub Actions.

---

## File Structure

- Create `pyproject.toml`: root UV workspace coordinator with `tool.uv.package = false`.
- Modify `s3torchconnector/pyproject.toml`: switch from setuptools to Hatchling and add workspace source mapping for `s3torchconnectorclient`.
- Modify `s3torchbenchmarking/pyproject.toml`: switch from setuptools to Hatchling and include configuration files in wheels.
- Modify `s3torchconnectorclient/pyproject.toml`: switch from setuptools-rust to Maturin while preserving existing cibuildwheel configuration.
- Create `s3torchconnector/README.md`: package-local readme for direct subdirectory builds.
- Create `s3torchconnectorclient/README.md`: package-local readme for direct subdirectory builds.
- Modify `DEVELOPMENT.md`: replace pip/venv workflow with UV commands.
- Modify `README.md`: document UV Git install commands for both package subdirectories.
- Modify `.github/workflows/wheels.yml`: use `uv build` for source distributions.
- Optionally modify Python CI workflows only where package install commands must change for the new backends.

---

### Task 1: Add the Root UV Workspace

**Files:**
- Create: `pyproject.toml`

- [ ] **Step 1: Create the workspace root**

Add this file:

```toml
[project]
name = "s3-connector-for-pytorch-workspace"
version = "0.0.0"
requires-python = ">=3.8,<3.15"

[tool.uv]
package = false

[tool.uv.workspace]
members = [
    "s3torchconnectorclient",
    "s3torchconnector",
    "s3torchbenchmarking",
]
```

- [ ] **Step 2: Verify UV recognizes the workspace**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv lock
```

Expected: `uv.lock` is created or updated, and all three workspace members are discovered.

---

### Task 2: Move Pure Python Packages to Hatchling

**Files:**
- Modify: `s3torchconnector/pyproject.toml`
- Modify: `s3torchbenchmarking/pyproject.toml`
- Create: `s3torchconnector/README.md`

- [ ] **Step 1: Update `s3torchconnector` build backend and metadata**

Replace the build-system section with:

```toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"
```

Ensure `[project]` has a package-local readme and SPDX license expression:

```toml
readme = "README.md"
license = "BSD-3-Clause"
```

Keep the existing runtime dependency:

```toml
dependencies = [
    "torch >= 2.0.1, != 2.5.0",
    "s3torchconnectorclient == 1.5.0",
]
```

Add UV workspace source resolution:

```toml
[tool.uv.sources]
s3torchconnectorclient = { workspace = true }
```

Replace setuptools package configuration with:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/s3torchconnector"]

[tool.hatch.build.targets.sdist]
include = [
    "/README.md",
    "/src",
    "/pyproject.toml",
    "/MANIFEST.in",
]
```

- [ ] **Step 2: Add `s3torchconnector/README.md`**

Create:

```markdown
# s3torchconnector

S3 connector integration for PyTorch.

For complete documentation, see the repository README.
```

- [ ] **Step 3: Update `s3torchbenchmarking` build backend**

Replace the build-system section with:

```toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"
```

Ensure `[project]` includes:

```toml
license = "BSD-3-Clause"
```

Add Hatchling configuration:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/s3torchbenchmarking"]

[tool.hatch.build.targets.wheel.force-include]
"conf" = "s3torchbenchmarking/conf"

[tool.hatch.build.targets.sdist]
include = [
    "/README.md",
    "/conf",
    "/src",
    "/tst",
    "/pyproject.toml",
]
```

- [ ] **Step 4: Build the pure Python package sdists and wheels**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv build ./s3torchconnector --out-dir /tmp/s3tc-build-check/s3torchconnector
UV_CACHE_DIR=/tmp/uv-cache uv build ./s3torchbenchmarking --out-dir /tmp/s3tc-build-check/s3torchbenchmarking
```

Expected: both packages build without setuptools warnings or missing README warnings.

---

### Task 3: Move the Native Client to Maturin

**Files:**
- Modify: `s3torchconnectorclient/pyproject.toml`
- Create: `s3torchconnectorclient/README.md`

- [ ] **Step 1: Update `s3torchconnectorclient` build backend**

Replace the build-system section with:

```toml
[build-system]
requires = ["maturin>=1.9,<2"]
build-backend = "maturin"
```

Ensure `[project]` has:

```toml
readme = "README.md"
license = "BSD-3-Clause"
```

Remove:

```toml
[tool.setuptools.packages]
find = { where = ["python/src"] }

[[tool.setuptools-rust.ext-modules]]
target = "s3torchconnectorclient._mountpoint_s3_client"

[tool.setuptools]
license-files = [ "LICENSE", "THIRD-PARTY-LICENSES", "NOTICE"]
```

Add:

```toml
[tool.maturin]
bindings = "pyo3"
python-source = "python/src"
module-name = "s3torchconnectorclient._mountpoint_s3_client"
```

Keep the existing `[tool.cibuildwheel]` sections unless validation shows a cibuildwheel incompatibility.

- [ ] **Step 2: Add `s3torchconnectorclient/README.md`**

Create:

```markdown
# s3torchconnectorclient

Internal Rust/PyO3 S3 client implementation for s3torchconnector.

For complete documentation, see the repository README.
```

- [ ] **Step 3: Build the Maturin package**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv build ./s3torchconnectorclient --out-dir /tmp/s3tc-build-check/s3torchconnectorclient
```

Expected: Maturin builds an sdist and a platform wheel containing:

```text
s3torchconnectorclient/__init__.py
s3torchconnectorclient/_logger_patch.py
s3torchconnectorclient/_mountpoint_s3_client.pyi
s3torchconnectorclient/py.typed
s3torchconnectorclient/_mountpoint_s3_client.*
```

- [ ] **Step 4: Import-smoke the built wheel**

Install the built wheel into a temporary UV environment and run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --isolated --with /tmp/s3tc-build-check/s3torchconnectorclient/*.whl python -c "import s3torchconnectorclient; import s3torchconnectorclient._mountpoint_s3_client as m; print(s3torchconnectorclient.__version__); print(m.__name__)"
```

Expected: command exits successfully and prints the package version and `s3torchconnectorclient._mountpoint_s3_client`.

---

### Task 4: Update Docs and CI Commands

**Files:**
- Modify: `DEVELOPMENT.md`
- Modify: `README.md`
- Modify: `.github/workflows/wheels.yml`

- [ ] **Step 1: Update development setup docs**

Replace the editable pip install instructions in `DEVELOPMENT.md` with:

```bash
uv sync --all-packages
```

Add package-specific examples:

```bash
uv run --package s3torchconnectorclient pytest s3torchconnectorclient/python/tst/unit
uv run --package s3torchconnector pytest s3torchconnector/tst/unit
uv build ./s3torchconnectorclient
uv build ./s3torchconnector
uv build ./s3torchbenchmarking
```

Keep the Rust, clang, and cmake prerequisite notes.

- [ ] **Step 2: Add UV Git install docs to `README.md`**

Add a section near installation:

````markdown
### Install from Git with UV

When installing from this repository, install both package subdirectories from
the same tag or commit:

```bash
uv pip install \
  "s3torchconnectorclient @ git+https://github.com/awslabs/s3-connector-for-pytorch.git@<ref>#subdirectory=s3torchconnectorclient" \
  "s3torchconnector[dcp,lightning] @ git+https://github.com/awslabs/s3-connector-for-pytorch.git@<ref>#subdirectory=s3torchconnector"
```

Use a tag or commit SHA for `<ref>`. Installing from Git builds
`s3torchconnectorclient` from source, so Rust, clang, and cmake must be
available.
````

- [ ] **Step 3: Update source distribution build workflow**

In `.github/workflows/wheels.yml`, replace:

```bash
python -m pip install build
python -m build --sdist
```

with:

```bash
python -m pip install uv
uv build --sdist
```

Keep the existing license-copy step unless local `uv build` validation proves it is unnecessary for release artifacts.

---

### Task 5: Validate Workspace, Git-Install Shape, and Existing Tests

**Files:**
- Generated: `uv.lock`

- [ ] **Step 1: Lock the workspace**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv lock
```

Expected: lock succeeds and writes `uv.lock`.

- [ ] **Step 2: Sync the workspace enough to install editable members**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --all-packages
```

Expected: workspace sync succeeds. If external dependency resolution is too large or unavailable, record the exact failure and continue with direct package build validation.

- [ ] **Step 3: Validate Git-install equivalent local builds**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system --dry-run "s3torchconnectorclient @ ./s3torchconnectorclient"
UV_CACHE_DIR=/tmp/uv-cache uv pip install --system --dry-run "s3torchconnector @ ./s3torchconnector"
```

Expected: UV recognizes each subdirectory as a buildable package.

- [ ] **Step 4: Run focused package tests**

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest s3torchconnectorclient/python/tst/unit -q
UV_CACHE_DIR=/tmp/uv-cache uv run pytest s3torchconnector/tst/unit --ignore-glob '*/**/lightning' --ignore-glob '*/**/dcp' -q
```

Expected: tests pass or fail only for pre-existing unrelated dependency/environment issues that are documented in the final handoff.

- [ ] **Step 5: Check final diff**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; status shows only packaging migration files plus pre-existing user changes.
