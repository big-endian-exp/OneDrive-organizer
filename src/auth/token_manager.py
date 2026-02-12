"""
Secure token storage and management with encryption.
Tokens are encrypted at rest using Fernet (symmetric encryption).
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from ..utils.logger import get_logger

logger = get_logger()


class TokenManager:
    """Manage secure storage and retrieval of OAuth tokens."""

    def __init__(self, token_dir: str = "data/tokens"):
        """
        Initialize token manager.

        Args:
            token_dir: Directory to store encrypted tokens
        """
        self.token_dir = Path(token_dir)
        self.token_dir.mkdir(parents=True, exist_ok=True)

        self.token_file = self.token_dir / "token.enc"
        self.key_file = self.token_dir / "key.key"

        # Set restrictive permissions on token directory
        try:
            os.chmod(self.token_dir, 0o700)
        except Exception as e:
            logger.warning(f"Could not set directory permissions: {e}")

        logger.debug(f"Token manager initialized with directory: {token_dir}")

    def _get_or_create_key(self) -> bytes:
        """
        Get existing encryption key or create new one.

        Returns:
            Encryption key bytes
        """
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                key = f.read()
            logger.debug("Loaded existing encryption key")
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)

            # Set restrictive permissions
            try:
                os.chmod(self.key_file, 0o600)
            except Exception as e:
                logger.warning(f"Could not set key file permissions: {e}")

            logger.info("Generated new encryption key")

        return key

    def save_token(self, token_data: Dict) -> None:
        """
        Save token data with encryption.

        Args:
            token_data: Token dictionary from OAuth response

        Raises:
            Exception: If save fails
        """
        logger.info("Saving encrypted token...")

        try:
            # Get or create encryption key
            key = self._get_or_create_key()
            fernet = Fernet(key)

            # Add metadata
            token_data['saved_at'] = datetime.utcnow().isoformat()

            # Serialize and encrypt
            token_json = json.dumps(token_data)
            encrypted_data = fernet.encrypt(token_json.encode('utf-8'))

            # Write to file
            with open(self.token_file, 'wb') as f:
                f.write(encrypted_data)

            # Set restrictive permissions
            try:
                os.chmod(self.token_file, 0o600)
            except Exception as e:
                logger.warning(f"Could not set token file permissions: {e}")

            logger.info("Token saved successfully")

        except Exception as e:
            logger.error(f"Failed to save token: {e}")
            raise

    def load_token(self) -> Optional[Dict]:
        """
        Load and decrypt token data.

        Returns:
            Token dictionary if available, None if not found

        Raises:
            Exception: If decryption fails
        """
        if not self.token_file.exists():
            logger.debug("No saved token found")
            return None

        logger.debug("Loading encrypted token...")

        try:
            # Get encryption key
            if not self.key_file.exists():
                logger.error("Encryption key not found")
                return None

            key = self._get_or_create_key()
            fernet = Fernet(key)

            # Read and decrypt
            with open(self.token_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = fernet.decrypt(encrypted_data)
            token_data = json.loads(decrypted_data.decode('utf-8'))

            logger.debug("Token loaded successfully")
            return token_data

        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            raise

    def delete_token(self) -> None:
        """Delete saved token and encryption key."""
        logger.info("Deleting saved tokens...")

        if self.token_file.exists():
            self.token_file.unlink()
            logger.debug("Token file deleted")

        if self.key_file.exists():
            self.key_file.unlink()
            logger.debug("Key file deleted")

        logger.info("Tokens deleted successfully")

    def is_token_expired(self, token_data: Dict, buffer_seconds: int = 300) -> bool:
        """
        Check if token is expired or about to expire.

        Args:
            token_data: Token dictionary
            buffer_seconds: Safety buffer before actual expiry

        Returns:
            True if token is expired or about to expire
        """
        if 'expires_in' not in token_data or 'saved_at' not in token_data:
            logger.warning("Token missing expiry information")
            return True

        try:
            saved_at = datetime.fromisoformat(token_data['saved_at'])
            expires_in = token_data['expires_in']

            expiry_time = saved_at + timedelta(seconds=expires_in)
            now = datetime.utcnow()

            # Check with buffer
            is_expired = (expiry_time - timedelta(seconds=buffer_seconds)) <= now

            if is_expired:
                logger.debug("Token is expired or about to expire")
            else:
                remaining = (expiry_time - now).total_seconds()
                logger.debug(f"Token valid for {remaining:.0f} more seconds")

            return is_expired

        except Exception as e:
            logger.error(f"Error checking token expiry: {e}")
            return True

    def get_valid_token(self, oauth_handler) -> Optional[str]:
        """
        Get valid access token, refreshing if necessary.

        Args:
            oauth_handler: OAuthHandler instance for token refresh

        Returns:
            Valid access token, or None if refresh fails

        Raises:
            RuntimeError: If token refresh fails
        """
        token_data = self.load_token()

        if not token_data:
            logger.debug("No token available")
            return None

        # Check if expired
        if self.is_token_expired(token_data):
            logger.info("Token expired, attempting refresh...")

            if 'refresh_token' not in token_data:
                logger.error("No refresh token available")
                return None

            try:
                # Refresh token
                new_token_data = oauth_handler.refresh_token(token_data['refresh_token'])

                # Save new token
                self.save_token(new_token_data)

                return new_token_data['access_token']

            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                raise RuntimeError("Token refresh failed, please re-authenticate")

        return token_data['access_token']
