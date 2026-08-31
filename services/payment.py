from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Tuple
from uuid import uuid4

import mercadopago
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Payment, PaymentStatus, PaymentMethod, TransactionType, User
from services.balance import BalanceService


class PaymentService:
    """Integração com Mercado Pago + gestão de cobranças PIX."""

    def __init__(self):
        self.sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)

    async def create_pix(
        self,
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
    ) -> Payment:
        if amount < Decimal(str(settings.PIX_MIN_VALUE)):
            raise ValueError(f"Valor mínimo: R$ {settings.PIX_MIN_VALUE:.2f}")
        if amount > Decimal(str(settings.PIX_MAX_VALUE)):
            raise ValueError(f"Valor máximo: R$ {settings.PIX_MAX_VALUE:.2f}")

        # Calcula bônus
        bonus = Decimal("0.00")
        if settings.BONUS_ENABLED and amount >= Decimal(str(settings.BONUS_MIN_VALUE)):
            bonus = (amount * Decimal(str(settings.BONUS_PERCENT)) / Decimal("100")).quantize(Decimal("0.01"))
            if settings.BONUS_MAX_VALUE:
                max_bonus = Decimal(str(settings.BONUS_MAX_VALUE))
                if bonus > max_bonus:
                    bonus = max_bonus

        total_credited = amount + bonus
        external_ref = str(uuid4())

        # Cria cobrança no Mercado Pago
        payment_data = {
            "transaction_amount": float(amount),
            "description": f"Recarga {settings.STORE_NAME}",
            "payment_method_id": "pix",
            "payer": {
                "email": f"user{user_id}@telegram.local",
            },
            "external_reference": external_ref,
        }

        if settings.MP_NOTIFICATION_URL:
            payment_data["notification_url"] = settings.MP_NOTIFICATION_URL

        result = self.sdk.payment().create(payment_data)
        response = result.get("response", {})

        if result.get("status") not in (200, 201):
            raise RuntimeError(f"Erro Mercado Pago: {response}")

        mp_id = str(response["id"])
        pix_data = response.get("point_of_interaction", {}).get("transaction_data", {})

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PIX_EXPIRATION_MINUTES)

        payment = Payment(
            user_id=user_id,
            amount=amount,
            bonus_amount=bonus,
            total_credited=total_credited,
            status=PaymentStatus.PENDING,
            method=PaymentMethod.PIX,
            gateway="mercadopago",
            gateway_id=mp_id,
            pix_copy_paste=pix_data.get("qr_code"),
            qr_code_base64=pix_data.get("qr_code_base64"),
            expires_at=expires_at,
            external_reference=external_ref,
            metadata_={"mp_response": response},
        )
        session.add(payment)
        await session.flush()
        return payment

    async def process_webhook(
        self,
        session: AsyncSession,
        gateway_id: str,
    ) -> Optional[Payment]:
        """
        Processa notificação do Mercado Pago de forma idempotente.
        """
        # Busca pagamento local
        result = await session.execute(
            select(Payment).where(Payment.gateway_id == gateway_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            return None

        # Já processado → idempotência
        if payment.status == PaymentStatus.APPROVED:
            return payment

        # Consulta status real no MP
        mp_result = self.sdk.payment().get(gateway_id)
        mp_payment = mp_result.get("response", {})
        status = mp_payment.get("status")

        if status == "approved":
            payment.status = PaymentStatus.APPROVED
            payment.paid_at = datetime.now(timezone.utc)

            # Credita saldo (idempotente por causa do status acima)
            await BalanceService.add_balance(
                session=session,
                user_id=payment.user_id,
                amount=payment.amount,
                tx_type=TransactionType.DEPOSIT,
                description=f"Depósito PIX #{payment.uuid[:8]}",
                payment_id=payment.id,
            )

            if payment.bonus_amount > 0:
                await BalanceService.add_balance(
                    session=session,
                    user_id=payment.user_id,
                    amount=payment.bonus_amount,
                    tx_type=TransactionType.BONUS,
                    description=f"Bônus de recarga #{payment.uuid[:8]}",
                    payment_id=payment.id,
                )

            await session.flush()
            return payment

        elif status in ("rejected", "cancelled"):
            payment.status = PaymentStatus.REJECTED if status == "rejected" else PaymentStatus.CANCELLED
            await session.flush()

        elif status == "expired":
            payment.status = PaymentStatus.EXPIRED
            await session.flush()

        return payment

    async def expire_pending(self, session: AsyncSession) -> int:
        """Marca como expirados os PIX vencidos (rodar periodicamente)."""
        now = datetime.now(timezone.utc)
        result = await session.execute(
            select(Payment).where(
                Payment.status == PaymentStatus.PENDING,
                Payment.expires_at < now,
            )
        )
        payments = list(result.scalars().all())
        for p in payments:
            p.status = PaymentStatus.EXPIRED
        await session.flush()
        return len(payments)
