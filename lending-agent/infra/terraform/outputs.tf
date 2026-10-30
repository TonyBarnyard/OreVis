output "app_url" {
  value = "https://${var.domain_name}"
}

output "alb_dns_name" {
  description = "Point the app's DNS record (CNAME/alias) here."
  value       = aws_lb.main.dns_name
}

output "documents_bucket" {
  value = aws_s3_bucket.documents.id
}

output "db_endpoint" {
  value     = aws_db_instance.main.address
  sensitive = true
}

output "ecr_repositories" {
  value = { for k, r in aws_ecr_repository.app : k => r.repository_url }
}
