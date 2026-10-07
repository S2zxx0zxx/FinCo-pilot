"""Explicit finite Test mandate enrollment; durable one-POST claim before I/O."""
import asyncio
from datetime import datetime, timedelta, timezone
import math
import re
import uuid

from fastapi import HTTPException
from sqlalchemy import select, update
from starlette.concurrency import run_in_threadpool

from app.billing.activation import activation_enabled
from app.billing.enums import BillingInterval, PlanId
from app.billing.offer_service import _stored_utc
from app.billing.offers import PROVIDER_PLAN_SPECS
from app.billing.razorpay_catalog import configured_provider_plan_id, validate_provider_plan
from app.core.config import get_settings
from app.models.account_deletion import AccountDeletion
from app.models.payment_activation import PaymentActivation
from app.models.payment_renewal import RenewalCycle, RenewalMandate
from app.models.pricing_offer import CheckoutReservation
from app.models.subscription import Subscription
from app.models.user import User


def enabled() -> bool:
    return activation_enabled() and get_settings().billing_renewal_enabled


def utc_required(value):
    result = _stored_utc(value)
    if result is None:
        raise ValueError("Required renewal timestamp is missing")
    return result


def identifier(value, prefix):
    return isinstance(value, str) and re.fullmatch(prefix + r"_[A-Za-z0-9]{1,100}", value) is not None


def mandate_notes(row):
    return {"fincopilot_renewal_id": str(row.id), "fincopilot_user_id": str(row.user_id),
            "fincopilot_activation_id": str(row.activation_id), "fincopilot_subscription_id": str(row.subscription_id),
            "fincopilot_plan": row.plan, "fincopilot_interval": row.billing_interval}


def validate_plan(row, plan):
    spec = PROVIDER_PLAN_SPECS.get((PlanId(row.plan), BillingInterval(row.billing_interval)))
    if (spec is None or not isinstance(plan, dict) or plan.get("entity") != "plan"
            or type(plan.get("interval")) is not int or not isinstance(plan.get("item"), dict)
            or type(plan["item"].get("amount")) is not int
            or row.amount_minor != spec.amount_minor or row.currency != spec.currency
            or not validate_provider_plan(spec=spec, provider_plan_id=row.provider_plan_id, provider_plan=plan).valid):
        raise ValueError("Invalid configured renewal plan")


def validate_subscription(row, subscription, *, statuses=None):
    allowed = statuses if statuses is not None else {"created", "authenticated", "active", "completed", "expired"}
    if (not isinstance(subscription, dict) or subscription.get("entity") != "subscription"
            or not identifier(subscription.get("id"), "sub")
            or (row.provider_subscription_id and subscription["id"] != row.provider_subscription_id)
            or subscription.get("status") not in allowed
            or type(subscription.get("paid_count")) is not int
            or not 0 <= subscription["paid_count"] <= row.total_count
            or subscription.get("plan_id") != row.provider_plan_id
            or type(subscription.get("quantity")) is not int or subscription["quantity"] != 1
            or type(subscription.get("total_count")) is not int or subscription["total_count"] != row.total_count
            or type(subscription.get("start_at")) is not int
            or subscription["start_at"] != int(utc_required(row.starts_at).timestamp())
            or type(subscription.get("expire_by")) is not int
            or subscription["expire_by"] != int(utc_required(row.starts_at).timestamp())
            or not isinstance(subscription.get("notes"), dict)
            or any(subscription["notes"].get(k) != v for k, v in mandate_notes(row).items())):
        raise ValueError("Invalid bound renewal subscription")
    return subscription["id"]


def response(row):
    return {"available": True, "mandate_id": str(row.id), "state": row.state,
            "key_id": row.provider_key_id, "subscription_id": row.provider_subscription_id,
            "plan": row.plan, "interval": row.billing_interval, "amount_minor": row.amount_minor,
            "currency": row.currency, "starts_at": _stored_utc(row.starts_at), "total_count": row.total_count}


async def source(session, user_id, *, lock=False):
    settings = get_settings()
    query = select(User).where(User.id == user_id)
    user = await session.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
    if user is None or not user.is_active:
        raise HTTPException(409, "An active account is required.")
    if await session.scalar(select(AccountDeletion.id).where(AccountDeletion.user_id == user_id,
                                                           AccountDeletion.state != "cancelled").limit(1)):
        raise HTTPException(409, "Account deletion prevents renewal enrollment.")
    query = select(Subscription).where(Subscription.user_id == user_id)
    sub = await session.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
    grant = await session.scalar(select(PaymentActivation).where(PaymentActivation.user_id == user_id).limit(1))
    if (sub is None or grant is None or sub.provider != "razorpay" or sub.status != "active"
            or sub.paid_term_refunded or sub.cancel_at_period_end or (sub.plan, sub.billing_interval) != (grant.plan, grant.billing_interval)
            or grant.mode != "test" or grant.account_id != settings.razorpay_webhook_account_id
            or grant.provider_key_id != settings.razorpay_key_id or _stored_utc(sub.current_period_end) is None):
        raise HTTPException(409, "Verified compatible paid service is required for renewal.")
    from app.models.payment_cancellation import PaymentCancellation
    if await session.scalar(select(PaymentCancellation.id).where(PaymentCancellation.user_id == user_id).limit(1)):
        raise HTTPException(409, "Cancellation requires reconciliation before new enrollment.")
    quote = await session.get(CheckoutReservation, grant.reservation_id)
    spec = PROVIDER_PLAN_SPECS.get((PlanId(sub.plan), BillingInterval(sub.billing_interval)))
    if quote is None or spec is None or quote.renewal_amount_minor != spec.amount_minor or quote.renewal_interval != sub.billing_interval:
        raise HTTPException(409, "Renewal price requires review against the original quote.")
    last = await session.scalar(select(RenewalCycle).where(RenewalCycle.user_id == user_id).order_by(RenewalCycle.period_end.desc()).limit(1))
    paid_end = _stored_utc(last.period_end if last else grant.period_end)
    if _stored_utc(sub.current_period_end) != paid_end:
        raise HTTPException(409, "Paid term changed; reconciliation is required.")
    return sub, grant, spec


async def preview(session, user_id):
    if not enabled():
        return {"available": False}
    try:
        sub, _, spec = await source(session, user_id)
    except HTTPException:
        return {"available": False}
    row = await session.scalar(select(RenewalMandate).where(RenewalMandate.active_user_id == user_id))
    if row:
        result = response(row)
        result["paid_cycles"] = len(list((await session.scalars(select(RenewalCycle.id).where(RenewalCycle.mandate_id == row.id))).all()))
        return result
    return {"available": True, "plan": sub.plan, "interval": sub.billing_interval,
            "amount_minor": spec.amount_minor, "currency": spec.currency, "total_count_max": 120,
            "paid_through": _stored_utc(sub.current_period_end)}


async def create_mandate(session, user_id, total_count, client, *, now=None):
    if not enabled():
        raise HTTPException(503, "Renewal enrollment is disabled.")
    if type(total_count) is not int or not 1 <= total_count <= 120:
        raise HTTPException(422, "Select between 1 and 120 finite renewal cycles.")
    current = now or datetime.now(timezone.utc)
    settings = get_settings()
    key, account = settings.razorpay_key_id, settings.razorpay_webhook_account_id
    sub, grant, spec = await source(session, user_id, lock=True)
    row = await session.scalar(select(RenewalMandate).where(RenewalMandate.active_user_id == user_id).with_for_update())
    dispatch = row is None or row.state == "unstarted"
    if row:
        if row.total_count != total_count or row.provider_key_id != key or row.account_id != account:
            raise HTTPException(409, "Finish the original renewal enrollment before changing its terms.")
        if row.state == "ready" and utc_required(row.starts_at) > current:
            await session.commit()
            return response(row)
        if row.state == "creating" and utc_required(row.requested_at) > current - timedelta(seconds=60):
            raise HTTPException(409, "Renewal enrollment is already in progress.", headers={"Retry-After": "5"})
    else:
        plan_id = configured_provider_plan_id(PlanId(sub.plan), BillingInterval(sub.billing_interval))
        if not identifier(plan_id, "plan"):
            raise HTTPException(503, "A verified Test renewal plan must be configured.")
        if sub.provider_subscription_id:
            previous = await session.scalar(select(RenewalMandate).where(
                RenewalMandate.provider_subscription_id == sub.provider_subscription_id,
                RenewalMandate.user_id == user_id, RenewalMandate.state == "completed"))
            if previous is None:
                raise HTTPException(409, "An existing provider mandate requires review.")
        start_epoch = max(math.ceil(utc_required(sub.current_period_end).timestamp()), math.ceil(current.timestamp()) + 900)
        row = RenewalMandate(id=uuid.uuid4(), user_id=user_id, active_user_id=user_id,
            activation_id=grant.id, subscription_id=sub.id, mode="test", account_id=account,
            provider_key_id=key, provider_plan_id=plan_id, plan=sub.plan, billing_interval=sub.billing_interval,
            amount_minor=spec.amount_minor, currency=spec.currency, total_count=total_count,
            starts_at=datetime.fromtimestamp(start_epoch, timezone.utc), requested_at=current, state="unstarted")
        session.add(row)
    identity = row.id
    # Auth/user/claim reads are all committed before GET/POST, including API's auth transaction.
    await session.commit()
    await session.refresh(row)
    await session.commit()
    try:
        async with asyncio.timeout(150):
            plan = await run_in_threadpool(client.plan.fetch, row.provider_plan_id)
            validate_plan(row, plan)
            if dispatch:
                # A transient plan GET failure is known not to have dispatched a
                # POST. Only a committed unstarted -> creating claim may send it.
                await source(session, user_id, lock=True)
                fresh = await session.scalar(select(RenewalMandate).where(RenewalMandate.id == identity)
                    .with_for_update().execution_options(populate_existing=True))
                if (fresh is None or fresh.provider_key_id != key or fresh.account_id != account
                        or not enabled() or settings.razorpay_key_id != key
                        or settings.razorpay_webhook_account_id != account):
                    raise HTTPException(409, "Renewal enrollment changed before dispatch.")
                validate_plan(fresh, plan)
                claim = await session.execute(update(RenewalMandate).where(RenewalMandate.id == identity,
                    RenewalMandate.state == "unstarted").values(state="creating").returning(RenewalMandate.id))
                claimed = claim.scalar_one_or_none() is not None
                await session.commit()
                if not claimed:
                    raise HTTPException(409, "The original enrollment is already dispatched; reconcile it.")
                row = fresh
                provider = await run_in_threadpool(client.subscription.create, data={
                    "plan_id": row.provider_plan_id, "total_count": row.total_count, "quantity": 1,
                    "start_at": int(utc_required(row.starts_at).timestamp()),
                    "expire_by": int(utc_required(row.starts_at).timestamp()), "customer_notify": True,
                    "notes": mandate_notes(row)})
            elif row.provider_subscription_id:
                provider = await run_in_threadpool(client.subscription.fetch, row.provider_subscription_id)
            else:
                matches = []
                for page in range(5):
                    listing = await run_in_threadpool(client.subscription.all, {"count": 100, "skip": page * 100})
                    if (not isinstance(listing, dict) or listing.get("entity") != "collection"
                            or not isinstance(listing.get("items"), list) or type(listing.get("count")) is not int
                            or listing["count"] != len(listing["items"])):
                        raise ValueError("Invalid mandate inventory")
                    items = listing["items"]
                    matches.extend(item for item in items if isinstance(item, dict)
                                   and isinstance(item.get("notes"), dict)
                                   and item["notes"].get("fincopilot_renewal_id") == str(identity))
                    if len(items) < 100:
                        break
                else:
                    raise ValueError("Incomplete mandate inventory")
                if len(matches) != 1:
                    raise ValueError("Unresolved mandate inventory")
                provider = matches[0]
            provider_id = validate_subscription(row, provider)
    except HTTPException:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        await session.execute(update(RenewalMandate).where(RenewalMandate.id == identity,
            RenewalMandate.state.in_(("creating", "uncertain"))).values(state="uncertain"))
        await session.commit()
        raise HTTPException(502, "Renewal enrollment outcome is unresolved. Retry this same enrollment; no second subscription is created.") from None
    try:
        sub, _, _ = await source(session, user_id, lock=True)
        fresh = await session.scalar(select(RenewalMandate).where(RenewalMandate.id == identity).with_for_update().execution_options(populate_existing=True))
        if (fresh is None or fresh.active_user_id != user_id or fresh.subscription_id != sub.id
                or not enabled() or settings.razorpay_key_id != key or settings.razorpay_webhook_account_id != account
                or fresh.provider_key_id != key or fresh.account_id != account
                or validate_subscription(fresh, provider) != provider_id):
            raise HTTPException(409, "Renewal enrollment changed; reconciliation is required.")
        if provider.get("status") == "expired" and type(provider.get("paid_count")) is int and provider["paid_count"] == 0:
            if await session.scalar(select(RenewalCycle.id).where(RenewalCycle.mandate_id == fresh.id).limit(1)):
                raise HTTPException(409, "Expired mandate conflicts with paid cycle evidence.")
            fresh.state, fresh.active_user_id = "expired", None
            if sub.provider_subscription_id == provider_id:
                sub.provider_subscription_id = None
            await session.commit()
            raise HTTPException(409, "Enrollment expired without a paid cycle. Submit a new finite authorization.")
        fresh.provider_subscription_id, fresh.state = provider_id, "ready"
        sub.provider_subscription_id = provider_id
        await session.commit()
        return response(fresh)
    except Exception:
        await session.rollback()
        raise
