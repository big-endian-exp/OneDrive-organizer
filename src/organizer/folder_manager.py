"""
Folder structure management for organized files.
"""

from typing import Dict, Set
from ..api.onedrive_operations import OneDriveOperations
from ..utils.logger import get_logger

logger = get_logger()


class FolderManager:
    """Manage folder structure creation."""

    def __init__(self, onedrive_ops: OneDriveOperations):
        """
        Initialize folder manager.

        Args:
            onedrive_ops: OneDriveOperations instance
        """
        self.onedrive_ops = onedrive_ops
        self.created_folders: Set[str] = set()
        self.folder_cache: Dict[str, Dict] = {}

    def ensure_folder_exists(self, folder_path: str, dry_run: bool = False) -> Dict:
        """
        Ensure folder exists, creating if necessary.

        Args:
            folder_path: Full folder path
            dry_run: If True, don't actually create folders

        Returns:
            Folder dictionary (or mock in dry-run mode)
        """
        # Check cache first
        if folder_path in self.folder_cache:
            logger.debug(f"Folder found in cache: {folder_path}")
            return self.folder_cache[folder_path]

        if dry_run:
            logger.info(f"[DRY RUN] Would ensure folder exists: {folder_path}")
            mock_folder = {
                'id': f'mock_folder_{folder_path}',
                'name': folder_path.split('/')[-1],
                'path': folder_path
            }
            self.folder_cache[folder_path] = mock_folder
            self.created_folders.add(folder_path)
            return mock_folder

        try:
            logger.info(f"Ensuring folder exists: {folder_path}")
            folder = self.onedrive_ops.ensure_folder_path(folder_path)

            # Cache the folder
            self.folder_cache[folder_path] = folder
            self.created_folders.add(folder_path)

            return folder

        except Exception as e:
            logger.error(f"Failed to ensure folder exists {folder_path}: {e}")
            raise

    def prepare_folders_for_moves(
        self,
        move_plans: list,
        dry_run: bool = False
    ) -> Dict[str, Dict]:
        """
        Create all necessary folders for planned moves.

        Args:
            move_plans: List of move plan dictionaries
            dry_run: If True, don't actually create folders

        Returns:
            Dictionary mapping folder paths to folder info
        """
        # Collect unique destination folders
        destination_folders = set()
        for plan in move_plans:
            if plan['action'] == 'move' and plan['destination_path']:
                destination_folders.add(plan['destination_path'])

        logger.info(f"Preparing {len(destination_folders)} destination folders...")

        # Create all folders
        folder_map = {}
        for folder_path in sorted(destination_folders):
            try:
                folder = self.ensure_folder_exists(folder_path, dry_run)
                folder_map[folder_path] = folder
            except Exception as e:
                logger.error(f"Failed to prepare folder {folder_path}: {e}")
                # Continue with other folders

        logger.info(f"Prepared {len(folder_map)} folders")
        return folder_map

    def get_created_folders(self) -> Set[str]:
        """
        Get set of folders created in this session.

        Returns:
            Set of folder paths
        """
        return self.created_folders.copy()

    def clear_cache(self) -> None:
        """Clear folder cache."""
        self.folder_cache.clear()
        self.created_folders.clear()
        logger.debug("Folder cache cleared")
