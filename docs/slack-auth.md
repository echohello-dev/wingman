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

**Pros:** No public URL needed, works behind firewalls, easy setup

**Cons:** Not ideal for production scale

**Setup:**
```bash
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_APP_TOKEN=xapp-xxx
SLACK_SIGNING_SECRET=xxx
```

**Code:**
```python
from slack_bolt.adapter.socket_mode import SocketModeHandler

handler = SocketModeHandler(app, SLACK_APP_TOKEN)
handler.start()
```

### HTTP Mode (Production) ✅ Recommended for Production

**Pros:** Better for scale, standard HTTP infrastructure

**Cons:** Requires public HTTPS endpoint

**Setup:**
```bash
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_SIGNING_SECRET=xxx
# No SLACK_APP_TOKEN needed
```

**Requirements:**
- Public HTTPS URL
- Valid SSL certificate
- Configure Request URL in Slack app settings

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
