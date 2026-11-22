"""What the basket endpoints accept and return. Never the model itself."""

from datetime import datetime

from pydantic import BaseModel, Field

from faisca.modules.records.public import MarcFormat


class BasketItemCreate(BaseModel):
    """The body of `POST /basket`: a record id from a catalogue search."""

    record_id: str = Field(min_length=3, max_length=300)


class BasketItemRead(BaseModel):
    """One record in the basket."""

    id: int
    record_id: str
    title: str
    authors: list[str]
    year: str | None
    target_name: str
    source_format: MarcFormat
    created_at: datetime


class BasketRead(BaseModel):
    """The whole basket, oldest first (the order of the exported file)."""

    items: list[BasketItemRead]
    count: int


# moarch:module-schemas
