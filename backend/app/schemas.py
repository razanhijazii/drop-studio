"""Request and response shapes for the API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal["hoodie", "t-shirt", "sweatshirt", "sweatpants"]
Size = Literal["XS", "S", "M", "L", "XL", "XXL"]
Status = Literal["draft", "production", "launched", "closed"]
Channel = Literal["store", "online", "instagram", "event", "other"]
Month = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ brand

class ProfileIn(BaseModel):
    name: str = ""
    one_liner: str = ""
    concepts: str = ""
    price_position: str = ""
    customer: str = ""
    never_do: str = ""
    currency: str = Field("USD", min_length=3, max_length=3)
    target_margin: float = Field(0.70, gt=0, lt=1)
    min_margin: float = Field(0.55, gt=0, lt=1)
    market_position: float = Field(0.90, gt=0.3, le=1.5)
    first_drop_units: int = Field(30, ge=1, le=10000)
    min_order_qty: int = Field(0, ge=0, le=10000)

    @field_validator("currency")
    @classmethod
    def upper(cls, v: str) -> str:
        return v.upper()


class ProfileOut(ProfileIn, ORM):
    updated_at: datetime | None = None


class DnaIn(BaseModel):
    text: str = Field(min_length=2, max_length=500)
    source: str = "added by you"
    active: bool = True


class DnaOut(DnaIn, ORM):
    id: int
    created_at: datetime


class SignalIn(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    source: str = ""
    note: str = ""
    url: str = ""


class SignalOut(SignalIn, ORM):
    id: int
    created_at: datetime


class ScoutIn(BaseModel):
    launch_month: str = Month
    hint: str = ""


class TrendReportOut(ORM):
    id: int
    launch_month: str
    hint: str
    result: dict
    created_at: datetime


# ------------------------------------------------------------------ drops

class Colour(BaseModel):
    name: str
    hex: str


class PieceIn(BaseModel):
    category: Category
    name: str = ""
    color: str = ""
    fit: str = ""
    fabric: str = ""
    gsm: int | None = Field(None, ge=50, le=1000)
    unit_cost: float | None = Field(None, ge=0)
    price: float | None = Field(None, ge=0)
    units_made: int | None = Field(None, ge=0)
    made_by_size: dict[Size, int] = {}


class PieceUpdate(BaseModel):
    category: Category | None = None
    name: str | None = None
    color: str | None = None
    fit: str | None = None
    fabric: str | None = None
    gsm: int | None = Field(None, ge=50, le=1000)
    unit_cost: float | None = Field(None, ge=0)
    price: float | None = Field(None, ge=0)
    units_made: int | None = Field(None, ge=0)
    made_by_size: dict[Size, int] | None = None


class PieceOut(PieceIn, ORM):
    id: int
    look_id: int


class LookIn(BaseModel):
    position: int = Field(1, ge=1, le=4)
    name: str = ""
    signature_detail: str = ""
    pieces: list[PieceIn] = []


class LookUpdate(BaseModel):
    name: str | None = None
    signature_detail: str | None = None


class LookOut(ORM):
    id: int
    position: int
    name: str
    signature_detail: str
    pieces: list[PieceOut]


class StoreMood(BaseModel):
    lighting: str = ""
    scent: str = ""
    sound: str = ""
    display: str = ""
    ritual: str = ""


class DropIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    trend: str = ""
    launch_month: str = ""
    story: str = ""
    palette: list[Colour] = []
    store: StoreMood = StoreMood()
    moodboard: list[str] = []
    avoid: list[str] = []
    looks: list[LookIn] = Field([], max_length=4)


class DropUpdate(BaseModel):
    name: str | None = None
    trend: str | None = None
    launch_month: str | None = None
    story: str | None = None
    palette: list[Colour] | None = None
    store: StoreMood | None = None
    moodboard: list[str] | None = None
    avoid: list[str] | None = None
    status: Status | None = None
    launched_on: date | None = None


class ExpenseIn(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    amount: float = Field(ge=0)
    spent_on: date | None = None


class ExpenseOut(ExpenseIn, ORM):
    id: int
    drop_id: int


class DropSummary(ORM):
    id: int
    name: str
    trend: str
    launch_month: str
    status: str
    launched_on: date | None
    created_at: datetime
    revenue: float = 0
    units_sold: int = 0
    sell_through: float | None = None
    net_profit: float = 0


class DropOut(ORM):
    id: int
    name: str
    trend: str
    launch_month: str
    story: str
    palette: list[Colour]
    store: StoreMood
    moodboard: list[str]
    avoid: list[str]
    status: str
    launched_on: date | None
    created_at: datetime
    looks: list[LookOut]
    expenses: list[ExpenseOut]


class GenerateDropIn(BaseModel):
    trend: str = Field(min_length=2)
    launch_month: str = Month
    direction: str = ""


# ------------------------------------------------------------------ sales

class SaleIn(BaseModel):
    piece_id: int
    quantity: int = Field(ge=1, le=10000)
    unit_price: float | None = Field(None, ge=0, description="Defaults to the piece's list price")
    size: Size | None = None
    sold_on: date | None = None
    channel: Channel = "store"
    note: str = ""


class SaleOut(ORM):
    id: int
    piece_id: int
    quantity: int
    unit_price: float
    size: str | None
    sold_on: date
    channel: str
    note: str
    piece_name: str = ""
    drop_id: int | None = None
    drop_name: str = ""


# ------------------------------------------------------------------ pricing

class CompetitorIn(BaseModel):
    brand: str = Field(min_length=1, max_length=120)
    category: Category
    price: float = Field(gt=0)
    note: str = ""


class CompetitorOut(CompetitorIn, ORM):
    id: int


class PriceQuery(BaseModel):
    unit_cost: float = Field(gt=0)
    category: Category
    current_price: float | None = Field(None, gt=0)


# ------------------------------------------------------------------ auth

class LoginIn(BaseModel):
    password: str


class TokenOut(BaseModel):
    token: str
    expires_at: datetime
