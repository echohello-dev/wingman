#!/usr/bin/env python3
"""Sync Slack tokens from .env to Terraform Cloud workspace."""

import json
import os
import sys
from pathlib import Path

import httpx


def log_info(msg: str) -> None:
    print(f"ℹ️  {msg}")


def log_success(msg: str) -> None:
    print(f"✅ {msg}")


def log_error(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)


def log_action(msg: str) -> None:
    print(f"🔄 {msg}")


def log_warning(msg: str) -> None:
    print(f"⚠️  {msg}")


def get_env_var(key: str, required: bool = True) -> str | None:
    """Get environment variable, optionally required."""
    value = os.getenv(key)
    if not value and required:
        log_error(f"{key} must be set in .env")
        sys.exit(1)
    return value


def validate_slack_token(refresh_token: str) -> bool:
    """Validate a Slack token by attempting to rotate it. Returns True if valid."""
    try:
        response = httpx.post(
            "https://slack.com/api/tooling.tokens.rotate",
            data={"refresh_token": refresh_token},
            timeout=10.0
        )
        data = response.json()
        return data.get("ok", False)
    except (httpx.RequestError, json.JSONDecodeError):
        return False


def rotate_slack_tokens(refresh_token: str) -> tuple[str, str]:
    """Rotate Slack tokens and return (new_access_token, new_refresh_token)."""
    try:
        response = httpx.post(
            "https://slack.com/api/tooling.tokens.rotate",
            data={"refresh_token": refresh_token},
            timeout=10.0
        )
        data = response.json()
    except (httpx.RequestError, json.JSONDecodeError):
        log_error("Failed to connect to Slack API")
        sys.exit(1)
    
    if not data.get("ok"):
        log_error("Failed to validate Slack tokens")
        print(json.dumps(data, indent=2), file=sys.stderr)
        sys.exit(1)
    
    log_success("Tokens validated and rotated")
    return data["token"], data["refresh_token"]


def prompt_for_refresh_token() -> str:
    """Prompt user for Slack refresh token with instructions."""
    print()
    log_warning("Both .env and Terraform Cloud tokens are invalid")
    print()
    print("📱 To get a new refresh token:")
    print("   1. Go to: https://api.slack.com/apps")
    print("   2. Select your Wingman app (A0A71KHRFNU)")
    print("   3. Navigate to: Features > Tokens and installation")
    print("   4. Copy the 'Refresh token for rotation' (xoxe-1-...)")
    print()
    
    while True:
        token = input("📝 Enter your Slack refresh token: ").strip()
        if not token:
            log_error("Token cannot be empty")
            continue
        
        log_action("Validating token...")
        if validate_slack_token(token):
            log_success("Token is valid")
            return token
        else:
            log_error("Token validation failed. Please check and try again")
            print()


def update_env_file(access_token: str, refresh_token: str) -> None:
    """Update .env file with new tokens."""
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        log_error(".env file not found")
        sys.exit(1)
    
    content = env_path.read_text()
    lines = content.split("\n")
    
    updated_lines = []
    access_updated = False
    refresh_updated = False
    
    for line in lines:
        if line.startswith("SLACK_CONFIG_ACCESS_TOKEN="):
            updated_lines.append(f"SLACK_CONFIG_ACCESS_TOKEN={access_token}")
            access_updated = True
        elif line.startswith("SLACK_CONFIG_REFRESH_TOKEN="):
            updated_lines.append(f"SLACK_CONFIG_REFRESH_TOKEN={refresh_token}")
            refresh_updated = True
        else:
            updated_lines.append(line)
    
    # Add if not found
    if not access_updated:
        updated_lines.append(f"SLACK_CONFIG_ACCESS_TOKEN={access_token}")
    if not refresh_updated:
        updated_lines.append(f"SLACK_CONFIG_REFRESH_TOKEN={refresh_token}")
    
    env_path.write_text("\n".join(updated_lines))
    log_success("Updated local .env with fresh tokens")


def get_workspace_id(org: str, workspace: str, token: str) -> str:
    """Get Terraform Cloud workspace ID."""
    try:
        response = httpx.get(
            f"https://app.terraform.io/api/v2/organizations/{org}/workspaces/{workspace}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )
        data = response.json()
    except (httpx.RequestError, json.JSONDecodeError):
        log_error("Failed to get workspace ID from Terraform Cloud API")
        sys.exit(1)
    
    workspace_id = data.get("data", {}).get("id")
    if not workspace_id:
        log_error("Failed to get workspace ID")
        print(json.dumps(data, indent=2), file=sys.stderr)
        sys.exit(1)
    
    return workspace_id


def get_workspace_variables(workspace_id: str, token: str) -> dict[str, str]:
    """Get existing workspace variables. Returns {key: var_id} mapping."""
    try:
        response = httpx.get(
            f"https://app.terraform.io/api/v2/workspaces/{workspace_id}/vars",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )
        data = response.json()
    except (httpx.RequestError, json.JSONDecodeError):
        log_error("Failed to parse Terraform Cloud API response")
        sys.exit(1)
    
    return {v["attributes"]["key"]: v["id"] for v in data.get("data", [])}


def get_tf_cloud_var_value(workspace_id: str, var_id: str, token: str) -> str | None:
    """Get the value of a Terraform Cloud variable."""
    try:
        response = httpx.get(
            f"https://app.terraform.io/api/v2/workspaces/{workspace_id}/vars/{var_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )
        data = response.json()
        return data.get("data", {}).get("attributes", {}).get("value")
    except (httpx.RequestError, json.JSONDecodeError):
        return None


def update_or_create_variable(
    workspace_id: str,
    var_key: str,
    var_value: str,
    var_id: str | None,
    token: str
) -> None:
    """Update existing variable or create new one."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.api+json"
    }
    
    payload = {
        "data": {
            "type": "vars",
            "attributes": {
                "key": var_key,
                "value": var_value,
                "category": "env",
                "sensitive": True
            }
        }
    }
    
    try:
        if var_id:
            log_action(f"Updating {var_key}...")
            payload["data"]["id"] = var_id
            
            httpx.patch(
                f"https://app.terraform.io/api/v2/workspaces/{workspace_id}/vars/{var_id}",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            log_success(f"Updated {var_key}")
        else:
            log_action(f"Creating {var_key}...")
            
            httpx.post(
                f"https://app.terraform.io/api/v2/workspaces/{workspace_id}/vars",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            log_success(f"Created {var_key}")
    except httpx.RequestError as e:
        log_error(f"Failed to {'update' if var_id else 'create'} {var_key}: {e}")
        sys.exit(1)


def main() -> None:
    """Main sync function."""
    print("🔄 Syncing Slack tokens to Terraform Cloud...")
    
    # Validate Terraform Cloud environment variables
    org = get_env_var("TF_CLOUD_ORGANIZATION")
    workspace = get_env_var("TF_WORKSPACE")
    tf_token = get_env_var("TF_TOKEN_app_terraform_io")
    
    print(f"   Organization: {org}")
    print(f"   Workspace: {workspace}")
    
    # Get refresh token from .env or prompt for it
    print()
    log_action("Validating Slack tokens...")
    
    refresh_token = get_env_var("SLACK_CONFIG_REFRESH_TOKEN", required=False)
    
    if refresh_token:
        if validate_slack_token(refresh_token):
            log_success(".env tokens are valid")
        else:
            log_warning(".env tokens are invalid, checking Terraform Cloud...")
            
            # Try to get valid tokens from Terraform Cloud
            workspace_id = get_workspace_id(org, workspace, tf_token)
            existing_vars = get_workspace_variables(workspace_id, tf_token)
            
            if "SLACK_REFRESH_TOKEN" in existing_vars:
                # Try the TF Cloud token
                tf_refresh_token = get_tf_cloud_var_value(
                    workspace_id,
                    existing_vars["SLACK_REFRESH_TOKEN"],
                    tf_token
                )
                
                if validate_slack_token(tf_refresh_token):
                    log_warning("Using Terraform Cloud token instead")
                    refresh_token = tf_refresh_token
                else:
                    refresh_token = prompt_for_refresh_token()
            else:
                refresh_token = prompt_for_refresh_token()
    else:
        log_warning("SLACK_CONFIG_REFRESH_TOKEN not found in .env")
        refresh_token = prompt_for_refresh_token()
    
    # Rotate tokens
    print()
    log_action("Rotating Slack tokens...")
    new_access_token, new_refresh_token = rotate_slack_tokens(refresh_token)
    
    # Update local .env
    update_env_file(new_access_token, new_refresh_token)
    
    # Get workspace ID
    print()
    log_info("Getting workspace information...")
    workspace_id = get_workspace_id(org, workspace, tf_token)
    log_info(f"Workspace ID: {workspace_id}")
    
    # Get existing variables
    print()
    log_action("Checking existing variables...")
    existing_vars = get_workspace_variables(workspace_id, tf_token)
    
    # Update or create tokens
    access_token_id = existing_vars.get("SLACK_APP_CONFIGURATION_TOKEN")
    refresh_token_id = existing_vars.get("SLACK_REFRESH_TOKEN")
    
    update_or_create_variable(
        workspace_id,
        "SLACK_APP_CONFIGURATION_TOKEN",
        new_access_token,
        access_token_id,
        tf_token
    )
    
    update_or_create_variable(
        workspace_id,
        "SLACK_REFRESH_TOKEN",
        new_refresh_token,
        refresh_token_id,
        tf_token
    )
    
    # Success message
    print()
    log_success("Sync complete! Tokens are now up-to-date in Terraform Cloud")
    print("   You can now run: mise run load-tf-vars")
    print("   Or:              mise run tf-apply")


if __name__ == "__main__":
    main()
