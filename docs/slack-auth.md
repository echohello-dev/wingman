# Slack Authentication Reference

Detailed guide on Slack token types and authentication for Wingman.

## Token Types

| Token | Format | Purpose | Use Case |
|-------|--------|---------|----------|
| **Bot Token** | xoxb-* | Bot actions in workspace | Posting, reading channels, reacting |
| **App Token** | xapp-* | Socket Mode connections | Development, real-time events |
| **User Token** | xoxp-* | Acts on behalf of user | Private channels, user-specific data |

### Bot Token (xoxb-*)

- Used by bot to perform actions
- Required for all operations
- Can be regenerated if compromised
- Environment variable: `SLACK_BOT_TOKEN`

**Required scopes (minimum):**
```
app_mentions:read, channels:history, channels:read, chat:write,
im:history, im:read, im:write, users:read
```

### App Token (xapp-*)

- Used for Socket Mode (WebSocket connections)
- Only needed for development with Socket Mode
- Requires `connections:write` scope
- Environment variable: `SLACK_APP_TOKEN`

### User Token (xoxp-*)

- Acts as a specific user
- Access to private channels that user can access
- Most sensitive token type
- Environment variable: `SLACK_USER_TOKEN` (optional)

## Authentication Modes

### Socket Mode (Development) ✅ Recommended for Local

**What it is**: WebSocket connection instead of HTTP webhooks. Perfect for local development and testing.

**Pros:**
- No public URL needed
- Works behind firewalls
- Easy local testing
- No redirect URIs required

**Cons:**
- Not recommended for production scale

**Setup:**
```bash
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_APP_TOKEN=xapp-xxx
SLACK_SIGNING_SECRET=xxx
```

**Installation process:**
1. Run `mise run tf-apply` (Terraform creates the app definition)
2. Go to [api.slack.com/apps](https://api.slack.com/apps) and select your app
3. Click **"Install to Workspace"** button
4. Click **"Allow"**
5. After installation, go to **OAuth & Permissions** → Copy **Bot User OAuth Token** (xoxb-...)
6. Go to **Basic Information** → **App-Level Tokens** → Click **"Generate Token and Scopes"**
   - Name it (e.g., "Socket Mode")
   - Add scope: `connections:write`
   - Copy the token (xapp-...)
7. Go to **Basic Information** → Copy **Signing Secret**
8. Add all three to `.env` and run `mise run tf-sync-vars`

### HTTP Mode (Production) ✅ Recommended for Production

**What it is**: Traditional HTTP webhooks. Better for production deployments.

**Pros:**
- Better for scale and production
- Standard HTTP infrastructure
- Mature and stable

**Cons:**
- Requires public HTTPS endpoint
- Requires valid SSL certificate

**Setup:**
```bash
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_SIGNING_SECRET=xxx
# No SLACK_APP_TOKEN needed for HTTP mode
```

**Requirements:**
- Public HTTPS URL
- Valid SSL certificate
- Configure Request URL in Slack app settings under **Event Subscriptions**

## Security Best Practices

❌ **Don't**:
- Hardcode tokens in code
- Commit .env to version control
- Request more scopes than needed
- Share tokens publicly

✅ **Do**:
- Use environment variables
- Add .env to .gitignore
- Follow principle of least privilege
- Use secret managers in production (AWS Secrets Manager, Vault, etc.)
- Rotate tokens periodically
- Verify all Slack requests with signing secret

### Request Verification

Always verify Slack requests:

```python
import hmac, hashlib, time

def verify_slack_request(request, signing_secret):
    timestamp = request.headers.get('X-Slack-Request-Timestamp')
    signature = request.headers.get('X-Slack-Signature')
    
    # Verify timestamp (reject if > 5 minutes old)
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False
    
    # Verify signature
    sig_basestring = f"v0:{timestamp}:{request.get_data().decode()}"
    my_signature = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(my_signature, signature)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Invalid token | Verify token prefix (xoxb-, xapp-, xoxp-), regenerate if needed, check .env |
| Missing scope | Add scope in OAuth & Permissions, reinstall app, get new token |
| Not in channel | Invite bot: `/invite @Wingman`, or add `channels:join` scope |
| Token revoked | Reinstall app to workspace, generate new token, update .env |
| Permission denied | Review OAuth scopes in Slack app settings |

## References

- [Slack Token Types](https://api.slack.com/authentication/token-types)
- [OAuth Scopes](https://api.slack.com/scopes)
- [Socket Mode](https://api.slack.com/apis/connections/socket)
- [Request Verification](https://api.slack.com/authentication/verifying-requests-from-slack)
- [Slack Bolt Python](https://slack.dev/bolt-python/)
