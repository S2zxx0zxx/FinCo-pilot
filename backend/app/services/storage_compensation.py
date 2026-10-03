"""Compensate failed new uploads without deleting ambiguously committed data."""
import logging

from sqlalchemy import Select, CompoundSelect
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.storage import StorageProvider

logger = logging.getLogger(__name__)


async def compensate_upload(
    session: AsyncSession, storage: StorageProvider, key: str, reference_query: Select | CompoundSelect,
) -> None:
    try:
        await session.rollback()
        # A commit can succeed remotely even when its acknowledgement is lost.
        # Delete only after a new transaction proves that no row references it.
        referenced = (await session.execute(reference_query)).first()
        if referenced is not None:
            return
        await storage.delete(key)
    except Exception as exc:
        # Preserve bytes when DB state is unknown. Never log provider messages
        # or object keys; reconciliation is part of the deletion workflow.
        logger.warning("Upload compensation deferred (%s)", type(exc).__name__)
