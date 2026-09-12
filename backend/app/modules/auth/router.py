from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_admin
from app.core.security import create_access_token
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    BusinessSettingsOut,
    BusinessSettingsUpdate,
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = service.authenticate(db, data.email, data.password)
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    return service.list_users(db)


@router.post(
    "/users", response_model=UserOut, status_code=201, dependencies=[Depends(require_admin)]
)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    return service.create_user(db, data)


@router.patch("/users/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db)):
    return service.update_user(db, user_id, data)


@router.get(
    "/settings/business",
    response_model=BusinessSettingsOut,
    dependencies=[Depends(get_current_user)],
)
def get_settings(db: Session = Depends(get_db)):
    return service.get_business_settings(db)


@router.put(
    "/settings/business",
    response_model=BusinessSettingsOut,
    dependencies=[Depends(require_admin)],
)
def update_settings(data: BusinessSettingsUpdate, db: Session = Depends(get_db)):
    return service.update_business_settings(db, data)
