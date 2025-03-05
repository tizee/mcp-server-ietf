# MCP-Server-IETF

A Model Context Protocol server for fetching IETF documents (RFCs) for Large Language Models.

## Overview

This project implements a [Model Context Protocol (MCP)](https://modelcontextprotocol.github.io/) server that provides access to IETF RFC documents. It enables Large Language Models to access RFC specifications through a standardized interface.

Key features:
- Download and cache RFC index and documents
- Search RFCs by keyword in titles
- Access RFC documents with pagination support
- Extract metadata like page numbers from documents

## Installation

### Requirements
- Python 3.11 or higher
- Dependencies as listed in `pyproject.toml`

### Install from source

```bash
# Clone the repository
git clone https://github.com/tizee/mcp-server-ietf
cd mcp-server-ietf

# Install with pip
pip install -e .
```

## Usage

### Starting the server

```bash
# Start the server
mcp-server-ietf
```

Or use it with the MCP inspector:

```bash
npx @modelcontextprotocol/inspector uv run mcp-server-ietf
```

### Available Tools

When connected to the server, the following tools are available:

#### `list_docs_number`
Get the total number of RFC documents available in the index.

#### `get_doc`
Get an RFC document by its number with pagination support.

Parameters:
- `number`: The RFC number (e.g., "1234")
- `start_line`: The line number to start from (default: 1)
- `max_lines`: Maximum number of lines to return (default: 200)

#### `search_rfc_by_keyword`
Search for RFC documents by keyword in their titles.

Parameters:
- `keyword`: The search term to look for in RFC titles

## Development

### Setup Development Environment

```bash
# Install development dependencies
uv install -e .[dev]
```

Run inspector with Makefile:

```
make dev
```

### Running Tests

```bash
# Run tests
uv run pytest
```

Or using the Makefile:

```bash
make test
```

### Cache Location

By default, the server caches RFC documents and the index at `~/.cache/ietf-doc-server`.

### Environment Variables

- `LOG_LEVEL`: Set the logging level (default: "DEBUG")

## License

MIT License - See `LICENSE` file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
