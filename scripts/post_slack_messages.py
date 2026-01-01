#!/usr/bin/env python3
"""
Post realistic support messages to Slack using session tokens.
Generates conversations using OpenRouter Gemini 3 Flash if API key available.
Can optionally use GitHub context (commits, PRs, issues) to make messages more realistic.
"""
import json
import subprocess
import time
import uuid

import httpx
from dotenv import dotenv_values

# Load config
config = dotenv_values("/Users/johnny/projects/github.com/echohello-dev/wingman/.env")

XOXC_TOKEN = config['SLACK_XOXC_TOKEN']
XOXD_TOKEN = config['SLACK_XOXD_TOKEN']
CHANNEL = config.get('SLACK_CHANNEL_ID')
TEAM_ID = config.get('SLACK_TEAM_ID')
OPENROUTER_API_KEY = config.get('OPENROUTER_API_KEY')
GITHUB_TOKEN = config.get('GITHUB_TOKEN')

if not XOXC_TOKEN or not XOXD_TOKEN or not CHANNEL or not TEAM_ID:
    print("Missing required env vars: SLACK_XOXC_TOKEN, SLACK_XOXD_TOKEN, SLACK_CHANNEL_ID, SLACK_TEAM_ID")
    import sys
    sys.exit(1)


def get_github_context():
    """Fetch recent commits, PRs, and issues from GitHub to provide context for AI."""
    print("Fetching GitHub context...")
    
    # Try to get GitHub token from gh auth
    gh_token = GITHUB_TOKEN
    if not gh_token:
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                gh_token = result.stdout.strip()
                print("Using GitHub token from gh auth")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    if not gh_token:
        print("No GitHub token available, skipping GitHub context")
        return None
    
    context = {}
    headers = {"Authorization": f"Bearer {gh_token}"}
    
    try:
        # Get recent commits
        print("  Fetching recent commits...")
        response = httpx.get(
            "https://api.github.com/repos/echohello-dev/wingman/commits",
            headers=headers,
            params={"per_page": 10},
            timeout=10
        )
        if response.status_code == 200:
            commits = response.json()
            context['commits'] = [
                {
                    "message": c.get('commit', {}).get('message', ''),
                    "author": c.get('commit', {}).get('author', {}).get('name', 'Unknown'),
                    "date": c.get('commit', {}).get('author', {}).get('date', '')
                }
                for c in commits[:5]
            ]
        
        # Get recent PRs
        print("  Fetching recent PRs...")
        response = httpx.get(
            "https://api.github.com/repos/echohello-dev/wingman/pulls",
            headers=headers,
            params={"state": "all", "per_page": 10},
            timeout=10
        )
        if response.status_code == 200:
            prs = response.json()
            context['prs'] = [
                {
                    "title": pr.get('title', ''),
                    "number": pr.get('number', 0),
                    "state": pr.get('state', ''),
                    "author": pr.get('user', {}).get('login', 'Unknown')
                }
                for pr in prs[:5]
            ]
        
        # Get recent issues
        print("  Fetching recent issues...")
        response = httpx.get(
            "https://api.github.com/repos/echohello-dev/wingman/issues",
            headers=headers,
            params={"state": "all", "per_page": 10},
            timeout=10
        )
        if response.status_code == 200:
            issues = response.json()
            context['issues'] = [
                {
                    "title": i.get('title', ''),
                    "number": i.get('number', 0),
                    "state": i.get('state', ''),
                    "labels": [l.get('name', '') for l in i.get('labels', [])]
                }
                for i in issues[:5]
            ]
        
        print(f"GitHub context loaded: {len(context)} sections")
        return context
    except Exception as e:
        print(f"Error fetching GitHub context: {e}")
        return None


def generate_messages_with_ai(github_context=None):
    """Generate realistic Slack conversations using OpenRouter Gemini 3 Flash with structured outputs."""
    print("Generating conversations with Gemini 3 Flash...")
    
    # Build prompt with GitHub context if available
    base_prompt = """Generate 20 realistic Slack channel messages for an engineering team support channel. 
Messages should include:
- Technical questions and troubleshooting
- Status updates and announcements
- Deployment notices
- Deprecation warnings
- Casual but professional tone (semi-formal)
- Some typos and natural language variation
- Emoji use (minimal, natural)
- Mix of quick questions, detailed issues, and team coordination
- Each message has 0-3 replies"""

    if github_context:
        context_str = "Use this real project context when generating messages:\n"
        if github_context.get('commits'):
            context_str += "\nRecent commits:\n"
            for c in github_context['commits'][:3]:
                context_str += f"- {c['message'][:60]} (by {c['author']})\n"
        if github_context.get('prs'):
            context_str += "\nRecent PRs:\n"
            for pr in github_context['prs'][:3]:
                context_str += f"- #{pr['number']}: {pr['title']} ({pr['state']})\n"
        if github_context.get('issues'):
            context_str += "\nRecent issues:\n"
            for issue in github_context['issues'][:3]:
                context_str += f"- #{issue['number']}: {issue['title']} ({', '.join(issue['labels'])})\n"
        
        prompt = base_prompt + "\n\n" + context_str
    else:
        prompt = base_prompt

    # JSON Schema for structured output
    schema = {
        "type": "object",
        "properties": {
            "messages": {
                "type": "array",
                "description": "Array of Slack messages",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The main message text"
                        },
                        "replies": {
                            "type": "array",
                            "description": "Array of reply messages",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["text", "replies"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["messages"],
        "additionalProperties": False
    }

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/echohello-dev/wingman"
            },
            json={
                "model": "google/gemini-3-flash-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 4000,
                "top_p": 0.9,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "slack_messages",
                        "strict": True,
                        "schema": schema
                    }
                }
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # With structured outputs, content is already valid JSON
            try:
                data = json.loads(content)
                messages = data.get('messages', [])
                print(f"Generated {len(messages)} messages from Gemini 3 Flash")
                return messages
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"   Content: {content[:200]}")
                return None
        else:
            error_body = response.text
            print(f"AI generation failed: {response.status_code}")
            print(f"   Response: {error_body[:200]}")
            return None
    except httpx.TimeoutException:
        print("AI generation timed out (30s)")
        return None
    except Exception as e:
        print(f"AI generation error: {e}")
        return None


# Default fallback messages
fallback_messages = [
    {
        "text": "Hey team, I'm getting a 403 on the new dashboard analytics endpoint :thinking_face: Has anyone else run into this?",
        "replies": [
            "Did you check if your token has the analytics.read scope?",
            "Also, make sure the URL is /api/v3/analytics, not /api/analytics. Easy typo to make"
        ]
    },
    {
        "text": "Quick question - what's our data retention policy for session logs? Need this for the compliance audit",
        "replies": [
            "90 days in hot storage, then goes to cold storage for 7 years per policy"
        ]
    },
    {
        "text": "This error just showed up in prod :bug:: \n```\nTypeError: Cannot read property 'userId' of undefined\n  at UserService.authenticate (user-service.js:45)\n```\nAnyone know what we deployed?",
        "replies": [
            "Did we change the auth middleware recently?",
            "Yeah, I see it now. JWT decode is failing silently. Let me push a fix"
        ]
    },
    {
        "text": "Could someone send me the rate limiter config docs? Setting up limits for the payment service and need guidance",
        "replies": []
    },
    {
        "text": "Onboarding new team member tomorrow - where can I find the local dev setup guide? Need the Docker compose instructions :wave:",
        "replies": [
            "Root README has everything including the Docker compose setup :whale:"
        ]
    },
    {
        "text": "Has anyone successfully integrated Stripe webhooks? Signature validation keeps failing and I can't figure out why",
        "replies": [
            "Make sure you're using the webhook secret from the dashboard, not your API secret",
            "Also gotta read the raw request body before parsing as JSON. That's a common gotcha"
        ]
    },
    {
        "text": "Could use some help - how does the authentication flow work on mobile? Is there a sequence diagram or docs somewhere?",
        "replies": []
    },
    {
        "text": "Quick question on database migrations: should I create a new file or modify the existing one? Adding a column to the users table",
        "replies": [
            "Always create a new migration file. Never modify deployed migrations - that's how things break :no_entry:"
        ]
    },
    {
        "text": "Getting timeout errors on /api/v2/reports when generating large reports. Timeout is set to 30s currently - what's the recommended value?",
        "replies": [
            "60s is typical for report generation. Or consider making it async with a callback if reports are heavy"
        ]
    },
    {
        "text": "What's the best approach for handling retries in the payment module? How do you differentiate between transient and permanent failures?",
        "replies": []
    },
    {
        "text": "Question - staging vs pre-prod: which one should I use for feature flag testing? :rocket:",
        "replies": [
            "Staging is for integration testing. Pre-prod mirrors production config. Use pre-prod for feature flags"
        ]
    },
    {
        "text": "Looking for documentation on user permissions. Need to implement role-based access control for the admin dashboard",
        "replies": []
    },
    {
        "text": "Push notifications aren't showing on iOS. Has anyone worked with the notification service recently? :iphone:",
        "replies": [
            "When's the last time you updated the APNs certificate? Pretty sure it expired :warning:",
            "Oh, that's probably it! Where can I find the new one? :bulb:"
        ]
    },
    {
        "text": "Security question - do we automatically redact credit card numbers in logs, or should they be manually scrubbed?",
        "replies": []
    },
    {
        "text": "Seeing inconsistent results from the search API. Same query returns different results on subsequent calls. Is Redis caching enabled?",
        "replies": [
            "Yes, Redis caching with 5-minute TTL. Could be cache warming issues :redis:"
        ]
    },
    {
        "text": ":rocket: heads up - deploying auth service v2.1 to staging in 30min. if you're testing auth stuff plz use staging-v2",
        "replies": [
            "thanks for the heads up! when's it going to prod?",
            "probably friday if no issues in staging. ill ping the channel"
        ]
    },
    {
        "text": "just merged PR #487 - refactored the payment webhook handler to be more robust. plz review when u get a sec",
        "replies": [
            "lgtm! just left a comment on line 42",
            "approved! ship it"
        ]
    },
    {
        "text": ":warning: ATTENTION: we're deprecating the old `/api/v1/users` endpoint next month. migrate to `/api/v2/users` asap. see docs for migration guide",
        "replies": [
            "how long do we have to migrate?",
            "until feb 15. we're sending emails to all customers but best to get it done early"
        ]
    },
    {
        "text": "performance update: search endpoint now doing fuzzy matching. this may affect some queries but accuracy is way better. feedback welcome :mag:",
        "replies": [
            "nice! how's the perf impact?",
            "minimal actually. redis caching handles most of it"
        ]
    },
    {
        "text": "planned maintenance: database will be down for upgrades tomorrow 2am-3am pst. notify ur customers pls",
        "replies": [
            "done. already sent notifications",
            "thx. also FYI we're upgrading to postgres 15"
        ]
    },
    {
        "text": "FYI rolling out new UI theme next week. if things look weird that's expected lol. should stabilize by wed",
        "replies": [
            "dark mode finally??",
            "yeah! and better mobile responsive too"
        ]
    },
    {
        "text": "quick status: api latency spiked this morning around 9am but we've sorted it now. no data loss",
        "replies": [
            "what caused it?",
            "one of the load balancers got overloaded. scaled it up"
        ]
    }
]

# Choose messages source
if OPENROUTER_API_KEY:
    github_context = get_github_context()
    generated = generate_messages_with_ai(github_context)
    messages = generated if generated else fallback_messages
else:
    print("No OpenRouter API key found, using deterministic messages")
    messages = fallback_messages

print(f"Posting {len(messages)} realistic support messages...\n")

success = 0
total_posts = sum(1 + len(msg['replies']) for msg in messages)
posted_count = 0

for i, msg_data in enumerate(messages, 1):
    text = msg_data['text']
    
    # Create rich text blocks
    blocks = [{
        "type": "rich_text",
        "elements": [{
            "type": "rich_text_section",
            "elements": [{"type": "text", "text": text}]
        }]
    }]
    
    # Match browser's exact form data
    data = {
        'token': XOXC_TOKEN,
        'channel': CHANNEL,
        'type': 'message',
        'xArgs': '{}',
        'unfurl': '[]',
        'client_context_team_id': TEAM_ID,
        'blocks': json.dumps(blocks),
        'include_channel_perm_error': 'true',
        'client_msg_id': str(uuid.uuid4()),
        '_x_reason': 'webapp_message_send',
        '_x_mode': 'online',
        '_x_sonic': 'true',
        '_x_app_name': 'client'
    }
    
    cookies = {'d': XOXD_TOKEN}
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    
    response = httpx.post(
        'https://johnnyhuy.slack.com/api/chat.postMessage',
        data=data,
        cookies=cookies,
        headers=headers
    )
    
    result = response.json()
    
    if result.get('ok'):
        posted_count += 1
        thread_ts = result['ts']
        print(f"Message {i}/{len(messages)} posted successfully")
        success += 1
        
        # Post replies if any
        for reply_idx, reply_text in enumerate(msg_data['replies'], 1):
            time.sleep(1)  # Small delay between replies
            
            reply_blocks = [{
                "type": "rich_text",
                "elements": [{
                    "type": "rich_text_section",
                    "elements": [{"type": "text", "text": reply_text}]
                }]
            }]
            
            reply_data = {
                'token': XOXC_TOKEN,
                'channel': CHANNEL,
                'type': 'message',
                'xArgs': '{}',
                'reply_broadcast': 'false',
                'thread_ts': thread_ts,
                'unfurl': '[]',
                'client_context_team_id': TEAM_ID,
                'blocks': json.dumps(reply_blocks),
                'include_channel_perm_error': 'true',
                'client_msg_id': str(uuid.uuid4()),
                '_x_reason': 'webapp_message_send',
                '_x_mode': 'online',
                '_x_sonic': 'true',
                '_x_app_name': 'client'
            }
            
            reply_response = httpx.post(
                'https://johnnyhuy.slack.com/api/chat.postMessage',
                data=reply_data,
                cookies=cookies,
                headers=headers
            )
            
            if reply_response.json().get('ok'):
                posted_count += 1
                print(f"   Reply {reply_idx}/{len(msg_data['replies'])} posted")
            else:
                print(f"   Reply {reply_idx} failed: {reply_response.json().get('error')}")
    else:
        print(f"Message {i}/{len(messages)} failed: {result.get('error')}")
    
    # Delay between main messages
    if i < len(messages):
        time.sleep(2)

print(f"\nComplete! {posted_count}/{total_posts} messages/replies posted successfully")
print(f"\n✨ Complete! {posted_count}/{total_posts} messages/replies posted successfully")
