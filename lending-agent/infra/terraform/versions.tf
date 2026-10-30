terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
  # State holds resource ids and ARNs: keep it in an encrypted, versioned bucket
  # with locking. Create the bucket once by hand, then uncomment.
  # backend "s3" {
  #   bucket         = "lendagent-tfstate-<account-id>"
  #   key            = "platform/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "lendagent-tf-locks"
  # }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      DataClass   = "confidential-npi"
      ManagedBy   = "terraform"
    }
  }
}

provider "aws" {
  alias  = "dr"
  region = var.dr_region
  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      DataClass   = "confidential-npi"
      ManagedBy   = "terraform"
    }
  }
}
