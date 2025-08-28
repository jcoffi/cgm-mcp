#!/bin/sh
set -e

FLAVOR_VAL="${FLAVOR:-modelless}"
CMD_BIN="cgm-mcp-modelless"

# Select CLI based on flavor, defaulting to modelless
if [ "$FLAVOR_VAL" = "full" ]; then
  CMD_BIN="cgm-mcp"
elif [ "$FLAVOR_VAL" != "modelless" ]; then
  echo "[entrypoint] Unknown FLAVOR='$FLAVOR_VAL', defaulting to modelless" >&2
fi

# Validate binary exists
if ! command -v "$CMD_BIN" >/dev/null 2>&1; then
  echo "[entrypoint] Error: command '$CMD_BIN' not found in PATH" >&2
  exit 127
fi

exec "$CMD_BIN" "$@"
