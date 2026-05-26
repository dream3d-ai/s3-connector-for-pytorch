# Single s3torchconnector Wheel Design

## Goal

Make the repository installable from a single Git URL without requiring package
subdirectory references:

```bash
uv pip install "git+https://github.com/awslabs/s3-connector-for-pytorch.git@<ref>"
```

The installed distribution should be `s3torchconnector`; the native client
should become an internal package bundled inside that wheel instead of a
separately installed `s3torchconnectorclient` distribution.

## Architecture

The repository root becomes the primary installable project. It uses Maturin as
the build backend and produces one wheel containing both Python packages:

- `s3torchconnector`
- `s3torchconnectorclient`

The `s3torchconnectorclient` import package remains available for existing
internal imports and compatibility, but it no longer has its own published
distribution metadata. `s3torchconnector` removes its runtime dependency on
`s3torchconnectorclient == 1.5.0` because the client module is bundled in the
same wheel.

## Layout

Move the public connector package and native client package into root-level
source and Rust locations:

```text
pyproject.toml
Cargo.toml
Cargo.lock
rust-toolchain.toml
rust/
src/
  s3torchconnector/
  s3torchconnectorclient/
s3torchbenchmarking/
```

The existing `s3torchbenchmarking` package remains separate. It stays in the UV
workspace and depends on `s3torchconnector[lightning,dcp]`.

## Build Backend

The root `pyproject.toml` becomes the `s3torchconnector` package metadata and is
configured with Maturin:

```toml
[build-system]
requires = ["maturin>=1.9,<2"]
build-backend = "maturin"

[project]
name = "s3torchconnector"

[tool.maturin]
bindings = "pyo3"
python-source = "src"
module-name = "s3torchconnectorclient._mountpoint_s3_client"
```

The Rust library keeps the Python extension module name
`_mountpoint_s3_client`, preserving imports such as:

```python
from s3torchconnectorclient._mountpoint_s3_client import MountpointS3Client
```

## Workspace

The root project remains a UV workspace root and package at the same time.
Workspace members become:

- `.`
- `s3torchbenchmarking`

The former `s3torchconnector` and `s3torchconnectorclient` package directories
are removed after their contents move to the root layout.

## CI and Docs

Documentation should describe a single Git install command for the main package.
CI should build and install `s3torchconnector` from the repository root. Any test
paths that referenced the old package directories should point to the new
root-level `src/`, `rust/`, and `tst/` paths.

The wheel release workflow should build native wheels from the repository root.
If source distribution jobs still need to build benchmarking artifacts, they can
run `uv build ./s3torchbenchmarking` separately.

## Compatibility

Runtime import compatibility is preserved because `s3torchconnectorclient`
remains a Python import package inside the wheel. Distribution-level
compatibility is intentionally changed: users should install `s3torchconnector`,
not `s3torchconnectorclient`.

Existing test files can move with minimal edits. Assertions that check package
metadata for `s3torchconnectorclient` should be updated because that name is no
longer a separately installed distribution.

## Testing

Validation should cover:

- `uv lock`
- `uv build .`
- `uv pip install --dry-run "s3torchconnector @ ."`
- Import smoke for `s3torchconnector` and
  `s3torchconnectorclient._mountpoint_s3_client`
- Native client unit tests from their new path
- Connector unit tests from their new path
- Benchmarking compatibility test
- `git diff --check`
