# Bootstraps the S3 bucket + DynamoDB table used as the remote state
# backend for terraform/aws. Chicken-and-egg: this config keeps its own
# state local (no backend block) since it creates the infrastructure that
# would otherwise hold it.
#
# One-time setup, run manually (not from session-up.sh):
#   terraform -chdir=terraform/bootstrap init
#   terraform -chdir=terraform/bootstrap apply
# After that, terraform/aws's backend "s3" block resolves against the
# bucket/table created here.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "sre-lab-tfstate-prontx"

  # State history is the point of this bucket — don't let a stray
  # `terraform destroy` in the wrong directory take it out.
  lifecycle {
    prevent_destroy = true
  }

  tags = { Name = "sre-lab-tfstate" }
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "tflock" {
  name         = "sre-lab-tflock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = { Name = "sre-lab-tflock" }
}

output "state_bucket" {
  value = aws_s3_bucket.tfstate.bucket
}

output "lock_table" {
  value = aws_dynamodb_table.tflock.name
}
