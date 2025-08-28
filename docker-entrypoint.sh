#!/bin/sh
set -e
FLAVOR_VAL="${FLAVOR:-modelless}"
CMD_BIN="cgm-mcp-modelless"
if [ "$FLAVOR_VAL" = "full" ]; then
  CMD_BIN="cgm-mcp"
fi
exec "$CMD_BIN" "$@"
