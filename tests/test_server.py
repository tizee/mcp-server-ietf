import os
import pytest
import tempfile
import textwrap
import requests
from unittest.mock import patch, mock_open, MagicMock
from mcp_server_ietf.rfc_parser import (
    download_rfc_index, parse_rfc_index, download_rfc,
    get_rfc_document, extract_page_info, search_rfc_by_keyword,
    RFCIndexData
)

@pytest.fixture
def sample_rfc_index():
    """Sample RFC index content for testing"""
    return textwrap.dedent("""
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

                                 RFC INDEX
                               -------------

    (CREATED ON: 03/04/2025.)

    This file contains citations for all RFCs in numeric order.

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

                                    RFC INDEX
                                    ---------

    0001 Host Software. S. Crocker. April 1969. (Format: TXT, HTML) (Status:
         UNKNOWN) (DOI: 10.17487/RFC0001)

    0002 Host software. B. Duvall. April 1969. (Format: TXT, PDF, HTML)
         (Status: UNKNOWN) (DOI: 10.17487/RFC0002)

    0014 Not Issued.

    0026 Not Issued.

    9748 The Latest RFC. Some Author. March 2025. (Format: TXT, HTML) (Status:
         PROPOSED STANDARD) (DOI: 10.17487/RFC9748)
    """)

def test_parse_rfc_index_counts_correctly(sample_rfc_index):
    """Test that parse_rfc_index counts RFCs correctly"""
    # Create a temporary file with sample content
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file.write(sample_rfc_index)
        temp_path = temp_file.name

    try:
        # Parse the index file
        result = parse_rfc_index(temp_path)

        # Check the document count (should be 5 in our sample)
        assert result.docs_count == 5

        # Check that all RFC numbers are parsed correctly
        assert "1" in result.rfc_titles  # Note: leading zeros are removed
        assert "2" in result.rfc_titles
        assert "14" in result.rfc_titles
        assert "26" in result.rfc_titles
        assert "9748" in result.rfc_titles

        # Check titles are parsed correctly
        assert result.rfc_titles["1"] == "Host Software"
        assert result.rfc_titles["2"] == "Host software"
        assert result.rfc_titles["14"] == "Not Issued"
        assert result.rfc_titles["26"] == "Not Issued"
        assert result.rfc_titles["9748"] == "The Latest RFC"

    finally:
        # Clean up the temporary file
        os.unlink(temp_path)


def test_parse_rfc_index_empty_file():
    """Test parsing with an empty file"""
    with patch('builtins.open', mock_open(read_data="")):
        result = parse_rfc_index("dummy_path")

        assert result.docs_count == 0
        assert len(result.rfc_titles) == 0

def test_parse_rfc_index_handles_edge_cases():
    """Test edge cases in RFC index parsing"""
    # Create a sample with unusual formatting
    sample = textwrap.dedent("""
    RFC INDEX
    ---------

    0000 Zero RFC. Author. Date. (Format: TXT)

    00001 Leading zeros. Author. Date. (Format: TXT)

    12345 Five digits. Author. Date. (Format: TXT)

      0042 Indented number. Author. Date. (Format: TXT)
    """)

    # Mock the file open
    with patch('builtins.open', mock_open(read_data=sample)):
        result = parse_rfc_index("dummy_path")

        # Should handle zero
        assert "0" in result.rfc_titles
        assert result.rfc_titles["0"] == "Zero RFC"

        # Should handle extra leading zeros
        assert "1" in result.rfc_titles
        assert result.rfc_titles["1"] == "Leading zeros"

        # Should handle 5-digit RFCs
        assert "12345" in result.rfc_titles
        assert result.rfc_titles["12345"] == "Five digits"

        # Should handle indentation
        assert "42" in result.rfc_titles
        assert result.rfc_titles["42"] == "Indented number"

        # Total count should be 4
        assert result.docs_count == 4


# Tests for download_rfc_index
def test_download_rfc_index_cached():
    """Test download_rfc_index when file is already cached"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a fake cached index file
        cache_file = os.path.join(temp_dir, "rfc-index.txt")
        with open(cache_file, "w") as f:
            f.write("This is a cached index")

        # Mock the requests.get to ensure it's not called
        with patch('requests.get') as mock_get:
            result = download_rfc_index(temp_dir)

            # Function should return path to existing file without downloading
            assert result == cache_file
            mock_get.assert_not_called()

def test_download_rfc_index_not_cached():
    """Test download_rfc_index when file needs to be downloaded"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock the requests.get response
        mock_response = MagicMock()
        mock_response.text = "Downloaded RFC index content"

        with patch('requests.get', return_value=mock_response) as mock_get:
            result = download_rfc_index(temp_dir)

            # Function should download and save the file
            expected_path = os.path.join(temp_dir, "rfc-index.txt")
            assert result == expected_path
            mock_get.assert_called_once()

            # Check the content was saved
            with open(result, 'r') as f:
                assert f.read() == "Downloaded RFC index content"

# Tests for download_rfc
def test_download_rfc_cached():
    """Test download_rfc when file is already cached"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a fake cached RFC file
        rfc_num = "2119"
        cache_file = os.path.join(temp_dir, f"rfc{rfc_num}.txt")
        with open(cache_file, "w") as f:
            f.write("This is a cached RFC")

        # Mock the requests.get to ensure it's not called
        with patch('requests.get') as mock_get:
            result = download_rfc(rfc_num, temp_dir)

            # Function should return path to existing file without downloading
            assert result == cache_file
            mock_get.assert_not_called()

def test_download_rfc_not_cached():
    """Test download_rfc when file needs to be downloaded"""
    with tempfile.TemporaryDirectory() as temp_dir:
        rfc_num = "2119"

        # Mock the requests.get response
        mock_response = MagicMock()
        mock_response.text = "Downloaded RFC content"

        with patch('requests.get', return_value=mock_response) as mock_get:
            result = download_rfc(rfc_num, temp_dir)

            # Function should download and save the file
            expected_path = os.path.join(temp_dir, f"rfc{rfc_num}.txt")
            assert result == expected_path
            mock_get.assert_called_once_with(
                f"https://www.rfc-editor.org/rfc/rfc{rfc_num}.txt"
            )

            # Check the content was saved
            with open(result, 'r') as f:
                assert f.read() == "Downloaded RFC content"

def test_download_rfc_failed():
    """Test download_rfc when download fails"""
    with tempfile.TemporaryDirectory() as temp_dir:
        rfc_num = "2119"

        # Mock a failed request
        mock_error = requests.RequestException("Network error")
        with patch('requests.get', side_effect=mock_error):
            with pytest.raises(Exception) as exc_info:
                download_rfc(rfc_num, temp_dir)

            # Check that the exception message is correct
            assert f"Failed to download RFC {rfc_num}" in str(exc_info.value)
            assert "Network error" in str(exc_info.value)

# Tests for extract_page_info
def test_extract_page_info_no_pages():
    """Test extract_page_info with content having no page markers"""
    content = "This is some content with no page markers"
    result = extract_page_info(content)

    assert result["pages_found"] is False
    assert result["first_page"] is None
    assert result["last_page"] is None

def test_extract_page_info_with_pages():
    """Test extract_page_info with content having page markers"""
    content = """
    Some content
    [Page 1]
    More content
    [Page 2]
    Even more content
    [Page 3]
    """
    result = extract_page_info(content)

    assert result["pages_found"] is True
    assert result["first_page"] == 1
    assert result["last_page"] == 3

def test_extract_page_info_with_single_page():
    """Test extract_page_info with content having a single page marker"""
    content = """
    Some content
    [Page 42]
    More content
    """
    result = extract_page_info(content)

    assert result["pages_found"] is True
    assert result["first_page"] == 42
    assert result["last_page"] == 42

# Tests for search_rfc_by_keyword
def test_search_rfc_by_keyword_matches():
    """Test search_rfc_by_keyword with matching keywords"""
    # Create sample index data
    index_data = RFCIndexData(
        index_path="dummy_path",
        docs_count=3,
        rfc_titles={
            "1": "Host Software",
            "2": "Host software implementation",
            "3": "Network Protocol"
        }
    )

    # Search for "host" (case-insensitive)
    results = search_rfc_by_keyword("host", index_data)

    assert len(results) == 2
    assert {"number": "1", "title": "Host Software"} in results
    assert {"number": "2", "title": "Host software implementation"} in results

def test_search_rfc_by_keyword_no_matches():
    """Test search_rfc_by_keyword with no matching keywords"""
    # Create sample index data
    index_data = RFCIndexData(
        index_path="dummy_path",
        docs_count=3,
        rfc_titles={
            "1": "Host Software",
            "2": "Host software implementation",
            "3": "Network Protocol"
        }
    )

    # Search for keyword with no matches
    results = search_rfc_by_keyword("encryption", index_data)

    assert len(results) == 0

def test_search_rfc_by_keyword_empty_index():
    """Test search_rfc_by_keyword with empty index"""
    # Create empty index data
    index_data = RFCIndexData(
        index_path="dummy_path",
        docs_count=0,
        rfc_titles={}
    )

    # Search in empty index
    results = search_rfc_by_keyword("host", index_data)

    assert len(results) == 0

# Tests for get_rfc_document
@pytest.fixture
def mock_index_data():
    """Fixture for mock index data"""
    return RFCIndexData(
        index_path="dummy_path",
        docs_count=2,
        rfc_titles={
            "1": "Host Software",
            "2": "Host software implementation"
        }
    )

def test_get_rfc_document_validation_errors():
    """Test validation errors in get_rfc_document"""
    # Test invalid RFC number
    result = get_rfc_document("abc")
    assert "error" in result
    assert "RFC number must be a number" in result["error"]

    # Test invalid start_line
    result = get_rfc_document("1", start_line=0)
    assert "error" in result
    assert "start_line must be 1 or greater" in result["error"]

    # Test invalid max_lines
    result = get_rfc_document("1", max_lines=0)
    assert "error" in result
    assert "max_lines must be 1 or greater" in result["error"]

def test_get_rfc_document_not_in_index(mock_index_data):
    """Test get_rfc_document with RFC not in index"""
    result = get_rfc_document("999", index_data=mock_index_data)

    assert "error" in result
    assert "RFC 999 not found in index" in result["error"]

def test_get_rfc_document_download_error():
    """Test get_rfc_document with download error"""
    # Create a minimal mock index data
    index_data = RFCIndexData(
        index_path="dummy_path",
        docs_count=1,
        rfc_titles={"1": "Host Software"}
    )

    # Mock download_rfc to raise an exception
    with patch('mcp_server_ietf.rfc_parser.download_rfc',
              side_effect=Exception("Download failed")):
        result = get_rfc_document("1", index_data=index_data)

        assert "error" in result
        assert "Download failed" in result["error"]

def test_get_rfc_document_success():
    """Test successful get_rfc_document"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock RFC file
        rfc_num = "1"
        rfc_path = os.path.join(temp_dir, f"rfc{rfc_num}.txt")
        rfc_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        with open(rfc_path, "w") as f:
            f.write(rfc_content)

        # Create mock index data
        index_data = RFCIndexData(
            index_path="dummy_path",
            docs_count=1,
            rfc_titles={rfc_num: "Host Software"}
        )

        # Mock the download_rfc function to return our mock file
        with patch('mcp_server_ietf.rfc_parser.download_rfc',
                  return_value=rfc_path):
            # Request with pagination
            result = get_rfc_document(
                rfc_num,
                start_line=2,
                max_lines=2,
                cache_dir=temp_dir,
                index_data=index_data
            )

            # Check result
            assert "error" not in result
            assert result["content"] == "Line 2\nLine 3\n"
            assert result["title"] == "Host Software"
            assert result["start_line"] == 2
            assert result["end_line"] == 3
            assert result["total_lines"] == 5
            assert result["truncated"] is True
            assert result["next_chunk_start"] == 4

def test_get_rfc_document_pagination_edge_cases():
    """Test pagination edge cases in get_rfc_document"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock RFC file
        rfc_num = "1"
        rfc_path = os.path.join(temp_dir, f"rfc{rfc_num}.txt")
        rfc_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        with open(rfc_path, "w") as f:
            f.write(rfc_content)

        # Create mock index data
        index_data = RFCIndexData(
            index_path="dummy_path",
            docs_count=1,
            rfc_titles={rfc_num: "Host Software"}
        )

        # Mock the download_rfc function to return our mock file
        with patch('mcp_server_ietf.rfc_parser.download_rfc',
                  return_value=rfc_path):
            # Test requesting beyond file length
            result = get_rfc_document(
                rfc_num,
                start_line=10,  # Beyond total_lines
                cache_dir=temp_dir,
                index_data=index_data
            )
            assert "error" in result
            assert "exceeds document length" in result["error"]

            # Test requesting the entire file
            result = get_rfc_document(
                rfc_num,
                start_line=1,
                max_lines=10,  # More than total_lines
                cache_dir=temp_dir,
                index_data=index_data
            )
            assert "error" not in result
            assert result["content"] == rfc_content
            assert result["truncated"] is False
            assert result["next_chunk_start"] is None

def test_get_rfc_document_with_page_info():
    """Test get_rfc_document with page info extraction"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock RFC file with page markers
        rfc_num = "1"
        rfc_path = os.path.join(temp_dir, f"rfc{rfc_num}.txt")
        rfc_content = "Line 1\n[Page 1]\nLine 3\n[Page 2]\nLine 5\n"
        with open(rfc_path, "w") as f:
            f.write(rfc_content)

        # Create mock index data
        index_data = RFCIndexData(
            index_path="dummy_path",
            docs_count=1,
            rfc_titles={rfc_num: "Host Software"}
        )

        # Mock the download_rfc function to return our mock file
        with patch('mcp_server_ietf.rfc_parser.download_rfc',
                  return_value=rfc_path):
            result = get_rfc_document(
                rfc_num,
                cache_dir=temp_dir,
                index_data=index_data
            )

            # Check page info was extracted
            assert result["page_info"]["pages_found"] is True
            assert result["page_info"]["first_page"] == 1
            assert result["page_info"]["last_page"] == 2
