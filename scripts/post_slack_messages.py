#!/usr/bin/env python3
"""
Post realistic support messages to Slack using session tokens.
Generates conversations using OpenRouter Gemini 3 Flash if API key available.
Can optionally use GitHub context (commits, PRs, issues) to make messages more realistic.
Includes message formatting (bold, links, emojis, lists) and reactions.
"""
import json
import logging
import re
import subprocess
import sys
import time
import uuid

import httpx
from dotenv import dotenv_values
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn,
                           TaskProgressColumn, TextColumn)

# ============================================================================
# Rich Console & Logging Configuration
# ============================================================================

console = Console()

# Configure logging with Rich handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
)

logger = logging.getLogger(__name__)

# Disable httpx logging to reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)

# Load config
with console.status("[bold blue]Loading environment configuration...", spinner="dots"):
    config = dotenv_values("/Users/johnny/projects/github.com/echohello-dev/wingman/.env")
    
    XOXC_TOKEN = config['SLACK_XOXC_TOKEN']
    XOXD_TOKEN = config['SLACK_XOXD_TOKEN']
    SLACK_ORG_URL = config.get('SLACK_ORG_URL')
    CHANNEL = config.get('SLACK_CHANNEL_ID')
    TEAM_ID = config.get('SLACK_TEAM_ID')
    OPENROUTER_API_KEY = config.get('OPENROUTER_API_KEY')
    GITHUB_TOKEN = config.get('GITHUB_TOKEN')
    time.sleep(0.2)  # Brief pause for visual effect

if not XOXC_TOKEN or not XOXD_TOKEN or not SLACK_ORG_URL or not CHANNEL or not TEAM_ID:
    console.print("[bold red]✗ Missing required environment variables:[/bold red]")
    if not XOXC_TOKEN:
        console.print("  [red]- SLACK_XOXC_TOKEN[/red]")
    if not XOXD_TOKEN:
        console.print("  [red]- SLACK_XOXD_TOKEN[/red]")
    if not SLACK_ORG_URL:
        console.print("  [red]- SLACK_ORG_URL[/red]")
    if not CHANNEL:
        console.print("  [red]- SLACK_CHANNEL_ID[/red]")
    if not TEAM_ID:
        console.print("  [red]- SLACK_TEAM_ID[/red]")
    sys.exit(1)

console.print("[bold green]✓ All required environment variables loaded[/bold green]")


def parse_rich_text_from_string(text):
    """
    Parse a string with markdown-like formatting and convert to rich_text elements.
    Supports:
    - *bold text* or **bold text**
    - _italic text_
    - ~strikethrough~
    - `code`
    - <url|label> or <url> for links
    - :emoji_name: for emoji
    - Bullet points with • or -
    """
    elements = []
    
    # Split by newlines to handle lists
    lines = text.split('\n')
    
    for line_idx, line in enumerate(lines):
        # Check if this is a bullet point
        is_bullet = line.strip().startswith('•') or (line.strip().startswith('-') and len(line.strip()) > 1 and line.strip()[1] == ' ')
        
        if is_bullet:
            # Add spacing before list items
            if line_idx > 0 and not lines[line_idx - 1].strip().startswith(('•', '-')):
                elements.append({"type": "text", "text": "\n"})
            
            # Process the line content (remove bullet point)
            line_content = re.sub(r'^[\s•-]+', '', line).lstrip()
        else:
            line_content = line
        
        # Parse inline formatting using a more robust approach
        pos = 0
        pattern = re.compile(
            r'(\*\*)([^*]+?)\1|'  # **bold** (double asterisk)
            r'(\*)([^\s*][^*]*?[^\s*]|[^\s*])\3(?!\*)|'  # *bold* (single asterisk, non-greedy)
            r'(_)([^_]+?)\5|'  # _italic_
            r'(~)([^~]+?)\7|'  # ~strikethrough~
            r'(`)([^`]+?)\9|'  # `code`
            r'(<(https?://[^|>]+)(?:\|([^>]+))?[^<]*>)|'  # <url|label> or <url>
            r'(https?://[^\s<>]+)|'  # Raw URLs (https://example.com/...)
            r'(:([a-z_0-9]+):)'  # :emoji_name:
        )
        
        for match in pattern.finditer(line_content):
            # Add text before match
            if match.start() > pos:
                plain_text = line_content[pos:match.start()]
                if plain_text:
                    elements.append({"type": "text", "text": plain_text})
            
            # Process the match
            if match.group(2):  # **bold**
                elements.append({
                    "type": "text",
                    "text": match.group(2),
                    "style": {"bold": True}
                })
            elif match.group(4):  # *bold*
                elements.append({
                    "type": "text",
                    "text": match.group(4),
                    "style": {"bold": True}
                })
            elif match.group(6):  # _italic_
                elements.append({
                    "type": "text",
                    "text": match.group(6),
                    "style": {"italic": True}
                })
            elif match.group(8):  # ~strikethrough~
                elements.append({
                    "type": "text",
                    "text": match.group(8),
                    "style": {"strike": True}
                })
            elif match.group(10):  # `code`
                elements.append({
                    "type": "text",
                    "text": match.group(10),
                    "style": {"code": True}
                })
            elif match.group(12):  # <url|label> or <url>
                url = match.group(12)
                label = match.group(13) if match.group(13) else url
                elements.append({
                    "type": "link",
                    "url": url,
                    "text": label
                })
            elif match.group(14):  # Raw URL (https://...)
                url = match.group(14)
                # Extract GitHub issue/PR number if available
                if 'github.com' in url:
                    if '/pull/' in url or '/issues/' in url:
                        # Extract just the repo and number for cleaner display
                        parts = url.rstrip('/').split('/')
                        if len(parts) >= 2:
                            label = f"{parts[-2]}/{parts[-1]}"
                        else:
                            label = url
                    else:
                        label = url.split('/')[-1][:20]
                else:
                    label = url[:30] + ('...' if len(url) > 30 else '')
                elements.append({
                    "type": "link",
                    "url": url,
                    "text": label
                })
            elif match.group(16):  # :emoji:
                elements.append({
                    "type": "emoji",
                    "name": match.group(16)
                })
            
            pos = match.end()
        
        # Add remaining text
        if pos < len(line_content):
            remaining = line_content[pos:]
            if remaining:
                elements.append({"type": "text", "text": remaining})
        
        # Add newline between lines (except last)
        if line_idx < len(lines) - 1:
            elements.append({"type": "text", "text": "\n"})
    
    return elements if elements else [{"type": "text", "text": text}]


def add_reaction(channel, timestamp, emoji):
    """Add a reaction to a message."""
    data = {
        'token': XOXC_TOKEN,
        'channel': channel,
        'timestamp': timestamp,
        'name': emoji,
    }
    
    cookies = {'d': XOXD_TOKEN}
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    
    try:
        response = httpx.post(
            f'{SLACK_ORG_URL}/api/reactions.add',
            data=data,
            cookies=cookies,
            headers=headers,
            timeout=5
        )
        return response.json().get('ok', False)
    except Exception:
        return False



def get_user_repos(gh_token, max_repos=5):
    """Fetch the authenticated user's repos, prioritizing recent activity."""
    try:
        # Get user's repos (owned and contributed to)
        logger.debug(f"Fetching user's repositories (top {max_repos})...")
        response = httpx.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {gh_token}"},
            params={"sort": "updated", "per_page": 20},
            timeout=10
        )
        if response.status_code == 200:
            repos = response.json()
            # Get repo full names, sort by recent activity
            repo_names = [r.get('full_name') for r in repos if r.get('full_name')]
            selected = repo_names[:max_repos]
            console.print(f"[bold green]✓ Found {len(repo_names)} user repos, using top {len(selected)}[/bold green]")
            for i, repo in enumerate(selected, 1):
                console.print(f"  [cyan][{i}][/cyan] {repo}")
            return selected
        else:
            logger.warning(f"GitHub API returned status {response.status_code}")
    except httpx.TimeoutException:
        logger.error("Timeout fetching user repos from GitHub")
    except Exception as e:
        logger.error(f"Error fetching user repos: {type(e).__name__}: {e}")
    
    return []


def get_github_context():
    """Fetch recent commits, PRs, and issues from user's repositories."""
    console.print("\n[bold blue]━━━ GitHub Context ━━━[/bold blue]")
    
    # Try to get GitHub token from gh auth
    gh_token = GITHUB_TOKEN
    if not gh_token:
        try:
            logger.debug("GITHUB_TOKEN not set, attempting to get from 'gh auth token'...")
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                gh_token = result.stdout.strip()
                console.print("[bold green]✓ Using GitHub token from 'gh auth token'[/bold green]")
            else:
                logger.warning("'gh auth token' failed with return code {result.returncode}")
        except subprocess.TimeoutExpired:
            logger.error("Timeout running 'gh auth token'")
        except FileNotFoundError:
            logger.error("'gh' command not found. Install GitHub CLI or set GITHUB_TOKEN env var")
    else:
        logger.debug("Using GITHUB_TOKEN from environment")
    
    if not gh_token:
        logger.warning("No GitHub token available, skipping GitHub context")
        return None
    
    context = {
        'commits': [],
        'prs': [],
        'issues': []
    }
    
    headers = {"Authorization": f"Bearer {gh_token}"}
    
    try:
        # Get user's repos (fallback to wingman if none found)
        repos = get_user_repos(gh_token)
        if not repos:
            logger.warning("No user repos found, falling back to echohello-dev/wingman")
            repos = ["echohello-dev/wingman"]
        
        logger.info(f"Fetching context from {len(repos)} repositories...")
        
        # Fetch data from multiple repos
        for repo_idx, repo in enumerate(repos, 1):
            try:
                logger.debug(f"  [{repo_idx}/{len(repos)}] Processing {repo}...")
                
                # Get recent commits
                response = httpx.get(
                    f"https://api.github.com/repos/{repo}/commits",
                    headers=headers,
                    params={"per_page": 5},
                    timeout=10
                )
                if response.status_code == 200:
                    commits = response.json()
                    fetched = len(commits[:3])
                    context['commits'].extend([
                        {
                            "message": c.get('commit', {}).get('message', ''),
                            "author": c.get('commit', {}).get('author', {}).get('name', 'Unknown'),
                            "repo": repo,
                            "date": c.get('commit', {}).get('author', {}).get('date', '')
                        }
                        for c in commits[:3]
                    ])
                    logger.debug(f"    ✓ Fetched {fetched} commits")
                else:
                    logger.debug(f"    ⚠ Commits API returned {response.status_code}")
                
                # Get recent PRs
                response = httpx.get(
                    f"https://api.github.com/repos/{repo}/pulls",
                    headers=headers,
                    params={"state": "all", "per_page": 5},
                    timeout=10
                )
                if response.status_code == 200:
                    prs = response.json()
                    fetched = len(prs[:3])
                    context['prs'].extend([
                        {
                            "title": pr.get('title', ''),
                            "number": pr.get('number', 0),
                            "state": pr.get('state', ''),
                            "repo": repo,
                            "url": pr.get('html_url', ''),
                            "author": pr.get('user', {}).get('login', 'Unknown')
                        }
                        for pr in prs[:3]
                    ])
                    logger.debug(f"    ✓ Fetched {fetched} PRs")
                else:
                    logger.debug(f"    ⚠ PRs API returned {response.status_code}")
                
                # Get recent issues
                response = httpx.get(
                    f"https://api.github.com/repos/{repo}/issues",
                    headers=headers,
                    params={"state": "all", "per_page": 5},
                    timeout=10
                )
                if response.status_code == 200:
                    issues = response.json()
                    issues_filtered = [i for i in issues[:3] if not i.get('pull_request')]
                    fetched = len(issues_filtered)
                    context['issues'].extend([
                        {
                            "title": i.get('title', ''),
                            "number": i.get('number', 0),
                            "repo": repo,
                            "url": i.get('html_url', ''),
                            "labels": [l.get('name', '') for l in i.get('labels', [])]
                        }
                        for i in issues_filtered
                    ])
                    logger.debug(f"    ✓ Fetched {fetched} issues")
                else:
                    logger.debug(f"    ⚠ Issues API returned {response.status_code}")
                    
            except httpx.TimeoutException:
                logger.error(f"  Timeout fetching data from {repo}")
                continue
            except Exception as e:
                logger.error(f"  Error fetching data from {repo}: {type(e).__name__}: {e}")
                continue
        
        # Trim to reasonable sizes
        context['commits'] = context['commits'][:5]
        context['prs'] = context['prs'][:5]
        context['issues'] = context['issues'][:5]
        
        total = len(context['commits']) + len(context['prs']) + len(context['issues'])
        logger.info(f"✓ GitHub context loaded: {len(context['commits'])} commits, {len(context['prs'])} PRs, {len(context['issues'])} issues")
        return context if context['commits'] or context['prs'] or context['issues'] else None
    
    except Exception as e:
        logger.error(f"Error fetching GitHub context: {type(e).__name__}: {e}")
        return None


def generate_messages_with_ai(github_context=None):
    """Generate realistic Slack conversations using OpenRouter Gemini 3 Flash with structured outputs."""
    logger.info("Generating conversations with Gemini 3 Flash...")
    
    # Build prompt with GitHub context if available
    base_prompt = """Generate 20 realistic Slack channel messages for an engineering team support channel. 
Messages should include:
- Technical questions and troubleshooting
- Status updates and announcements
- Deployment notices
- Deprecation warnings
- Casual but professional tone (semi-formal)
- Some typos and natural language variation
- Minimal emoji use with :emoji_name: syntax (e.g., :rocket:, :warning:, :wave:)
- Links with format <url|label> for URLs
- Formatting: use *bold*, _italic_, ~strikethrough~, `code` for inline code
- Bullet points with • or - prefix
- Mix of quick questions, detailed issues, and team coordination
- Each message has 0-3 replies

IMPORTANT: Use markdown-like formatting in text:
- *bold text* for emphasis
- _italic text_ for secondary emphasis
- `code` for technical terms
- <https://example.com|link text> for URLs
- :emoji_name: for emojis
- • bullet points for lists

Example: "*Issue*: _Database timeout_ on <https://github.com|PR#123>. `SELECT` query taking 30s :warning:"
"""

    if github_context:
        context_str = "Use this real project context when generating messages. Reference actual repos, PRs, and issues:\n"
        if github_context.get('commits'):
            context_str += "\nRecent commits (repos touched):\n"
            for c in github_context['commits'][:3]:
                context_str += f"- {c['message'][:60]} ({c['repo']})\n"
        if github_context.get('prs'):
            context_str += "\nRecent PRs to reference:\n"
            for pr in github_context['prs'][:3]:
                url = pr.get('url', '').replace('/api/v3/', '/')
                context_str += f"- #{pr['number']}: {pr['title']} ({pr['state']}) - <{url}>\n"
        if github_context.get('issues'):
            context_str += "\nRecent issues to reference:\n"
            for issue in github_context['issues'][:3]:
                url = issue.get('url', '').replace('/api/v3/', '/')
                labels = ', '.join(issue['labels']) if issue['labels'] else 'no labels'
                context_str += f"- #{issue['number']}: {issue['title']} ({labels}) - <{url}>\n"
        
        context_str += "\n\nWhen generating messages:\n"
        context_str += "- Reference actual PR/issue numbers and URLs from the context above\n"
        context_str += "- Use raw GitHub URLs like https://github.com/owner/repo/issues/123\n"
        context_str += "- Include actual commit messages and PR titles from your repos\n"
        context_str += "- Make questions/discussions specific to the repos and issues you actually work on\n"
        
        prompt = base_prompt + "\n\n" + context_str
        logger.debug("AI prompt includes GitHub context")
    else:
        prompt = base_prompt
        logger.debug("AI prompt using default template (no GitHub context)")

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
        with console.status("[bold magenta]Generating messages with Gemini 3 Flash...", spinner="dots"):
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
                timeout=30
                )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # With structured outputs, content is already valid JSON
            try:
                data = json.loads(content)
                messages = data.get('messages', [])
                logger.info(f"✓ Generated {len(messages)} messages from Gemini 3 Flash")
                return messages
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {type(e).__name__}: {e}")
                logger.debug(f"   Content: {content[:200]}")
                return None
        else:
            error_body = response.text
            logger.error(f"AI generation failed: HTTP {response.status_code}")
            logger.debug(f"   Response: {error_body[:200]}")
            return None
    except httpx.TimeoutException:
        logger.error("AI generation timed out (30s)")
        return None
    except Exception as e:
        logger.error(f"AI generation error: {type(e).__name__}: {e}")
        return None


# Default fallback messages
fallback_messages = [
    {
        "text": "Hey team, I'm getting a *403* on the new dashboard analytics endpoint :thinking_face: Has anyone else run into this?",
        "replies": [
            "Did you check if your token has the `analytics.read` scope?",
            "Also, make sure the URL is `/api/v3/analytics`, not `/api/analytics`. Easy typo to make"
        ]
    },
    {
        "text": "Quick question - what's our _data retention policy_ for session logs? Need this for the compliance audit",
        "replies": [
            "90 days in hot storage, then goes to cold storage for 7 years per policy"
        ]
    },
    {
        "text": "*Issue* in prod :bug:: Database query timeout on user auth\n`TypeError: Cannot read property 'userId' of undefined` at `user-service.js:45`\nAnyone know what we deployed?",
        "replies": [
            "Did we change the auth middleware recently?",
            "Yeah, I see it now. JWT decode is failing silently. Let me push a fix"
        ]
    },
    {
        "text": "Could someone send me the rate limiter config docs? Setting up limits for the _payment service_ and need guidance",
        "replies": []
    },
    {
        "text": "Onboarding new team member tomorrow - where can I find the local dev setup guide? Need the Docker compose instructions :wave:",
        "replies": [
            "Root `README` has everything including the Docker compose setup :whale:"
        ]
    },
    {
        "text": "Has anyone successfully integrated <https://stripe.com/docs/webhooks|Stripe webhooks>? Signature validation keeps failing and I can't figure out why",
        "replies": [
            "Make sure you're using the webhook secret from the dashboard, not your API secret",
            "Also gotta read the raw request body before parsing as JSON. That's a common gotcha"
        ]
    },
    {
        "text": "Could use some help - how does the *authentication flow* work on mobile? Is there a sequence diagram or docs somewhere?",
        "replies": []
    },
    {
        "text": "Quick question on _database migrations_: should I create a new file or modify the existing one? Adding a column to the `users` table",
        "replies": [
            "Always create a *new migration file*. Never modify deployed migrations - that's how things break :no_entry:"
        ]
    },
    {
        "text": "Getting timeout errors on `/api/v2/reports` when generating large reports. Timeout is set to 30s currently - what's the recommended value?",
        "replies": [
            "60s is typical for report generation. Or consider making it _async with a callback_ if reports are heavy"
        ]
    },
    {
        "text": "What's the best approach for handling *retries* in the payment module? How do you differentiate between `transient` and `permanent` failures?",
        "replies": []
    },
    {
        "text": "Question - _staging_ vs _pre-prod_: which one should I use for feature flag testing? :rocket:",
        "replies": [
            "Staging is for integration testing. Pre-prod mirrors production config. Use *pre-prod* for feature flags"
        ]
    },
    {
        "text": "Looking for documentation on *user permissions*. Need to implement role-based access control for the admin dashboard",
        "replies": []
    },
    {
        "text": "*Push notifications* aren't showing on iOS. Has anyone worked with the notification service recently? :iphone:",
        "replies": [
            "When's the last time you updated the *APNs certificate*? Pretty sure it expired :warning:",
            "Oh, that's probably it! Where can I find the new one? :bulb:"
        ]
    },
    {
        "text": "*Security question* - do we automatically redact _credit card numbers_ in logs, or should they be manually scrubbed?",
        "replies": []
    },
    {
        "text": "Seeing _inconsistent results_ from the search API. Same query returns different results on subsequent calls. Is Redis caching enabled?",
        "replies": [
            "Yes, Redis caching with 5-minute TTL. Could be cache warming issues :mag:"
        ]
    },
    {
        "text": ":rocket: *heads up* - deploying _auth service v2.1_ to staging in 30min. if you're testing auth stuff plz use `staging-v2`",
        "replies": [
            "thanks for the heads up! when's it going to prod?",
            "probably friday if no issues in staging. ill ping the channel"
        ]
    },
    {
        "text": "just merged <https://github.com/echohello-dev/wingman/pull/487|PR #487> - refactored the payment webhook handler to be more robust. plz review when u get a sec :eyes:",
        "replies": [
            "lgtm! just left a comment on line 42 :+1:",
            "approved! ship it :ship:"
        ]
    },
    {
        "text": ":warning: *ATTENTION*: we're deprecating the old `/api/v1/users` endpoint _next month_. migrate to `/api/v2/users` asap. see <https://docs.example.com|docs> for migration guide",
        "replies": [
            "how long do we have to migrate?",
            "until feb 15. we're sending emails to all customers but best to get it done early"
        ]
    },
    {
        "text": "*performance update*: search endpoint now doing _fuzzy matching_. this may affect some queries but accuracy is way better. feedback welcome :mag:",
        "replies": [
            "nice! how's the perf impact?",
            "minimal actually. redis caching handles most of it :zap:"
        ]
    },
    {
        "text": "*planned maintenance*: database will be down for upgrades tomorrow 2am-3am pst. notify ur customers pls :warning:",
        "replies": [
            "done. already sent notifications :email:",
            "thx. also FYI we're upgrading to `postgres 15` :elephant:"
        ]
    },
    {
        "text": "*FYI* rolling out new UI theme next week. if things look weird that's expected lol. should stabilize by wed :art:",
        "replies": [
            "dark mode finally?? :moon:",
            "yeah! and better mobile responsive too :iphone:"
        ]
    },
    {
        "text": "quick *status update*: api latency spiked this morning around 9am but we've sorted it now. no data loss :relieved:",
        "replies": [
            "what caused it?",
            "one of the load balancers got overloaded. scaled it up :muscle:"
        ]
    }
]

# Choose messages source
if OPENROUTER_API_KEY:
    github_context = get_github_context()
    generated = generate_messages_with_ai(github_context)
    messages = generated if generated else fallback_messages
    if not generated:
        logger.warning("AI generation failed, falling back to default messages")
else:
    logger.warning("OPENROUTER_API_KEY not set, using default fallback messages")
    messages = fallback_messages

total_posts = sum(1 + len(msg['replies']) for msg in messages)
console.print(f"\n[bold blue]━━━ Posting Messages ━━━[/bold blue]")
console.print(Panel.fit(
    f"[bold cyan]{len(messages)}[/bold cyan] messages\n[bold cyan]{total_posts}[/bold cyan] total posts (including replies)",
    title="[bold]Slack Post Summary[/bold]",
    border_style="blue"
))

success = 0
failed = 0
posted_count = 0

# Use Progress bar for message posting
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    console=console
) as progress:
    task = progress.add_task(f"[green]Posting messages...", total=len(messages))
    
    for i, msg_data in enumerate(messages, 1):
        progress.update(task, description=f"[green]Message {i}/{len(messages)}")
        text = msg_data['text']
        
        # Parse formatting and create rich text elements
        elements = parse_rich_text_from_string(text)
    
        # Create rich text blocks with formatted elements
        blocks = [{
            "type": "rich_text",
            "elements": [{
                "type": "rich_text_section",
                "elements": elements
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
        
        try:
            response = httpx.post(
                f'{SLACK_ORG_URL}/api/chat.postMessage',
                data=data,
                cookies=cookies,
                headers=headers,
                timeout=10
            )
            
            result = response.json()
            
            if result.get('ok'):
                posted_count += 1
                thread_ts = result['ts']
                success += 1
                
                # Extract emoji from message and add as reaction (optional)
                emoji_match = re.search(r':([a-z_0-9]+):', text)
                if emoji_match:
                    emoji_name = emoji_match.group(1)
                    time.sleep(0.5)
                    add_reaction(CHANNEL, thread_ts, emoji_name)
                
                # Post replies if any
                if 'replies' in msg_data:
                    for reply_idx, reply_text in enumerate(msg_data['replies'], 1):
                        time.sleep(1)  # Small delay between replies
                        
                        # Parse reply formatting
                        reply_elements = parse_rich_text_from_string(reply_text)
                        
                        reply_blocks = [{
                            "type": "rich_text",
                            "elements": [{
                                "type": "rich_text_section",
                                "elements": reply_elements
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
                            f'{SLACK_ORG_URL}/api/chat.postMessage',
                            data=reply_data,
                            cookies=cookies,
                            headers=headers,
                            timeout=10
                        )
                        
                        reply_result = reply_response.json()
                        if reply_result.get('ok'):
                            posted_count += 1
                            success += 1
                        else:
                            logger.error(f"Reply {reply_idx} failed: {reply_result.get('error', 'Unknown error')}")
                            failed += 1
            else:
                logger.error(f"Message {i} failed: {result.get('error', 'Unknown error')}")
                failed += 1
        
        except Exception as e:
            logger.error(f"Message {i} error: {type(e).__name__}: {e}")
            failed += 1
        
        progress.advance(task)
        
        # Delay between main messages
        if i < len(messages):
            time.sleep(2)

# Final summary panel
console.print("\n")
console.print(Panel.fit(
    f"[bold green]✓ {success} successful[/bold green]\n"
    f"[bold red]✗ {failed} failed[/bold red]\n"
    f"[bold cyan]{posted_count}/{total_posts} total posts[/bold cyan]",
    title="[bold]Completion Summary[/bold]",
    border_style="green" if failed == 0 else "yellow"
))
))
