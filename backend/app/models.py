"""Database tables.

Money is stored as NUMERIC(12, 2) so totals never drift from float rounding.
A drop holds up to four looks; each look holds its pieces; every piece carries
its own cost, price and production quantity; sales are logged per piece.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

Money = Numeric(12, 2)

CATEGORIES = ("hoodie", "t-shirt", "sweatshirt", "sweatpants")
SIZES = ("XS", "S", "M", "L", "XL", "XXL")
DROP_STATUSES = ("draft", "production", "launched", "closed")
CHANNELS = ("store", "online", "instagram", "event", "other")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BrandProfile(Base):
    """A single row (id=1) describing the brand and its business settings."""

    __tablename__ = "brand_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    one_liner: Mapped[str] = mapped_column(Text, default="")
    concepts: Mapped[str] = mapped_column(Text, default="")
    price_position: Mapped[str] = mapped_column(Text, default="")
    customer: Mapped[str] = mapped_column(Text, default="")
    never_do: Mapped[str] = mapped_column(Text, default="")
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    # Business levers used by pricing and stock planning.
    target_margin: Mapped[float] = mapped_column(Numeric(4, 3), default=Decimal("0.700"))
    min_margin: Mapped[float] = mapped_column(Numeric(4, 3), default=Decimal("0.550"))
    market_position: Mapped[float] = mapped_column(Numeric(4, 3), default=Decimal("0.900"))
    first_drop_units: Mapped[int] = mapped_column(Integer, default=30)
    min_order_qty: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DnaRule(Base):
    __tablename__ = "dna_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200), default="added by you")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TrendSignal(Base):
    __tablename__ = "trend_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TrendReport(Base):
    __tablename__ = "trend_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    launch_month: Mapped[str] = mapped_column(String(7))
    hint: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Drop(Base):
    __tablename__ = "drops"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    trend: Mapped[str] = mapped_column(String(200), default="")
    launch_month: Mapped[str] = mapped_column(String(7), default="")
    story: Mapped[str] = mapped_column(Text, default="")
    palette: Mapped[list] = mapped_column(JSON, default=list)
    store: Mapped[dict] = mapped_column(JSON, default=dict)
    moodboard: Mapped[list] = mapped_column(JSON, default=list)
    avoid: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    launched_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    looks: Mapped[list[Look]] = relationship(
        back_populates="drop", cascade="all, delete-orphan", order_by="Look.position"
    )
    expenses: Mapped[list[Expense]] = relationship(back_populates="drop", cascade="all, delete-orphan")


class Look(Base):
    __tablename__ = "looks"

    id: Mapped[int] = mapped_column(primary_key=True)
    drop_id: Mapped[int] = mapped_column(ForeignKey("drops.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(200), default="")
    signature_detail: Mapped[str] = mapped_column(Text, default="")

    drop: Mapped[Drop] = relationship(back_populates="looks")
    pieces: Mapped[list[Piece]] = relationship(
        back_populates="look", cascade="all, delete-orphan", order_by="Piece.id"
    )


class Piece(Base):
    __tablename__ = "pieces"

    id: Mapped[int] = mapped_column(primary_key=True)
    look_id: Mapped[int] = mapped_column(ForeignKey("looks.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200), default="")
    color: Mapped[str] = mapped_column(String(120), default="")
    fit: Mapped[str] = mapped_column(String(200), default="")
    fabric: Mapped[str] = mapped_column(String(300), default="")
    gsm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    units_made: Mapped[int | None] = mapped_column(Integer, nullable=True)
    made_by_size: Mapped[dict] = mapped_column(JSON, default=dict)

    look: Mapped[Look] = relationship(back_populates="pieces")
    sales: Mapped[list[Sale]] = relationship(back_populates="piece", cascade="all, delete-orphan")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    piece_id: Mapped[int] = mapped_column(ForeignKey("pieces.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Money)
    size: Mapped[str | None] = mapped_column(String(8), nullable=True)
    sold_on: Mapped[date] = mapped_column(Date, index=True)
    channel: Mapped[str] = mapped_column(String(20), default="store")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    piece: Mapped[Piece] = relationship(back_populates="sales")


class Expense(Base):
    """Costs that aren't a single garment: store setup, launch event, packaging, ads."""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    drop_id: Mapped[int] = mapped_column(ForeignKey("drops.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Money)
    spent_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    drop: Mapped[Drop] = relationship(back_populates="expenses")


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(20))
    price: Mapped[Decimal] = mapped_column(Money)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DesignReview(Base):
    __tablename__ = "design_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="Untitled design")
    drop_id: Mapped[int | None] = mapped_column(ForeignKey("drops.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[bytes] = mapped_column(LargeBinary)
    image_type: Mapped[str] = mapped_column(String(40))
    feedback: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
