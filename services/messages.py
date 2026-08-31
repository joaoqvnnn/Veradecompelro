from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MessageTemplate


# =========================================================
# TEMPLATES PADRÃO (usados quando não existe no banco)
# =========================================================

DEFAULT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "start": {
        "title": "Mensagem de Boas-vindas",
        "content": (
            "🎬 <b>Bem-vindo à {store_name}!</b> ✨\n\n"
            "A sua central de streamings com entrega <b>100% automática</b>.\n"
            "Pagou, recebeu. Sem filas, sem precisar falar com atendente, 24 horas por dia! ⚡️\n\n"
            "🛡 <b>Segurança e Suporte:</b>\n"
            "Mais de 12.000 clientes já passaram por aqui.\n\n"
            "💠 <b>Seus Dados:</b>\n"
            "├ 👤 ID: <code>{user_id}</code>\n"
            "└ 💰 Saldo Atual: <b>R$ {balance}</b>\n\n"
            "👇 <b>COMO COMEÇAR:</b>\n"
            "Clique em <b>\"🛍 Comprar Produtos\"</b> para acessar nosso catálogo."
        ),
        "parse_mode": "HTML",
        "buttons": [
            [{"text": "🛍 Comprar Produtos", "action": "catalog"}],
            [
                {"text": "💰 Recarregar Saldo", "action": "recharge"},
                {"text": "👤 Meu Perfil", "action": "profile"},
            ],
            [
                {"text": "🤝 Afiliados", "action": "affiliates"},
                {"text": "🏆 Ranking", "action": "ranking"},
            ],
            [
                {"text": "🎁 Gift Card", "action": "gift_card"},
                {"text": "🔎 Pesquisar", "action": "search"},
            ],
            [
                {"text": "📢 Alertas", "action": "alerts"},
                {"text": "🎧 Atendimento", "action": "support"},
            ],
            [{"text": "ℹ️ Sobre o Bot", "action": "about"}],
        ],
    },
    "catalog": {
        "title": "Catálogo",
        "content": (
            "📱 <b>{store_name} | Catálogo de Serviços</b>\n\n"
            "💰 Saldo da Carteira: <b>R$ {balance}</b>\n\n"
            "⬇️ Selecione uma categoria abaixo:"
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "product": {
        "title": "Página do Produto",
        "content": (
            "🔥 <b>OPORTUNIDADE EXCLUSIVA</b> 🔥\n\n"
            "{emoji} <b>{product_name}</b>\n"
            "{status_text}\n\n"
            "├ 💵 Preço: <b>R$ {price}</b>\n"
            "├ 💰 Seu Saldo: <b>R$ {balance}</b>\n"
            "└ 📦 Estoque: <b>{stock}</b>\n\n"
            "📝 <b>Descrição:</b>\n"
            "{description}\n\n"
            "📊 <b>Estatísticas:</b>\n"
            "⚡️ Já foram vendidas <b>{sold}</b> unidades!\n"
            "👀 Visualizações: <b>{views}</b>\n\n"
            "🛡 Garantia: <b>{warranty} dias</b>\n"
            "✅ Compra segura.\n"
            "Ao adquirir, concorda com /termos"
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "insufficient_balance": {
        "title": "Saldo Insuficiente",
        "content": (
            "❌ <b>Saldo insuficiente!</b>\n\n"
            "💰 Seu saldo: <b>R$ {balance}</b>\n"
            "💵 Valor do produto: <b>R$ {product_price}</b>\n"
            "📉 Faltam: <b>R$ {missing}</b>\n\n"
            "💡 Deseja gerar um PIX de <b>R$ {missing}</b> para completar a compra?"
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "pix_created": {
        "title": "PIX Gerado",
        "content": (
            "💰 <b>Comprar Saldo com Pix Automático</b>\n\n"
            "⏱️ Expira em: <b>{expiration} minutos</b>\n"
            "💵 Valor: <b>R$ {amount}</b>\n"
            "🎁 Bônus: <b>R$ {bonus}</b>\n"
            "✨ ID da Recarga: <code>{payment_id}</code>\n\n"
            "💎 <b>Pix Copia e Cola:</b>\n"
            "<code>{pix_code}</code>\n\n"
            "📊 <b>Dados:</b>\n"
            "💰 Saldo Atual: <b>R$ {balance}</b>\n"
            "💸 Saldo após pagamento: <b>R$ {balance_after}</b>\n\n"
            "⚠️ O saldo será creditado <b>automaticamente</b> após a confirmação."
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "payment_approved": {
        "title": "Pagamento Aprovado",
        "content": (
            "✅ <b>PAGAMENTO APROVADO!</b>\n\n"
            "💰 Valor: <b>R$ {amount}</b>\n"
            "🎁 Bônus: <b>R$ {bonus}</b>\n"
            "💳 Total creditado: <b>R$ {total}</b>\n\n"
            "Seu saldo já está disponível."
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "payment_expired": {
        "title": "PIX Expirado",
        "content": (
            "⌛️ <b>PAGAMENTO PIX EXPIRADO</b>\n\n"
            "⚠️ O tempo limite para realizar este pagamento foi excedido.\n\n"
            "🆔 Referência: <code>{payment_id}</code>\n"
            "💸 Valor solicitado: <b>R$ {amount}</b>"
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "purchase_success": {
        "title": "Compra Aprovada",
        "content": (
            "✅ <b>COMPRA APROVADA!</b>\n\n"
            "🎬 Produto: <b>{product_name}</b>\n"
            "💰 Valor: <b>R$ {price}</b>\n"
            "📅 Data: {date}\n"
            "💳 Pagamento: Saldo\n"
            "📦 Sua entrega está pronta:\n\n"
            "<code>{delivery}</code>\n\n"
            "🛡 Guarde esses dados com segurança!"
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "profile": {
        "title": "Meu Perfil",
        "content": (
            "👤 <b>Meu Perfil</b>\n\n"
            "🆔 ID: <code>{user_id}</code>\n"
            "💰 Saldo: <b>R$ {balance}</b>\n"
            "📲 WhatsApp: {whatsapp}\n"
            "📧 E-mail: {email}\n\n"
            "🛒 Compras: <b>{orders}</b>\n"
            "💰 Total gasto: <b>R$ {total_spent}</b>\n"
            "💠 Depositado: <b>R$ {total_deposited}</b>\n"
            "🎁 Bônus: <b>R$ {total_bonus}</b>"
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "affiliates": {
        "title": "Programa de Afiliados",
        "content": (
            "💰 <b>PROGRAMA DE AFILIADOS</b>\n\n"
            "⚙️ Status: <b>{status}</b>\n"
            "🧲 Comissão: <b>{commission}%</b>\n"
            "👥 Indicações: <b>{referrals}</b>\n"
            "🪙 Total ganho: <b>R$ {total_earned}</b>\n"
            "💰 Saque mínimo: <b>R$ {min_withdraw}</b>\n"
            "🔥 Saldo de comissões: <b>R$ {affiliate_balance}</b>\n\n"
            "🔗 <b>Seu link:</b>\n"
            "<code>{link}</code>"
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "gift_card": {
        "title": "Gift Card",
        "content": (
            "🎁 <b>RESGATAR GIFT CARD</b>\n\n"
            "Digite o código do seu Gift Card:\n"
            "Exemplo: <code>ABC123XYZ456</code>"
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "about": {
        "title": "Sobre o Bot",
        "content": (
            "ℹ️ <b>Sobre o Bot</b>\n\n"
            "🏪 Nome: <b>{store_name}</b>\n"
            "🤖 Bot: @{bot_username}\n"
            "🛡 Entrega 100% automática\n"
            "💳 Pagamento via PIX instantâneo\n\n"
            "Use /termos para ver os termos de uso."
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "maintenance": {
        "title": "Modo Manutenção",
        "content": (
            "🔧 <b>MANUTENÇÃO</b>\n\n"
            "Nosso sistema está temporariamente em manutenção.\n"
            "Voltaremos em breve."
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
    "terms": {
        "title": "Termos de Uso",
        "content": (
            "📜 <b>Termos de Uso</b>\n\n"
            "1. Ao comprar, você concorda com as regras da loja.\n"
            "2. Produtos digitais não possuem reembolso após a entrega.\n"
            "3. Garantia conforme descrito em cada produto.\n"
            "4. É proibido revender ou compartilhar dados de acesso indevidamente.\n"
            "5. Suporte disponível pelo botão de Atendimento.\n\n"
            "Em caso de dúvidas, fale com o suporte."
        ),
        "parse_mode": "HTML",
        "buttons": [],
    },
}


class MessageService:
    """Carrega e renderiza templates de mensagem (banco ou padrão)."""

    @staticmethod
    async def get_template(session: AsyncSession, key: str) -> Dict[str, Any]:
        result = await session.execute(
            select(MessageTemplate).where(
                MessageTemplate.key == key,
                MessageTemplate.is_active.is_(True),
            )
        )
        tpl = result.scalar_one_or_none()

        if tpl:
            return {
                "key": tpl.key,
                "title": tpl.title,
                "content": tpl.content,
                "parse_mode": tpl.parse_mode or "HTML",
                "media_file_id": tpl.media_file_id,
                "media_type": tpl.media_type,
                "buttons": tpl.buttons or [],
            }

        # Fallback para o padrão
        default = DEFAULT_TEMPLATES.get(key)
        if default:
            return {
                "key": key,
                "title": default.get("title"),
                "content": default["content"],
                "parse_mode": default.get("parse_mode", "HTML"),
                "media_file_id": None,
                "media_type": None,
                "buttons": default.get("buttons", []),
            }

        return {
            "key": key,
            "title": key,
            "content": f"Template '{key}' não configurado.",
            "parse_mode": "HTML",
            "media_file_id": None,
            "media_type": None,
            "buttons": [],
        }

    @staticmethod
    def render(content: str, **kwargs) -> str:
        """Substitui {variaveis} no texto."""
        try:
            return content.format(**kwargs)
        except KeyError:
            # Se faltar alguma variável, devolve o texto original
            return content

    @staticmethod
    async def get_rendered(
        session: AsyncSession,
        key: str,
        **kwargs,
    ) -> Dict[str, Any]:
        tpl = await MessageService.get_template(session, key)
        tpl["content"] = MessageService.render(tpl["content"], **kwargs)
        return tpl

    @staticmethod
    async def list_templates(session: AsyncSession) -> List[Dict[str, Any]]:
        """Lista todos os templates (banco + padrões)."""
        result = await session.execute(select(MessageTemplate))
        db_templates = {t.key: t for t in result.scalars().all()}

        items = []
        all_keys = set(DEFAULT_TEMPLATES.keys()) | set(db_templates.keys())

        for key in sorted(all_keys):
            if key in db_templates:
                t = db_templates[key]
                items.append({
                    "key": key,
                    "title": t.title or key,
                    "source": "database",
                    "is_active": t.is_active,
                })
            else:
                items.append({
                    "key": key,
                    "title": DEFAULT_TEMPLATES[key].get("title", key),
                    "source": "default",
                    "is_active": True,
                })
        return items

    @staticmethod
    async def save_template(
        session: AsyncSession,
        key: str,
        content: str,
        title: Optional[str] = None,
        parse_mode: str = "HTML",
        buttons: Optional[list] = None,
        admin_id: Optional[int] = None,
    ) -> MessageTemplate:
        result = await session.execute(
            select(MessageTemplate).where(MessageTemplate.key == key)
        )
        tpl = result.scalar_one_or_none()

        if tpl:
            tpl.content = content
            if title is not None:
                tpl.title = title
            tpl.parse_mode = parse_mode
            if buttons is not None:
                tpl.buttons = buttons
            tpl.updated_by = admin_id
        else:
            tpl = MessageTemplate(
                key=key,
                title=title or key,
                content=content,
                parse_mode=parse_mode,
                buttons=buttons,
                updated_by=admin_id,
            )
            session.add(tpl)

        await session.flush()
        return tpl

    @staticmethod
    async def reset_template(session: AsyncSession, key: str) -> bool:
        """Remove do banco para voltar ao padrão."""
        result = await session.execute(
            select(MessageTemplate).where(MessageTemplate.key == key)
        )
        tpl = result.scalar_one_or_none()
        if tpl:
            await session.delete(tpl)
            await session.flush()
            return True
        return False
