"""
Input validation utilities for the OneDrive Organizer.
"""

import re
from pathlib import Path
from typing import Optional


def validate_folder_path(path: str) -> bool:
    """
    Validate OneDrive folder path format.

    Args:
        path: Folder path to validate

    Returns:
        True if valid, False otherwise
    """
    if not path:
        return True  # Empty path means root

    # Check for invalid characters
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
    if any(char in path for char in invalid_chars):
        return False

    # Check for invalid path segments
    segments = path.split('/')
    for segment in segments:
        if segment in ['.', '..']:
            return False
        if segment.startswith(' ') or segment.endswith(' '):
            return False

    return True


def validate_date_field(field: str) -> bool:
    """
    Validate date field name.

    Args:
        field: Date field name

    Returns:
        True if valid, False otherwise
    """
    valid_fields = [
        'createdDateTime',
        'lastModifiedDateTime',
        'createdByUser',
        'lastModifiedByUser'
    ]
    return field in valid_fields


def validate_folder_structure_pattern(pattern: str) -> bool:
    """
    Validate folder structure pattern.

    Args:
        pattern: Folder structure pattern (e.g., "{year}/{month}")

    Returns:
        True if valid, False otherwise
    """
    if not pattern:
        return False

    # Extract placeholders
    placeholders = re.findall(r'\{(\w+)\}', pattern)

    # Valid placeholders
    valid_placeholders = ['year', 'month', 'day', 'quarter']

    # Check all placeholders are valid
    for placeholder in placeholders:
        if placeholder not in valid_placeholders:
            return False

    return True


def validate_cron_schedule(schedule: str) -> bool:
    """
    Validate cron schedule format (basic validation).

    Args:
        schedule: Cron schedule string

    Returns:
        True if valid format, False otherwise
    """
    parts = schedule.split()

    if len(parts) != 5:
        return False

    # Basic pattern check for each field
    for part in parts:
        if not re.match(r'^(\*|(\d+|\d+-\d+|\*/\d+)(,(\d+|\d+-\d+|\*/\d+))*)$', part):
            return False

    return True


def validate_file_extension(extension: str) -> bool:
    """
    Validate file extension format.

    Args:
        extension: File extension (e.g., ".txt")

    Returns:
        True if valid, False otherwise
    """
    if not extension:
        return False

    # Must start with dot
    if not extension.startswith('.'):
        return False

    # Check for valid characters (alphanumeric and some special chars)
    if not re.match(r'^\.[a-zA-Z0-9_-]+$', extension):
        return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')

    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed'

    return filename


def validate_operation_id(operation_id: str) -> bool:
    """
    Validate operation ID format.

    Args:
        operation_id: Operation ID to validate

    Returns:
        True if valid, False otherwise
    """
    # Operation ID should be timestamp-based: YYYYMMDD_HHMMSS_randomstr
    pattern = r'^\d{8}_\d{6}_[a-zA-Z0-9]+$'
    return bool(re.match(pattern, operation_id))
