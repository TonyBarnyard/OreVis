environment         = "prod"
domain_name         = "app.example.com" # replace
acm_certificate_arn = "arn:aws:acm:us-east-1:000000000000:certificate/replace-me"
api_image           = "000000000000.dkr.ecr.us-east-1.amazonaws.com/lendagent-prod-api@sha256:replace"
worker_image        = "000000000000.dkr.ecr.us-east-1.amazonaws.com/lendagent-prod-worker@sha256:replace"
alarm_email         = "security@example.com" # replace
