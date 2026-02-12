"""
OneDrive-specific operations using Microsoft Graph API.
"""

from typing import Dict, List, Optional
from urllib.parse import quote
from .graph_client import GraphClient, GraphAPIError
from ..utils.logger import get_logger

logger = get_logger()


class OneDriveOperations:
    """High-level OneDrive operations wrapper."""

    def __init__(self, graph_client: GraphClient):
        """
        Initialize OneDrive operations.

        Args:
            graph_client: GraphClient instance
        """
        self.client = graph_client

    def list_items(
        self,
        folder_path: str = "",
        recursive: bool = False,
        max_items: Optional[int] = None
    ) -> List[Dict]:
        """
        List items in OneDrive folder.

        Args:
            folder_path: Path to folder (empty for root)
            recursive: If True, recursively list all items
            max_items: Maximum number of items to return

        Returns:
            List of item dictionaries
        """
        if folder_path:
            # Encode path for URL
            encoded_path = quote(folder_path)
            endpoint = f"/me/drive/root:/{encoded_path}:/children"
            logger.info(f"Listing items in folder: {folder_path}")
        else:
            endpoint = "/me/drive/root/children"
            logger.info("Listing items in root folder")

        items = self.client.get_paginated(endpoint)

        if recursive:
            all_items = []
            folders_to_process = [(item, folder_path) for item in items if 'folder' in item]

            # Add files first
            all_items.extend([item for item in items if 'file' in item])

            # Process folders recursively
            while folders_to_process:
                folder_item, parent_path = folders_to_process.pop(0)
                folder_name = folder_item['name']
                full_path = f"{parent_path}/{folder_name}" if parent_path else folder_name

                try:
                    sub_items = self.list_items(full_path, recursive=False)

                    # Add files
                    all_items.extend([item for item in sub_items if 'file' in item])

                    # Add subfolders to queue
                    folders_to_process.extend([
                        (item, full_path) for item in sub_items if 'folder' in item
                    ])

                except Exception as e:
                    logger.warning(f"Failed to list folder {full_path}: {e}")

            items = all_items

        logger.info(f"Found {len(items)} items")

        if max_items:
            items = items[:max_items]

        return items

    def get_item_by_path(self, path: str) -> Dict:
        """
        Get item metadata by path.

        Args:
            path: Item path

        Returns:
            Item dictionary

        Raises:
            GraphAPIError: If item not found
        """
        encoded_path = quote(path)
        endpoint = f"/me/drive/root:/{encoded_path}"
        logger.debug(f"Getting item: {path}")
        return self.client.get(endpoint)

    def create_folder(self, parent_path: str, folder_name: str) -> Dict:
        """
        Create folder in OneDrive.

        Args:
            parent_path: Parent folder path (empty for root)
            folder_name: Name of folder to create

        Returns:
            Created folder dictionary

        Raises:
            GraphAPIError: If creation fails
        """
        if parent_path:
            encoded_path = quote(parent_path)
            endpoint = f"/me/drive/root:/{encoded_path}:/children"
        else:
            endpoint = "/me/drive/root/children"

        payload = {
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail"
        }

        try:
            logger.info(f"Creating folder: {parent_path}/{folder_name}")
            return self.client.post(endpoint, json_data=payload)
        except GraphAPIError as e:
            if "nameAlreadyExists" in str(e):
                logger.debug(f"Folder already exists: {folder_name}")
                # Get existing folder
                folder_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
                return self.get_item_by_path(folder_path)
            raise

    def ensure_folder_path(self, folder_path: str) -> Dict:
        """
        Ensure folder path exists, creating folders as needed.

        Args:
            folder_path: Full folder path (e.g., "2024/January")

        Returns:
            Final folder dictionary
        """
        if not folder_path:
            return self.client.get("/me/drive/root")

        # Split path into segments
        segments = folder_path.split('/')
        current_path = ""

        for segment in segments:
            try:
                # Try to get existing folder
                test_path = f"{current_path}/{segment}" if current_path else segment
                folder = self.get_item_by_path(test_path)
                current_path = test_path
            except GraphAPIError:
                # Folder doesn't exist, create it
                folder = self.create_folder(current_path, segment)
                current_path = f"{current_path}/{segment}" if current_path else segment

        logger.debug(f"Ensured folder path exists: {folder_path}")
        return folder

    def move_item(
        self,
        item_id: str,
        destination_folder_id: str,
        new_name: Optional[str] = None
    ) -> Dict:
        """
        Move item to different folder.

        Args:
            item_id: ID of item to move
            destination_folder_id: ID of destination folder
            new_name: Optional new name for item

        Returns:
            Updated item dictionary

        Raises:
            GraphAPIError: If move fails
        """
        endpoint = f"/me/drive/items/{item_id}"

        payload = {
            "parentReference": {
                "id": destination_folder_id
            }
        }

        if new_name:
            payload["name"] = new_name

        logger.debug(f"Moving item {item_id} to folder {destination_folder_id}")
        return self.client.patch(endpoint, json_data=payload)

    def move_item_by_path(
        self,
        source_path: str,
        destination_path: str,
        new_name: Optional[str] = None
    ) -> Dict:
        """
        Move item by path.

        Args:
            source_path: Source item path
            destination_path: Destination folder path
            new_name: Optional new name

        Returns:
            Updated item dictionary
        """
        logger.info(f"Moving {source_path} to {destination_path}")

        # Get source item
        source_item = self.get_item_by_path(source_path)
        item_id = source_item['id']

        # Ensure destination folder exists
        dest_folder = self.ensure_folder_path(destination_path)
        dest_folder_id = dest_folder['id']

        # Move item
        return self.move_item(item_id, dest_folder_id, new_name)

    def get_item_metadata(self, item_id: str) -> Dict:
        """
        Get full metadata for an item.

        Args:
            item_id: Item ID

        Returns:
            Item metadata dictionary
        """
        endpoint = f"/me/drive/items/{item_id}"
        return self.client.get(endpoint)

    def search_items(self, query: str) -> List[Dict]:
        """
        Search for items in OneDrive.

        Args:
            query: Search query

        Returns:
            List of matching items
        """
        encoded_query = quote(query)
        endpoint = f"/me/drive/root/search(q='{encoded_query}')"
        logger.info(f"Searching for: {query}")
        return self.client.get_paginated(endpoint)

    def get_item_path(self, item: Dict) -> str:
        """
        Extract full path from item dictionary.

        Args:
            item: Item dictionary from API

        Returns:
            Full path string
        """
        if 'parentReference' in item and 'path' in item['parentReference']:
            parent_path = item['parentReference']['path']
            # Remove '/drive/root:' prefix
            if parent_path.startswith('/drive/root:'):
                parent_path = parent_path[12:]  # len('/drive/root:')
            if parent_path == '':
                return item['name']
            return f"{parent_path}/{item['name']}"
        return item['name']
