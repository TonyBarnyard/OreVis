data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  key_admin_policy = {
    Sid       = "AccountAdmin"
    Effect    = "Allow"
    Principal = { AWS = "arn:aws:iam::${local.account_id}:root" }
    Action    = "kms:*"
    Resource  = "*"
  }
}

# Separate keys per data domain limit blast radius; per-tenant document keys
# are created by the onboarding service (see SECURITY.md, "Tenant keys").
resource "aws_kms_key" "data" {
  description             = "${local.name} database + application data"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "data" {
  name          = "alias/${local.name}-data"
  target_key_id = aws_kms_key.data.key_id
}

resource "aws_kms_key" "documents" {
  description             = "${local.name} default key for uploaded borrower documents"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "documents" {
  name          = "alias/${local.name}-documents"
  target_key_id = aws_kms_key.documents.key_id
}

resource "aws_kms_key" "logs" {
  description             = "${local.name} logs and audit trail"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      local.key_admin_policy,
      {
        Sid       = "CloudWatchLogs"
        Effect    = "Allow"
        Principal = { Service = "logs.${var.region}.amazonaws.com" }
        Action    = ["kms:Encrypt*", "kms:Decrypt*", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:Describe*"]
        Resource  = "*"
      },
      {
        Sid       = "CloudTrail"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = ["kms:GenerateDataKey*", "kms:DescribeKey"]
        Resource  = "*"
      }
    ]
  })
}

resource "aws_kms_key" "dr" {
  provider                = aws.dr
  description             = "${local.name} DR-region replica encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}
