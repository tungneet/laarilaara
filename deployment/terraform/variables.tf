variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "service_name" {
  description = "Base name used to prefix/tag every resource."
  type        = string
  default     = "laarilaara"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "production"
}

variable "dynamodb_table_name" {
  type    = string
  default = "laarilaara-prod"
}

variable "media_bucket_name" {
  type    = string
  default = "laarilaara-prod-media"
}

variable "artifacts_bucket_name" {
  type    = string
  default = "laarilaara-prod-artifacts"
}

variable "embeddings_bucket_name" {
  type    = string
  default = "laarilaara-prod-embeddings"
}

variable "cors_allowed_origins" {
  description = "Origins allowed to call the API and the media bucket (CORS)."
  type        = list(string)
  default     = ["https://laarilaara.netlify.app"]
}

variable "lambda_memory_mb" {
  type    = number
  default = 512
}

variable "lambda_timeout_seconds" {
  description = "Must stay below API Gateway's 29s hard limit."
  type        = number
  default     = 28
}

variable "openai_api_key" {
  description = "OpenAI API key, set via TF_VAR_openai_api_key env var — never committed."
  type        = string
  sensitive   = true
  default     = ""
}

variable "log_retention_days" {
  type    = number
  default = 14
}
