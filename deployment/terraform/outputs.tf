output "api_base_url" {
  description = "Base URL for the deployed API (set as NEXT_PUBLIC_API_BASE_URL on Netlify)."
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.main.name
}

output "lambda_function_name" {
  value = aws_lambda_function.api.function_name
}

output "media_bucket_name" {
  value = aws_s3_bucket.buckets["media"].bucket
}
