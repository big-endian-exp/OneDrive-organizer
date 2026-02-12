"""
Content-based file categorization using file names, types, and content analysis.
Intelligently categorizes files into Finance, Pictures, Government Documents, etc.
"""

import re
from typing import Dict, List, Optional, Set
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger()


class ContentCategorizer:
    """Categorize files based on content, file type, and name analysis."""

    def __init__(self, categories_config: Dict):
        """
        Initialize content categorizer.

        Args:
            categories_config: Configuration dictionary with category definitions
        """
        self.categories_config = categories_config
        self.categories = self._load_categories()
        self.default_category = categories_config.get('default_category', 'Other')

        logger.debug(f"Content categorizer initialized with {len(self.categories)} categories")

    def _load_categories(self) -> Dict[str, Dict]:
        """
        Load category definitions from config.

        Returns:
            Dictionary of category definitions
        """
        categories = {}

        for category_name, category_def in self.categories_config.get('definitions', {}).items():
            categories[category_name] = {
                'keywords': [kw.lower() for kw in category_def.get('keywords', [])],
                'extensions': [ext.lower() for ext in category_def.get('extensions', [])],
                'patterns': [re.compile(pattern, re.IGNORECASE)
                           for pattern in category_def.get('patterns', [])],
                'priority': category_def.get('priority', 50)  # Higher priority = checked first
            }

        return categories

    def categorize(self, item: Dict, item_path: str) -> str:
        """
        Categorize a file based on its properties.

        Args:
            item: Item dictionary from OneDrive API
            item_path: Full path to the item

        Returns:
            Category name (e.g., "Finance", "Pictures", "Other")
        """
        file_name = item.get('name', '').lower()
        file_ext = Path(file_name).suffix.lower()

        # Score each category
        category_scores = {}

        for category_name, category_def in self.categories.items():
            score = 0

            # Check file extension (highest confidence)
            if file_ext in category_def['extensions']:
                score += 100

            # Check filename keywords
            for keyword in category_def['keywords']:
                if keyword in file_name or keyword in item_path.lower():
                    score += 50

            # Check regex patterns
            for pattern in category_def['patterns']:
                if pattern.search(file_name) or pattern.search(item_path):
                    score += 75

            # Apply priority multiplier
            score = score * (category_def['priority'] / 50.0)

            if score > 0:
                category_scores[category_name] = score

        # Return category with highest score
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
            logger.debug(f"Categorized '{file_name}' as '{best_category}' (score: {category_scores[best_category]})")
            return best_category

        logger.debug(f"Categorized '{file_name}' as '{self.default_category}' (no matches)")
        return self.default_category

    def get_category_statistics(self, items: List[Dict]) -> Dict[str, int]:
        """
        Get statistics on how many files fall into each category.

        Args:
            items: List of items to analyze

        Returns:
            Dictionary mapping category names to file counts
        """
        stats = {category: 0 for category in self.categories.keys()}
        stats[self.default_category] = 0

        for item_data in items:
            if 'file' not in item_data.get('item', {}):
                continue  # Skip folders

            category = self.categorize(
                item_data.get('item', {}),
                item_data.get('path', '')
            )
            stats[category] = stats.get(category, 0) + 1

        return stats

    def suggest_categories(self, sample_files: List[str]) -> List[str]:
        """
        Analyze sample filenames and suggest potential new categories.

        Args:
            sample_files: List of filenames to analyze

        Returns:
            List of suggested category keywords
        """
        # Extract common words from filenames
        word_frequency = {}

        for filename in sample_files:
            # Remove extension and split into words
            name_without_ext = Path(filename).stem.lower()
            words = re.findall(r'\b[a-z]{4,}\b', name_without_ext)

            for word in words:
                word_frequency[word] = word_frequency.get(word, 0) + 1

        # Suggest words that appear frequently
        suggestions = [
            word for word, count in word_frequency.items()
            if count >= max(3, len(sample_files) * 0.1)  # At least 3 times or 10% of files
        ]

        return sorted(suggestions, key=lambda w: word_frequency[w], reverse=True)[:10]


def create_default_categories() -> Dict:
    """
    Create default category definitions.

    Returns:
        Dictionary of default categories
    """
    return {
        'default_category': 'Other',
        'definitions': {
            'Finance': {
                'keywords': [
                    'invoice', 'receipt', 'bill', 'payment', 'transaction',
                    'bank', 'statement', 'tax', 'expense', 'budget',
                    'payroll', 'salary', 'credit', 'debit', 'financial',
                    'accounting', 'quickbooks', 'mint', 'venmo', 'paypal'
                ],
                'extensions': [],
                'patterns': [
                    r'\d{4}[-_]?\d{2}[-_]?\d{2}.*(?:invoice|receipt|bill)',
                    r'(?:USD|EUR|GBP|\$)\s*\d+',
                ],
                'priority': 60
            },
            'Pictures': {
                'keywords': [
                    'photo', 'image', 'picture', 'img', 'pic',
                    'camera', 'screenshot', 'wallpaper', 'avatar'
                ],
                'extensions': [
                    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
                    '.heic', '.webp', '.svg', '.raw', '.cr2', '.nef'
                ],
                'patterns': [
                    r'IMG_\d+',
                    r'DSC\d+',
                    r'DCIM',
                    r'\d{8}_\d{6}'  # YYYYMMDD_HHMMSS
                ],
                'priority': 70
            },
            'Videos': {
                'keywords': [
                    'video', 'movie', 'film', 'clip', 'recording'
                ],
                'extensions': [
                    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',
                    '.webm', '.m4v', '.mpg', '.mpeg'
                ],
                'patterns': [
                    r'VID_\d+',
                ],
                'priority': 70
            },
            'Traffic_Tickets': {
                'keywords': [
                    'ticket', 'citation', 'violation', 'speeding', 'parking',
                    'traffic', 'fine', 'dmv', 'vehicle', 'court'
                ],
                'extensions': [],
                'patterns': [
                    r'ticket.*\d+',
                    r'citation.*\d+',
                    r'violation.*\d+',
                ],
                'priority': 80  # High priority for specific documents
            },
            'Government_Documents': {
                'keywords': [
                    'passport', 'license', 'ssn', 'birth certificate',
                    'marriage', 'divorce', 'deed', 'title', 'registration',
                    'visa', 'permit', 'tax return', 'w2', 'w-2', '1099',
                    'social security', 'medicare', 'voter', 'legal',
                    'court', 'contract', 'government', 'official',
                    'dmv', 'irs', 'state', 'federal'
                ],
                'extensions': [],
                'patterns': [
                    r'w[-_]?2',
                    r'1099',
                    r'tax.*return',
                    r'form.*\d+',
                ],
                'priority': 90  # Highest priority for important docs
            },
            'Medical': {
                'keywords': [
                    'medical', 'health', 'doctor', 'hospital', 'prescription',
                    'insurance', 'claim', 'diagnosis', 'lab', 'results',
                    'appointment', 'vaccine', 'immunization', 'patient',
                    'medication', 'pharmacy', 'eob', 'billing'
                ],
                'extensions': [],
                'patterns': [
                    r'medical.*record',
                    r'lab.*result',
                ],
                'priority': 75
            },
            'Insurance': {
                'keywords': [
                    'insurance', 'policy', 'coverage', 'claim', 'premium',
                    'deductible', 'beneficiary', 'auto insurance',
                    'home insurance', 'life insurance', 'health insurance'
                ],
                'extensions': [],
                'patterns': [
                    r'policy.*\d+',
                    r'claim.*\d+',
                ],
                'priority': 75
            },
            'Work': {
                'keywords': [
                    'work', 'project', 'presentation', 'meeting', 'report',
                    'proposal', 'contract', 'agreement', 'memo', 'employee',
                    'employer', 'job', 'resume', 'cv', 'offer letter'
                ],
                'extensions': [
                    '.pptx', '.ppt', '.xlsx', '.xls', '.docx', '.doc'
                ],
                'patterns': [],
                'priority': 55
            },
            'Education': {
                'keywords': [
                    'school', 'university', 'college', 'course', 'homework',
                    'assignment', 'lecture', 'notes', 'syllabus', 'grade',
                    'transcript', 'diploma', 'degree', 'certificate',
                    'student', 'textbook', 'exam', 'test', 'quiz'
                ],
                'extensions': [],
                'patterns': [],
                'priority': 60
            },
            'Personal': {
                'keywords': [
                    'personal', 'private', 'family', 'journal', 'diary',
                    'letter', 'card', 'note', 'memory', 'keepsake'
                ],
                'extensions': [],
                'patterns': [],
                'priority': 50
            },
            'Travel': {
                'keywords': [
                    'travel', 'trip', 'vacation', 'hotel', 'flight',
                    'booking', 'reservation', 'itinerary', 'boarding pass',
                    'passport', 'visa', 'destination', 'tour', 'ticket'
                ],
                'extensions': [],
                'patterns': [
                    r'booking.*\d+',
                    r'confirmation.*\d+',
                ],
                'priority': 65
            },
            'Utilities': {
                'keywords': [
                    'utility', 'electric', 'gas', 'water', 'internet',
                    'phone', 'cable', 'bill', 'pg&e', 'comcast', 'att',
                    'verizon', 'spectrum'
                ],
                'extensions': [],
                'patterns': [],
                'priority': 60
            },
            'Real_Estate': {
                'keywords': [
                    'property', 'house', 'apartment', 'lease', 'rent',
                    'mortgage', 'deed', 'title', 'closing', 'escrow',
                    'inspection', 'appraisal', 'real estate', 'realtor',
                    'landlord', 'tenant'
                ],
                'extensions': [],
                'patterns': [],
                'priority': 70
            }
        }
    }
