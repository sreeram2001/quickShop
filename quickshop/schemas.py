# The shapes/schemas of the data the tools return.
from typing import Literal

from pydantic import BaseModel

class Listing(BaseModel):
    title: str
    price: float
    merchant: str
    domain: str | None = None
    rating: float | None = None
    reviews: int | None = None
    url: str

class Evidence(BaseModel):
    url: str
    composition: dict[str, float] | None = None
    origin: str | None = None
    seller_identity: str | None = None
    return_policy: bool | None = None
    color: str | None = None
    available: bool = True

class MerchantSignals(BaseModel):
    merchant: str
    known_brand: bool | None = None
    domain_age_years: float | None = None
    third_party_reviews: int | None = None
    return_policy: bool | None = None
    available: bool = True

class Scores(BaseModel):
    url: str
    price: int | None = None
    quality: int | None = None
    legitimacy: int | None = None
    overall: float | None = None
    eligible: bool = False
    risk: Literal["low", "medium", "high"] | None = None
    evidence: list[str] = []
    available: bool = True
