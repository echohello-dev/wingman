# Slack Authentication Guide

This guide explains the different Slack token types and authentication options for Wingman.

## Overview

Slack uses different token types for different purposes. Understanding these tokens is crucial for properly configuring your bot.

## Token Types

### 1. Bot User OAuth Token (xoxb-*)

**Format**: `xoxb-xxxxxxxxxxxx-xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx`

**Purpose**: Used by your bot to perform actions in the workspace.

**Use Cases**:
- Posting messages
- Reading channel history
- Reacting to messages
- Joining channels
- Most bot operations

**How to Get**:
1. Go to your app's **OAuth & Permissions** page
2. Install the app to your workspace
3. Copy the **Bot User OAuth Token**

**Scopes Required** (minimum):
```
app_mentions:read
channels:history
channels:read
chat:write
im:history
im:read
im:write
users:read
```

**Environment Variable**:
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
```

**Security Notes**:
- Treat this like a password
- Never commit to version control
- Can be regenerated if compromised
- Tied to the bot user, not a specific person

---

### 2. App-Level Token (xapp-*)

**Format**: `xapp-x-xxxxxxxxxxxx-xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx`

**Purpose**: Used for Socket Mode connections.

**Use Cases**:
- Receiving events via WebSocket (Socket Mode)
- Preferred for development/testing
- No public URL required

**How to Get**:
1. Go to your app's **Basic Information** page
2. Scroll to **App-Level Tokens**
3. Click **Generate Token and Scopes**
4. Add the `connections:write` scope
5. Copy the token

**Required Scope**:
```
connections:write
```

**Environment Variable**:
```bash
SLACK_APP_TOKEN=xapp-your-app-token
```

**When to Use**:
- ✅ Local development
- ✅ Testing without exposing a public URL
- ✅ Environments behind firewalls
- ❌ Production (consider HTTP mode with proper infrastructure)

**Security Notes**:
- Less critical than bot token but still sensitive
- Only needed if using Socket Mode
- Can be regenerated

---

### 3. User OAuth Token (xoxp-*)

**Format**: `xoxp-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx`

**Purpose**: Acts on behalf of a specific user.

**Use Cases**:
- Reading private channels the user has access to
- Performing actions as a specific user
- Accessing user-level data
- Impersonating user actions

**How to Get**:
1. Implement OAuth flow in your app
2. User authorizes your app
3. Exchange code for token
4. OR manually generate at **OAuth & Permissions**

**Scopes** (examples):
```
channels:read
channels:write
chat:write
users:read
files:read
```

**Environment Variable**:
```bash
SLACK_USER_TOKEN=xoxp-your-user-token
```

**When to Use**:
- ✅ Need to access user's private channels
- ✅ Perform actions as the user
- ✅ Read user-specific data
- ⚠️ Use sparingly - prefer bot tokens

**Security Notes**:
- Most sensitive token type
- Represents a real user
- Can access private data
- Should have minimal scopes
- Can be revoked by user

---

### 4. Workspace Token (xoxc-*)

**Format**: `xoxc-xxxxxxxxxxxx-xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx`

**Purpose**: Internal Slack client token (not typically used by apps).

**Use Cases**:
- Internal Slack operations
- Not recommended for custom apps
- Can be extracted from Slack web client

**When to Use**:
- ❌ Generally avoid
- ⚠️ Only for advanced use cases
- ⚠️ Not officially supported

**Security Notes**:
- Not officially documented
- Can be invalidated
- Use official token types instead

---

### 5. Legacy Tokens (xoxd-*, xoxs-*)

**Format**: Various

**Purpose**: Older token types, mostly deprecated.

**Status**: Being phased out by Slack

**Recommendation**: Use modern token types (xoxb, xoxp, xapp)

---

## Wingman Configuration

### Minimum Setup (Socket Mode)

For basic functionality with Socket Mode:

```bash
# Required
SLACK_BOT_TOKEN=xoxb-xxx          # Bot actions
SLACK_APP_TOKEN=xapp-xxx          # Socket Mode
SLACK_SIGNING_SECRET=xxx          # Request verification
```

### Recommended Setup

```bash
# Required
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_APP_TOKEN=xapp-xxx
SLACK_SIGNING_SECRET=xxx

# Optional but recommended
SLACK_USER_TOKEN=xoxp-xxx         # For private channel access
```

### OAuth Flow Setup

If implementing OAuth for multi-workspace installation:

```bash
# Required
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_SIGNING_SECRET=xxx

# OAuth
SLACK_CLIENT_ID=xxx
SLACK_CLIENT_SECRET=xxx

# Optional
SLACK_APP_TOKEN=xapp-xxx          # If using Socket Mode
```

## Authentication Modes

### Socket Mode (Development)

**Best for**: Local development, testing

**Pros**:
- No public URL needed
- Easy to set up
- Works behind firewalls
- Real-time events

**Cons**:
- Not ideal for production scale
- Requires App-Level Token

**Setup**:
```bash
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_APP_TOKEN=xapp-xxx
SLACK_SIGNING_SECRET=xxx
```

**Code**:
```python
from slack_bolt.adapter.socket_mode import SocketModeHandler

handler = SocketModeHandler(app, SLACK_APP_TOKEN)
handler.start()
```

---

### HTTP Mode (Production)

**Best for**: Production deployments

**Pros**:
- Better for scale
- Standard HTTP infrastructure
- No WebSocket connection

**Cons**:
- Requires public HTTPS endpoint
- More complex setup

**Setup**:
```bash
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_SIGNING_SECRET=xxx
# No SLACK_APP_TOKEN needed
```

**Requirements**:
- Public HTTPS URL
- Valid SSL certificate
- Configure Request URL in Slack app

**Code**:
```python
from flask import Flask, request
from slack_bolt.adapter.flask import SlackRequestHandler

app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)
```

---

## Security Best Practices

### 1. Token Storage

❌ **Never**:
```bash
# Don't hardcode
SLACK_BOT_TOKEN = "xoxb-123456789..."

# Don't commit
git add .env
```

✅ **Do**:
```bash
# Use environment variables
export SLACK_BOT_TOKEN=xoxb-xxx

# Use .env files (gitignored)
echo ".env" >> .gitignore

# Use secret managers (production)
# AWS Secrets Manager, HashiCorp Vault, etc.
```

### 2. Token Scopes

❌ **Don't**:
- Request more scopes than needed
- Use admin scopes unnecessarily
- Keep unused scopes

✅ **Do**:
- Follow principle of least privilege
- Review scopes regularly
- Remove unused scopes

### 3. Token Rotation

✅ **Do**:
- Rotate tokens periodically
- Rotate immediately if compromised
- Use different tokens per environment
- Log token usage

### 4. Request Verification

Always verify requests from Slack:

```python
import hmac
import hashlib

def verify_slack_request(request, signing_secret):
    timestamp = request.headers.get('X-Slack-Request-Timestamp')
    signature = request.headers.get('X-Slack-Signature')
    
    # Verify timestamp
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

### "Invalid Token"

**Causes**:
- Wrong token type
- Token expired/revoked
- Token not properly set

**Solutions**:
1. Verify token starts with correct prefix (xoxb-, xapp-, xoxp-)
2. Regenerate token in Slack app settings
3. Check environment variables are loaded
4. Verify no extra whitespace in token

### "Missing Scope"

**Causes**:
- Token doesn't have required scope
- Scope was removed

**Solutions**:
1. Go to **OAuth & Permissions**
2. Add required scope
3. Reinstall app to workspace
4. Get new token

### "Not in Channel"

**Causes**:
- Bot not invited to channel
- Trying to read without permission

**Solutions**:
1. Invite bot: `/invite @Wingman`
2. Add `channels:join` scope for auto-join
3. Check bot is added to workspace

### "Token Revoked"

**Causes**:
- App uninstalled
- Token manually revoked
- Token expired

**Solutions**:
1. Reinstall app
2. Generate new token
3. Update environment variables

## Token Comparison

| Feature | Bot Token (xoxb) | App Token (xapp) | User Token (xoxp) |
|---------|------------------|------------------|-------------------|
| **Purpose** | Bot actions | Socket Mode | User actions |
| **Scope** | Bot scopes | Connection only | User scopes |
| **Access** | Public channels | N/A | Private channels |
| **Required** | ✅ Yes | ⚠️ Socket Mode | ❌ Optional |
| **Sensitivity** | 🔒 High | 🔒 Medium | 🔒🔒 Very High |
| **Best For** | Most actions | Development | User context |

## References

- [Slack Token Types](https://api.slack.com/authentication/token-types)
- [OAuth Scopes](https://api.slack.com/scopes)
- [Socket Mode](https://api.slack.com/apis/connections/socket)
- [Request Verification](https://api.slack.com/authentication/verifying-requests-from-slack)
- [Security Best Practices](https://api.slack.com/authentication/best-practices)

## Support

If you encounter authentication issues:

1. Check [Slack API Documentation](https://api.slack.com/)
2. Review [Slack Bolt Documentation](https://slack.dev/bolt-python/)
3. Verify token types and scopes
4. Check application logs
5. Open an issue on GitHub

---

**Remember**: Treat all tokens as passwords. Never share them publicly or commit them to version control.
