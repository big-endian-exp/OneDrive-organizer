"""
Microsoft Graph API client with retry logic and rate limiting.
"""

import time
import requests
from typing import Dict, List, Optional, Any
from ..utils.logger import get_logger

logger = get_logger()


class GraphAPIError(Exception):
    """Custom exception for Graph API errors."""
    pass


class GraphClient:
    """Microsoft Graph API client wrapper."""

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, access_token: str):
        """
        Initialize Graph API client.

        Args:
            access_token: OAuth2 access token
        """
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        max_retries: int = 3,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with retry logic and rate limiting.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            endpoint: API endpoint (relative to BASE_URL)
            max_retries: Maximum number of retries
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            GraphAPIError: If request fails after retries
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"

        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)

                # Handle rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue

                # Handle server errors with exponential backoff
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"Server error {response.status_code}. "
                            f"Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue

                # Raise for other error status codes
                response.raise_for_status()

                return response

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Request failed: {e}. "
                        f"Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise GraphAPIError(f"Request failed: {e}")

        raise GraphAPIError(f"Request failed after {max_retries} attempts")

    def get(self, endpoint: str, **kwargs) -> Dict:
        """
        Make GET request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional request arguments

        Returns:
            Response JSON as dictionary
        """
        response = self._make_request('GET', endpoint, **kwargs)
        return response.json()

    def post(self, endpoint: str, json_data: Optional[Dict] = None, **kwargs) -> Dict:
        """
        Make POST request.

        Args:
            endpoint: API endpoint
            json_data: JSON payload
            **kwargs: Additional request arguments

        Returns:
            Response JSON as dictionary
        """
        response = self._make_request('POST', endpoint, json=json_data, **kwargs)
        return response.json()

    def patch(self, endpoint: str, json_data: Optional[Dict] = None, **kwargs) -> Dict:
        """
        Make PATCH request.

        Args:
            endpoint: API endpoint
            json_data: JSON payload
            **kwargs: Additional request arguments

        Returns:
            Response JSON as dictionary
        """
        response = self._make_request('PATCH', endpoint, json=json_data, **kwargs)
        return response.json()

    def delete(self, endpoint: str, **kwargs) -> None:
        """
        Make DELETE request.

        Args:
            endpoint: API endpoint
            **kwargs: Additional request arguments
        """
        self._make_request('DELETE', endpoint, **kwargs)

    def get_paginated(
        self,
        endpoint: str,
        max_pages: Optional[int] = None
    ) -> List[Dict]:
        """
        Get all items from paginated endpoint.

        Args:
            endpoint: API endpoint
            max_pages: Maximum number of pages to fetch (None = all)

        Returns:
            List of all items from all pages

        Yields:
            Items from each page
        """
        all_items = []
        next_link = endpoint
        page_count = 0

        while next_link:
            # Check page limit
            if max_pages and page_count >= max_pages:
                logger.debug(f"Reached max pages limit: {max_pages}")
                break

            # Use full URL if it's a nextLink
            if next_link.startswith('http'):
                response = self.session.get(next_link)
                response.raise_for_status()
                data = response.json()
            else:
                data = self.get(next_link)

            # Get items from response
            items = data.get('value', [])
            all_items.extend(items)

            page_count += 1
            logger.debug(f"Fetched page {page_count} with {len(items)} items")

            # Get next page link
            next_link = data.get('@odata.nextLink')

        logger.info(f"Fetched total of {len(all_items)} items from {page_count} pages")
        return all_items

    def get_user_info(self) -> Dict:
        """
        Get current user information.

        Returns:
            User information dictionary
        """
        logger.debug("Fetching user information...")
        return self.get('/me')

    def get_drive_info(self) -> Dict:
        """
        Get OneDrive information.

        Returns:
            Drive information dictionary
        """
        logger.debug("Fetching drive information...")
        return self.get('/me/drive')
