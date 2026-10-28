terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0, < 6.0" }
    random = { source = "hashicorp/random", version = ">= 3.0, < 4.0" }
  }
}
provider "aws" { region = var.aws_region }
variable "aws_region" { type = string; default = "ap-south-1" }
variable "retention_days" {
  type = number
  default = 90
  validation { condition = var.retention_days >= 30 && var.retention_days <= 3650; error_message = "retention_days must be between 30 and 3650." }
}
resource "random_id" "suffix" { byte_length = 4 }
resource "aws_s3_bucket" "backup" { bucket = "cloud-backups-${random_id.suffix.hex}" }
resource "aws_s3_bucket_public_access_block" "backup" {
  bucket = aws_s3_bucket.backup.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "backup" {
  bucket = aws_s3_bucket.backup.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "backup" {
  bucket = aws_s3_bucket.backup.id
  rule { apply_server_side_encryption_by_default { sse_algorithm = "AES256" } }
}
resource "aws_s3_bucket_lifecycle_configuration" "backup" {
  bucket = aws_s3_bucket.backup.id
  rule {
    id = "expire-old-backups"
    status = "Enabled"
    filter { prefix = "backups/" }
    expiration { days = var.retention_days }
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
}
output "bucket_name" { value = aws_s3_bucket.backup.bucket }
