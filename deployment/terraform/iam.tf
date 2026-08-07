data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.service_name}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# Basic CloudWatch Logs permissions (AWS-managed).
resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Least-privilege access to exactly the resources this app uses — no
# wildcards, no other AWS services. Matches the "scoped deploy policy"
# recommendation from the security review after the credential incident.
data "aws_iam_policy_document" "lambda_app_access" {
  statement {
    sid    = "DynamoDbTableAccess"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem",
      "dynamodb:DescribeTable",
    ]
    resources = [
      aws_dynamodb_table.main.arn,
      "${aws_dynamodb_table.main.arn}/index/*",
    ]
  }

  statement {
    sid    = "S3BucketObjectAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [for b in aws_s3_bucket.buckets : "${b.arn}/*"]
  }

  statement {
    sid       = "S3BucketListAccess"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [for b in aws_s3_bucket.buckets : b.arn]
  }

  statement {
    sid       = "SesTransactionalEmail"
    effect    = "Allow"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = [local.ses_identity_arn]
  }

  statement {
    sid    = "SnsTransactionalSms"
    effect = "Allow"
    # SNS SMS publishes directly to a phone number, not a topic/resource ARN
    # we control, so this can't be scoped narrower than "*" — standard for
    # transactional SMS via SNS. Restricted to just sns:Publish (no topic
    # management, subscriptions, etc.).
    actions   = ["sns:Publish"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "lambda_app_access" {
  name   = "${var.service_name}-lambda-app-access"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_app_access.json
}
