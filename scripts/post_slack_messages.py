#!/usr/bin/env python3
"""
Post realistic support messages to Slack using session tokens.
"""
import json
import time
import uuid

import requests
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
        "text": "Hey team! I'm trying to set up the new customer dashboard but getting a 403 error when accessing the analytics endpoint. Has anyone seen this before?",
        "replies": [
            "Check if you have the analytics.read permission in your API token scope",
            "Also verify the endpoint URL - it should be /api/v3/analytics not /api/analytics"
        ]
    },
    {
        "text": "Quick question - what's our current policy on data retention for user session logs? Need this for the compliance audit.",
        "replies": [
            "We keep session logs for 90 days, then they're automatically archived to cold storage for 7 years per compliance requirements"
        ]
    },
    {
        "text": "Getting a weird error in production:\n```\nTypeError: Cannot read property 'userId' of undefined\n  at UserService.authenticate (user-service.js:45)\n```\nThis started happening after the last deployment. Any ideas?",
        "replies": [
            "This looks like the user object is null. Did we change the auth middleware recently?",
            "Yes, I see the issue. The JWT decode is failing silently. I'll push a fix"
        ]
    },
    {
        "text": "Can someone point me to the documentation on how to configure the rate limiter for our API endpoints? I need to adjust the limits for the new payment service.",
        "replies": []
    },
    {
        "text": "I'm onboarding a new team member - where can I find the setup guide for local development environment? Specifically looking for the Docker compose setup instructions.",
        "replies": [
            "Check the README.md in the root - it has the full setup guide including Docker compose"
        ]
    },
    {
        "text": "Has anyone successfully integrated the webhook system with Stripe? I'm following the docs but the signature validation keeps failing.",
        "replies": [
            "Make sure you're using the webhook secret from the Stripe dashboard, not the API secret",
            "Also check that you're reading the raw request body before parsing it as JSON"
        ]
    },
    {
        "text": "Need help understanding the authentication flow in our mobile app. Is there a sequence diagram or architecture doc somewhere?",
        "replies": []
    },
    {
        "text": "Question about our database migration strategy - should I create a new migration file or modify the existing one? This is for adding a new column to the users table.",
        "replies": [
            "Always create a new migration file. Never modify existing ones that have been deployed"
        ]
    },
    {
        "text": "Getting timeout errors on the `/api/v2/reports` endpoint when generating large reports. Current timeout is set to 30s - is there a recommended value for this?",
        "replies": [
            "For report generation, we typically use 60s timeout. You can also consider making it async with a webhook callback"
        ]
    },
    {
        "text": "I need to update the error handling in our payment processing module. What's the best practice for handling transient failures vs permanent failures?",
        "replies": []
    },
    {
        "text": "Can someone explain the difference between our staging and pre-prod environments? Which one should I use for testing the new feature flag system?",
        "replies": [
            "Staging is for integration testing, pre-prod mirrors production config. Use pre-prod for feature flags"
        ]
    },
    {
        "text": "Looking for the API documentation on user permissions. I need to implement role-based access control for the new admin dashboard.",
        "replies": []
    },
    {
        "text": "Has anyone worked with the notification service recently? I'm trying to send push notifications but they're not showing up on iOS devices.",
        "replies": [
            "Did you update the APNs certificate? It expired last month",
            "Oh that's probably it! Where do I find the new certificate?"
        ]
    },
    {
        "text": "Quick one - what's our standard for logging sensitive information? Should I redact credit card numbers in application logs or do we have automatic scrubbing?",
        "replies": []
    },
    {
        "text": "I'm seeing inconsistent results from the search API. Same query returns different results on subsequent calls. Is caching enabled and could that be the issue?",
        "replies": [
            "Yes, we have Redis caching with 5-minute TTL. The inconsistency might be from cache warming"
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
    
    response = requests.post(
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
            
            reply_response = requests.post(
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
