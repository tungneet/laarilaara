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

output "ses_domain_verification_record" {
  description = "TXT record to add in Hostinger DNS for SES domain verification."
  value = {
    name  = "_amazonses.${var.email_domain}"
    type  = "TXT"
    value = aws_ses_domain_identity.main.verification_token
  }
}

output "ses_dkim_records" {
  description = "CNAME records to add in Hostinger DNS for SES DKIM signing."
  value = [
    for token in aws_ses_domain_dkim.main.dkim_tokens : {
      name  = "${token}._domainkey.${var.email_domain}"
      type  = "CNAME"
      value = "${token}.dkim.amazonses.com"
    }
  ]
}
