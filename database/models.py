from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ==================== ENUMS ====================

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    BANNED = "banned"


class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    OUT_OF_STOCK = "out_of_stock"
    DELETED = "deleted"


class DeliveryType(str, enum.Enum):
    LOGIN_PASSWORD = "login_password"
    CODE = "code"
    LINK = "link"
    TEXT = "text"
    FILE = "file"
    CUSTOM = "custom"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    BALANCE = "balance"
    PIX = "pix"
    GIFT_CARD = "gift_card"
    ADMIN = "admin"
    BONUS = "bonus"
    AFFILIATE = "affiliate"


class TransactionType(str, enum.Enum):
    DEPOSIT = "deposit"
    PURCHASE = "purchase"
    REFUND = "refund"
    BONUS = "bonus"
    GIFT_CARD = "gift_card"
    AFFILIATE_COMMISSION = "affiliate_commission"
    AFFILIATE_WITHDRAW = "affiliate_withdraw"
    ADMIN_ADD = "admin_add"
    ADMIN_REMOVE = "admin_remove"
    ADJUSTMENT = "adjustment"


class WithdrawStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class GiftCardStatus(str, enum.Enum):
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    DISABLED = "disabled"


class AdminRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    STOCK = "stock"
    SUPPORT = "support"
    FINANCE = "finance"
    ANALYST = "analyst"


# ==================== USERS ====================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram User ID
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Contato
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Financeiro
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_deposited: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Afiliados
    affiliate_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    referred_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    total_referrals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_commission_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Status
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_role: Mapped[Optional[AdminRole]] = mapped_column(Enum(AdminRole), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    referrer: Mapped[Optional["User"]] = relationship("User", remote_side=[id], backref="referrals")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user", foreign_keys="Order.user_id")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="user")
    alerts: Mapped[List["ProductAlert"]] = relationship("ProductAlert", back_populates="user")
    gift_cards_redeemed: Mapped[List["GiftCard"]] = relationship("GiftCard", back_populates="redeemed_by_user")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} balance={self.balance}>"


# ==================== CATEGORIES ====================

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), default="📦", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name}>"


# ==================== PRODUCTS ====================

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    emoji: Mapped[str] = mapped_column(String(10), default="🔥", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    image_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Estoque (calculado dinamicamente, mas mantemos cache)
    stock_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sold_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Garantia e validade
    warranty_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    validity_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # None = sem validade

    delivery_type: Mapped[DeliveryType] = mapped_column(
        Enum(DeliveryType), default=DeliveryType.LOGIN_PASSWORD, nullable=False
    )
    delivery_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[ProductStatus] = mapped_column(Enum(ProductStatus), default=ProductStatus.ACTIVE, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Estatísticas extras
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products")
    stock_items: Mapped[List["StockItem"]] = relationship("StockItem", back_populates="product")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="product")
    alerts: Mapped[List["ProductAlert"]] = relationship("ProductAlert", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} price={self.price} stock={self.stock_count}>"


# ==================== STOCK ITEMS (unidades individuais) ====================

class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    # Dados da entrega (flexível)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # login:senha ou código ou link etc.
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    is_sold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product: Mapped["Product"] = relationship("Product", back_populates="stock_items")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="stock_items")

    __table_args__ = (
        Index("ix_stock_items_available", "product_id", "is_sold"),
    )

    def __repr__(self) -> str:
        return f"<StockItem id={self.id} product_id={self.product_id} sold={self.is_sold}>"


# ==================== ORDERS ====================

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), unique=True, nullable=False)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)

    # Entrega
    delivery_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Conteúdo consolidado
    delivery_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delivery_whatsapp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Validade
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Referência de pagamento
    payment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("payments.id"), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="orders", foreign_keys=[user_id])
    product: Mapped["Product"] = relationship("Product", back_populates="orders")
    stock_items: Mapped[List["StockItem"]] = relationship("StockItem", back_populates="order")
    payment: Mapped[Optional["Payment"]] = relationship("Payment", back_populates="orders")

    def __repr__(self) -> str:
        return f"<Order id={self.id} uuid={self.uuid} user={self.user_id} status={self.status}>"


# ==================== PAYMENTS (PIX / cobranças) ====================

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), unique=True, nullable=False)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    bonus_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_credited: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.PIX, nullable=False)

    # Mercado Pago
    gateway: Mapped[str] = mapped_column(String(50), default="mercadopago", nullable=False)
    gateway_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # ID da cobrança no MP
    pix_copy_paste: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qr_code_base64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Controle
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Idempotência
    external_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)

    # Metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="payments")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="payment")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="payment")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} uuid={self.uuid} amount={self.amount} status={self.status}>"


# ==================== TRANSACTIONS (movimentações de saldo) ====================

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), unique=True, nullable=False)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # positivo = crédito, negativo = débito
    balance_before: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Referências opcionais
    payment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("payments.id"), nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)
    gift_card_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("gift_cards.id"), nullable=True)
    admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # quem fez a ação admin

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="transactions")
    payment: Mapped[Optional["Payment"]] = relationship("Payment", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} user={self.user_id} type={self.type} amount={self.amount}>"


# ==================== GIFT CARDS ====================

class GiftCard(Base):
    __tablename__ = "gift_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[GiftCardStatus] = mapped_column(Enum(GiftCardStatus), default=GiftCardStatus.ACTIVE, nullable=False)

    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    redeemed_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    redeemed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    redeemed_by_user: Mapped[Optional["User"]] = relationship("User", back_populates="gift_cards_redeemed")

    def __repr__(self) -> str:
        return f"<GiftCard code={self.code} value={self.value} status={self.status}>"


# ==================== AFILIADOS - SAQUES ====================

class AffiliateWithdraw(Base):
    __tablename__ = "affiliate_withdraws"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), unique=True, nullable=False)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[WithdrawStatus] = mapped_column(Enum(WithdrawStatus), default=WithdrawStatus.PENDING, nullable=False)

    # Dados de pagamento
    payment_method: Mapped[str] = mapped_column(String(50), default="pix", nullable=False)
    pix_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pix_key_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # cpf, email, phone, random
    holder_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Processamento
    processed_by_admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<AffiliateWithdraw id={self.id} user={self.user_id} amount={self.amount} status={self.status}>"


# ==================== ALERTAS DE ESTOQUE ====================

class ProductAlert(Base):
    __tablename__ = "product_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="alerts")
    product: Mapped["Product"] = relationship("Product", back_populates="alerts")

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_product_alert"),
    )

    def __repr__(self) -> str:
        return f"<ProductAlert user={self.user_id} product={self.product_id}>"


# ==================== LOGS ADMINISTRATIVOS ====================

class AdminLog(Base):
    __tablename__ = "admin_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # user, product, order, etc.
    target_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<AdminLog id={self.id} admin={self.admin_id} action={self.action}>"


# ==================== TEMPLATES DE MENSAGENS (editáveis pelo admin) ====================

class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # ex: start, product_page, insufficient_balance
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parse_mode: Mapped[str] = mapped_column(String(20), default="HTML", nullable=False)  # HTML ou Markdown
    media_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    media_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # photo, video, animation
    buttons: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # estrutura de botões
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<MessageTemplate key={self.key}>"


# ==================== CONFIGURAÇÕES DINÂMICAS ====================

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), default="string", nullable=False)  # string, int, float, bool, json
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SystemSetting key={self.key}>"
