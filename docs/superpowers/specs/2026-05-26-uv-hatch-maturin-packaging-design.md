# UV, Hatchling, and Maturin Packaging Migration Design

## Goal

Move the repository to a UV-based development and build workflow while removing
setuptools from the package build backends.

The repository will keep its three separately published Python packages:

- `s3torchconnectorclient`: Rust/PyO3 native client package.
- `s3torchconnector`: Python connector package.
- `s3torchbenchmarking`: benchmarking tools package.

## Architecture

Add a root UV workspace with these three package directories as members. The root
project is only a workspace coordinator and should not be installed as a package.
The workspace owns the shared `uv.lock`, common development dependency groups,
and local workspace source resolution.

Within the workspace, `s3torchconnector` continues to publish a normal runtime
dependency on `s3torchconnectorclient == 1.5.0`, so built distributions remain
valid outside UV. For local development, `tool.uv.sources` maps
`s3torchconnectorclient` to the workspace member, so edits to the native client
are tested without pulling the released package from an index.

## Build Backends

Use Hatchling for pure Python packages:

- `s3torchconnector`
- `s3torchbenchmarking`

Each Hatchling package will explicitly select its source package directory so
wheel contents match the existing `src` layout.

Use Maturin for the Rust/PyO3 package:

- `s3torchconnectorclient`

The Maturin package will remain a mixed Rust/Python project. The existing Python
files stay under `python/src`, and Maturin is configured with:

- `bindings = "pyo3"`
- `python-source = "python/src"`
- `module-name = "s3torchconnectorclient._mountpoint_s3_client"`

This preserves the existing import path and keeps the current `.pyi`, `py.typed`,
and logger patch files in the wheel.

## Workflow

Local development should use UV commands:

- `uv sync --all-extras` for a broad development environment.
- `uv run --package <package> ...` for package-scoped commands.
- `uv build ./s3torchconnectorclient`
- `uv build ./s3torchconnector`
- `uv build ./s3torchbenchmarking`

The developer documentation will replace editable `pip install` instructions
with UV workspace commands. Rust client changes will still require rebuilding the
native extension, but the recommended command becomes a UV/Maturin-backed install
or build instead of `pip install -e`.

## CI and Release

CI Python setup should move toward UV for dependency installation and command
execution. The wheel workflow can keep `cibuildwheel` initially because it will
invoke each package's PEP 517 backend; after this migration, the native client
backend will be Maturin instead of setuptools-rust.

The release workflow should use `uv build` for source distributions and pure
Python wheels. Replacing the native wheel matrix with `PyO3/maturin-action` is
out of scope for this migration. The only exception is a required CI fix if
`cibuildwheel` cannot invoke the Maturin backend successfully.

## Packaging Details

Root metadata files currently live at the repository root while package
`pyproject.toml` files refer to files like `README.md`, `LICENSE`, `NOTICE`, and
`THIRD-PARTY-LICENSES` from the package directory. The migration should make this
explicit instead of relying on ad hoc copy steps. The preferred approach is to
configure the build backends to include the root metadata files in sdists where
supported. If backend limitations make that brittle, the existing CI copy step may
remain for release builds, but local `uv build` should be validated and the
remaining warning documented.

## Testing

Validation should cover:

- `uv lock`
- `uv sync` for the workspace or targeted packages
- `uv build` for all three packages
- Import smoke test for `s3torchconnectorclient._mountpoint_s3_client`
- Existing focused unit tests for the Python connector and native client

If a full dependency sync is too slow or unavailable in the local environment,
record the exact blocker and run package build/import validation with the
available cached or installed dependencies.
