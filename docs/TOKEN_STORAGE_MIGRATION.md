# Token Storage Migration Guide

This guide explains the migration from in-memory token storage to production-ready encrypted database storage.

## What Changed?

### Before (In-Memory Storage)
- OAuth tokens stored in Python dictionaries
- Lost on server restart
- No encryption
- Development-only
- Not production-ready

### After (Database + Encryption)
- OAuth tokens stored in SQLite/PostgreSQL database
- Encrypted using Fernet (AES-128 CBC)
- Persistent across restarts
- Automatic token refresh before expiration
- Production-ready

## New Features

### 1. **Encrypted Token Storage**
All OAuth access and refresh tokens are encrypted before being stored in the database using Fernet symmetric encryption.

- **Algorithm**: Fernet (AES-128 CBC + HMAC)
- **Key Source**: `ENCRYPTION_KEY` environment variable
- **Automatic**: Encrypt on write, decrypt on read

### 2. **Automatic Token Refresh**
Tokens are automatically refreshed 10 minutes before expiration:

- Checks expiration on each token access
- Uses refresh token to get new access token
- Updates database with new encrypted tokens
- Transparent to API clients
- No manual intervention required

### 3. **Database Persistence**
Connections persist across server restarts:

- **Development**: SQLite (file-based)
- **Production**: PostgreSQL (recommended)
- Automatic schema creation on first run
- Connection pooling and async support

## Setup Instructions

### 1. Generate Encryption Key

Generate a secure encryption key for your environment:

```bash
cd api
uv run python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

**Example output**:
```
B_p8LAliDskrtwFlnXv6TMuw-6536O3UZatuDeaA8wY=
```

⚠️ **IMPORTANT**:
- Generate a NEW key for each environment (dev, staging, prod)
- NEVER commit encryption keys to version control
- Back up your encryption key securely
- Losing the key makes all stored tokens unrecoverable

### 2. Update Environment Variables

Add to your `.env` file:

```bash
# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./pocket_claude.db

# Database (PostgreSQL for production)
# DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# Encryption Key (REQUIRED)
ENCRYPTION_KEY=<your_generated_key_here>
```

### 3. Install Dependencies

Dependencies are automatically installed with:

```bash
uv sync
```

New dependencies added:
- `sqlalchemy>=2.0.0` - ORM and database toolkit
- `alembic>=1.13.0` - Database migrations
- `cryptography>=44.0.0` - Token encryption
- `aiosqlite>=0.20.0` - Async SQLite driver

### 4. Start the Application

The database will be automatically initialized on first startup:

```bash
python -m uvicorn app.main:app --reload
```

You should see:
```
INFO:app.main:Initializing database
INFO:app.core.database:Created database engine for sqlite+aiosqlite:///./pocket_claude.db
INFO:app.core.database:Database tables initialized
```

## Database Schema

The `git_connections` table stores encrypted connection data:

```sql
CREATE TABLE git_connections (
    id VARCHAR(32) PRIMARY KEY,
    provider VARCHAR(20) NOT NULL,
    instance_url VARCHAR(255),
    username VARCHAR(255),
    email VARCHAR(255),
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scopes JSON,
    connected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
```

## Token Refresh Flow

1. **Client Requests Token**
   ```python
   access_token = await git_service.get_decrypted_token(connection_id)
   ```

2. **Service Checks Expiration**
   - If expires in < 10 minutes → trigger refresh
   - If expired → trigger refresh
   - Otherwise → return current token

3. **Automatic Refresh** (if needed)
   - Use refresh_token to request new access_token
   - Encrypt and store new tokens in database
   - Update expiration time
   - Return fresh access_token

4. **Client Uses Token**
   - Receives valid, fresh access_token
   - No awareness of refresh happening
   - Transparent token management

## API Changes

### Async Methods

The following methods are now async and must be awaited:

```python
# Before (synchronous)
connection = git_service.get_connection(connection_id)
connections = git_service.list_connections()
git_service.delete_connection(connection_id)

# After (async)
connection = await git_service.get_connection(connection_id)
connections = await git_service.list_connections()
await git_service.delete_connection(connection_id)
```

### New Methods

**Get Decrypted Token** (with auto-refresh):
```python
access_token = await git_service.get_decrypted_token(connection_id)
```

This method:
- Retrieves encrypted token from database
- Decrypts the token
- Checks if refresh is needed
- Automatically refreshes if necessary
- Returns valid access token

## Production Deployment

### PostgreSQL Setup

1. **Install PostgreSQL** (if not already installed)

2. **Create Database**
   ```sql
   CREATE DATABASE pocket_claude;
   CREATE USER pocket_claude_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE pocket_claude TO pocket_claude_user;
   ```

3. **Update DATABASE_URL**
   ```bash
   DATABASE_URL=postgresql+asyncpg://pocket_claude_user:secure_password@localhost:5432/pocket_claude
   ```

4. **Install PostgreSQL Driver**
   ```bash
   uv add asyncpg
   ```

### Security Best Practices

1. **Encryption Key Management**
   - Use secret management service (AWS Secrets Manager, HashiCorp Vault)
   - Rotate keys periodically (requires user re-authentication)
   - Different key per environment
   - Never log or expose encryption keys

2. **Database Security**
   - Enable SSL/TLS for database connections
   - Use strong database passwords
   - Restrict database network access
   - Enable database encryption at rest
   - Regular database backups

3. **Token Security**
   - Tokens are encrypted in database
   - Tokens decrypted only when needed
   - No token logging
   - Automatic refresh prevents expired tokens
   - Token scopes limited to minimum required

### Monitoring

Monitor these metrics in production:

- **Token Refresh Rate**: How often tokens are refreshed
- **Token Refresh Failures**: Failed refresh attempts
- **Database Connection Pool**: Active/idle connections
- **Encryption/Decryption Errors**: Key or encryption issues

### Backup Strategy

**Critical Data to Backup**:
1. **Encryption Key** - Without this, tokens are unrecoverable
2. **Database** - Contains encrypted tokens and metadata
3. **Environment Configuration** - `.env` file (without sensitive values committed)

**Backup Frequency**:
- Encryption key: Once (store in secure vault)
- Database: Daily (or more frequently for production)
- Configuration: On each change

## Troubleshooting

### "ENCRYPTION_KEY environment variable must be set"

**Solution**: Generate and set encryption key in `.env`:
```bash
uv run python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
# Add output to .env as ENCRYPTION_KEY=<key>
```

### "Token refresh failed"

**Possible Causes**:
- Refresh token expired or invalid
- OAuth provider connectivity issues
- Invalid client_id configuration

**Solution**:
1. Check logs for detailed error message
2. Verify provider OAuth configuration
3. User may need to re-authenticate

### "Invalid token" during decryption

**Possible Causes**:
- Encryption key changed
- Database corruption
- Token manually modified

**Solution**:
1. Verify `ENCRYPTION_KEY` matches what was used to encrypt
2. If key lost, users must re-authenticate
3. Check database integrity

### Database connection errors

**Solution**:
1. Verify `DATABASE_URL` is correct
2. Check database server is running
3. Verify database credentials
4. Check network connectivity
5. Review database logs

## Migration from In-Memory

If you have existing OAuth connections in memory (from before this update):

1. **They will be lost** - In-memory storage is not persistent
2. Users will need to **re-authenticate** after upgrade
3. No migration path from memory to database
4. Fresh start with new database storage

## Testing

### Unit Tests

Test encryption service:
```python
from app.core.encryption import get_encryption_service

service = get_encryption_service()
encrypted = service.encrypt("test_token")
decrypted = service.decrypt(encrypted)
assert decrypted == "test_token"
```

### Integration Tests

Test token refresh:
```python
# Create mock connection with expiring token
# Call get_decrypted_token()
# Verify token was refreshed
# Verify new token stored in database
```

## Support

For issues or questions:
- Check this migration guide
- Review application logs
- See `docs/GIT_OAUTH_SETUP.md` for OAuth configuration
- Open issue on GitHub

## References

- [Cryptography Fernet Documentation](https://cryptography.io/en/latest/fernet/)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [OAuth 2.0 Token Refresh](https://datatracker.ietf.org/doc/html/rfc6749#section-6)
