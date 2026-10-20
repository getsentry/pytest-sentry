#!/usr/bin/env bash
# Called by craft as `bump-version.sh <old> <new>`. Avoids needing uv on the
# release runner: rewrites the version in pyproject.toml and the matching
# editable entry in uv.lock so `uv sync --locked` keeps passing.
set -euxo pipefail

NEW_VERSION="$2"

# The version is interpolated into sed programs below; only allow PEP 440
# characters so it can't inject sed commands.
if [[ ! "${NEW_VERSION}" =~ ^[0-9A-Za-z.+!-]+$ ]]; then
    echo "invalid version: ${NEW_VERSION}" >&2
    exit 1
fi

sed -i "s/^version = \".*\"/version = \"${NEW_VERSION}\"/" pyproject.toml
sed -i "/^name = \"pytest-sentry\"$/{n;s/^version = \".*\"/version = \"${NEW_VERSION}\"/}" uv.lock
