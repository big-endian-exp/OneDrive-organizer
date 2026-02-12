"""
Operation history tracking and undo functionality.
"""

import json
import random
import string
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ..utils.logger import get_logger

logger = get_logger()


class HistoryManager:
    """Manage operation history for undo capability."""

    def __init__(self, history_dir: str = "data/history"):
        """
        Initialize history manager.

        Args:
            history_dir: Directory to store history files
        """
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"History manager initialized: {history_dir}")

    def _generate_operation_id(self) -> str:
        """
        Generate unique operation ID.

        Returns:
            Operation ID string (format: YYYYMMDD_HHMMSS_randomstr)
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{timestamp}_{random_str}"

    def _get_history_file(self, operation_id: str) -> Path:
        """
        Get path to history file for operation.

        Args:
            operation_id: Operation ID

        Returns:
            Path to history file
        """
        return self.history_dir / f"{operation_id}.json"

    def save_operation(self, operation_data: Dict) -> str:
        """
        Save operation to history.

        Args:
            operation_data: Operation data dictionary

        Returns:
            Operation ID
        """
        operation_id = self._generate_operation_id()

        history_data = {
            'operation_id': operation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'operation_data': operation_data
        }

        history_file = self._get_history_file(operation_id)

        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Operation saved to history: {operation_id}")

        return operation_id

    def load_operation(self, operation_id: str) -> Optional[Dict]:
        """
        Load operation from history.

        Args:
            operation_id: Operation ID

        Returns:
            Operation data dictionary, or None if not found
        """
        history_file = self._get_history_file(operation_id)

        if not history_file.exists():
            logger.warning(f"Operation not found: {operation_id}")
            return None

        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)

        logger.debug(f"Loaded operation from history: {operation_id}")

        return history_data

    def list_operations(
        self,
        limit: Optional[int] = None,
        days: Optional[int] = None
    ) -> List[Dict]:
        """
        List saved operations.

        Args:
            limit: Maximum number of operations to return
            days: Only return operations from last N days

        Returns:
            List of operation summary dictionaries
        """
        history_files = sorted(
            self.history_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        operations = []

        for history_file in history_files:
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)

                # Filter by date if specified
                if days is not None:
                    op_time = datetime.fromisoformat(history_data['timestamp'])
                    cutoff = datetime.utcnow() - timedelta(days=days)

                    if op_time < cutoff:
                        continue

                # Create summary
                operation_data = history_data.get('operation_data', {})
                stats = operation_data.get('stats', {})

                operations.append({
                    'operation_id': history_data['operation_id'],
                    'timestamp': history_data['timestamp'],
                    'files_moved': stats.get('files_moved', 0),
                    'files_failed': stats.get('files_failed', 0),
                    'dry_run': operation_data.get('dry_run', False)
                })

                if limit and len(operations) >= limit:
                    break

            except Exception as e:
                logger.warning(f"Failed to load history file {history_file}: {e}")

        return operations

    def cleanup_old_operations(self, days: int = 90) -> int:
        """
        Delete operation history older than specified days.

        Args:
            days: Delete operations older than this many days

        Returns:
            Number of operations deleted
        """
        logger.info(f"Cleaning up operations older than {days} days...")

        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted_count = 0

        for history_file in self.history_dir.glob("*.json"):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history_data = json.load(f)

                op_time = datetime.fromisoformat(history_data['timestamp'])

                if op_time < cutoff:
                    history_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old operation: {history_data['operation_id']}")

            except Exception as e:
                logger.warning(f"Failed to process history file {history_file}: {e}")

        logger.info(f"Deleted {deleted_count} old operations")

        return deleted_count

    def can_undo(self, operation_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if operation can be undone.

        Args:
            operation_id: Operation ID

        Returns:
            Tuple of (can_undo, reason_if_not)
        """
        history_data = self.load_operation(operation_id)

        if not history_data:
            return False, "Operation not found"

        operation_data = history_data.get('operation_data', {})

        if operation_data.get('dry_run'):
            return False, "Cannot undo dry run (no actual changes were made)"

        if operation_data.get('status') != 'success':
            return False, "Operation did not complete successfully"

        operation_results = operation_data.get('operation_results', [])

        if not operation_results:
            return False, "No operations to undo"

        successful_moves = [
            r for r in operation_results if r.get('status') == 'success'
        ]

        if not successful_moves:
            return False, "No successful moves to undo"

        return True, None

    def create_undo_plan(self, operation_id: str) -> Optional[List[Dict]]:
        """
        Create undo plan for operation.

        Args:
            operation_id: Operation ID

        Returns:
            List of undo operations, or None if cannot undo
        """
        can_undo, reason = self.can_undo(operation_id)

        if not can_undo:
            logger.warning(f"Cannot undo operation {operation_id}: {reason}")
            return None

        history_data = self.load_operation(operation_id)
        operation_data = history_data['operation_data']
        operation_results = operation_data['operation_results']

        undo_plan = []

        for result in operation_results:
            if result.get('status') == 'success':
                # Reverse the move
                undo_operation = {
                    'item_id': result['item']['id'],
                    'current_name': result.get('new_name') or result['item']['name'],
                    'original_path': result['source_path'],
                    'current_path': result['destination_path']
                }
                undo_plan.append(undo_operation)

        logger.info(f"Created undo plan with {len(undo_plan)} operations")

        return undo_plan
