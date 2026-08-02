# Generated secrets (Terraform-managed; never appear in git — state itself
# is gitignored per deployment/.gitignore). Recorded in the Lambda's
# environment so app.core.config.Settings can read them as LAARA_* env vars.
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "webhook_secret" {
  length  = 48
  special = false
}

data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = "${path.module}/../build/lambda_package"
  output_path = "${path.module}/../build/lambda.zip"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.service_name}-api"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.service_name}-api"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "app.lambda_handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  memory_size      = var.lambda_memory_mb
  timeout          = var.lambda_timeout_seconds

  environment {
    variables = {
      LAARA_ENVIRONMENT      = var.environment
      LAARA_CONFIG_FILE      = "config.yaml" # bundled by deployment/build_lambda.py
      LAARA_JWT_SECRET       = random_password.jwt_secret.result
      LAARA_WEBHOOK_SIGNING_SECRET = random_password.webhook_secret.result
      LAARA_OPENAI_API_KEY   = var.openai_api_key
      LAARA_STORAGE__DYNAMODB_TABLE_NAME  = aws_dynamodb_table.main.name
      LAARA_STORAGE__MEDIA_BUCKET_NAME      = aws_s3_bucket.buckets["media"].bucket
      LAARA_STORAGE__ARTIFACTS_BUCKET_NAME  = aws_s3_bucket.buckets["artifacts"].bucket
      LAARA_STORAGE__EMBEDDINGS_BUCKET_NAME = aws_s3_bucket.buckets["embeddings"].bucket
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]

  tags = {
    Service     = var.service_name
    Environment = var.environment
  }
}
