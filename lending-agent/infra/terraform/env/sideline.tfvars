# Smaller production footprint for the side-line launch (~$850/month, see the model's
# Infrastructure sheet). Same security controls as full production; less capacity.
# Scale up by switching to prod.tfvars values when usage grows.
environment          = "prod"
vpc_cidr             = "10.42.0.0/16"
az_count             = 2
db_instance_class    = "db.t4g.medium"
db_multi_az          = true
api_desired_count    = 1
worker_desired_count = 1
domain_name          = "app.example.com" # replace
acm_certificate_arn  = "arn:aws:acm:us-east-1:000000000000:certificate/replace-me"
api_image            = "000000000000.dkr.ecr.us-east-1.amazonaws.com/lendagent-prod-api@sha256:replace"
worker_image         = "000000000000.dkr.ecr.us-east-1.amazonaws.com/lendagent-prod-worker@sha256:replace"
alarm_email          = "security@example.com" # replace
