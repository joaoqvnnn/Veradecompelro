from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import User, TransactionType, AffiliateWithdraw, WithdrawStatus
from services.balance import BalanceService


class AffiliateService:

    @staticmethod
    async def pay_commission(
        session: AsyncSession,
        referred_user_id: int,
        order_amount: Decimal,
        order_id: int,
    ) -> Optional[Decimal]:
        if not settings.AFFILIATE_ENABLED:
            return None

        user = await session.get(User, referred_user_id)
        if not user or not user.referred_by:
            return None

        commission = (order_amount * Decimal(str(settings.AFFILIATE_COMMISSION_PERCENT)) / Decimal("100")).quantize(Decimal("0.01"))
        if commission <= 0:
            return None

        await BalanceService.add_balance(
            session=session,
            user_id=user.referred_by,
            amount=commission,
            tx_type=TransactionType.AFFILIATE_COMMISSION,
            description=f"Comissão da compra #{order_id}",
            order_id=order_id,
        )
        return commission

    @staticmethod
    async def request_withdraw(
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        pix_key: str,
        pix_key_type: str,
        holder_name: str,
    ) -> AffiliateWithdraw:
        if amount < Decimal(str(settings.AFFILIATE_MIN_WITHDRAW)):
            raise ValueError(f"Valor mínimo para saque: R$ {settings.AFFILIATE_MIN_WITHDRAW:.2f}")

        user = await session.get(User, user_id, with_for_update=True)
        if not user:
            raise ValueError("Usuário não encontrado")
        if user.affiliate_balance < amount:
            raise ValueError("Saldo de comissão insuficiente")

        # Reserva o valor
        user.affiliate_balance -= amount

        withdraw = AffiliateWithdraw(
            user_id=user_id,
            amount=amount,
            status=WithdrawStatus.PENDING,
            payment_method="pix",
            pix_key=pix_key,
            pix_key_type=pix_key_type,
            holder_name=holder_name,
        )
        session.add(withdraw)
        await session.flush()
        return withdraw
