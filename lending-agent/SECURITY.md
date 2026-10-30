# Client data protection strategy

Brokers upload the most sensitive data that exists about their borrowers and guarantors: tax
returns, Social Security numbers, bank statements, personal financial statements. Under the
Gramm-Leach-Bliley Act this is *nonpublic personal information* (NPI). Brokers, and the lenders
they submit to, will ask how we protect it. The strategy has seven layers. Items marked **[infra]** are
implemented in `infra/terraform/`. Items marked **[app]** are application requirements.

## 1. Frameworks we commit to

| Framework | Why | When |
|---|---|---|
| FTC GLBA Safeguards Rule (16 CFR 314) | Brokers handle guarantors' personal financial data, and we're their service provider | Day 1: written security program, qualified individual, risk assessment |
| SOC 2 Type I, then Type II (Security, Confidentiality, Availability) | Gives brokers and their lenders independent proof that borrower data is safe; brokerage firms will ask for it | Side line: controls built from day 1, independent pen test before launch, formal audit once brokerage firms require it |
| State breach-notification laws, CCPA/CPRA | Legal obligation | Incident response plan at launch |

## 2. Account isolation: one broker can never see another's data

- **Per-tenant encryption keys [app + infra].** Each broker account gets its own AWS KMS
  key at onboarding, tagged `Project=lendagent`. The runtime role can only use tagged keys.
  All documents are encrypted with the owning tenant's key. Deleting a tenant schedules its key
  for deletion, which crypto-shreds every copy, including backups and the DR replica.
- **Row-level security in Postgres [app].** Every table carries `tenant_id`. RLS policies
  filter on a session variable set from the authenticated token, so even a buggy query can't
  read across tenants.
- **Tenant-scoped storage paths [infra + app].** Documents live under `tenants/<tenant_id>/`
  in S3. The agent's file tools can't leave the deal workspace (tested in
  `agent/tests/test_documents.py`).
- **Model calls carry no cross-tenant context.** Each agent run is built only from that
  tenant's workspace. Prompt caches are scoped per request prefix, and we never share
  conversations or retrieved chunks between tenants.

## 3. Encryption everywhere

- **In transit:** TLS 1.2+ only (TLS 1.3 preferred) at the load balancer **[infra]**. Postgres
  `rds.force_ssl=1` **[infra]**. S3 bucket policies deny non-TLS requests **[infra]**. Traffic
  to AWS services, including Claude on Bedrock and Textract OCR, runs over VPC PrivateLink
  endpoints and never crosses the public internet **[infra]**.
- **At rest:** KMS with automatic key rotation on the database, Performance Insights,
  documents, logs, ECR images, backups and the DR copies **[infra]**.
- **Secrets:** the database master password is generated and rotated by RDS in Secrets Manager
  and never appears in code or Terraform state **[infra]**. The app connects with IAM database
  auth (short-lived tokens) **[infra]**.

## 4. Network and compute hardening [infra]

- Three-tier VPC: only the load balancer and NAT gateways are public. App tasks run in private
  subnets. The database sits in isolated subnets with no internet route.
- Security groups allow only ALB → app :8080, app → DB :5432 and app → endpoints :443. The
  default security group is locked down.
- AWS WAF: managed common, known-bad-input, IP-reputation and SQL-injection rule sets, plus
  per-IP rate limiting.
- Containers run as non-root with a read-only root filesystem and all Linux capabilities
  dropped. Images are immutable and scanned on push (ECR + Inspector), and deployments are
  pinned by digest.
- Deployment circuit breaker with automatic rollback.

## 5. AI-specific protections

- **No training on client data.** Claude on Amazon Bedrock doesn't use inputs to train models,
  and data stays in our AWS region. If we call the Anthropic API directly, we do it under a
  zero-data-retention agreement. Either way, the arrangement goes in our DPA.
- **Data minimization [app].** SSNs, account numbers and dates of birth are masked before text
  is sent to the model unless the task needs them (for example matching a guarantor across
  documents). The model sees only the current deal's documents.
- **Prompt-injection defense [app].** Uploaded documents are wrapped as data. The system prompt
  tells the agent never to follow instructions found inside documents. Tools are least-privilege
  (they can only read and write the current workspace), and there is no tool that sends email
  or moves money.
- **Fair-lending guardrail [app].** The agent excludes ECOA prohibited-basis attributes from
  analysis and notes the exclusion. It never issues a credit decision.
- **Human in the loop.** Every deliverable carries a "prepared for review by a qualified lending
  professional" notice and a sign-off block the broker completes before anything is sent.
- **Opaque identifiers only.** Calls to the model carry a tenant ID, never a name or email.

## 6. Access control and monitoring

- **Brokers [app]:** single sign-on (SAML/OIDC via WorkOS) for brokerage-firm accounts, mandatory MFA for
  everyone, role-based access (admin / analyst / read-only), and per-deal sharing.
- **Our staff:** no standing production access. Engineers get break-glass, time-limited roles
  that are logged and alerted. Production data is never copied to laptops or staging; staging
  uses synthetic loan packages only. Company laptops are under MDM with disk encryption.
- **Audit trail [infra]:** multi-region CloudTrail with log-file validation, plus S3
  data-event logging of every read and write of a borrower document. Logs go to a separate
  Object Lock (WORM, compliance mode) bucket for 7 years. Application audit events (who
  viewed or exported which deal) go to the same place **[app]**.
- **Detection [infra]:** GuardDuty (including S3, RDS-login and runtime monitoring), Security
  Hub with the AWS Foundational Security Best Practices standard, and VPC flow logs.
  High-severity findings and any root-account sign-in page the security on-call by SNS.

## 7. Resilience and data lifecycle

- **Backups [infra]:** RDS Multi-AZ, 35-day point-in-time recovery, daily AWS Backup copies to
  us-west-2, and S3 versioning with cross-region replication to a separately keyed DR bucket.
- **Targets:** RPO ≤ 15 minutes and RTO ≤ 4 hours. DR restore is tested quarterly.
- **Retention:** broker-configurable (default: deal documents retained while the account
  is active, deleted 30 days after the deal is closed out or the account terminates). Deletion
  is crypto-shredding via the tenant key, and we issue a certificate of deletion on request.
- **Incident response:** written plan, 24-hour customer notification commitment in the DPA
  (tighter than most state laws), annual tabletop exercise.

## 8. Before the first real borrower file

- [ ] Written information security program and named qualified individual (GLBA)
- [ ] Risk assessment and data-flow diagram
- [ ] Terraform applied to a dedicated prod AWS account inside an AWS Organization with SCPs
      (deny disabling CloudTrail/GuardDuty, deny leaving approved regions)
- [ ] Per-tenant KMS key creation and RLS policies implemented and tested
- [ ] PII masking, injection-defense tests and fair-lending tests in the eval suite
- [ ] Independent penetration test passed, and findings remediated
- [ ] SOC 2 Type I report issued (side line: once brokerage firms require it)
- [ ] DPA, MSA and privacy policy reviewed by counsel
- [ ] Cyber and tech E&O insurance bound
