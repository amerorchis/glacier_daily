#!/usr/bin/env bash
# Pre-commit hook: encrypt email.env → email.enc.env via SOPS.
# Skips re-encryption if email.env hasn't changed (avoids noisy
# diffs from SOPS timestamp/MAC changes).
# Fails loudly if email.env exists but sops is not installed.

set -euo pipefail

HASH_FILE=".email.env.sha256"

if [ ! -f email.env ]; then
    exit 0
fi

if ! command -v sops >/dev/null 2>&1; then
    echo "ERROR: email.env exists but sops is not installed." >&2
    echo "Install with: brew install sops" >&2
    exit 1
fi

# Check if email.env has changed since last encryption.
current_hash=$(shasum -a 256 email.env | awk '{print $1}')

if [ -f "$HASH_FILE" ] && [ -f email.enc.env ]; then
    stored_hash=$(cat "$HASH_FILE")
    if [ "$current_hash" = "$stored_hash" ]; then
        exit 0
    fi
fi

# Content changed (or first run) — re-encrypt.
tmp="email.enc.env.tmp"
sops encrypt --input-type dotenv --output-type dotenv email.env > "$tmp"
mv "$tmp" email.enc.env
echo "$current_hash" > "$HASH_FILE"
git add email.enc.env
