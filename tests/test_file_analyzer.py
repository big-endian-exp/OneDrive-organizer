"""
Unit tests for FileAnalyzer
"""

import pytest
from datetime import datetime
from src.organizer.file_analyzer import FileAnalyzer


def test_file_analyzer_initialization():
    """Test FileAnalyzer initialization."""
    analyzer = FileAnalyzer(
        date_field="createdDateTime",
        folder_structure="{year}/{month}",
        destination_root="Organized"
    )

    assert analyzer.date_field == "createdDateTime"
    assert analyzer.folder_structure == "{year}/{month}"
    assert analyzer.destination_root == "Organized"


def test_extract_date():
    """Test date extraction from item."""
    analyzer = FileAnalyzer()

    item = {
        "name": "test.pdf",
        "createdDateTime": "2024-01-15T10:30:00Z"
    }

    date = analyzer.extract_date(item)

    assert date is not None
    assert date.year == 2024
    assert date.month == 1
    assert date.day == 15


def test_generate_destination_path():
    """Test destination path generation."""
    analyzer = FileAnalyzer(
        folder_structure="{year}/{month}",
        destination_root="Organized"
    )

    item = {
        "name": "document.pdf",
        "createdDateTime": "2024-03-20T14:30:00Z"
    }

    path = analyzer.generate_destination_path(item)

    assert path is not None
    assert "Organized" in path
    assert "2024" in path
    assert "03_March" in path


def test_is_already_organized():
    """Test detection of already organized files."""
    analyzer = FileAnalyzer(destination_root="Organized")

    # Should detect organized paths
    assert analyzer.is_already_organized("Organized/2024/01_January/file.pdf") == True

    # Should not detect non-organized paths
    assert analyzer.is_already_organized("Documents/file.pdf") == False
    assert analyzer.is_already_organized("file.pdf") == False


def test_should_skip_folder():
    """Test that folders are skipped."""
    analyzer = FileAnalyzer()

    item = {
        "name": "My Folder",
        "folder": {}
    }

    should_skip, reason = analyzer.should_skip_item(item, "My Folder")

    assert should_skip == True
    assert reason == "is_folder"


def test_should_skip_excluded_extension():
    """Test extension exclusion."""
    analyzer = FileAnalyzer()

    item = {
        "name": "temp.tmp",
        "file": {}
    }

    should_skip, reason = analyzer.should_skip_item(
        item,
        "temp.tmp",
        exclude_extensions=[".tmp", ".lock"]
    )

    assert should_skip == True
    assert "excluded_extension" in reason


def test_analyze_item():
    """Test full item analysis."""
    analyzer = FileAnalyzer()

    item = {
        "name": "document.pdf",
        "file": {},
        "createdDateTime": "2024-01-15T10:30:00Z"
    }

    result = analyzer.analyze_item(item, "Documents/document.pdf")

    assert result['action'] == 'move'
    assert result['destination_path'] is not None
    assert "2024" in result['destination_path']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
