from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_keyboard_from_buttons(
    buttons: List[List[Dict[str, Any]]],
    extra_rows: Optional[List[List[InlineKeyboardButton]]] = None,
) -> InlineKeyboardMarkup:
    """
    Constrói teclado a partir da estrutura salva no banco.

    Formato esperado:
    [
        [{"text": "🛍 Comprar", "action": "catalog"}],
        [{"text": "💰 Saldo", "action": "recharge"}, {"text": "👤 Perfil", "action": "profile"}]
    ]
    """
    builder = InlineKeyboardBuilder()

    for row in buttons or []:
        row_buttons = []
        for btn in row:
            text = btn.get("text", "Botão")
            action = btn.get("action", "noop")
            url = btn.get("url")

            if url:
                row_buttons.append(InlineKeyboardButton(text=text, url=url))
            else:
                row_buttons.append(
                    InlineKeyboardButton(text=text, callback_data=action)
                )
        if row_buttons:
            builder.row(*row_buttons)

    if extra_rows:
        for row in extra_rows:
            builder.row(*row)

    return builder.as_markup()
