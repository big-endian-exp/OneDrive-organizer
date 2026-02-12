"""
File analysis for determining organization destinations.
"""

import re
from datetime import datetime
from typing import Dict, Optional, Tuple
from dateutil import parser
from ..utils.logger import get_logger

logger = get_logger()


class FileAnalyzer:
    """Analyze files to determine organization destinations."""

    def __init__(
        self,
        date_field: str = "createdDateTime",
        folder_structure: str = "{year}/{month}",
        destination_root: str = "Organized",
        categorizer: Optional[object] = None
    ):
        """
        Initialize file analyzer.

        Args:
            date_field: Field to use for date (createdDateTime or lastModifiedDateTime)
            folder_structure: Folder structure pattern
            destination_root: Root folder for organized files
            categorizer: Optional ContentCategorizer instance for categorization
        """
        self.date_field = date_field
        self.folder_structure = folder_structure
        self.destination_root = destination_root
        self.categorizer = categorizer

        logger.debug(
            f"File analyzer initialized: date_field={date_field}, "
            f"structure={folder_structure}, "
            f"categorization={'enabled' if categorizer else 'disabled'}"
        )

    def extract_date(self, item: Dict) -> Optional[datetime]:
        """
        Extract date from item metadata.

        Args:
            item: Item dictionary from API

        Returns:
            datetime object, or None if not found
        """
        date_str = item.get(self.date_field)

        if not date_str:
            logger.warning(f"Item {item.get('name')} missing {self.date_field}")
            return None

        try:
            return parser.isoparse(date_str)
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None

    def generate_destination_path(self, item: Dict, item_path: str = "") -> Optional[str]:
        """
        Generate destination path for item based on date and category.

        Args:
            item: Item dictionary
            item_path: Full path to item (for categorization)

        Returns:
            Destination path string, or None if cannot determine
        """
        date = self.extract_date(item)

        if not date:
            return None

        # Build path from structure pattern
        path_parts = [self.destination_root]

        # Replace placeholders
        structure = self.folder_structure

        # Category placeholder (if categorizer is enabled)
        if '{category}' in structure:
            if self.categorizer:
                category = self.categorizer.categorize(item, item_path)
                structure = structure.replace('{category}', category)
            else:
                # No categorizer but structure expects category - use 'Other'
                structure = structure.replace('{category}', 'Other')

        # Date placeholders
        structure = structure.replace('{year}', str(date.year))
        structure = structure.replace('{month}', date.strftime('%m_%B'))  # e.g., "01_January"
        structure = structure.replace('{day}', date.strftime('%d'))
        structure = structure.replace('{quarter}', f"Q{(date.month - 1) // 3 + 1}")

        path_parts.append(structure)

        destination_path = '/'.join(path_parts)

        logger.debug(f"Generated path for {item['name']}: {destination_path}")
        return destination_path

    def is_already_organized(self, item_path: str) -> bool:
        """
        Check if item is already in organized structure.

        Args:
            item_path: Full path of item

        Returns:
            True if already organized
        """
        # Check if path starts with destination root
        if not item_path.startswith(self.destination_root):
            return False

        # Check if path matches organized pattern
        # Patterns to match:
        # - Organized/YYYY/MM_MonthName/... (date-only)
        # - Organized/Category/YYYY/MM_MonthName/... (category + date)
        patterns = [
            rf"{re.escape(self.destination_root)}/\d{{4}}/\d{{2}}_\w+/",  # Date-only
            rf"{re.escape(self.destination_root)}/\w+/\d{{4}}/\d{{2}}_\w+/",  # Category + date
        ]

        is_organized = any(re.search(pattern, item_path) for pattern in patterns)

        if is_organized:
            logger.debug(f"Item already organized: {item_path}")

        return is_organized

    def should_skip_item(
        self,
        item: Dict,
        item_path: str,
        skip_already_organized: bool = True,
        exclude_extensions: Optional[list] = None,
        min_age_days: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if item should be skipped.

        Args:
            item: Item dictionary
            item_path: Full path of item
            skip_already_organized: Skip items already in organized structure
            exclude_extensions: List of extensions to exclude
            min_age_days: Only process files older than this many days

        Returns:
            Tuple of (should_skip, reason)
        """
        # Skip folders
        if 'folder' in item:
            return True, "is_folder"

        # Check if already organized
        if skip_already_organized and self.is_already_organized(item_path):
            return True, "already_organized"

        # Check extension
        if exclude_extensions:
            name = item.get('name', '')
            extension = '.' + name.rsplit('.', 1)[-1] if '.' in name else ''

            if extension.lower() in [ext.lower() for ext in exclude_extensions]:
                return True, f"excluded_extension_{extension}"

        # Check minimum age
        if min_age_days > 0:
            date = self.extract_date(item)
            if date:
                age_days = (datetime.utcnow() - date.replace(tzinfo=None)).days
                if age_days < min_age_days:
                    return True, f"too_recent_{age_days}_days"

        return False, None

    def analyze_item(
        self,
        item: Dict,
        item_path: str,
        **skip_options
    ) -> Dict:
        """
        Analyze item and generate move plan.

        Args:
            item: Item dictionary
            item_path: Full path of item
            **skip_options: Options for should_skip_item

        Returns:
            Analysis result dictionary
        """
        result = {
            'item': item,
            'source_path': item_path,
            'destination_path': None,
            'action': None,
            'reason': None
        }

        # Check if should skip
        should_skip, reason = self.should_skip_item(item, item_path, **skip_options)

        if should_skip:
            result['action'] = 'skip'
            result['reason'] = reason
            return result

        # Generate destination
        destination_path = self.generate_destination_path(item, item_path)

        if not destination_path:
            result['action'] = 'skip'
            result['reason'] = 'no_date_field'
            return result

        result['destination_path'] = destination_path
        result['action'] = 'move'

        # Add category info if categorization is enabled
        if self.categorizer and '{category}' in self.folder_structure:
            result['category'] = self.categorizer.categorize(item, item_path)

        return result
