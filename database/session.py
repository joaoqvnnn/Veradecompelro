from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from config import settings


# Engine principal
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,                    # True só em desenvolvimento se quiser ver SQL
    pool_pre_ping=True,            # Verifica conexão antes de usar
    pool_size=20,                  # Conexões no pool
    max_overflow=10,               # Conexões extras permitidas
    pool_recycle=3600,             # Recicla conexões a cada 1h
)


# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,        # Importante para não perder objetos após commit
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency / generator de sessão.
    Uso típico:

        async with get_session() as session:
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager limpo para uso em handlers e serviços.
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """
    Cria todas as tabelas (apenas para desenvolvimento / primeiro deploy).
    Em produção use Alembic.
    """
    from database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Fecha o engine (chamar no shutdown do bot)."""
    await engine.dispose()
