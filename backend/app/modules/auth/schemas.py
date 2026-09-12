from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2, max_length=120)
    role: str = Field(pattern="^(admin|vendedor)$")


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = Field(default=None, pattern="^(admin|vendedor)$")
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)


class BusinessSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_name: str
    tax_id: str | None
    address: str | None
    phone: str | None
    default_tax_rate: Decimal
    invoice_prefix: str
    default_low_stock_threshold: Decimal
    currency: str
    default_opening_amount: Decimal


class BusinessSettingsUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=1, max_length=150)
    tax_id: str | None = None
    address: str | None = None
    phone: str | None = None
    default_tax_rate: Decimal | None = Field(default=None, ge=0, le=1)
    invoice_prefix: str | None = Field(default=None, min_length=1, max_length=10)
    default_low_stock_threshold: Decimal | None = Field(default=None, ge=0)
    default_opening_amount: Decimal | None = Field(default=None, ge=0)
