# Borrower documents (tax returns, financials, appraisals): private, KMS-encrypted,
# versioned, TLS-only, and replicated to the DR region.
resource "aws_s3_bucket" "documents" {
  bucket = "${local.name}-documents-${local.account_id}"
}

resource "aws_s3_bucket" "documents_dr" {
  provider = aws.dr
  bucket   = "${local.name}-documents-dr-${local.account_id}"
}

resource "aws_s3_bucket" "audit" {
  bucket              = "${local.name}-audit-${local.account_id}"
  object_lock_enabled = true # WORM: audit evidence cannot be altered or deleted, even by admins
}

locals {
  private_buckets = {
    documents = aws_s3_bucket.documents.id
    audit     = aws_s3_bucket.audit.id
  }
}

resource "aws_s3_bucket_public_access_block" "private" {
  for_each                = local.private_buckets
  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "documents_dr" {
  provider                = aws.dr
  bucket                  = aws_s3_bucket.documents_dr.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "private" {
  for_each = local.private_buckets
  bucket   = each.value
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "documents_dr" {
  provider = aws.dr
  bucket   = aws_s3_bucket.documents_dr.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "audit" {
  bucket = aws_s3_bucket.audit.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.documents.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents_dr" {
  provider = aws.dr
  bucket   = aws_s3_bucket.documents_dr.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.dr.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.logs.arn
    }
  }
}

resource "aws_s3_bucket_object_lock_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id
  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = var.document_retention_days
    }
  }
}

# Deny any request that is not TLS, and any upload not encrypted with KMS.
resource "aws_s3_bucket_policy" "documents" {
  bucket = aws_s3_bucket.documents.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.documents.arn, "${aws_s3_bucket.documents.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "DenyUnencryptedUploads"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.documents.arn}/*"
        Condition = { StringNotEquals = { "s3:x-amz-server-side-encryption" = "aws:kms" } }
      }
    ]
  })
}

resource "aws_s3_bucket_policy" "audit" {
  bucket = aws_s3_bucket.audit.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.audit.arn, "${aws_s3_bucket.audit.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "CloudTrailAclCheck"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = aws_s3_bucket.audit.arn
      },
      {
        Sid       = "CloudTrailWrite"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.audit.arn}/cloudtrail/AWSLogs/${local.account_id}/*"
      }
    ]
  })
}

# Abandoned uploads and old versions are cleaned up; current documents follow tenant retention settings.
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    id     = "expire-noncurrent"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

resource "aws_iam_role" "replication" {
  name = "${local.name}-s3-replication"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "s3.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "replication" {
  role = aws_iam_role.replication.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetReplicationConfiguration", "s3:ListBucket"], Resource = aws_s3_bucket.documents.arn },
      { Effect = "Allow", Action = ["s3:GetObjectVersionForReplication", "s3:GetObjectVersionAcl", "s3:GetObjectVersionTagging"], Resource = "${aws_s3_bucket.documents.arn}/*" },
      { Effect = "Allow", Action = ["s3:ReplicateObject", "s3:ReplicateDelete", "s3:ReplicateTags"], Resource = "${aws_s3_bucket.documents_dr.arn}/*" },
      { Effect = "Allow", Action = ["kms:Decrypt"], Resource = aws_kms_key.documents.arn },
      { Effect = "Allow", Action = ["kms:Encrypt", "kms:GenerateDataKey"], Resource = aws_kms_key.dr.arn }
    ]
  })
}

resource "aws_s3_bucket_replication_configuration" "documents" {
  depends_on = [aws_s3_bucket_versioning.documents, aws_s3_bucket_versioning.documents_dr]
  bucket     = aws_s3_bucket.documents.id
  role       = aws_iam_role.replication.arn
  rule {
    id     = "dr"
    status = "Enabled"
    filter {}
    delete_marker_replication {
      status = "Enabled"
    }
    source_selection_criteria {
      sse_kms_encrypted_objects {
        status = "Enabled"
      }
    }
    destination {
      bucket        = aws_s3_bucket.documents_dr.arn
      storage_class = "STANDARD_IA"
      encryption_configuration {
        replica_kms_key_id = aws_kms_key.dr.arn
      }
    }
  }
}
