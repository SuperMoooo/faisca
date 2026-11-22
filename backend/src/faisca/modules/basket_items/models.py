"""The basket_items table: records chosen for export, kept until removed."""

from sqlalchemy import LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from faisca.db.base import Base, TimestampMixin


class BasketItem(TimestampMixin, Base):
    """One record in the export basket, with its UNIMARC ISO 2709 bytes.

    The bytes are stored when the record is added: search results live in the
    cache for a day, but the basket keeps its records until it is exported.
    """

    __tablename__ = "basket_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[str] = mapped_column(String(300), unique=True)
    title: Mapped[str] = mapped_column(String(1000))
    # Joined with AUTHOR_SEPARATOR; the basket only displays them.
    authors: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[str | None] = mapped_column(String(4))
    target_name: Mapped[str] = mapped_column(String(300))
    source_format: Mapped[str] = mapped_column(String(10))
    unimarc_iso2709: Mapped[bytes] = mapped_column(LargeBinary)


AUTHOR_SEPARATOR = "\n"

# moarch:module-models
