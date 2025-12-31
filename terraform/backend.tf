terraform {
  # Terraform Cloud backend
  # Configure via environment variables:
  # - TF_CLOUD_ORGANIZATION (required)
  # - TF_WORKSPACE (required)
  # - TF_TOKEN_app_terraform_io (authentication)
  #
  # To use local state instead, comment out the cloud block below
  cloud {
    # Organization and workspace read from environment variables:
    # TF_CLOUD_ORGANIZATION and TF_WORKSPACE
  }
}
