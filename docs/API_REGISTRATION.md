# Azure AD Application Registration Guide

This guide explains how to register an Azure AD application for the OneDrive Organizer.

## Why Azure AD Registration?

To access OneDrive via the Microsoft Graph API, you need to register an application in Azure Active Directory. This provides:
- OAuth2 authentication credentials
- Permission scopes for OneDrive access
- Secure token-based access

## Prerequisites

- Microsoft account (personal or work/school)
- Access to [Azure Portal](https://portal.azure.com)

**Note**: Personal Microsoft accounts can register Azure AD apps for free.

## Step-by-Step Registration

### 1. Access Azure Portal

1. Open browser to https://portal.azure.com
2. Sign in with your Microsoft account
3. If this is your first time:
   - You may need to verify your account
   - Accept terms if prompted

### 2. Navigate to App Registrations

**Path**: Azure Active Directory → App registrations

**Steps**:
1. Click the menu icon (☰) in top-left
2. Search for "Azure Active Directory" or find it in the menu
3. In the left sidebar, click "App registrations"
4. You'll see a list of registered applications (empty if first time)

### 3. Create New Registration

Click **"+ New registration"** button at the top.

Fill in the form:

**Name**:
```
OneDrive Personal Organizer
```
(You can choose any name - this is just for your reference)

**Supported account types**:
Select:
```
☑ Accounts in any organizational directory (Any Azure AD directory - Multitenant)
  and personal Microsoft accounts (e.g. Skype, Xbox)
```

**Why this option?**
- Allows personal Microsoft accounts (needed for personal OneDrive)
- Works with both personal and work accounts

**Redirect URI**:
- Platform: Select "Public client/native (mobile & desktop)"
- URI: `http://localhost:8080`

Click **"Register"** button at the bottom.

### 4. Copy Application (Client) ID

After registration, you'll see the Overview page.

**Important**: Copy the "Application (client) ID"

Example:
```
Application (client) ID: 12345678-1234-1234-1234-123456789abc
```

**Save this!** You'll need it for the .env file.

### 5. Configure API Permissions

**Path**: Your App → API permissions (left sidebar)

#### 5.1. Remove Default Permission (Optional)

You may see "User.Read" already added. This is fine to keep.

#### 5.2. Add Microsoft Graph Permissions

1. Click **"+ Add a permission"**
2. Select **"Microsoft Graph"**
3. Select **"Delegated permissions"**
   - **Important**: Not "Application permissions"

4. Search for and add these permissions:

   **Files.ReadWrite.All**:
   - Expand "Files"
   - Check ☑ "Files.ReadWrite.All"
   - This allows reading and writing all files the user can access

   **User.Read** (should already be there):
   - Expand "User"
   - Check ☑ "User.Read"
   - This allows reading basic profile information

5. Click **"Add permissions"** at the bottom

#### 5.3. Verify Permissions

Your permission list should show:
```
API / Permission name             Type       Status
Microsoft Graph / Files.ReadWrite.All   Delegated  Not granted for...
Microsoft Graph / User.Read             Delegated  Not granted for...
```

**Note**: "Not granted for..." is normal for personal apps. Admin consent is not required for personal Microsoft accounts.

### 6. Configure Authentication Settings

**Path**: Your App → Authentication (left sidebar)

#### 6.1. Platform Configuration

Verify the platform configuration:
- Platform: Public client/native
- Redirect URI: http://localhost:8080

#### 6.2. Advanced Settings

Scroll down to "Advanced settings" section:

**Allow public client flows**: YES
- Toggle this to "Yes"
- Required for device code flow

**Supported account types**:
- Should show "Multitenant and personal accounts"

Click **"Save"** at the top if you made changes.

### 7. No Client Secret Needed

**Important**: Do NOT create a client secret!

For public client applications (desktop apps), we use:
- Device code flow
- No client secret required
- More secure for desktop applications

### 8. Final Configuration Summary

Your app registration should have:

✅ **Application (client) ID**: Copied and saved
✅ **Supported accounts**: Multitenant + personal
✅ **Redirect URI**: http://localhost:8080
✅ **API Permissions**:
   - Files.ReadWrite.All (Delegated)
   - User.Read (Delegated)
✅ **Allow public client flows**: YES
❌ **Client secret**: NOT needed

## Using Your Client ID

### Add to .env File

1. Navigate to project directory:
   ```bash
   cd /Users/amritshandilya/My_Agents/onedrive_organizer
   ```

2. Copy template:
   ```bash
   cp config/.env.example .env
   ```

3. Edit .env:
   ```bash
   nano .env
   ```

4. Add your Client ID:
   ```
   CLIENT_ID=12345678-1234-1234-1234-123456789abc
   ```
   (Replace with your actual Client ID)

5. Save and exit (Ctrl+X, then Y, then Enter in nano)

### Verify Configuration

```bash
# Check .env file exists and has content
cat .env
# Should show: CLIENT_ID=your_actual_client_id

# Verify it's not tracked by git
git status .env
# Should show: nothing to commit or file is in .gitignore
```

## Authentication Flow

Once registered, the authentication flow works like this:

1. **You run**: `python src/main.py --authenticate`

2. **App initiates device code flow**:
   - Requests authentication from Microsoft
   - Receives a device code and URL

3. **You authenticate**:
   - Open browser to https://microsoft.com/devicelogin
   - Enter the code shown
   - Sign in with your Microsoft account
   - Grant permissions to the app

4. **App receives token**:
   - Access token for API calls
   - Refresh token for automatic renewal
   - Tokens are encrypted and stored locally

5. **Future requests**:
   - App uses saved token
   - Automatically refreshes when expired
   - No need to re-authenticate (until token revoked)

## Security Best Practices

### What We Do

✅ Store Client ID in .env (gitignored)
✅ Encrypt tokens at rest
✅ Use restricted file permissions (600)
✅ Token auto-refresh
✅ Delegated permissions (user context)
✅ Public client flow (no secrets)

### What You Should Do

✅ Never commit .env to version control
✅ Keep your Client ID private
✅ Don't share tokens or keys
✅ Revoke app access if compromised
✅ Use strong Microsoft account password
✅ Enable 2FA on Microsoft account

### Revoking Access

If you need to revoke the app's access:

**Method 1: Microsoft Account Settings**
1. Go to https://account.microsoft.com/privacy
2. Click "Apps and services"
3. Find "OneDrive Personal Organizer"
4. Click "Remove these permissions"

**Method 2: Azure Portal**
1. Go to Azure Portal
2. Azure Active Directory → App registrations
3. Find your app
4. Click "Delete"

## Troubleshooting

### "AADSTS700016: Application not found"

**Cause**: Client ID is incorrect

**Fix**:
1. Go to Azure Portal → App registrations
2. Click on your app
3. Copy the correct "Application (client) ID"
4. Update .env file

### "AADSTS65001: The user or administrator has not consented"

**Cause**: Permissions not properly configured

**Fix**:
1. Azure Portal → Your App → API permissions
2. Verify Files.ReadWrite.All is listed
3. Ensure "Delegated" type (not Application)
4. Try authentication again

### "AADSTS650053: Invalid redirect URI"

**Cause**: Redirect URI mismatch

**Fix**:
1. Azure Portal → Your App → Authentication
2. Verify redirect URI: http://localhost:8080
3. Verify platform: Public client/native
4. Save changes

### "AADSTS7000218: Invalid client secret"

**Cause**: Trying to use client secret with public client

**Fix**:
1. Don't create or use client secrets
2. Azure Portal → Your App → Authentication
3. Set "Allow public client flows" to YES
4. Use device code flow (automatic in our app)

### "Unsupported account type"

**Cause**: App registered for wrong account type

**Fix**:
1. Azure Portal → Your App → Authentication
2. Supported account types should be:
   "Accounts in any organizational directory and personal Microsoft accounts"
3. If wrong, you may need to re-register the app

## Testing the Registration

After setup, test your registration:

```bash
# From project directory
cd /Users/amritshandilya/My_Agents/onedrive_organizer

# Activate virtual environment
source venv/bin/activate

# Test authentication
python src/main.py --authenticate
```

Expected output:
```
============================================================
DEVICE CODE AUTHENTICATION
============================================================
To sign in, use a web browser to open the page
https://microsoft.com/devicelogin and enter the code ABC123XYZ
to authenticate.
============================================================
```

Follow the prompts, and you should see:
```
Authentication successful!
Token saved securely.
Authenticated as: Your Name (your.email@example.com)
```

If you see errors, refer to the troubleshooting section above.

## Additional Resources

- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
- [Azure AD App Registration](https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [OneDrive API Reference](https://docs.microsoft.com/en-us/graph/api/resources/onedrive)
- [OAuth 2.0 Device Code Flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code)

## Support

If you encounter issues during registration:

1. **Check Microsoft documentation**: Links above
2. **Verify account status**: Ensure your Microsoft account is active
3. **Try different browser**: Some corporate networks block Azure Portal
4. **Clear browser cache**: Sometimes helps with authentication issues
5. **Check for service outages**: https://status.azure.com/

## Next Steps

After successful registration:
1. ✅ Add Client ID to .env file
2. ✅ Test authentication: `python src/main.py --authenticate`
3. ✅ Continue with [SETUP.md](SETUP.md) for full setup
4. ✅ Run dry-run test: `python src/main.py --dry-run`
