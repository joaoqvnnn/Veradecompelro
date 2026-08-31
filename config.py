from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ==================== BOT ====================
    BOT_TOKEN: str = Field(..., description="Token do bot do Telegram")
    BOT_USERNAME: str = Field(default="larizinhastorebot", description="Username do bot sem @")

    # ==================== ADMIN ====================
    ADMIN_IDS: List[int] = Field(default_factory=list, description="IDs dos administradores (Owner)")
    
    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    # ==================== DATABASE ====================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/larizinha",
        description="URL do PostgreSQL (async)"
    )

    # ==================== REDIS ====================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="URL do Redis"
    )

    # ==================== MERCADO PAGO ====================
    MP_ACCESS_TOKEN: str = Field(..., description="Access Token do Mercado Pago")
    MP_PUBLIC_KEY: Optional[str] = Field(default=None, description="Public Key do Mercado Pago")
    MP_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Secret para validar webhooks (opcional)")
    MP_NOTIFICATION_URL: Optional[str] = Field(
        default=None,
        description="URL pública do webhook (ex: https://seudominio.com/webhook/mercadopago)"
    )

    # ==================== LOJA ====================
    STORE_NAME: str = Field(default="Larizinha Store", description="Nome da loja")
    STORE_CURRENCY: str = Field(default="BRL", description="Moeda")
    STORE_TIMEZONE: str = Field(default="America/Sao_Paulo", description="Fuso horário")
    SUPPORT_USERNAME: str = Field(default="suporte_larizinha", description="Username do suporte sem @")
    CHANNEL_USERNAME: Optional[str] = Field(default=None, description="Canal oficial sem @")
    GROUP_USERNAME: Optional[str] = Field(default=None, description="Grupo oficial sem @")

    # ==================== PIX ====================
    PIX_EXPIRATION_MINUTES: int = Field(default=10, description="Tempo de expiração do PIX em minutos")
    PIX_MIN_VALUE: float = Field(default=1.00, description="Valor mínimo de recarga")
    PIX_MAX_VALUE: float = Field(default=5000.00, description="Valor máximo de recarga")

    # ==================== BÔNUS DE RECARGA ====================
    BONUS_ENABLED: bool = Field(default=True, description="Ativar bônus de recarga")
    BONUS_PERCENT: float = Field(default=10.0, description="Porcentagem de bônus")
    BONUS_MIN_VALUE: float = Field(default=10.00, description="Valor mínimo para receber bônus")
    BONUS_MAX_VALUE: Optional[float] = Field(default=None, description="Valor máximo de bônus (None = sem limite)")

    # ==================== AFILIADOS ====================
    AFFILIATE_ENABLED: bool = Field(default=True, description="Sistema de afiliados ativo")
    AFFILIATE_COMMISSION_PERCENT: float = Field(default=20.0, description="Comissão padrão em %")
    AFFILIATE_MIN_WITHDRAW: float = Field(default=20.00, description="Valor mínimo para saque")
    AFFILIATE_LEVELS_ENABLED: bool = Field(default=False, description="Ativar níveis de afiliado")

    # ==================== ESTOQUE ====================
    LOW_STOCK_THRESHOLD: int = Field(default=5, description="Aviso de estoque baixo quando chegar nesse valor")

    # ==================== SEGURANÇA / ANTI-FLOOD ====================
    RATE_LIMIT_COMMANDS: int = Field(default=5, description="Máximo de comandos por janela")
    RATE_LIMIT_WINDOW: int = Field(default=10, description="Janela de rate limit em segundos")
    CALLBACK_RATE_LIMIT: int = Field(default=3, description="Máximo de cliques em botões por segundo")
    MAX_PIX_PER_HOUR: int = Field(default=10, description="Máximo de PIX gerados por usuário por hora")
    MAX_GIFT_ATTEMPTS: int = Field(default=5, description="Tentativas de gift card por hora")

    # ==================== MANUTENÇÃO ====================
    MAINTENANCE_MODE: bool = Field(default=False, description="Modo manutenção")
    MAINTENANCE_MESSAGE: str = Field(
        default="🔧 Nosso sistema está temporariamente em manutenção.\nVoltaremos em breve.",
        description="Mensagem exibida no modo manutenção"
    )

    # ==================== ENTREGA ====================
    DELIVERY_EMAIL_ENABLED: bool = Field(default=True, description="Permitir entrega por e-mail")
    DELIVERY_WHATSAPP_ENABLED: bool = Field(default=False, description="Permitir entrega por WhatsApp")
    WHATSAPP_API_URL: Optional[str] = Field(default=None, description="URL da API WhatsApp Business")
    WHATSAPP_API_TOKEN: Optional[str] = Field(default=None, description="Token da API WhatsApp")

    # ==================== WEBHOOK SERVER ====================
    WEBHOOK_HOST: str = Field(default="0.0.0.0", description="Host do servidor de webhook")
    WEBHOOK_PORT: int = Field(default=8080, description="Porta do servidor de webhook")
    WEBHOOK_PATH: str = Field(default="/webhook/mercadopago", description="Path do webhook do Mercado Pago")

    # ==================== LOGS ====================
    LOG_LEVEL: str = Field(default="INFO", description="Nível de log (DEBUG, INFO, WARNING, ERROR)")


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Atalho global
settings = get_settings()
