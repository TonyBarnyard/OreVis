# Remote servers (AWS)

`terraform/` defines the full production footprint: a three-tier VPC across 3 AZs with
PrivateLink endpoints (including Bedrock for Claude and Textract for OCR), ECS Fargate API and
worker services, encrypted Multi-AZ PostgreSQL, KMS-encrypted document storage replicated to a
DR region, a WORM audit bucket, WAF, CloudTrail, GuardDuty, Security Hub, Inspector, AWS Backup
and security alerting. `terraform validate` passes. It has not been applied to an account yet.

## First deployment

1. Create an AWS Organization with separate `prod`, `staging` and `security` accounts. Enable
   SCPs that deny disabling CloudTrail/GuardDuty and deny unapproved regions.
2. Create the Terraform state bucket and lock table, then uncomment `backend "s3"` in
   `versions.tf`.
3. Request an ACM certificate for your domain. Enable Claude model access in the Bedrock
   console (us-east-1).
4. Fill in `env/staging.tfvars`, then:
   `terraform init && terraform plan -var-file=env/staging.tfvars -out=plan && terraform apply plan`
5. Build and push the `api` and `worker` images to the ECR repos in the outputs, pin them by
   digest in the tfvars, and apply again.
6. Repeat for prod with `env/prod.tfvars`.

Estimated cost: about $2,950/month for prod + staging + DR at launch scale (itemized in the
model's Infrastructure sheet).
