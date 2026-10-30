variable "project" {
  type    = string
  default = "lendagent"
}

variable "environment" {
  type        = string
  description = "prod or staging"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "dr_region" {
  type        = string
  default     = "us-west-2"
  description = "Region that receives encrypted backup and document replicas."
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "az_count" {
  type    = number
  default = 3
}

variable "domain_name" {
  type        = string
  description = "Public hostname of the app, e.g. app.example.com. An ACM certificate must already exist for it."
}

variable "acm_certificate_arn" {
  type = string
}

variable "db_instance_class" {
  type    = string
  default = "db.r6g.large"
}

variable "db_multi_az" {
  type    = bool
  default = true
}

variable "api_image" {
  type        = string
  description = "ECR image URI (pinned by digest) for the web/API service."
}

variable "worker_image" {
  type        = string
  description = "ECR image URI (pinned by digest) for the document/agent worker."
}

variable "api_desired_count" {
  type    = number
  default = 3
}

variable "worker_desired_count" {
  type    = number
  default = 4
}

variable "log_retention_days" {
  type    = number
  default = 400 # > 1 year to support SOC 2 / GLBA Safeguards evidence requests
}

variable "document_retention_days" {
  type        = number
  default     = 2555 # 7 years; align with each subscriber's record-retention policy
  description = "Object Lock retention for the audit-log bucket."
}

variable "alarm_email" {
  type = string
}
