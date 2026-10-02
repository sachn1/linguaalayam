# CI identity — a separate Terraform module, deliberately

This defines the GitHub Actions identity that reviews changes to the application infrastructure in `../` — a Workload Identity Federation pool/provider and a read-only service account, used by `.github/workflows/terraform-plan.yml` to run `terraform plan` on PRs.

**Why this isn't just part of `../`**: it's the identity that gets to *see and review* changes to the application infra. If it lived in the same state as that infra, the exact same routine `apply` that ships a new VPC rule or Cloud Run setting could also silently reshape who's trusted to watch those changes — no separation between "changing the app" and "changing who's allowed to review the app changing." Keeping it in its own state, applied far less often, is the same instinct as `RUNBOOK.md`'s rules for the main module: keep the rarely-touched, security-sensitive stuff deliberately harder to change by accident.

Same state backend (`gs://linguaalayam-tfstate`), different prefix (`linguaalayam-ci`) — so it's independently applied but not a second bucket to manage.

**The Workload Identity Federation pool/provider defined here is also reused by `../cd.tf`** (the write-capable Cloud Run deploy identity, via a `data` source — a cross-state reference by GCP resource ID, not a remote-state read). That's why the provider's `attribute_mapping` includes `attribute.ref` as well as `attribute.repository`: the read-only plan SA here is still bound to the whole repository (any branch, since it only ever reads), but `cd.tf`'s binding is scoped tighter — `attribute.ref == refs/heads/master` — since that identity can actually deploy production.

## Usage

Same rules as `../RUNBOOK.md` — never a bare `apply`:

```bash
cd terraform/ci
terraform init
../scripts/safe-apply.sh .
```

After applying, copy the two outputs (`ci_workload_identity_provider`, `ci_service_account_email`) into the GitHub repo's Actions secrets as `GCP_WIF_PROVIDER` and `GCP_CI_PLAN_SA`.
