#!/usr/bin/env bash
# Pre-commit hook: encrypt email.env → email.enc.env via SOPS.
# Fails loudly if email.env exists but sops is not installed.

set -euo pipefail

if [ ! -f email.env ]; then
    exit 0
fi

if ! command -v sops >/dev/null 2>&1; then
    echo "ERROR: email.env exists but sops is not installed." >&2
    echo "Install with: brew install sops" >&2
    exit 1
fi

tmp="email.enc.env.tmp"
sops encrypt --input-type dotenv --output-type dotenv email.env > "$tmp"
mv "$tmp" email.enc.env
git add email.enc.env
