data "aws_caller_identity" "current" {}

resource "aws_ses_domain_identity" "main" {
  domain = var.email_domain
}

resource "aws_ses_domain_dkim" "main" {
  domain = aws_ses_domain_identity.main.domain
}

locals {
  ses_identity_arn = "arn:aws:ses:${var.aws_region}:${data.aws_caller_identity.current.account_id}:identity/${var.email_domain}"
}