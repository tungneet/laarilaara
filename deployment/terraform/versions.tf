terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Local state on purpose for this first deployment (no S3 backend/DynamoDB
  # lock table set up yet). deployment/.gitignore already excludes *.tfstate*.
  # Move to a remote backend before more than one person touches this.
}

provider "aws" {
  region = var.aws_region
}
