"""
Main organization engine implementing the 4-phase algorithm.
Phases: Discovery, Analysis, Planning, Execution
"""

from typing import Dict, List, Optional
from datetime import datetime
from .file_analyzer import FileAnalyzer
from .folder_manager import FolderManager
from .content_categorizer import ContentCategorizer
from ..api.onedrive_operations import OneDriveOperations
from ..utils.logger import get_logger

logger = get_logger()


class OrganizerEngine:
    """Main engine for organizing OneDrive files."""

    def __init__(
        self,
        onedrive_ops: OneDriveOperations,
        config: Dict
    ):
        """
        Initialize organizer engine.

        Args:
            onedrive_ops: OneDriveOperations instance
            config: Configuration dictionary
        """
        self.onedrive_ops = onedrive_ops
        self.config = config

        # Initialize components
        org_config = config.get('organization', {})
        cat_config = config.get('categorization', {})

        # Initialize categorizer if enabled
        categorizer = None
        if cat_config.get('enabled', False):
            categorizer = ContentCategorizer(cat_config)
            logger.info("Content-based categorization enabled")

        self.file_analyzer = FileAnalyzer(
            date_field=org_config.get('date_field', 'createdDateTime'),
            folder_structure=org_config.get('folder_structure', '{year}/{month}'),
            destination_root=org_config.get('destination_root', 'Organized'),
            categorizer=categorizer
        )

        self.folder_manager = FolderManager(onedrive_ops)

        # Statistics
        self.stats = {
            'total_files': 0,
            'files_to_move': 0,
            'files_skipped': 0,
            'files_moved': 0,
            'files_failed': 0,
            'folders_created': 0,
            'skip_reasons': {},
            'categories': {}  # Category breakdown
        }

        self.categorizer = categorizer

    def phase_1_discovery(
        self,
        source_folder: str = "",
        recursive: bool = True,
        max_files: Optional[int] = None
    ) -> List[Dict]:
        """
        Phase 1: Discover files in OneDrive.

        Args:
            source_folder: Source folder to scan
            recursive: Scan recursively
            max_files: Maximum number of files to process

        Returns:
            List of discovered items with paths
        """
        logger.info("=" * 60)
        logger.info("PHASE 1: DISCOVERY")
        logger.info("=" * 60)

        logger.info(f"Scanning OneDrive folder: '{source_folder or 'root'}'")

        items = self.onedrive_ops.list_items(
            folder_path=source_folder,
            recursive=recursive,
            max_items=max_files
        )

        # Add full paths to items
        items_with_paths = []
        for item in items:
            item_path = self.onedrive_ops.get_item_path(item)
            items_with_paths.append({
                'item': item,
                'path': item_path
            })

        # Count files only (exclude folders)
        file_count = sum(1 for i in items_with_paths if 'file' in i['item'])

        self.stats['total_files'] = file_count
        logger.info(f"Discovered {file_count} files")

        return items_with_paths

    def phase_2_analysis(
        self,
        items_with_paths: List[Dict],
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Phase 2: Analyze files and determine destinations.

        Args:
            items_with_paths: List of items with paths from Phase 1
            filters: Filter configuration

        Returns:
            List of analysis results
        """
        logger.info("=" * 60)
        logger.info("PHASE 2: ANALYSIS")
        logger.info("=" * 60)

        if filters is None:
            filters = self.config.get('organization', {}).get('filters', {})

        skip_options = {
            'skip_already_organized': filters.get('skip_already_organized', True),
            'exclude_extensions': filters.get('exclude_extensions', []),
            'min_age_days': filters.get('min_age_days', 0)
        }

        logger.info(f"Analyzing {len(items_with_paths)} items...")

        analysis_results = []
        for item_data in items_with_paths:
            result = self.file_analyzer.analyze_item(
                item_data['item'],
                item_data['path'],
                **skip_options
            )
            analysis_results.append(result)

            # Update statistics
            if result['action'] == 'skip':
                self.stats['files_skipped'] += 1
                reason = result.get('reason', 'unknown')
                self.stats['skip_reasons'][reason] = \
                    self.stats['skip_reasons'].get(reason, 0) + 1
            elif result['action'] == 'move' and 'category' in result:
                # Track category statistics
                category = result['category']
                self.stats['categories'][category] = \
                    self.stats['categories'].get(category, 0) + 1

        files_to_move = sum(1 for r in analysis_results if r['action'] == 'move')
        self.stats['files_to_move'] = files_to_move

        logger.info(f"Analysis complete:")
        logger.info(f"  Files to move: {files_to_move}")
        logger.info(f"  Files to skip: {self.stats['files_skipped']}")

        if self.stats['skip_reasons']:
            logger.info("  Skip reasons:")
            for reason, count in self.stats['skip_reasons'].items():
                logger.info(f"    {reason}: {count}")

        if self.stats['categories']:
            logger.info("  Category breakdown:")
            for category, count in sorted(self.stats['categories'].items(),
                                         key=lambda x: x[1], reverse=True):
                logger.info(f"    {category}: {count}")

        return analysis_results

    def phase_3_planning(
        self,
        analysis_results: List[Dict]
    ) -> Dict:
        """
        Phase 3: Create execution plan.

        Args:
            analysis_results: Results from Phase 2

        Returns:
            Execution plan dictionary
        """
        logger.info("=" * 60)
        logger.info("PHASE 3: PLANNING")
        logger.info("=" * 60)

        move_plans = [r for r in analysis_results if r['action'] == 'move']

        logger.info(f"Planning moves for {len(move_plans)} files...")

        # Detect conflicts (multiple files to same destination)
        destination_map = {}
        for plan in move_plans:
            dest = plan['destination_path']
            filename = plan['item']['name']
            full_dest = f"{dest}/{filename}"

            if full_dest not in destination_map:
                destination_map[full_dest] = []
            destination_map[full_dest].append(plan)

        # Resolve conflicts
        conflicts = {k: v for k, v in destination_map.items() if len(v) > 1}

        if conflicts:
            logger.warning(f"Found {len(conflicts)} destination conflicts")
            for dest, plans in conflicts.items():
                logger.warning(f"  Conflict at {dest}: {len(plans)} files")

                # Resolve by adding timestamp to filename
                for i, plan in enumerate(plans[1:], 1):
                    original_name = plan['item']['name']
                    name_parts = original_name.rsplit('.', 1)

                    if len(name_parts) == 2:
                        new_name = f"{name_parts[0]}_{i}.{name_parts[1]}"
                    else:
                        new_name = f"{original_name}_{i}"

                    plan['new_name'] = new_name
                    logger.info(f"    Renamed: {original_name} -> {new_name}")

        # Collect unique folders needed
        folders_needed = set(p['destination_path'] for p in move_plans)

        execution_plan = {
            'move_plans': move_plans,
            'folders_needed': list(folders_needed),
            'conflicts_resolved': len(conflicts),
            'total_moves': len(move_plans)
        }

        logger.info(f"Execution plan created:")
        logger.info(f"  Total moves: {execution_plan['total_moves']}")
        logger.info(f"  Folders needed: {len(folders_needed)}")
        logger.info(f"  Conflicts resolved: {conflicts}")

        return execution_plan

    def phase_4_execution(
        self,
        execution_plan: Dict,
        dry_run: bool = False
    ) -> List[Dict]:
        """
        Phase 4: Execute the plan.

        Args:
            execution_plan: Plan from Phase 3
            dry_run: If True, simulate without actually moving files

        Returns:
            List of operation results
        """
        logger.info("=" * 60)
        logger.info(f"PHASE 4: EXECUTION {'(DRY RUN)' if dry_run else ''}")
        logger.info("=" * 60)

        move_plans = execution_plan['move_plans']

        if not move_plans:
            logger.info("No files to move")
            return []

        # Step 1: Create folders
        logger.info("Creating destination folders...")
        folder_map = self.folder_manager.prepare_folders_for_moves(move_plans, dry_run)
        self.stats['folders_created'] = len(folder_map)

        # Step 2: Move files
        logger.info(f"Moving {len(move_plans)} files...")

        operation_results = []

        for i, plan in enumerate(move_plans, 1):
            item = plan['item']
            source_path = plan['source_path']
            dest_path = plan['destination_path']
            new_name = plan.get('new_name')

            logger.info(f"[{i}/{len(move_plans)}] {source_path} -> {dest_path}")

            if dry_run:
                operation_results.append({
                    'item': item,
                    'source_path': source_path,
                    'destination_path': dest_path,
                    'new_name': new_name,
                    'status': 'dry_run',
                    'timestamp': datetime.utcnow().isoformat()
                })
                self.stats['files_moved'] += 1
                continue

            try:
                # Get destination folder ID
                folder_info = folder_map.get(dest_path)
                if not folder_info:
                    raise Exception(f"Destination folder not found: {dest_path}")

                dest_folder_id = folder_info['id']

                # Move item
                result = self.onedrive_ops.move_item(
                    item_id=item['id'],
                    destination_folder_id=dest_folder_id,
                    new_name=new_name
                )

                operation_results.append({
                    'item': item,
                    'source_path': source_path,
                    'destination_path': dest_path,
                    'new_name': new_name,
                    'status': 'success',
                    'result': result,
                    'timestamp': datetime.utcnow().isoformat()
                })

                self.stats['files_moved'] += 1
                logger.info(f"  ✓ Moved successfully")

            except Exception as e:
                logger.error(f"  ✗ Failed to move: {e}")

                operation_results.append({
                    'item': item,
                    'source_path': source_path,
                    'destination_path': dest_path,
                    'new_name': new_name,
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })

                self.stats['files_failed'] += 1

        return operation_results

    def organize(
        self,
        source_folder: str = "",
        dry_run: bool = False,
        max_files: Optional[int] = None
    ) -> Dict:
        """
        Run full organization process (all 4 phases).

        Args:
            source_folder: Source folder to organize
            dry_run: If True, simulate without making changes
            max_files: Maximum number of files to process

        Returns:
            Organization result dictionary
        """
        start_time = datetime.utcnow()

        logger.info("\n" + "=" * 60)
        logger.info("ONEDRIVE ORGANIZER")
        logger.info("=" * 60)
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        logger.info(f"Source: '{source_folder or 'root'}'")
        logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("=" * 60 + "\n")

        try:
            # Phase 1: Discovery
            items_with_paths = self.phase_1_discovery(
                source_folder=source_folder,
                max_files=max_files
            )

            # Phase 2: Analysis
            analysis_results = self.phase_2_analysis(items_with_paths)

            # Phase 3: Planning
            execution_plan = self.phase_3_planning(analysis_results)

            # Phase 4: Execution
            operation_results = self.phase_4_execution(
                execution_plan,
                dry_run=dry_run
            )

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.info("\n" + "=" * 60)
            logger.info("ORGANIZATION COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Duration: {duration:.1f} seconds")
            logger.info(f"Total files: {self.stats['total_files']}")
            logger.info(f"Files moved: {self.stats['files_moved']}")
            logger.info(f"Files skipped: {self.stats['files_skipped']}")
            logger.info(f"Files failed: {self.stats['files_failed']}")
            logger.info(f"Folders created: {self.stats['folders_created']}")

            if self.stats['categories']:
                logger.info("\nCategory breakdown:")
                for category, count in sorted(self.stats['categories'].items(),
                                             key=lambda x: x[1], reverse=True):
                    logger.info(f"  {category}: {count} files")

            logger.info("=" * 60 + "\n")

            return {
                'status': 'success',
                'stats': self.stats.copy(),
                'operation_results': operation_results,
                'execution_plan': execution_plan,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'dry_run': dry_run
            }

        except Exception as e:
            logger.error(f"Organization failed: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'stats': self.stats.copy(),
                'dry_run': dry_run
            }

    def get_statistics(self) -> Dict:
        """
        Get current statistics.

        Returns:
            Statistics dictionary
        """
        return self.stats.copy()
