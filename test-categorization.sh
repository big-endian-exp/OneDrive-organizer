#!/bin/bash
# Test script to verify categorization is working

cd /Users/amritshandilya/My_Agents/onedrive_organizer
source venv/bin/activate

echo "Testing categorization feature..."
echo ""
echo "Current configuration:"
grep -A 2 "folder_structure:" config/config.yaml
echo ""
grep -A 2 "categorization:" config/config.yaml
echo ""
echo "Running dry-run to test categorization..."
echo "Look for 'Category breakdown' in the output"
echo ""

python src/main.py --dry-run 2>&1 | grep -A 20 "Category breakdown"

