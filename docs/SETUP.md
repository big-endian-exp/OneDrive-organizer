# OneDrive Organizer - Detailed Setup Guide

This guide walks you through setting up the OneDrive Personal Organization Agent step-by-step.

## Prerequisites

- Python 3.8 or higher
- Personal Microsoft account with OneDrive
- Azure AD account (free, can use same Microsoft account)
- macOS, Linux, or Windows

## Step-by-Step Setup

### 1. Verify Python Installation

```bash
python3 --version
# Should show Python 3.8 or higher
```

If Python is not installed:
- **macOS**: `brew install python3`
- **Linux**: `sudo apt-get install python3 python3-pip python3-venv`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

### 2. Set Up Project

```bash
# Navigate to the project directory
cd /Users/amritshandilya/My_Agents/onedrive_organizer

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Verify activation (prompt should show "(venv)")
```

### 3. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list | grep msal
# Should show: msal 1.24.0 or higher
```

If installation fails:
```bash
# Update pip first
pip install --upgrade pip

# Try again
pip install -r requirements.txt
```

### 4. Register Azure AD Application

See [API_REGISTRATION.md](API_REGISTRATION.md) for detailed instructions.

**Quick Steps**:
1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to Azure Active Directory → App Registrations
3. Click "New registration"
4. Set up as described in API_REGISTRATION.md
5. Copy the Client ID

### 5. Configure Environment Variables

```bash
# Copy template
cp config/.env.example .env

# Edit .env file
nano .env
# or
code .env
# or
vim .env
```

Add your Client ID:
```
CLIENT_ID=your_actual_client_id_here
```

**Security Note**: Never commit .env to version control! It's already in .gitignore.

### 6. Customize Configuration (Optional)

Edit `config/config.yaml` to customize behavior:

```bash
nano config/config.yaml
```

Key settings to review:

**Organization Strategy**:
```yaml
organization:
  source_folder: ""  # "" = organize entire OneDrive, or set specific folder
  destination_root: "Organized"  # Where organized files go
  date_field: "createdDateTime"  # or "lastModifiedDateTime"
  folder_structure: "{year}/{month}"  # Pattern for organization
```

**Safety Settings**:
```yaml
organization:
  safety:
    dry_run_default: true  # Safe by default
    require_confirmation: true  # Ask before moving
    max_files_per_run: 1000  # Batch limit
```

**Filters**:
```yaml
organization:
  filters:
    skip_already_organized: true  # Don't reorganize
    exclude_extensions:  # Skip these file types
      - ".tmp"
      - ".lock"
    min_age_days: 0  # Only organize files older than this
```

### 7. Authenticate with OneDrive

```bash
python src/main.py --authenticate
```

You'll see:
```
============================================================
DEVICE CODE AUTHENTICATION
============================================================
To sign in, use a web browser to open the page
https://microsoft.com/devicelogin and enter the code ABC123XYZ
to authenticate.
============================================================
```

**Steps**:
1. Open browser to https://microsoft.com/devicelogin
2. Enter the code shown
3. Sign in with your Microsoft account
4. Grant permissions when prompted
5. Return to terminal - should show "Authentication successful!"

**Verification**:
```bash
# Check token was saved
ls -la data/tokens/
# Should see: token.enc and key.key

# Verify permissions
stat -f "%A" data/tokens/token.enc  # macOS
# or
stat -c "%a" data/tokens/token.enc  # Linux
# Should show: 600
```

### 8. Test with Dry Run

```bash
python src/main.py --dry-run
```

This will:
1. Scan your OneDrive
2. Analyze files
3. Show what would be moved
4. **NOT** actually move anything

Review the output carefully:
```
============================================================
PHASE 1: DISCOVERY
============================================================
Scanning OneDrive folder: 'root'
Discovered 150 files

============================================================
PHASE 2: ANALYSIS
============================================================
Analyzing 150 items...
Analysis complete:
  Files to move: 145
  Files to skip: 5
  Skip reasons:
    already_organized: 3
    is_folder: 2

============================================================
PHASE 3: PLANNING
============================================================
Planning moves for 145 files...
Execution plan created:
  Total moves: 145
  Folders needed: 12
  Conflicts resolved: 0

============================================================
PHASE 4: EXECUTION (DRY RUN)
============================================================
Creating destination folders...
Moving 145 files...
[1/145] /document.pdf -> Organized/2024/01_January
...
```

### 9. Test with Small Batch (Recommended)

Before organizing your entire OneDrive, test with a small subset:

**Option A: Create Test Folder**

1. Create a folder in OneDrive called "Test_Organize"
2. Add a few test files to it
3. Update config.yaml:
   ```yaml
   organization:
     source_folder: "Test_Organize"
   ```
4. Run organizer:
   ```bash
   python src/main.py --organize
   ```

**Option B: Limit File Count**

Update config.yaml:
```yaml
organization:
  safety:
    max_files_per_run: 10  # Only process 10 files
```

Then run:
```bash
python src/main.py --organize
```

### 10. Full Organization

Once you're confident:

1. Update config.yaml (if you changed it for testing):
   ```yaml
   organization:
     source_folder: ""  # Organize entire OneDrive
     safety:
       max_files_per_run: 1000  # Reasonable batch size
   ```

2. Run organizer:
   ```bash
   python src/main.py --organize
   ```

3. Confirm when prompted

4. Monitor progress in terminal

5. Check logs:
   ```bash
   tail -f data/logs/organizer.log
   ```

### 11. Set Up Scheduling (Optional)

To run automatically on a schedule:

1. Edit config.yaml:
   ```yaml
   scheduling:
     enabled: true
     schedule: "0 2 * * 0"  # 2 AM every Sunday
     timezone: "America/Los_Angeles"  # Your timezone
   ```

2. Test scheduler:
   ```bash
   python src/main.py --daemon
   ```

3. For production, run as system service:

   **macOS (launchd)**:
   See [Running as Service](#running-as-service) section below

   **Linux (systemd)**:
   See [Running as Service](#running-as-service) section below

   **Windows (Task Scheduler)**:
   See [Running as Service](#running-as-service) section below

## Running as Service

### macOS (launchd)

Create `~/Library/LaunchAgents/com.onedrive.organizer.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.onedrive.organizer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/amritshandilya/My_Agents/onedrive_organizer/venv/bin/python</string>
        <string>/Users/amritshandilya/My_Agents/onedrive_organizer/src/main.py</string>
        <string>--daemon</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/amritshandilya/My_Agents/onedrive_organizer</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/amritshandilya/My_Agents/onedrive_organizer/data/logs/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/amritshandilya/My_Agents/onedrive_organizer/data/logs/daemon_error.log</string>
</dict>
</plist>
```

Load service:
```bash
launchctl load ~/Library/LaunchAgents/com.onedrive.organizer.plist
```

Manage service:
```bash
# Check status
launchctl list | grep onedrive

# Stop
launchctl unload ~/Library/LaunchAgents/com.onedrive.organizer.plist

# View logs
tail -f data/logs/daemon.log
```

### Linux (systemd)

Create `/etc/systemd/system/onedrive-organizer.service`:

```ini
[Unit]
Description=OneDrive Organization Agent
After=network.target

[Service]
Type=simple
User=amritshandilya
WorkingDirectory=/home/amritshandilya/My_Agents/onedrive_organizer
ExecStart=/home/amritshandilya/My_Agents/onedrive_organizer/venv/bin/python src/main.py --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable onedrive-organizer
sudo systemctl start onedrive-organizer
sudo systemctl status onedrive-organizer
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Name: "OneDrive Organizer"
4. Trigger: At startup
5. Action: Start a program
   - Program: `C:\Users\...\onedrive_organizer\venv\Scripts\python.exe`
   - Arguments: `src\main.py --daemon`
   - Start in: `C:\Users\...\onedrive_organizer`
6. Finish

## Verification Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed successfully
- [ ] Azure AD app registered
- [ ] Client ID added to .env
- [ ] Configuration customized in config.yaml
- [ ] Authentication successful
- [ ] Dry run completed without errors
- [ ] Test batch successful
- [ ] Logs generated in data/logs/
- [ ] Operation history saved in data/history/

## Troubleshooting

### "ModuleNotFoundError: No module named 'msal'"

Virtual environment not activated. Run:
```bash
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows
```

### "Environment variable 'CLIENT_ID' not found"

.env file not set up correctly. Ensure:
1. File is named `.env` (not `.env.txt`)
2. Contains: `CLIENT_ID=your_actual_client_id`
3. No spaces around `=`

### "Authentication failed: invalid_client"

Client ID is incorrect. Double-check:
1. Azure Portal → App Registrations → Your App → Overview
2. Copy "Application (client) ID"
3. Paste into .env

### "Permission denied" on token files

Fix permissions:
```bash
chmod 700 data/tokens
chmod 600 data/tokens/*
```

### Files not being organized

Check configuration:
- `dry_run_default: false` in config.yaml
- `skip_already_organized: true` might be filtering them
- `exclude_extensions` might be excluding file types
- `min_age_days` might be filtering recent files

## Next Steps

- Review [API_REGISTRATION.md](API_REGISTRATION.md) for Azure setup details
- Check [README.md](../README.md) for usage examples
- Explore configuration options in config.yaml
- Set up scheduling for automatic organization
- Monitor logs regularly: `tail -f data/logs/organizer.log`

## Support

If you encounter issues:
1. Check logs: `data/logs/organizer.log`
2. Run with dry-run first: `--dry-run`
3. Verify token: `ls -la data/tokens/`
4. Re-authenticate if needed: `--authenticate`
