#!/usr/bin/env python3
"""
OneDrive Personal Organization Agent
Main entry point for the application.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth.oauth_handler import OAuthHandler
from src.auth.token_manager import TokenManager
from src.api.graph_client import GraphClient
from src.api.onedrive_operations import OneDriveOperations
from src.organizer.organizer_engine import OrganizerEngine
from src.organizer.history_manager import HistoryManager
from src.scheduler.task_scheduler import TaskScheduler, run_scheduled_task
from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger, get_logger


def authenticate_command(config: dict) -> None:
    """
    Run authentication flow.

    Args:
        config: Configuration dictionary
    """
    logger = get_logger()
    logger.info("Starting authentication...")

    auth_config = config['authentication']

    oauth_handler = OAuthHandler(
        client_id=auth_config['client_id'],
        tenant_id=auth_config['tenant_id'],
        scopes=auth_config['scopes']
    )

    token_manager = TokenManager()

    # Attempt device code flow
    try:
        token_data = oauth_handler.authenticate_device_code()
        token_manager.save_token(token_data)

        logger.info("Authentication successful!")
        logger.info("Token saved securely.")

        # Test token by getting user info
        graph_client = GraphClient(token_data['access_token'])
        user_info = graph_client.get_user_info()

        logger.info(f"Authenticated as: {user_info.get('displayName')} ({user_info.get('userPrincipalName')})")

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        sys.exit(1)


def organize_command(config: dict, dry_run: bool = False) -> dict:
    """
    Run organization process.

    Args:
        config: Configuration dictionary
        dry_run: If True, simulate without making changes

    Returns:
        Operation result dictionary
    """
    logger = get_logger()

    # Get or refresh token
    auth_config = config['authentication']
    oauth_handler = OAuthHandler(
        client_id=auth_config['client_id'],
        tenant_id=auth_config['tenant_id'],
        scopes=auth_config['scopes']
    )

    token_manager = TokenManager()

    try:
        access_token = token_manager.get_valid_token(oauth_handler)

        if not access_token:
            logger.error("No valid token found. Please run --authenticate first.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Failed to get valid token: {e}")
        logger.info("Please run --authenticate to re-authenticate.")
        sys.exit(1)

    # Initialize API client
    graph_client = GraphClient(access_token)
    onedrive_ops = OneDriveOperations(graph_client)

    # Initialize organizer engine
    engine = OrganizerEngine(onedrive_ops, config)

    # Get organization settings
    org_config = config.get('organization', {})
    safety_config = org_config.get('safety', {})

    source_folder = org_config.get('source_folder', '')
    max_files = safety_config.get('max_files_per_run')
    require_confirmation = safety_config.get('require_confirmation', True)

    # Confirmation prompt (if not dry-run and confirmation required)
    if not dry_run and require_confirmation:
        print("\n" + "=" * 60)
        print("WARNING: This will move files in your OneDrive!")
        print("=" * 60)
        print(f"Source folder: '{source_folder or 'root'}'")
        print(f"Max files per run: {max_files or 'unlimited'}")
        print("\nAre you sure you want to proceed? (yes/no): ", end='')

        response = input().strip().lower()

        if response not in ['yes', 'y']:
            logger.info("Operation cancelled by user")
            sys.exit(0)

    # Run organization
    result = engine.organize(
        source_folder=source_folder,
        dry_run=dry_run,
        max_files=max_files
    )

    # Save to history (if not dry-run)
    if not dry_run and result.get('status') == 'success':
        history_manager = HistoryManager()
        operation_id = history_manager.save_operation(result)
        logger.info(f"Operation saved to history: {operation_id}")
        logger.info(f"To undo this operation, run: python src/main.py --undo {operation_id}")

    return result


def undo_command(config: dict, operation_id: str) -> None:
    """
    Undo a previous operation.

    Args:
        config: Configuration dictionary
        operation_id: Operation ID to undo
    """
    logger = get_logger()
    logger.info(f"Attempting to undo operation: {operation_id}")

    history_manager = HistoryManager()

    # Check if can undo
    can_undo, reason = history_manager.can_undo(operation_id)

    if not can_undo:
        logger.error(f"Cannot undo operation: {reason}")
        sys.exit(1)

    # Get undo plan
    undo_plan = history_manager.create_undo_plan(operation_id)

    if not undo_plan:
        logger.error("Failed to create undo plan")
        sys.exit(1)

    logger.info(f"Undo plan created: {len(undo_plan)} operations")

    # Confirmation
    print("\n" + "=" * 60)
    print(f"UNDO OPERATION: {operation_id}")
    print("=" * 60)
    print(f"This will reverse {len(undo_plan)} file moves")
    print("\nAre you sure you want to proceed? (yes/no): ", end='')

    response = input().strip().lower()

    if response not in ['yes', 'y']:
        logger.info("Undo cancelled by user")
        sys.exit(0)

    # Get token and initialize API
    auth_config = config['authentication']
    oauth_handler = OAuthHandler(
        client_id=auth_config['client_id'],
        tenant_id=auth_config['tenant_id'],
        scopes=auth_config['scopes']
    )

    token_manager = TokenManager()
    access_token = token_manager.get_valid_token(oauth_handler)

    if not access_token:
        logger.error("No valid token found. Please run --authenticate first.")
        sys.exit(1)

    graph_client = GraphClient(access_token)
    onedrive_ops = OneDriveOperations(graph_client)

    # Execute undo
    logger.info("Executing undo operations...")

    success_count = 0
    failed_count = 0

    for i, undo_op in enumerate(undo_plan, 1):
        logger.info(f"[{i}/{len(undo_plan)}] Reverting: {undo_op['current_name']}")

        try:
            # Parse original path to get parent folder and name
            original_path = undo_op['original_path']
            parts = original_path.rsplit('/', 1)

            if len(parts) == 2:
                parent_folder, original_name = parts
            else:
                parent_folder = ""
                original_name = parts[0]

            # Get parent folder
            if parent_folder:
                parent = onedrive_ops.get_item_by_path(parent_folder)
            else:
                parent = graph_client.get("/me/drive/root")

            # Move back
            onedrive_ops.move_item(
                item_id=undo_op['item_id'],
                destination_folder_id=parent['id'],
                new_name=original_name if undo_op['current_name'] != original_name else None
            )

            logger.info("  ✓ Reverted successfully")
            success_count += 1

        except Exception as e:
            logger.error(f"  ✗ Failed to revert: {e}")
            failed_count += 1

    logger.info("=" * 60)
    logger.info(f"Undo complete: {success_count} succeeded, {failed_count} failed")
    logger.info("=" * 60)


def daemon_command(config: dict) -> None:
    """
    Run as daemon with scheduling.

    Args:
        config: Configuration dictionary
    """
    logger = get_logger()

    schedule_config = config.get('scheduling', {})

    if not schedule_config.get('enabled', False):
        logger.error("Scheduling is not enabled in config.yaml")
        logger.info("Set scheduling.enabled = true to use daemon mode")
        sys.exit(1)

    schedule = schedule_config.get('schedule', '0 2 * * 0')
    timezone = schedule_config.get('timezone', 'UTC')

    logger.info("Starting daemon mode...")
    logger.info(f"Schedule: {schedule} ({timezone})")

    scheduler = TaskScheduler(schedule=schedule, timezone=timezone)

    # Get organization settings
    org_config = config.get('organization', {})
    dry_run = org_config.get('safety', {}).get('dry_run_default', False)

    # Add job
    scheduler.add_job(
        func=run_scheduled_task,
        job_id="organize_task",
        organize_func=lambda **kwargs: organize_command(config, dry_run=dry_run),
    )

    # Start scheduler (blocking)
    scheduler.start()


def list_history_command() -> None:
    """List operation history."""
    logger = get_logger()

    history_manager = HistoryManager()
    operations = history_manager.list_operations(limit=20)

    if not operations:
        logger.info("No operations in history")
        return

    print("\n" + "=" * 60)
    print("OPERATION HISTORY (last 20)")
    print("=" * 60)

    for op in operations:
        timestamp = op['timestamp'][:19].replace('T', ' ')
        status = "DRY RUN" if op['dry_run'] else "LIVE"

        print(f"\nOperation ID: {op['operation_id']}")
        print(f"  Timestamp:    {timestamp}")
        print(f"  Mode:         {status}")
        print(f"  Files moved:  {op['files_moved']}")
        print(f"  Files failed: {op['files_failed']}")

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OneDrive Personal Organization Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--authenticate',
        action='store_true',
        help='Run OAuth authentication flow'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without actually moving files'
    )

    parser.add_argument(
        '--organize',
        action='store_true',
        help='Run organization process'
    )

    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as daemon with scheduling'
    )

    parser.add_argument(
        '--undo',
        type=str,
        metavar='OPERATION_ID',
        help='Undo a previous operation'
    )

    parser.add_argument(
        '--history',
        action='store_true',
        help='List operation history'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Path to configuration file'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config_loader = ConfigLoader(args.config)
        config = config_loader.load()
        config_loader.validate()
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Set up logging
    log_config = config.get('logging', {})
    setup_logger(
        level=log_config.get('level', 'INFO'),
        log_to_file=log_config.get('log_to_file', True),
        log_file=log_config.get('log_file')
    )

    # Execute command
    try:
        if args.authenticate:
            authenticate_command(config)

        elif args.organize or args.dry_run:
            # Determine dry-run mode
            dry_run = args.dry_run
            if not dry_run:
                # Check config default
                dry_run = config.get('organization', {}).get('safety', {}).get('dry_run_default', True)

            organize_command(config, dry_run=dry_run)

        elif args.undo:
            undo_command(config, args.undo)

        elif args.daemon:
            daemon_command(config)

        elif args.history:
            list_history_command()

        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)

    except Exception as e:
        logger = get_logger()
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
