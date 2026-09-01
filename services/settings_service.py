from typing import Any, Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SystemSetting


# Valores padrão (usados se não existir no banco)
DEFAULTS: Dict[str, Any] = {
    # Gerais
    "store_name": "Larizinha Store",
    "support_link": "https://t.me/suporte",
    "logs_chat_id": "",
    "separator": "===",
    "maintenance_mode": "false",
    "registration_bonus": "0.00",

    # PIX
    "mp_access_token": "",
    "pix_min": "1.00",
    "pix_max": "150.00",
    "pix_expiration_minutes": "15",
    "bonus_percent": "0",
    "bonus_min_value": "0.00",
    "pix_manual_enabled": "false",
    "pix_auto_enabled": "true",

    # Afiliados (pontos)
    "affiliate_enabled": "true",
    "points_per_recharge": "1",
    "points_min_convert": "500",
    "points_multiplier": "0.01",

    # Outros
    "bot_username": "",
}


class SettingsService:
    """Lê e grava configurações no banco (SystemSetting)."""

    @staticmethod
    async def get(session: AsyncSession, key: str, default: Any = None) -> str:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        row = result.scalar_one_or_none()
        if row:
            return row.value
        if default is not None:
            return str(default)
        return str(DEFAULTS.get(key, ""))

    @staticmethod
    async def get_bool(session: AsyncSession, key: str) -> bool:
        val = await SettingsService.get(session, key)
        return str(val).lower() in ("1", "true", "yes", "on", "sim")

    @staticmethod
    async def get_float(session: AsyncSession, key: str) -> float:
        try:
            return float(await SettingsService.get(session, key) or 0)
        except ValueError:
            return 0.0

    @staticmethod
    async def get_int(session: AsyncSession, key: str) -> int:
        try:
            return int(float(await SettingsService.get(session, key) or 0))
        except ValueError:
            return 0

    @staticmethod
    async def set(
        session: AsyncSession,
        key: str,
        value: Any,
        admin_id: Optional[int] = None,
        description: str = "",
    ) -> SystemSetting:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        row = result.scalar_one_or_none()
        str_value = str(value)

        if row:
            row.value = str_value
            row.updated_by = admin_id
            if description:
                row.description = description
        else:
            row = SystemSetting(
                key=key,
                value=str_value,
                value_type="string",
                description=description or key,
                updated_by=admin_id,
            )
            session.add(row)

        await session.flush()
        return row

    @staticmethod
    async def get_many(session: AsyncSession, keys: list[str]) -> Dict[str, str]:
        out = {}
        for key in keys:
            out[key] = await SettingsService.get(session, key)
        return out

    @staticmethod
    async def ensure_defaults(session: AsyncSession) -> None:
        """Cria no banco as keys que ainda não existem."""
        for key, value in DEFAULTS.items():
            result = await session.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            if result.scalar_one_or_none() is None:
                session.add(
                    SystemSetting(
                        key=key,
                        value=str(value),
                        value_type="string",
                        description=key,
                    )
                )
        await session.flush()
