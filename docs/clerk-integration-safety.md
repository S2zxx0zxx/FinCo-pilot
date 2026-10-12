# Clerk exchange ownership and release gate

Reconciled from main 6bb8d293 (the owner's newly merged Clerk integration), preserving its custom login/register UI and all prior PR76–79 changes.

A Clerk session subject is an identity; a client-provided email does not prove ownership of a local financial account. The exchange now requires Clerk to confirm the exact session is active and belongs to that subject. Existing users authenticate only through the exact external identity mapping. Matching even an authoritative verified email never creates a legacy link; the migration must separately prove the internal UUID mapping. An absent/unverified primary email cannot provision a verified user, and the UI email cannot replace a failed provider lookup.

New user, external mapping, workspace, wallet, categories and rules commit as one transaction. Conflicts roll back and return 409 without linking another winner. An existing Clerk JWT does not attest recent reauthentication, so its exchange does not set the internal auth_time claim. Local inactivity remains enforced. Live Clerk status is checked at exchange time; subsequently issued local tokens retain the existing local revocation contract, not a claim of continuous Clerk revocation synchronization.

The provider must be explicitly enabled. Missing provider credentials, inactive sessions and unavailable verification fail closed. The configured issuer's JWKS must contain the requested kid, RSA signing use and RS256; another key is never silently substituted. Untrusted key identifiers are bounded and the cache has a fixed maximum. Provider identities cannot contain URL path characters.

This fixes an observed main CI lint failure and a further TypeScript build failure without dropping the Clerk work: shared frontend configuration moved out of the component module and unused React/Python imports removed. Tests include eight regressions that failed on the merged baseline, plus session status/subject, provisioning rollback, conflict rollback and JWKS key selection.

Production Clerk tenant configuration, independently approved legacy mappings, provider email delivery, real-browser MFA/logout/revocation journeys and all remaining master-PDF release gates still require acceptance. This document does not mark the app production-ready.

The public account-authentication exception is recorded in the existing permission inventory with its concrete ownership checks; financial workspace write gates remain intact. CLERK_SECRET_KEY is a server-only provider-managed secret in the canonical inventory with provider revoke-and-replace rotation. Rollback: disable Clerk exchange with CLERK_ENABLED=false while preserving its identity rows and all prior source changes; do not restore unsafe email linking.
