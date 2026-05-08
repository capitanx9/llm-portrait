##@ WebSocket demo

.PHONY: ws-demo

# Demo helpers for poking the WebSocket chat by hand. Automated coverage
# lives in tests/test_chat_ws.py (auth, broadcast, isolation, invalid
# JSON, persistence) — these targets are for eyeballing log output in
# `make logs-ws` while playing with two real connections.

WS_DEMO_USER_A ?= wsuser
WS_DEMO_USER_B ?= wsbob
WS_DEMO_PASS ?= secret123
WS_DEMO_ROOM ?= ws-debug

ws-demo: ## Print ready-to-paste websocat commands for two chat users
	@./scripts/ws-demo.sh $(WS_DEMO_USER_A) $(WS_DEMO_USER_B) $(WS_DEMO_PASS) $(WS_DEMO_ROOM)
