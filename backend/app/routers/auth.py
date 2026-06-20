from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.schemas import UserCreate, UserLogin, UserOut, Token
from app.core.security import hash_password, verify_password, create_access_token
from app.core.rate_limit import limiter
from app.crud import user_crud, participant_team_crud

router = APIRouter(prefix="/auth", tags=["Auth"])


# request: Request es obligatorio para que slowapi resuelva la IP del cliente.
@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(request: Request, data: UserCreate, db: AsyncSession = Depends(get_db)):
    if not await participant_team_crud.exists(db, data.team_name):
        raise HTTPException(
            status_code=400,
            detail=f"Equipo '{data.team_name}' no está en la lista de la quiniela.",
        )

    existing = await user_crud.get_by_email_or_team(db, data.email, data.team_name)
    if existing:
        raise HTTPException(status_code=409, detail="Email o equipo ya registrado.")

    user = await user_crud.create(
        db,
        team_name=data.team_name,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    return user


@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await user_crud.get_by_email(db, data.email)

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserOut.model_validate(user))
