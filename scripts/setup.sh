#!/usr/bin/env bash
# === Setup Android ===
# O Makefile é a fonte única de verdade para preparação do ambiente.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

make setup
make doctor
