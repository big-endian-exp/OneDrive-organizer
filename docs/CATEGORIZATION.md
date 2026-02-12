# Content-Based Categorization Guide

The OneDrive Organizer now includes intelligent content-based categorization that organizes files first by category, then by timeline.

## How It Works

The categorizer analyzes each file using:
1. **File extensions** (e.g., .jpg, .mp4, .pdf)
2. **Filename keywords** (e.g., "invoice", "receipt", "photo")
3. **Path keywords** (folder names containing category hints)
4. **Regex patterns** (e.g., detecting invoice numbers, dates)

Each category has a priority score. Files matching multiple categories are assigned to the highest-scoring match.

## Folder Structure

With categorization enabled, files are organized as:

```
OneDrive/
└── Organized/
    ├── Finance/
    │   ├── 2024/
    │   │   ├── 01_January/
    │   │   │   ├── invoice-2024-01-15.pdf
    │   │   │   └── receipt-groceries.pdf
    │   │   └── 02_February/
    │   └── 2025/
    ├── Pictures/
    │   ├── 2023/
    │   │   └── 07_July/
    │   │       ├── IMG_1234.jpg
    │   │       └── vacation.png
    │   └── 2024/
    ├── Traffic_Tickets/
    │   └── 2024/
    │       └── 03_March/
    │           └── speeding-ticket-2024.pdf
    ├── Government_Documents/
    │   └── 2024/
    │       └── 01_January/
    │           ├── tax-return-2023.pdf
    │           └── w2-form.pdf
    └── Other/
        └── 2024/
            └── 12_December/
                └── misc-file.txt
```

## Built-in Categories

### Finance
**Keywords:** invoice, receipt, bill, payment, transaction, bank, statement, tax, expense, budget, payroll, salary, quickbooks
**Patterns:** Date-based invoice numbers
**Priority:** 60

### Pictures
**Keywords:** photo, image, picture, img, screenshot
**Extensions:** .jpg, .jpeg, .png, .gif, .bmp, .heic, .webp
**Patterns:** IMG_####, DSC####
**Priority:** 70

### Videos
**Keywords:** video, movie, clip, recording
**Extensions:** .mp4, .avi, .mov, .mkv, .webm
**Patterns:** VID_####
**Priority:** 70

### Traffic_Tickets
**Keywords:** ticket, citation, violation, speeding, parking, traffic, fine
**Patterns:** ticket-####, citation-####
**Priority:** 80 (high priority for important docs)

### Government_Documents
**Keywords:** passport, license, ssn, birth certificate, tax return, w2, 1099, social security, legal, dmv, irs
**Patterns:** w2, w-2, 1099, tax return patterns
**Priority:** 90 (highest priority)

### Medical
**Keywords:** medical, health, doctor, hospital, prescription, insurance claim, lab results, vaccine
**Patterns:** medical record, lab result
**Priority:** 75

### Insurance
**Keywords:** insurance, policy, coverage, claim, premium
**Patterns:** policy-####, claim-####
**Priority:** 75

### Work
**Keywords:** work, project, presentation, meeting, report, proposal, resume, cv
**Extensions:** .pptx, .ppt, .xlsx, .xls, .docx, .doc
**Priority:** 55

### Education
**Keywords:** school, university, course, homework, assignment, syllabus, transcript, diploma
**Priority:** 60

### Travel
**Keywords:** travel, trip, vacation, hotel, flight, booking, itinerary, boarding pass
**Patterns:** booking-####, confirmation-####
**Priority:** 65

### Utilities
**Keywords:** utility, electric, gas, water, internet, phone bill
**Priority:** 60

### Real_Estate
**Keywords:** property, house, lease, rent, mortgage, deed, real estate
**Priority:** 70

### Other
Default category for files that don't match any rules.

## Configuration

### Enable/Disable Categorization

Edit `config/config.yaml`:

```yaml
# Change folder_structure to include {category}
organization:
  folder_structure: "{category}/{year}/{month}"

# Enable categorization
categorization:
  enabled: true
  default_category: "Other"
```

### Disable Categorization

```yaml
# Remove {category} from folder_structure
organization:
  folder_structure: "{year}/{month}"

# Disable categorization
categorization:
  enabled: false
```

## Customizing Categories

### Add Keywords to Existing Category

Edit `config/config.yaml`:

```yaml
categorization:
  definitions:
    Finance:
      keywords:
        - invoice
        - receipt
        - venmo      # Add new keyword
        - paypal     # Add new keyword
```

### Create New Category

```yaml
categorization:
  definitions:
    # ... existing categories ...

    Recipes:
      keywords:
        - recipe
        - cooking
        - food
        - ingredient
      extensions:
        - .recipe
      patterns:
        - 'recipe.*\d+'
      priority: 60
```

### Adjust Category Priority

Higher priority = checked first, wins ties:

```yaml
categorization:
  definitions:
    Finance:
      priority: 90  # Increase from 60 to make Finance win over other matches
```

### Add File Extensions

```yaml
categorization:
  definitions:
    Pictures:
      extensions:
        - .jpg
        - .png
        - .dng      # Add RAW format
        - .arw      # Add Sony RAW
```

### Add Regex Patterns

Patterns use Python regex syntax (case-insensitive):

```yaml
categorization:
  definitions:
    Finance:
      patterns:
        - '\d{4}[-_]?\d{2}[-_]?\d{2}.*invoice'  # YYYY-MM-DD-invoice
        - 'INV[-_]?\d{5,}'                        # INV-12345
```

## How Categorization Works

### Scoring System

For each file, the categorizer:
1. Checks file extension: +100 points if matched
2. Checks filename for keywords: +50 points per keyword
3. Checks regex patterns: +75 points per pattern match
4. Multiplies score by `(priority / 50)`
5. Assigns file to highest-scoring category

### Examples

**File:** `invoice-2024-01-15.pdf`
- Finance: keyword "invoice" (50) × priority (60/50) = 60 points
- Result: **Finance**

**File:** `IMG_1234.jpg`
- Pictures: extension .jpg (100) + pattern IMG_#### (75) × priority (70/50) = 245 points
- Result: **Pictures**

**File:** `speeding-ticket-2024-03.pdf`
- Traffic_Tickets: keywords "speeding" + "ticket" (100) + pattern ticket-#### (75) × priority (80/50) = 280 points
- Result: **Traffic_Tickets**

**File:** `random-file.txt`
- No matches
- Result: **Other** (default category)

## Testing Categorization

### Dry-Run with Categories

```bash
python src/main.py --dry-run
```

Output will show:
```
Analysis complete:
  Files to move: 500
  Category breakdown:
    Pictures: 215
    Finance: 87
    Work: 45
    Government_Documents: 23
    Other: 130
```

### Category-Specific Dry-Run

To see which files go to a specific category, check the logs:

```bash
tail -f data/logs/organizer.log | grep "Categorized"
```

Output:
```
Categorized 'invoice.pdf' as 'Finance' (score: 60)
Categorized 'IMG_1234.jpg' as 'Pictures' (score: 245)
Categorized 'ticket.pdf' as 'Traffic_Tickets' (score: 280)
```

## Migration from Date-Only to Category-Based

If you already organized files by date-only and want to add categories:

### Option 1: Fresh Start (Recommended)

1. **Backup current organization:**
   - Your files are safe in OneDrive
   - Previous "Organized" folder remains

2. **Update config:**
   ```yaml
   organization:
     folder_structure: "{category}/{year}/{month}"
   categorization:
     enabled: true
   ```

3. **Reorganize:**
   ```bash
   python src/main.py --organize
   ```

   Files will be moved into new category-based structure.

### Option 2: Keep Both Structures

1. **Change destination root:**
   ```yaml
   organization:
     destination_root: "Organized_By_Category"
     folder_structure: "{category}/{year}/{month}"
   ```

2. **Run organizer:**
   ```bash
   python src/main.py --organize
   ```

   This creates a new parallel structure without touching existing organization.

## Troubleshooting

### Files Going to Wrong Category

**Check category rules:**
1. Review filename and keywords
2. Check if multiple categories match (highest priority wins)
3. Adjust priority or add more specific keywords

**Example:** File "bank-statement.pdf" goes to "Work" instead of "Finance"
- Add "bank" keyword to Finance category
- Or increase Finance priority

### Too Many Files in "Other"

**Common causes:**
1. Filenames don't contain category keywords
2. File extensions not mapped to categories
3. Need to add custom categories

**Solutions:**
1. Add more keywords to existing categories
2. Create custom categories for your file types
3. Check logs to see why files aren't matching:
   ```bash
   grep "Categorized.*'Other'" data/logs/organizer.log
   ```

### Files Matching Multiple Categories

**By design:** Highest-scoring category wins

**To control:**
1. Adjust priorities (higher = wins ties)
2. Make keywords more specific
3. Use regex patterns for precise matching

**Example:** "work-invoice.pdf" matches both Work and Finance
- Finance has higher priority (60 vs 55)
- Result: Goes to Finance ✓

## Best Practices

1. **Start with dry-run:** Always test categorization before organizing
2. **Review category breakdown:** Check the statistics to ensure distribution makes sense
3. **Adjust gradually:** Add keywords/categories incrementally
4. **Use priority wisely:** Reserve high priorities (80+) for critical documents
5. **Keep default category:** "Other" catches anything that doesn't fit

## Advanced: Suggest New Categories

The categorizer can analyze your files and suggest new categories:

```python
from src.organizer.content_categorizer import ContentCategorizer

# Sample your filenames
filenames = [
    "recipe-pasta.pdf",
    "recipe-soup.txt",
    "cooking-notes.docx",
    # ... more files
]

# Get suggestions
cat_config = config['categorization']
categorizer = ContentCategorizer(cat_config)
suggestions = categorizer.suggest_categories(filenames)

print("Suggested category keywords:", suggestions)
# Output: ['recipe', 'cooking', 'food', 'ingredient']
```

Use these suggestions to create new categories!

## Summary

- ✅ Automatic categorization based on content, name, and type
- ✅ 13 built-in categories + customizable
- ✅ Priority-based scoring system
- ✅ Category statistics in reports
- ✅ Easy to customize and extend
- ✅ Works alongside timeline organization

For more help, see:
- `README.md` - Main documentation
- `SETUP.md` - Initial setup guide
- `config/config.yaml` - Configuration file with all categories
