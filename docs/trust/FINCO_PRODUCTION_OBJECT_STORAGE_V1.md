# FinCo-Pilot Production Object Storage V1

Roadmap item: **#16 — Object storage**

Status: **engineering/runtime contract implemented; live provider acceptance is release-gated until the operator-owned bucket and credentials pass the production probe.**

## 1. Selected launch provider

FinCo-Pilot selects **Cloudflare R2 Standard** for the zero-cost production launch path.

Why this is the launch default:

- R2 exposes an S3-compatible API, so the application remains provider-neutral.
- The S3 API endpoint is an HTTPS account endpoint and the S3 region is `auto`.
- Buckets are private by default; FinCo-Pilot does not require an `r2.dev` public bucket.
- The current published Standard free allowance includes 10 GB-month storage, 1 million Class A requests and 10 million Class B requests per month. This is an allowance, not a guarantee that production usage will stay free.
- R2 currently has no internet egress charge for Standard storage.

Current vendor references:
- https://developers.cloudflare.com/r2/get-started/s3/
- https://developers.cloudflare.com/r2/api/s3/api/
- https://developers.cloudflare.com/r2/pricing/
- https://developers.cloudflare.com/r2/buckets/public-buckets/
- https://developers.cloudflare.com/r2/reference/data-location/

This provider choice does **not** establish an India data-residency guarantee. Location hints/jurisdictions and the operator's legal/contract requirements must be reviewed separately before any residency claim is published.

## 2. Data stored

The object-storage boundary is for file bytes that are too large or inappropriate for PostgreSQL, including:

- transaction attachments;
- invoice source/supporting documents;
- historical invoice logos;
- future file classes only after they are added to the storage contract.

PostgreSQL remains authoritative for attachment/document metadata and authorization. Object storage does not become an alternate financial database.

## 3. Security contract

Production must use:

```env
STORAGE_PROVIDER=s3
REQUIRE_OBJECT_STORAGE=true
STORAGE_S3_VENDOR=cloudflare_r2
STORAGE_S3_BUCKET=<private-bucket>
STORAGE_S3_REGION=auto
STORAGE_S3_ENDPOINT_URL=https://<ACCOUNT_ID>[.<JURISDICTION>].r2.cloudflarestorage.com
STORAGE_S3_PREFIX=fincopilot-prod
STORAGE_S3_REQUEST_TIMEOUT_SECONDS=30
STORAGE_S3_PRESIGN_TTL_SECONDS=300
```

Credentials are secret material and must never be committed or placed in public issues:

- `STORAGE_S3_ACCESS_KEY` → production secret file `storage_s3_access_key`
- `STORAGE_S3_SECRET_KEY` → production secret file `storage_s3_secret_key`

For R2, create a token with **Object Read & Write** access limited to the FinCo-Pilot bucket. Do not grant account-wide bucket-management permissions when object-only access is sufficient.

Keep the bucket private. Public `r2.dev` access or a public custom-domain bucket is not part of this architecture.

## 4. Runtime behavior

The existing application storage interface remains provider-neutral.

The S3 adapter now provides:

- AWS Signature V4 requests over HTTPS;
- a fixed logical prefix inside the bucket;
- bounded request timeout;
- bounded presigned-URL lifetime;
- upload-time SHA-256 integrity metadata;
- integrity verification when metadata is present on download;
- maximum downloaded-object size enforcement;
- explicit 404 → `FileNotFoundError` behavior;
- idempotent delete behavior;
- no automatic redirect following;
- credential-free error/output paths.

Application database rows store logical storage keys, not Cloudflare account IDs or provider URLs. That makes provider migration possible without rewriting relational attachment identifiers.

## 5. Transaction / object consistency

Uploads necessarily cross two systems: object storage and PostgreSQL.

For transaction attachments, if the object upload succeeds but the relational commit fails, FinCo-Pilot now attempts to delete the just-created object before re-raising the database failure.

Invoice attachment upload already had equivalent cleanup for a uniqueness race.

Broad deletion workflows are deliberately not declared solved here. Roadmaps #29 and #30 still own durable account/workspace deletion, retries and orphan reconciliation. Roadmap #25 still owns backup/restore proof.

## 6. Deployment contract

### Docker Compose production

Production Compose:

- defaults to `STORAGE_PROVIDER=s3`;
- requires `REQUIRE_OBJECT_STORAGE=true`;
- defaults to the R2 vendor contract;
- receives R2 credentials only through the roadmap #13 secret directory;
- does not mount the legacy local attachment volume;
- runs the object-storage acceptance probe before the API starts.

### Kubernetes / Helm

Production Helm fails closed unless:

- `global.existingSecret` is supplied;
- `config.storageProvider=s3`;
- `config.requireObjectStorage=true`;
- `config.storageS3Vendor=cloudflare_r2`;
- bucket, region and endpoint are explicitly configured.

When S3 storage is active, the attachment PVC is not rendered/mounted. Development can still use local storage/PVCs.

## 7. Credential-safe acceptance probe

Run after the real private bucket and scoped credential have been installed:

```bash
cd backend
python -m scripts.verify_production_object_storage
```

The probe:

1. creates one cryptographically random temporary object under the acceptance namespace;
2. checks object metadata/size with HEAD;
3. downloads and compares the exact bytes;
4. deletes the object;
5. confirms the deleted object is no longer readable;
6. attempts cleanup again in `finally` so partial probe failures do not intentionally leave the test object behind.

Expected safe output:

```text
FinCo-Pilot object-storage acceptance: PASS
write_head_read_delete_roundtrip=pass
integrity_metadata=verified
```

The probe never prints the endpoint, bucket, access key, secret key, generated key or provider response body.

## 8. Operator setup checklist

1. Enable R2 for the operator-owned Cloudflare account.
2. Create a dedicated **private Standard** bucket.
3. Choose the bucket jurisdiction/location only after reviewing the actual deployment/legal need. Do not describe a location hint as guaranteed residency.
4. Create an S3 API token with Object Read & Write access scoped only to that bucket.
5. Copy the Access Key ID and Secret Access Key once and place them directly in the roadmap #13 production secret store.
6. Configure the non-secret bucket, `auto` region and exact S3 endpoint.
7. Keep `r2.dev` public access disabled.
8. Run `python -m scripts.verify_production_object_storage` from the deployed backend environment.
9. Upload a real harmless test attachment through FinCo-Pilot, download it through the authenticated app route, then delete it and verify the object disappears.
10. Record only acceptance timestamp, provider/account/bucket identifiers that are safe for the operator log, and probe result. Never record credential values.

## 9. Backup / deletion boundary

Roadmap #16 proves the primary object runtime only.

It does **not** by itself prove:

- isolated restore from backup (#25);
- disaster recovery (#26);
- personal deletion execution (#29);
- shared-workspace hard deletion (#30);
- provider-side legal retention/deletion guarantees.

Object versioning, lifecycle rules, bucket lock and any backup copy must be designed together with #25/#26. Do not enable an indefinite retention mechanism that conflicts with the deletion policy without an explicit legal/operational decision.

## 10. Completion rule

Engineering closure requires:

- S3/R2 configuration validation;
- private object namespace and integrity checks;
- transaction attachment orphan cleanup on DB failure;
- Docker/Helm production parity;
- CI tests and deployment gates green;
- processor inventory updated to Cloudflare R2 as selected/release-gated;
- this runbook and the safe acceptance probe merged.

Operational closure requires the operator-owned R2 bucket plus a successful real probe and one authenticated app upload/download/delete smoke. CI cannot substitute for those provider-owned facts.
