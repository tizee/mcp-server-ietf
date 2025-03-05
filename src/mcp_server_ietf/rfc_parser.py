import os
import logging
import re
import requests
from dataclasses import dataclass
from typing import Dict, List,  Any, Optional

# Constants
INDEX_URL = "https://www.rfc-editor.org/rfc-index.txt"
RFC_URL_TEMPLATE = "https://www.rfc-editor.org/rfc/rfc{number}.txt"
CACHE_DIR = os.path.expanduser("~/.cache/ietf-doc-server")
DEFAULT_MAX_LINES = 200  # Default pagination limit

@dataclass
class RFCIndexData:
    """Data structure for RFC index information"""
    index_path: str
    docs_count: int
    rfc_titles: Dict[str, str]  # Map of RFC number to title


def download_rfc_index(cache_dir: str = CACHE_DIR) -> str:
    """
    Download and cache the RFC index file

    Args:
        cache_dir: Directory to store cached files

    Returns:
        Path to the cached index file
    """
    # Create cache directory if not exists
    os.makedirs(cache_dir, exist_ok=True)

    index_path = os.path.join(cache_dir, "rfc-index.txt")

    # Download and cache index if not present
    if not os.path.exists(index_path):
        print(f"Downloading RFC index from {INDEX_URL}")
        response = requests.get(INDEX_URL)
        response.raise_for_status()

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(response.text)

    return index_path

def parse_rfc_index(index_path: str) -> RFCIndexData:
    """
    Parse the RFC index file to extract titles and count

    Args:
        index_path: Path to the RFC index file

    Returns:
        RFCIndexData with parsed information
    """
    rfc_titles = {}
    docs_count = 0

    # Parse index to extract titles and count
    with open(index_path, "r", encoding="utf-8") as f:
        parsing_started = False

        for line in f:
            # Skip until we reach the RFC INDEX section
            if "RFC INDEX" in line:
                parsing_started = True
                continue

            # Only process lines after we've found the start marker
            if not parsing_started:
                continue

            # Use regex to look for lines starting with RFC numbers
            # RFC numbers are typically zero-padded to 4 digits (e.g., "0001")
            # But could be 5 digits for newer RFCs
            match = re.match(r'^\s*(\d{4}|\d{5})\s+(.+)', line)
            if match:
                rfc_num = match.group(1).lstrip('0')  # Remove leading zeros
                if not rfc_num:  # In case it was all zeros
                    rfc_num = "0"

                title_text = match.group(2)

                # Handle "Not Issued" RFCs
                if "Not Issued" in title_text:
                    rfc_titles[rfc_num] = "Not Issued"
                else:
                    # Extract title up to the first period or end of line
                    title = title_text.split('.')[0].strip()
                    rfc_titles[rfc_num] = title

                docs_count += 1

    return RFCIndexData(
        index_path=index_path,
        docs_count=docs_count,
        rfc_titles=rfc_titles
    )

def download_rfc(rfc_number: str, cache_dir: str = CACHE_DIR) -> str:
    """
    Download and cache a specific RFC document

    Args:
        rfc_number: The RFC number to download
        cache_dir: Directory to store cached files

    Returns:
        Path to the cached RFC document
    """
    # Create cache directory if not exists
    os.makedirs(cache_dir, exist_ok=True)

    # Create cache path for this document
    doc_path = os.path.join(cache_dir, f"rfc{rfc_number}.txt")

    # Download if not cached
    if not os.path.exists(doc_path):
        url = RFC_URL_TEMPLATE.format(number=rfc_number)
        try:
            response = requests.get(url)
            response.raise_for_status()

            with open(doc_path, "w", encoding="utf-8") as f:
                f.write(response.text)

        except requests.RequestException as e:
            raise Exception(f"Failed to download RFC {rfc_number}: {str(e)}")

    return doc_path

def get_rfc_document(
    rfc_number: str,
    start_line: int = 1,
    max_lines: int = 200,
    cache_dir: str = CACHE_DIR,
    index_data: Optional[RFCIndexData] = None
) -> Dict[str, Any]:
    """
    Get an RFC document by its number with pagination support

    Args:
        rfc_number: The RFC number (e.g., "1234")
        start_line: The line number to start from (default: 1)
        max_lines: Maximum number of lines to return (default: 200)
        cache_dir: Directory to store cached files
        index_data: Optional pre-loaded index data

    Returns:
        A dictionary containing the document content and metadata
    """
    # Validate input
    if not rfc_number.isdigit():
        return {"error": "RFC number must be a number"}

    if start_line < 1:
        return {"error": "start_line must be 1 or greater"}

    if max_lines < 1:
        return {"error": "max_lines must be 1 or greater"}

    # Get index data if not provided
    if index_data is None:
        index_path = download_rfc_index(cache_dir)
        index_data = parse_rfc_index(index_path)

    # Check if RFC exists in our index
    if rfc_number not in index_data.rfc_titles:
        return {"error": f"RFC {rfc_number} not found in index"}

    # Download RFC if needed
    try:
        doc_path = download_rfc(rfc_number, cache_dir)
    except Exception as e:
        return {"error": str(e)}

    # Read and paginate the document
    with open(doc_path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
        total_lines = len(all_lines)

        # Validate start_line
        if start_line > total_lines:
            return {"error": f"start_line ({start_line}) exceeds document length ({total_lines})"}

        # Calculate pagination
        end_line = min(start_line + max_lines - 1, total_lines)
        paginated_lines = all_lines[start_line-1:end_line]
        paginated_content = ''.join(paginated_lines)

        # Check if truncated
        truncated = end_line < total_lines

        # Extract page numbers if available by scanning the content
        page_info = extract_page_info(paginated_content)

    # Basic metadata
    title = index_data.rfc_titles.get(rfc_number, "Unknown title")

    return {
        "content": paginated_content,
        "title": title,
        "path": doc_path,
        "start_line": start_line,
        "end_line": end_line,
        "max_lines": max_lines,
        "total_lines": total_lines,
        "truncated": truncated,
        "truncated_at_line": end_line if truncated else None,
        "page_info": page_info,
        "next_chunk_start": end_line + 1 if truncated else None
    }

def extract_page_info(content: str) -> Dict[str, Any]:
    """Extract page numbers from RFC content if available"""
    page_info = {
        "pages_found": False,
        "first_page": None,
        "last_page": None
    }

    # Look for page markers like "[Page X]" in the content
    page_matches = re.findall(r'\[Page\s+(\d+)\]', content)

    if page_matches:
        page_info["pages_found"] = True
        page_info["first_page"] = int(page_matches[0])
        page_info["last_page"] = int(page_matches[-1])

    return page_info

def search_rfc_by_keyword(keyword: str, index_data: RFCIndexData) -> List[Dict[str, str]]:
    """
    Search for RFC documents by keyword in their titles

    Args:
        keyword: The keyword to search for
        index_data: Pre-loaded index data

    Returns:
        A list of matching RFCs with their numbers and titles
    """
    results = []

    for number, title in index_data.rfc_titles.items():
        if keyword.lower() in title.lower():
            results.append({
                "number": number,
                "title": title
            })

    return results
