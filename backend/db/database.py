"""
Configuration SQLAlchemy async — connexion PostgreSQL.
Utilise asyncpg comme driver async.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from backend.config import settings


engine = create_async_engine(
    settings.database_url,
    echo=settings.env == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency FastAPI pour injecter une session DB."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Cree toutes les tables (utilisee au demarrage si besoin)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
