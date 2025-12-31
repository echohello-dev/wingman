#!/usr/bin/env python3
"""Load environment variables from Terraform outputs into .env file.

This script loads Slack app credentials from Terraform outputs:
- client_id, client_secret, signing_secret, verification_token from the Slack provider

Note: SLACK_BOT_TOKEN and SLACK_APP_TOKEN are NOT available from Terraform outputs.
These tokens are only generated after installing the app to your Slack workspace.
You must manually copy these tokens from Slack and add them to .env:
1. Visit the OAuth URL from terraform outputs
2. Install the app to your workspace
3. Copy SLACK_BOT_TOKEN (xoxb-...) and SLACK_APP_TOKEN (xapp-...) from Slack to .env
"""

import json
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")


def log_info(msg: str) -> None:
    print(f"ℹ️  {msg}")


def log_success(msg: str) -> None:
    print(f"✅ {msg}")


def log_error(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)


def log_action(msg: str) -> None:
    print(f"🔄 {msg}")


def get_env_var(key: str, required: bool = True) -> str | None:
    """Get environment variable, optionally required."""
    value = os.getenv(key)
    if not value and required:
        log_error(f"{key} must be set in .env")
        sys.exit(1)
    return value


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


def get_terraform_outputs() -> dict[str, str]:
    """Get Terraform outputs from terraform output command."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=Path(__file__).parent.parent / "terraform",
            capture_output=True,
            text=True,
            timeout=10.0
        )
        if result.returncode != 0:
            log_error(f"Failed to get Terraform outputs: {result.stderr}")
            return {}
        
        data = json.loads(result.stdout)
        outputs = {}
        
        # Extract output values, handling both simple and complex types
        for output_name, output_data in data.items():
            if isinstance(output_data, dict) and "value" in output_data:
                value = output_data["value"]
                # Handle nested objects - extract first level values
                if isinstance(value, dict):
                    for key, val in value.items():
                        outputs[key] = str(val)
                else:
                    outputs[output_name] = str(value)
        
        return outputs
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return {}


def load_vars_to_env_file() -> None:
    """Load outputs from Terraform state into .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        log_error(".env file not found")
        sys.exit(1)
    
    # Map of Terraform output names to .env variable names
    output_mapping = {
        "client_id": "SLACK_CLIENT_ID",
        "client_secret": "SLACK_CLIENT_SECRET",
        "signing_secret": "SLACK_SIGNING_SECRET",
        "verification_token": "SLACK_VERIFICATION_TOKEN",
        "bot_token": "SLACK_BOT_TOKEN",
        "app_token": "SLACK_APP_TOKEN",
    }
    
    # Get all Terraform outputs
    outputs = get_terraform_outputs()
    
    if not outputs:
        log_error("No Terraform outputs found")
        return
    
    # Read current .env
    content = env_path.read_text()
    lines = content.split("\n")
    updated_lines = []
    updated_vars = set()
    
    # Update existing lines
    for line in lines:
        updated = False
        for tf_output, env_var in output_mapping.items():
            if line.startswith(f"{env_var}=") and tf_output in outputs:
                output_value = outputs[tf_output]
                updated_lines.append(f"{env_var}={output_value}")
                updated_vars.add(env_var)
                log_success(f"Synced {env_var} from Terraform outputs")
                updated = True
                break
        
        if not updated:
            updated_lines.append(line)
    
    # Add missing variables from Terraform outputs
    for tf_output, env_var in output_mapping.items():
        if env_var not in updated_vars and tf_output in outputs:
            output_value = outputs[tf_output]
            updated_lines.append(f"{env_var}={output_value}")
            log_success(f"Added {env_var} from Terraform outputs")
    
    env_path.write_text("\n".join(updated_lines))




def main() -> None:
    """Main function to load variables from Terraform outputs."""
    print("🔄 Loading environment variables from Terraform outputs...")
    
    # Load variables from TF outputs to .env
    print()
    log_action("Loading variables from Terraform...")
    load_vars_to_env_file()
    
    # Success message
    print()
    log_success("Environment variables loaded from Terraform into .env")
    print()
    log_info("Note: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be manually added")
    log_info("      Visit Slack API settings after installing the app to your workspace")


if __name__ == "__main__":
    main()
