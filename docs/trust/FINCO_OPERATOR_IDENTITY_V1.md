# FinCo-Pilot Operator / Business Identity V1

Status: canonical implementation contract for roadmap **#8 — Operator / business identity**.

## 1. Launch identity

For the current launch posture:

- public product/brand name: **FinCo-Pilot**;
- operator type: **individual**;
- operator country: **India (IN)**;
- the product must **not** describe itself as a private limited company, LLP,
  corporation, registered company, bank, FIU, investment adviser, or other
  regulated/registered entity unless that status is actually obtained and the
  configuration is deliberately changed.

This contract is intentionally narrower than the later Privacy Policy and Terms
of Service work. Roadmap #8 defines who operates the service; roadmap #27/#28
will turn the verified facts into complete legal documents.

## 2. Canonical configuration

The backend is the source of truth:

```env
OPERATOR_IDENTITY_ENABLED=true
OPERATOR_BRAND_NAME=FinCo-Pilot
OPERATOR_ENTITY_TYPE=individual
OPERATOR_COUNTRY_CODE=IN
OPERATOR_LEGAL_NAME=
```

`OPERATOR_LEGAL_NAME` is optional for the individual launch posture and is
blank by default. Do not put a person's legal name in the public repository just
to satisfy configuration. Set it only in deployment configuration if the
operator explicitly intends that name to be publicly disclosed.

Supported entity types are:

- `individual`
- `sole_proprietorship`
- `partnership`
- `llp`
- `private_limited`
- `public_limited`
- `other_registered_entity`

A non-individual entity type fails configuration validation unless a legal name
is provided. This prevents a deployment from silently claiming a company form
without naming the actual entity.

## 3. Public API contract

`GET /api/info` exposes only non-secret operator metadata:

- brand name;
- entity type;
- two-letter country code;
- legal name only when deliberately configured;
- the configured human support email, when support is enabled.

It never exposes company-registration documents, tax IDs, personal addresses,
payment credentials, OAuth secrets, SMTP credentials, or other secret
configuration.

## 4. Separation of identities

Keep these concepts separate:

| Identity | Purpose |
| --- | --- |
| FinCo-Pilot operator identity | Who operates the FinCo-Pilot service |
| Workspace issuer identity | A user's/business workspace name, legal name, address and tax details used on invoices |
| Support identity | Human support destination / Zoho Desk |
| Transactional email identity | Automated reset/verification sender |
| Payment merchant identity | The verified merchant identity held by the payment provider |

Changing a user's workspace issuer profile must never change the service
operator identity.

## 5. Naming rules

Use **FinCo-Pilot** as the canonical public product name in trust/legal/operator
contexts. Existing technical identifiers such as package names, repository
names, environment-variable prefixes, `fincopilot` slugs and API paths do not
need cosmetic renaming.

Do not publish phrases such as "FinCo-Pilot Pvt Ltd", "FinCo-Pilot LLP",
"registered company", or equivalent unless a real entity with that status
exists and the corresponding operator configuration has been updated.

## 6. Change procedure

If the operator later becomes a proprietorship, partnership, LLP, private
limited company or another registered entity:

1. verify the actual legal form and exact legal name;
2. change `OPERATOR_ENTITY_TYPE` and `OPERATOR_LEGAL_NAME`;
3. update payment-provider merchant identity where required;
4. update Privacy Policy, Terms, invoices/receipts where applicable;
5. re-run API/config tests and production acceptance;
6. never rewrite historical records to imply the new entity existed earlier.

## 7. Roadmap boundary

This closes the engineering/identity-definition scope of roadmap #8. It does
**not** by itself complete:

- #9 data-retention policy;
- #12 third-party processor inventory;
- #17 transactional SMTP;
- #27 Privacy Policy;
- #28 Terms of Service;
- tax/GST/business registrations or any regulated financial authorization.
