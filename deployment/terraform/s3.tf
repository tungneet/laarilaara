locals {
  buckets = {
    media       = var.media_bucket_name
    artifacts   = var.artifacts_bucket_name
    embeddings  = var.embeddings_bucket_name
  }
}

resource "aws_s3_bucket" "buckets" {
  for_each = local.buckets
  bucket   = each.value

  tags = {
    Service     = var.service_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "buckets" {
  for_each = aws_s3_bucket.buckets

  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Media bucket needs browser-facing CORS (candidate photo uploads via
# presigned URLs) — matches the rule the local dev server sets up in
# backend/scripts/dev_server.py.
resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.buckets["media"].id

  cors_rule {
    allowed_origins = var.cors_allowed_origins
    allowed_methods = ["GET", "PUT", "HEAD"]
    allowed_headers = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
