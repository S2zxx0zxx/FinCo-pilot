#!/usr/bin/env python3
"""Explicit Razorpay base-plan catalog provisioning/verification utility.

This command is intentionally NEVER called at application startup.

Examples:
    # Validate configured provider plan IDs.
    python scripts/razorpay_catalog.py --check

    # In Razorpay Test Mode, reuse exact matches or create missing base plans.
    python scripts/razorpay_catalog.py --provision

Live keys are rejected unless --allow-live is supplied explicitly.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from app.billing.offers import PROVIDER_PLAN_SPECS
from app.billing.razorpay_catalog import (
    configured_provider_plan_id,
    find_exact_provider_plan,
    provider_plan_create_payload,
    validate_provider_plan,
)
from app.core.config import get_settings


def _client():
    try:
        import razorpay
    except ImportError as exc:
        raise RuntimeError("razorpay package is not installed") from exc

    settings = get_settings()
    key_id = settings.razorpay_key_id.strip()
    key_secret = settings.razorpay_key_secret.get_secret_value().strip()
    if not key_id or not key_secret:
        raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET are required")
    return razorpay.Client(auth=(key_id, key_secret)), key_id


def _all_plans(client: Any) -> list[dict[str, Any]]:
    """Fetch provider plans in bounded pages without assuming one response page."""
    items: list[dict[str, Any]] = []
    skip = 0
    page_size = 100
    while True:
        response = client.plan.all({"count": page_size, "skip": skip})
        page = response.get("items", []) if isinstance(response, dict) else []
        if not isinstance(page, list):
            raise RuntimeError("Unexpected Razorpay plan-list response")
        items.extend(item for item in page if isinstance(item, dict))
        if len(page) < page_size:
            break
        skip += len(page)
    return items


def _ensure_safe_environment(key_id: str, *, allow_live: bool) -> None:
    if key_id.startswith("rzp_live_") and not allow_live:
        raise RuntimeError(
            "Live Razorpay key detected. Re-run with --allow-live only after an "
            "explicit production change review."
        )
    if not key_id.startswith(("rzp_test_", "rzp_live_")):
        raise RuntimeError("Unrecognised Razorpay key mode; refusing provider mutation")


def _check(client: Any) -> int:
    failures = 0
    for (plan, interval), spec in PROVIDER_PLAN_SPECS.items():
        provider_plan_id = configured_provider_plan_id(plan, interval)
        if provider_plan_id is None:
            print(f"MISSING {spec.env_name}")
            failures += 1
            continue
        try:
            provider_plan = client.plan.fetch(provider_plan_id)
        except Exception as exc:
            print(
                f"INVALID {spec.env_name}={provider_plan_id}: "
                f"provider fetch failed ({type(exc).__name__})"
            )
            failures += 1
            continue
        if not isinstance(provider_plan, dict):
            print(f"INVALID {spec.env_name}={provider_plan_id}: unexpected response")
            failures += 1
            continue
        result = validate_provider_plan(
            spec=spec,
            provider_plan_id=provider_plan_id,
            provider_plan=provider_plan,
        )
        if result.valid:
            print(f"OK {spec.env_name}={provider_plan_id}")
        else:
            failures += 1
            print(f"INVALID {spec.env_name}={provider_plan_id}")
            for error in result.errors:
                print(f"  - {error}")
    return 0 if failures == 0 else 2


def _provision(client: Any) -> int:
    provider_plans = _all_plans(client)
    output: dict[str, str] = {}

    for spec in PROVIDER_PLAN_SPECS.values():
        exact = find_exact_provider_plan(spec, provider_plans)
        if exact is None:
            created = client.plan.create(provider_plan_create_payload(spec))
            if not isinstance(created, dict) or not created.get("id"):
                raise RuntimeError(
                    f"Razorpay did not return a plan id for {spec.provider_name}"
                )
            provider_plan_id = str(created["id"])
            validation = validate_provider_plan(
                spec=spec,
                provider_plan_id=provider_plan_id,
                provider_plan=created,
            )
            if not validation.valid:
                raise RuntimeError(
                    f"Provider created an unexpected plan for {spec.provider_name}: "
                    + "; ".join(validation.errors)
                )
            provider_plans.append(created)
            print(f"CREATED {spec.provider_name}: {provider_plan_id}")
        else:
            provider_plan_id = str(exact["id"])
            print(f"REUSED {spec.provider_name}: {provider_plan_id}")
        output[spec.env_name] = provider_plan_id

    print("\nSet these deployment variables (Plan IDs are identifiers, not secrets):")
    for env_name, provider_plan_id in output.items():
        print(f"{env_name}={provider_plan_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--provision", action="store_true")
    parser.add_argument(
        "--allow-live",
        action="store_true",
        help="Explicitly allow use of rzp_live_* credentials.",
    )
    args = parser.parse_args()

    try:
        client, key_id = _client()
        _ensure_safe_environment(key_id, allow_live=args.allow_live)
        return _provision(client) if args.provision else _check(client)
    except Exception as exc:
        # Do not print credentials/provider auth headers. Exception class plus
        # stable operator-facing message is enough to troubleshoot safely.
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
