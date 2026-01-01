#!/usr/bin/env python3
"""
Post realistic support messages to Slack using session tokens.
"""
import json
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

if not XOXC_TOKEN or not XOXD_TOKEN or not CHANNEL or not TEAM_ID:
    print("❌ Missing required env vars: SLACK_XOXC_TOKEN, SLACK_XOXD_TOKEN, SLACK_CHANNEL_ID, SLACK_TEAM_ID")
    import sys
    sys.exit(1)

messages = [
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

print(f"📤 Posting {len(messages)} realistic support messages...\n")

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
        print(f"✅ Message {i}/{len(messages)} posted successfully")
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
                print(f"   ↳ Reply {reply_idx}/{len(msg_data['replies'])} posted")
            else:
                print(f"   ✗ Reply {reply_idx} failed: {reply_response.json().get('error')}")
    else:
        print(f"❌ Message {i}/{len(messages)} failed: {result.get('error')}")
    
    # Delay between main messages
    if i < len(messages):
        time.sleep(2)

print(f"\n✨ Complete! {posted_count}/{total_posts} messages/replies posted successfully")
print(f"\n✨ Complete! {posted_count}/{total_posts} messages/replies posted successfully")
