#!/usr/bin/env bash
# Print ready-to-paste websocat commands for two chat users.
#
# Used from `make ws-demo`. Registers both users (idempotent — duplicate
# registration just returns 400 which we ignore) and logs them in to
# grab fresh JWT access tokens, then emits two websocat invocations
# that connect to the same room. One sends browser-like
# User-Agent/Origin headers so the connect log line shows the
# enriched handshake fields; the other connects bare, to demonstrate
# that empty fields are dropped from the output.
#
# Requires: a running stack (`make up`), `curl`, `jq`, and `websocat`
# installed locally (`brew install websocat`).

set -euo pipefail

USER_A="${1:-wsuser}"
USER_B="${2:-wsbob}"
PASS="${3:-secret123}"
ROOM="${4:-ws-debug}"

API="http://localhost:8000"
WS="ws://localhost:8001"

# Idempotent: 400 means "already exists", which is fine for a demo.
register() {
  local username="$1"
  curl -s -o /dev/null -X POST "$API/api/auth/register/" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$username\",\"email\":\"$username@e.com\",\"password\":\"$PASS\"}"
}

login() {
  local username="$1"
  curl -s -X POST "$API/api/auth/login/" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$username\",\"password\":\"$PASS\"}" | jq -r .access
}

register "$USER_A"
register "$USER_B"

TOKEN_A=$(login "$USER_A")
TOKEN_B=$(login "$USER_B")

if [[ -z "$TOKEN_A" || "$TOKEN_A" == "null" ]] || [[ -z "$TOKEN_B" || "$TOKEN_B" == "null" ]]; then
  echo "Failed to acquire tokens. Is the stack running? (make up)" >&2
  exit 1
fi

cat <<EOF

==========================================
Tail logs first, in another terminal:
  make logs-ws
==========================================

USER A ($USER_A) — with browser-like headers:
websocat \\
  -H='User-Agent: Mozilla/5.0 (Macintosh) Chrome/124.0' \\
  -H='Origin: http://localhost:3000' \\
  "$WS/ws/chat/$ROOM/?token=$TOKEN_A"

USER B ($USER_B) — bare connection:
websocat "$WS/ws/chat/$ROOM/?token=$TOKEN_B"

==========================================
Once connected, paste a JSON frame and hit Enter:
  {"text":"hello from $USER_A"}
  {"text":"hello from $USER_B"}

Try invalid JSON to see the error frame + log line:
  not json

Ctrl+C in either terminal to disconnect (you'll see
"ws disconnect" in the log with the same request_id).
==========================================

EOF
