.PHONEY: dev test

dev:
	npx @modelcontextprotocol/inspector uv run mcp-server-ietf
test:
	uv run pytest
