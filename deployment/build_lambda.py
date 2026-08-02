"""Builds the Lambda deployment package for the backend.

Produces deployment/build/lambda_package/ containing:
  - third-party dependencies (installed for the Lambda runtime platform,
    not necessarily the host OS — uses manylinux wheels so this works from
    Windows/macOS/Linux dev machines without Docker)
  - the app/ source tree
  - config.production.yaml copied in as config.yaml (the default filename
    Settings looks for)

Terraform's `archive_file` data source zips this directory; re-run this
script whenever backend requirements or source change, before `terraform
apply`.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
BUILD_DIR = REPO_ROOT / "deployment" / "build" / "lambda_package"

PYTHON_VERSION = "3.12"
PLATFORM = "manylinux2014_x86_64"


def main() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    print(f"Installing dependencies for {PLATFORM} / Python {PYTHON_VERSION}...")
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "-r", str(BACKEND_DIR / "requirements.txt"),
            "--platform", PLATFORM,
            "--implementation", "cp",
            "--python-version", PYTHON_VERSION,
            "--only-binary=:all:",
            "--target", str(BUILD_DIR),
        ],
        check=True,
    )

    print("Copying app/ source...")
    shutil.copytree(BACKEND_DIR / "app", BUILD_DIR / "app")

    print("Copying config.production.yaml -> config.yaml...")
    shutil.copyfile(BACKEND_DIR / "config.production.yaml", BUILD_DIR / "config.yaml")

    print(f"Done: {BUILD_DIR}")


if __name__ == "__main__":
    main()
