from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Order,
    OrderStatus,
    PaymentMethod,
    Product,
    TransactionType,
    User,
)
from services.balance import BalanceService
from services.stock import StockService
from services.affiliate import AffiliateService


class PurchaseService:
    """Fluxo completo de compra com proteção contra race condition."""

    @staticmethod
    async def buy_with_balance(
        session: AsyncSession,
        user_id: int,
        product_id: int,
        quantity: int = 1,
    ) -> Tuple[Order, List[str]]:
        """
        Compra usando saldo.
        Retorna (Order, lista de conteúdos entregues).
        """
        if quantity < 1:
            raise ValueError("Quantidade inválida")

        # Lock do produto e usuário
        product = await session.get(Product, product_id, with_for_update=True)
        if not product or product.status.value not in ("active",):
            raise ValueError("Produto indisponível")

        user = await session.get(User, user_id, with_for_update=True)
        if not user:
            raise ValueError("Usuário não encontrado")

        total_price = product.price * quantity

        if user.balance < total_price:
            raise ValueError("Saldo insuficiente")

        # Cria pedido
        order = Order(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=product.price,
            total_price=total_price,
            status=OrderStatus.PENDING,
            payment_method=PaymentMethod.BALANCE,
        )
        session.add(order)
        await session.flush()  # gera order.id

        # Reserva estoque
        items = await StockService.reserve_items(session, product_id, quantity, order.id)

        # Debita saldo
        await BalanceService.remove_balance(
            session=session,
            user_id=user_id,
            amount=total_price,
            tx_type=TransactionType.PURCHASE,
            description=f"Compra: {product.name} x{quantity}",
            order_id=order.id,
        )

        # Entrega
        delivery_contents = [item.content for item in items]
        order.delivery_content = "\n".join(delivery_contents)
        order.status = OrderStatus.DELIVERED
        order.delivered_at = datetime.now(timezone.utc)

        if product.validity_days:
            order.expires_at = datetime.now(timezone.utc) + timedelta(days=product.validity_days)

        # Comissão de afiliado
        if user.referred_by:
            await AffiliateService.pay_commission(
                session=session,
                referred_user_id=user_id,
                order_amount=total_price,
                order_id=order.id,
            )

        await session.flush()
        return order, delivery_contents

    @staticmethod
    async def check_can_buy(
        session: AsyncSession,
        user_id: int,
        product_id: int,
        quantity: int = 1,
    ) -> Tuple[bool, str, Decimal]:
        """
        Verifica se pode comprar.
        Retorna (pode, mensagem, valor_faltante)
        """
        product = await session.get(Product, product_id)
        if not product or product.status.value != "active":
            return False, "Produto indisponível", Decimal("0")

        available = await StockService.get_available_count(session, product_id)
        if available < quantity:
            return False, f"Estoque insuficiente. Disponível: {available}", Decimal("0")

        user = await session.get(User, user_id)
        if not user:
            return False, "Usuário não encontrado", Decimal("0")

        total = product.price * quantity
        if user.balance >= total:
            return True, "OK", Decimal("0")

        missing = total - user.balance
        return False, "Saldo insuficiente", missing
