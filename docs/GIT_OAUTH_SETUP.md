# Git Provider OAuth Setup Guide

This guide explains how to configure OAuth applications for GitHub, GitLab, and Gitea to enable git repository connections in Pocket Claude.

## Overview

Pocket Claude uses **OAuth 2.0 with PKCE** (Proof Key for Code Exchange) for secure authentication with git providers. PKCE is the recommended approach for mobile applications as it doesn't require storing client secrets.

## Important Note About OAuth Apps

Currently, this implementation demonstrates the OAuth flow architecture. To enable full functionality, you need to register OAuth applications with each provider and add the client IDs to your backend configuration.

## GitHub OAuth Setup

### Step 1: Register OAuth App

1. Go to [GitHub Settings > Developer settings > OAuth Apps](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the details:
   - **Application name**: Pocket Claude
   - **Homepage URL**: Your app homepage or `https://localhost` for development
   - **Authorization callback URL**: `pocketclaude://oauth-callback`
   - **Application description**: (Optional)

### Step 2: Get Client Credentials

1. After creating the app, note the **Client ID**
2. For public clients (mobile apps), you don't need the Client Secret when using PKCE

### Step 3: Configure Backend

Add to your `.env` file:
```bash
GITHUB_CLIENT_ID=your_client_id_here
```

Update `api/app/services/git_service.py`:
```python
params = {
    "client_id": settings.GITHUB_CLIENT_ID,  # Add this line
    "response_type": "code",
    # ... rest of params
}
```

### Scopes Required

- `repo` - Full control of private repositories
- `user:email` - Access user email addresses

## GitLab OAuth Setup

GitLab can be self-hosted, so users provide their instance URL.

### Step 1: Register Application

1. Go to your GitLab instance: Settings > Applications
   - For gitlab.com: https://gitlab.com/-/profile/applications
   - For self-hosted: `https://your-gitlab.com/-/profile/applications`

2. Fill in the details:
   - **Name**: Pocket Claude
   - **Redirect URI**: `pocketclaude://oauth-callback`
   - **Confidential**: Uncheck (for PKCE/public client)
   - **Scopes**: Select:
     - `api` - Access the authenticated user's API
     - `read_user` - Read the authenticated user's personal information
     - `read_repository` - Allows read-access to the repository
     - `write_repository` - Allows read-write access to the repository

### Step 2: Get Application ID

1. Note the **Application ID** after creation
2. For PKCE flow, you don't need the Secret

### Step 3: Configure Backend

Add to your `.env` file:
```bash
GITLAB_CLIENT_ID=your_application_id_here
```

Update `api/app/services/git_service.py` to include client_id in GitLab flow.

### Self-Hosted GitLab

Users will provide their instance URL when connecting (e.g., `https://gitlab.example.com`).

## Gitea OAuth Setup

Gitea is always self-hosted, so users must provide their instance URL.

### Step 1: Register OAuth2 Application

1. Go to your Gitea instance: Settings > Applications > Manage OAuth2 Applications
   - URL: `https://your-gitea.com/user/settings/applications`

2. Click "Create a new OAuth2 Application"

3. Fill in the details:
   - **Application Name**: Pocket Claude
   - **Redirect URI**: `pocketclaude://oauth-callback`
   - **Confidential Client**: No (for PKCE)

### Step 2: Get Client ID

1. Note the **Client ID** after creation
2. For public clients with PKCE, secret is not required

### Step 3: Configure Backend

Add to your `.env` file:
```bash
GITEA_CLIENT_ID=your_client_id_here
```

Update `api/app/services/git_service.py` to include client_id in Gitea flow.

### Scopes Available

- `read:user` - Read user information
- `read:repository` - Read repository data
- `write:repository` - Write repository data

## PKCE Flow Details

### What is PKCE?

PKCE (Proof Key for Code Exchange) is an OAuth 2.0 extension that protects against authorization code interception attacks in public clients (like mobile apps).

### How It Works

1. **Client generates code_verifier**: Random string (43-128 characters)
2. **Client computes code_challenge**: BASE64URL(SHA256(code_verifier))
3. **Authorization request**: Includes code_challenge
4. **User authorizes**: In browser/webview
5. **Callback**: Provider redirects with authorization code
6. **Token exchange**: Client sends code + code_verifier
7. **Provider verifies**: Checks that code_verifier hashes to code_challenge
8. **Token issued**: If verification passes

### Security Benefits

- No client secret needed (safe for public clients)
- Authorization code can't be used by attackers
- Works with dynamic redirect URIs
- Mitigates code interception attacks

## Mobile App Configuration

### Capacitor Configuration

Add the custom URL scheme to your Capacitor config:

**iOS** (`ios/App/App/Info.plist`):
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>pocketclaude</string>
    </array>
  </dict>
</array>
```

**Android** (`android/app/src/main/AndroidManifest.xml`):
```xml
<activity android:name=".MainActivity">
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="pocketclaude" android:host="oauth-callback" />
  </intent-filter>
</activity>
```

### Redirect URI

All providers should use the same redirect URI:
```
pocketclaude://oauth-callback
```

This deep link will open your app after OAuth authorization.

## Backend Implementation Notes

### Token Storage

Currently using in-memory storage (development only). For production:

1. **Use a database**: PostgreSQL, MySQL, or SQLite
2. **Encrypt tokens**: Use a library like `cryptography`
3. **Per-user storage**: Associate connections with user accounts
4. **Token refresh**: Implement refresh token handling

### Example Encryption

```python
from cryptography.fernet import Fernet

class TokenEncryption:
    def __init__(self, encryption_key: bytes):
        self.fernet = Fernet(encryption_key)

    def encrypt_token(self, token: str) -> str:
        return self.fernet.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()
```

### Database Schema

```sql
CREATE TABLE git_connections (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    provider VARCHAR(20) NOT NULL,
    instance_url VARCHAR(255),
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP,
    username VARCHAR(255),
    email VARCHAR(255),
    scopes TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

## Testing OAuth Flow

### Development Testing

1. Use ngrok or similar to expose localhost:
   ```bash
   ngrok http 8000
   ```

2. Update OAuth app redirect URI to use ngrok URL temporarily

3. Test flow:
   - Open settings page
   - Click connect provider
   - Authorize in browser
   - Verify redirect back to app
   - Check connection appears in list

### Production Testing

1. Deploy backend with HTTPS
2. Configure OAuth apps with production redirect URI
3. Build and sign mobile app
4. Test on physical devices (iOS/Android)

## Troubleshooting

### "Redirect URI mismatch"

- Ensure OAuth app has exact redirect URI: `pocketclaude://oauth-callback`
- Check for trailing slashes or case differences
- Verify custom URL scheme is registered in Capacitor config

### "Invalid client"

- Check client_id is correctly configured
- For public clients, ensure "Confidential" is unchecked
- Verify client_id in backend matches registered app

### "Code challenge failed"

- Ensure code_verifier is the same value used to generate code_challenge
- Check that code_challenge_method is "S256"
- Verify SHA256 hashing and base64url encoding is correct

### "State mismatch"

- OAuth state stored in localStorage might be cleared
- Check that state parameter matches between initiate and callback
- Ensure state is preserved across app suspend/resume

## Security Best Practices

1. **Always use HTTPS** for backend API
2. **Validate OAuth state** for CSRF protection
3. **Store tokens encrypted** in production
4. **Implement token expiration** and refresh
5. **Use minimal scopes** required for functionality
6. **Revoke tokens** when user disconnects
7. **Log OAuth events** for security monitoring
8. **Rate limit** OAuth endpoints

## References

- [OAuth 2.0 for Native Apps (RFC 8252)](https://datatracker.ietf.org/doc/html/rfc8252)
- [PKCE Extension (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
- [GitHub OAuth Documentation](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)
- [GitLab OAuth Provider API](https://docs.gitlab.com/ee/api/oauth2.html)
- [Gitea OAuth2 Provider](https://docs.gitea.com/development/oauth2-provider)
- [Capacitor Deep Links](https://capacitorjs.com/docs/guides/deep-links)
