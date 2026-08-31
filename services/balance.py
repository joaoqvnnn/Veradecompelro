from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Transaction, TransactionType


class BalanceService:
    """Gerencia saldo e movimentações de forma transacional."""

    @staticmethod
    async def get_balance(session: AsyncSession, user_id: int) -> Decimal:
        result = await session.execute(select(User.balance).where(User.id == user_id))
        balance = result.scalar_one_or_none()
        return balance or Decimal("0.00")

    @staticmethod
    async def add_balance(
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        tx_type: TransactionType,
        description: str = "",
        payment_id: Optional[int] = None,
        order_id: Optional[int] = None,
        gift_card_id: Optional[int] = None,
        admin_id: Optional[int] = None,
    ) -> Transaction:
        if amount <= 0:
            raise ValueError("Valor deve ser positivo para crédito")

        user = await session.get(User, user_id, with_for_update=True)
        if not user:
            raise ValueError("Usuário não encontrado")

        balance_before = user.balance
        user.balance += amount

        if tx_type == TransactionType.DEPOSIT:
            user.total_deposited += amount
        elif tx_type == TransactionType.BONUS:
            user.total_bonus += amount
        elif tx_type == TransactionType.GIFT_CARD:
            user.total_bonus += amount
        elif tx_type == TransactionType.AFFILIATE_COMMISSION:
            user.affiliate_balance += amount
            user.total_commission_earned += amount

        tx = Transaction(
            user_id=user_id,
            type=tx_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=user.balance,
            description=description,
            payment_id=payment_id,
            order_id=order_id,
            gift_card_id=gift_card_id,
            admin_id=admin_id,
        )
        session.add(tx)
        await session.flush()
        return tx

    @staticmethod
    async def remove_balance(
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        tx_type: TransactionType,
        description: str = "",
        order_id: Optional[int] = None,
        admin_id: Optional[int] = None,
    ) -> Transaction:
        if amount <= 0:
            raise ValueError("Valor deve ser positivo para débito")

        user = await session.get(User, user_id, with_for_update=True)
        if not user:
            raise ValueError("Usuário não encontrado")

        if user.balance < amount:
            raise ValueError("Saldo insuficiente")

        balance_before = user.balance
        user.balance -= amount

        if tx_type == TransactionType.PURCHASE:
            user.total_spent += amount

        tx = Transaction(
            user_id=user_id,
            type=tx_type,
            amount=-amount,  # negativo = débito
            balance_before=balance_before,
            balance_after=user.balance,
            description=description,
            order_id=order_id,
            admin_id=admin_id,
        )
        session.add(tx)
        await session.flush()
        return tx

    @staticmethod
    async def transfer_affiliate_to_main(
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
    ) -> None:
        """Move saldo de comissão para saldo principal (após saque aprovado ou conversão)."""
        user = await session.get(User, user_id, with_for_update=True)
        if not user:
            raise ValueError("Usuário não encontrado")
        if user.affiliate_balance < amount:
            raise ValueError("Saldo de afiliado insuficiente")

        user.affiliate_balance -= amount
        # O crédito no saldo principal é feito via add_balance se necessário
