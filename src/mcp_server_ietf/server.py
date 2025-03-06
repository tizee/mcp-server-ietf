import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, List,  Any
from .rfc_parser import download_rfc_index, parse_rfc_index, RFCIndexData, get_rfc_document
from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv

load_dotenv()
default_log_level = os.environ.get("LOG_LEVEL", "DEBUG").upper()
log_level = getattr(logging, default_log_level, logging.INFO)

# Constants
INDEX_URL = "https://www.rfc-editor.org/rfc-index.txt"
RFC_URL_TEMPLATE = "https://www.rfc-editor.org/rfc/rfc{number}.txt"
CACHE_DIR = os.path.expanduser("~/.cache/ietf-doc-server")
DEFAULT_MAX_LINES = 200  # Default pagination limit

log_file = os.path.join(CACHE_DIR, "mcp-server-ietf.log")

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)


logger = logging.getLogger("mcp-server-ietf")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[RFCIndexData]:
    """Initialize server resources and load/cache the RFC index"""
    # Create cache directory if not exists
    os.makedirs(CACHE_DIR, exist_ok=True)

    index_path = os.path.join(CACHE_DIR, "rfc-index.txt")

    # Download and cache index if not present
    download_rfc_index(CACHE_DIR)
    data = parse_rfc_index(index_path)
    logger.debug(f"data :{data}")

    try:
        yield data
    finally:
        # Cleanup if needed
        pass


# Create MCP server with lifespan
mcp = FastMCP("mcp-server-ietf", lifespan=server_lifespan,
              log_level = default_log_level)

@mcp.tool()
def list_ietf_docs_number(ctx: Context) -> int:
    """
    Get the total number of IETF RFC documents available in RFC editor Index
    """
    server_ctx = ctx.request_context.lifespan_context
    logger.debug(f"doc count:{server_ctx.docs_count}")
    return server_ctx.docs_count

@mcp.tool()
async def get_ietf_doc(
    ctx: Context,
    number: int,
    start_line: int = 1,
    max_lines: int = DEFAULT_MAX_LINES,
) -> Dict[str, Any]:
    """
    Get an RFC document by its number in RFC editor Index with pagination support

    Args:
        number: The RFC number str (e.g., "1234")
        start_line: The line number to start from (default: 1)
        max_lines: Maximum number of lines to return (default: 200)

    Returns:
        A dictionary containing the document content and metadata
    """
    server_ctx = ctx.request_context.lifespan_context
    data = get_rfc_document(str(number),
                                       start_line,
                                       max_lines,
                                       CACHE_DIR, server_ctx)
    logger.debug(f"get_doc: {data}")
    return data


@mcp.tool()
def search_ietf_rfc_by_keyword(keyword: str, ctx: Context) -> List[Dict[str, str]]:
    """
    Search for IETF RFC documents from RFC Editor Index by keyword in their titles

    Args:
        keyword: The keyword to search for

    Returns:
        A list of matching RFCs with their numbers and titles
    """
    server_ctx = ctx.request_context.lifespan_context
    results = []

    for number, title in server_ctx.rfc_titles.items():
        if keyword.lower() in title.lower():
            results.append({
                "number": number,
                "title": title
            })

    logger.debug(f"search_rfc_by_keyword: {results}")
    return results

def serve():
    print(f"Starting mcp-server-ietf. Cache directory: {CACHE_DIR}")
    logger.info(f"Logging to: {log_file}")
    mcp.run()

if __name__ == "__main__":
    serve()
