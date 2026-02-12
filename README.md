# OneDrive Personal Organization Agent

Automatically organize your OneDrive files by date with scheduled automation.

## Features

- **Automatic Organization**: Organize files by year/month (or custom date structure)
- **Scheduled Automation**: Run periodically using cron-style scheduling
- **Safe Operations**: Dry-run mode, operation history, and undo capability
- **Flexible Configuration**: Customize filters, date fields, and folder structures
- **Secure Authentication**: OAuth2 with encrypted token storage
- **Smart Filtering**: Skip already-organized files, exclude extensions, set minimum age

## Quick Start

### 1. Install Dependencies

```bash
cd onedrive_organizer
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Up Azure AD Application

See [API_REGISTRATION.md](docs/API_REGISTRATION.md) for detailed instructions.

1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory → App Registrations
2. Create new registration for personal Microsoft accounts
3. Add API permissions: `Files.ReadWrite.All`, `User.Read`
4. Copy the Client ID

### 3. Configure

```bash
# Copy environment template
cp config/.env.example .env

# Edit .env and add your CLIENT_ID
nano .env

# Customize config.yaml if needed
nano config/config.yaml
```

### 4. Authenticate

```bash
python src/main.py --authenticate
```

Follow the device code instructions to sign in.

### 5. Test with Dry Run

```bash
python src/main.py --dry-run
```

This will show what changes would be made without actually moving files.

### 6. Organize Files

```bash
python src/main.py --organize
```

Confirm when prompted, and files will be organized into year/month structure.

## Usage

### Commands

```bash
# Authenticate with OneDrive
python src/main.py --authenticate

# Preview changes (no actual moves)
python src/main.py --dry-run

# Organize files
python src/main.py --organize

# Run as scheduled daemon
python src/main.py --daemon

# Undo a previous operation
python src/main.py --undo OPERATION_ID

# List operation history
python src/main.py --history
```

### Configuration

Edit `config/config.yaml` to customize:

- **Organization**:
  - `source_folder`: Folder to organize (empty = root)
  - `destination_root`: Where to create organized structure
  - `date_field`: Use creation or modification date
  - `folder_structure`: Pattern like `{year}/{month}`

- **Filters**:
  - `skip_already_organized`: Don't reorganize existing structure
  - `exclude_extensions`: Skip certain file types
  - `min_age_days`: Only organize older files

- **Safety**:
  - `dry_run_default`: Safe mode by default
  - `require_confirmation`: Ask before moving files
  - `max_files_per_run`: Limit batch size

- **Scheduling**:
  - `enabled`: Enable scheduled automation
  - `schedule`: Cron schedule (e.g., "0 2 * * 0" = 2 AM Sundays)
  - `timezone`: Schedule timezone

## File Organization

Files are organized using this structure:

```
OneDrive/
└── Organized/
    ├── 2024/
    │   ├── 01_January/
    │   │   ├── document1.pdf
    │   │   └── photo1.jpg
    │   ├── 02_February/
    │   │   └── document2.pdf
    │   └── ...
    └── 2025/
        └── ...
```

The structure is configurable via `folder_structure` pattern:
- `{year}` → "2024"
- `{month}` → "01_January"
- `{day}` → "15"
- `{quarter}` → "Q1"

## Safety Features

1. **Dry-Run Mode**: Preview all changes before execution
2. **Operation History**: Every operation is logged
3. **Undo Capability**: Reverse any operation
4. **Confirmation Prompts**: Prevent accidental moves
5. **Encrypted Token Storage**: Secure credentials
6. **Batch Limits**: Prevent mass operations

## Scheduling

To run automatically:

1. Edit `config/config.yaml`:
   ```yaml
   scheduling:
     enabled: true
     schedule: "0 2 * * 0"  # 2 AM every Sunday
     timezone: "America/Los_Angeles"
   ```

2. Run daemon:
   ```bash
   python src/main.py --daemon
   ```

### Cron Schedule Examples

- `"0 2 * * 0"` → 2 AM every Sunday
- `"0 2 * * *"` → 2 AM every day
- `"0 */6 * * *"` → Every 6 hours
- `"0 0 1 * *"` → Midnight on 1st of every month

## Troubleshooting

### Authentication Issues

```bash
# Re-authenticate
python src/main.py --authenticate

# Check token
ls -la data/tokens/
```

### Files Not Moving

- Check `dry_run_default` in config.yaml
- Verify `skip_already_organized` setting
- Check `exclude_extensions` filter
- Review `min_age_days` setting

### Permission Errors

Ensure Azure AD app has:
- `Files.ReadWrite.All` (delegated)
- `User.Read` (delegated)

## Development

### Project Structure

```
onedrive_organizer/
├── src/
│   ├── auth/           # OAuth2 authentication
│   ├── api/            # Graph API client
│   ├── organizer/      # Organization logic
│   ├── scheduler/      # Task scheduling
│   ├── utils/          # Utilities
│   └── main.py         # Entry point
├── config/             # Configuration files
├── data/               # Runtime data (tokens, logs, history)
├── tests/              # Unit tests
└── docs/               # Documentation
```

### Running Tests

```bash
pytest tests/ -v --cov=src
```

## Security

- Tokens are encrypted at rest using Fernet (AES)
- Token files have 600 permissions (owner read/write only)
- No credentials stored in code or config files
- Environment variables for sensitive data

## Documentation

- [SETUP.md](docs/SETUP.md) - Detailed setup instructions
- [API_REGISTRATION.md](docs/API_REGISTRATION.md) - Azure AD app registration guide

## License

MIT License

## Support

For issues and questions:
1. Check documentation in `docs/`
2. Review logs in `data/logs/organizer.log`
3. Run with `--dry-run` to diagnose issues

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request
