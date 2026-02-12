"""
OAuth2 authentication handler using MSAL (Microsoft Authentication Library).
Supports both device code flow and interactive browser flow.
"""

import msal
from typing import Dict, List, Optional
from ..utils.logger import get_logger

logger = get_logger()


class OAuthHandler:
    """Handle OAuth2 authentication with Microsoft Identity Platform."""

    def __init__(
        self,
        client_id: str,
        tenant_id: str = "common",
        scopes: Optional[List[str]] = None
    ):
        """
        Initialize OAuth handler.

        Args:
            client_id: Azure AD application client ID
            tenant_id: Tenant ID or "common" for personal accounts
            scopes: List of permission scopes
        """
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.scopes = scopes or [
            "Files.ReadWrite.All",
            "User.Read"
        ]

        # Build authority URL
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"

        # Create MSAL PublicClientApplication
        self.app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=self.authority
        )

        logger.debug(f"OAuth handler initialized for tenant: {tenant_id}")

    def authenticate_device_code(self) -> Dict:
        """
        Authenticate using device code flow (no browser required).
        User enters code on another device.

        Returns:
            Authentication result with access_token and refresh_token

        Raises:
            RuntimeError: If authentication fails
        """
        logger.info("Starting device code authentication flow...")

        # Initiate device code flow
        flow = self.app.initiate_device_flow(scopes=self.scopes)

        if "user_code" not in flow:
            raise RuntimeError(
                f"Failed to create device flow: {flow.get('error_description', 'Unknown error')}"
            )

        # Display instructions to user
        print("\n" + "=" * 60)
        print("DEVICE CODE AUTHENTICATION")
        print("=" * 60)
        print(flow["message"])
        print("=" * 60 + "\n")

        logger.info("Waiting for user to complete authentication...")

        # Wait for user to authenticate
        result = self.app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            logger.info("Authentication successful!")
            return result
        else:
            error_msg = result.get("error_description", result.get("error", "Unknown error"))
            logger.error(f"Authentication failed: {error_msg}")
            raise RuntimeError(f"Authentication failed: {error_msg}")

    def authenticate_interactive(self, port: int = 8080) -> Dict:
        """
        Authenticate using interactive browser flow.

        Args:
            port: Local port for redirect URI

        Returns:
            Authentication result with access_token and refresh_token

        Raises:
            RuntimeError: If authentication fails
        """
        logger.info("Starting interactive authentication flow...")

        # Try interactive flow
        result = self.app.acquire_token_interactive(
            scopes=self.scopes,
            port=port,
            prompt="select_account"
        )

        if "access_token" in result:
            logger.info("Authentication successful!")
            return result
        else:
            error_msg = result.get("error_description", result.get("error", "Unknown error"))
            logger.error(f"Authentication failed: {error_msg}")
            raise RuntimeError(f"Authentication failed: {error_msg}")

    def refresh_token(self, refresh_token: str) -> Dict:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            New authentication result with refreshed access_token

        Raises:
            RuntimeError: If token refresh fails
        """
        logger.debug("Refreshing access token...")

        result = self.app.acquire_token_by_refresh_token(
            refresh_token=refresh_token,
            scopes=self.scopes
        )

        if "access_token" in result:
            logger.debug("Token refresh successful")
            return result
        else:
            error_msg = result.get("error_description", result.get("error", "Unknown error"))
            logger.warning(f"Token refresh failed: {error_msg}")
            raise RuntimeError(f"Token refresh failed: {error_msg}")

    def get_accounts(self) -> List[Dict]:
        """
        Get cached accounts.

        Returns:
            List of account dictionaries
        """
        accounts = self.app.get_accounts()
        logger.debug(f"Found {len(accounts)} cached accounts")
        return accounts

    def acquire_token_silent(self, account: Optional[Dict] = None) -> Optional[Dict]:
        """
        Try to acquire token silently from cache.

        Args:
            account: Account dictionary (if None, uses first available)

        Returns:
            Authentication result if successful, None if requires interaction
        """
        accounts = self.get_accounts()

        if not accounts:
            logger.debug("No cached accounts found")
            return None

        if account is None:
            account = accounts[0]

        logger.debug(f"Attempting silent token acquisition for: {account.get('username', 'unknown')}")

        result = self.app.acquire_token_silent(
            scopes=self.scopes,
            account=account
        )

        if result and "access_token" in result:
            logger.debug("Silent token acquisition successful")
            return result
        else:
            logger.debug("Silent token acquisition failed, requires interaction")
            return None


def authenticate(
    client_id: str,
    tenant_id: str = "common",
    scopes: Optional[List[str]] = None,
    use_device_code: bool = True
) -> Dict:
    """
    High-level authentication function.

    Args:
        client_id: Azure AD application client ID
        tenant_id: Tenant ID or "common" for personal accounts
        scopes: List of permission scopes
        use_device_code: If True, use device code flow; otherwise interactive

    Returns:
        Authentication result dictionary

    Raises:
        RuntimeError: If authentication fails
    """
    handler = OAuthHandler(client_id, tenant_id, scopes)

    if use_device_code:
        return handler.authenticate_device_code()
    else:
        return handler.authenticate_interactive()
