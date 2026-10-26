#!/usr/bin/env bash
set -euo pipefail

latest_sha=$(gh api "repos/$REPOSITORY/git/ref/heads/main" --jq .object.sha)
if [[ "$SHA" != "$latest_sha" ]]; then
  echo "::error::main has advanced; run the latest deployment instead."
  exit 1
fi
