# FinCo-Pilot AI Provider Admission Policy

FinCo-Pilot handles personal financial context, so a model being "free" is not enough to admit it into production.

The production OmniRoute pool is **fail-closed**. A provider/model may enter `fincopilot-free-smart` only when all of these are true at deployment time:

1. It is present in OmniRoute's current curated free-model catalog.
2. Its free regime is recurring, not a one-time signup credit.
3. OmniRoute's curated metadata has `hardStopGuaranteed: true`; exhausting free allowance must stop requests instead of starting paid usage.
4. Its curated ToS verdict is not `avoid`.
5. It is not marked `trainsOnPrompts: true`.
6. It has no unresolved regional/identity eligibility gate.
7. The operator has separately reviewed the provider's current official terms, privacy/retention policy, geographic processing implications, rate limits, and model/tool quality.
8. No billing method, paid API balance, paid subscription, or paid fallback connection is attached to the dedicated FinCo OmniRoute instance.
9. A real smoke test passes with the exact model route before it is admitted.
10. The model is fully qualified as `provider/model`; ambiguous aliases are not used in the production allowlist.

## Automatic enforcement

`bootstrap-free-combo.sh` applies two global OmniRoute guards before creating the combo:

- `freeAccessPolicy = strict`
- `excludeTosAvoid = true`

It then downloads the live instance's `/api/free-tier/summary` catalog and rejects any declared target that fails the recurring/hard-stop/privacy checks above.

Finally it creates or verifies the exact persisted `fincopilot-free-smart` combo and refuses to silently broaden an existing mismatched combo.

## Explicitly not sufficient

The following are **not** acceptable proof by themselves:

- a provider is shown under a "free" tab;
- a model name ends in `:free`;
- OmniRoute's aggregate free-token headline includes the provider;
- a provider offers initial signup credits;
- a provider has a cheap paid tier;
- an automatic router happens to choose a free model during one test.

Free quotas and terms can change. The launch gate is the combination of curated metadata, operator review, strict zero-cost policy, an explicit combo allowlist, and live smoke tests.

## Financial-context boundary

Even admitted providers receive only the minimum context needed for the user's question. FinCo-Pilot must never send:

- bank login credentials;
- bank/provider access tokens;
- full card/account numbers;
- application secrets;
- unrelated raw transaction history;
- another workspace's data.

The AI is read-only at launch. Money calculations and forecasts are produced/validated by FinCo's deterministic services; the LLM explains validated outputs in natural language.
