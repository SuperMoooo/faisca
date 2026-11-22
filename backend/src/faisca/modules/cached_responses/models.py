"""The cached_responses table: short-lived copies of what external services answered."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from faisca.db.base import Base, TimestampMixin


class CachedResponse(TimestampMixin, Base):
    """One cached answer (a target's results for a query, or one record), as JSON text."""

    __tablename__ = "cached_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True)
    payload: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


# moarch:module-models
