# Terraform runbook

Operating rules for this module, not a getting-started guide — see `docs/architecture.md` for that. Written after a state lock got stuck twice and a `deletion_protection` fight in the same week; the point of this file is to make sure those lessons outlive whoever remembers them.

## The one rule

**Never run a bare `terraform apply`.** Always review a saved plan first, then apply that exact file:

```bash
terraform plan -out=tfplan
# read it — especially any line starting with `-` or `-/+`
terraform apply tfplan
```

Applying a saved plan file (rather than letting `apply` re-plan implicitly) guarantees you're applying exactly what you reviewed — state can't have drifted in the gap between reading the plan and approving it.

In practice, use `scripts/safe-apply.sh .` instead of doing this by hand — it runs the same two steps and adds a hard stop if the plan would destroy or replace anything. (Shared across every module in this repo — see `ci/README.md` for the other user.)

## Handling a tainted resource

If a resource is `tainted` (shows up in `plan` as `# ... is tainted, so must be replaced`), the instinct to just apply is wrong — that forces a full destroy-and-recreate. Try this first, always:

```bash
terraform untaint <resource address>
terraform plan
```

If the resource just needed a normal update (new image, changed config), untainting is enough — Cloud Run especially creates a new revision on any template change anyway, so a destroy is almost never actually necessary to fix a tainted Cloud Run service.

## `deletion_protection`

Several resources in this module (`google_cloud_run_v2_service`) default to `deletion_protection = true` deliberately. If you ever need to set it `false` to get past a blocked destroy:

- Do it for the single `apply` that needs it, nothing more.
- Set it back to `true` immediately after, in the same session.
- Say why in the commit message — "why" here means which specific situation forced it, not just "unblocking apply."

## If a resource gets destroyed and recreated

Some fields force a full replace instead of an in-place update — renaming a resource, moving `region`, and (for Cloud Run specifically) the deletion_protection situation above if `untaint` genuinely doesn't apply. If `google_cloud_run_v2_service.linguaalayam` is ever actually replaced (not just given a new revision), **its default `.run.app` URL changes** — check whether `linguaalayam.org`'s Cloudflare DNS record needs updating to match, since that record depends on the current hostname.

## State locks

`gs://linguaalayam-tfstate` backs this module's state. A stuck lock (`Error acquiring the state lock`) is usually self-inflicted — a previous `plan`/`apply` that got interrupted before releasing it. Before clearing one:

```bash
date -u                          # compare against the lock's "Created" timestamp
ps aux | grep terraform          # confirm nothing is actually running right now
```

If the lock is recent (seconds to a couple of minutes old) and nothing is running, it's safe:

```bash
terraform force-unlock <LOCK_ID>
```

Never force-unlock if a `plan`/`apply` might genuinely still be in flight (yours or anyone else's).

## What CI does and doesn't do

A GitHub Actions job runs `terraform plan` automatically on any PR touching `terraform/` and posts the output as a PR comment — visibility before merge, nothing more. **CI's credentials (via Workload Identity Federation, see `ci/`) are read-only project-wide** — it cannot apply, and shouldn't be given credentials that could. The identity itself lives in a separate Terraform module (`ci/`, own state) from the infrastructure it reviews — see `ci/README.md` for why. Applying is always a human, locally, with `scripts/safe-apply.sh`, plan file in hand.

## Secrets

`db_password`, `together_api_key`, and `admin_password` have no default and always prompt — deliberately, so a wrong value has to be typed consciously rather than silently reused from a stale file. Set `TF_VAR_*` environment variables for a session if retyping them gets tedious; never put them in a committed file (`terraform.tfvars` and `*.auto.tfvars` are gitignored for exactly this reason, but gitignored isn't the same as safe to commit by accident).
