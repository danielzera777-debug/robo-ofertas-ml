"""
Formatadores centrais do Robo de Ofertas ML.

Responsável por transformar preços, números, textos,
datas e dados de produtos em formatos adequados para
a interface e para divulgação.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional


# ============================================================
# NÚMEROS
# ============================================================

def to_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        if isinstance(
            value,
            str,
        ):

            value = (
                value
                .strip()
                .replace("R$", "")
                .replace(" ", "")
            )

            # Trata formatos brasileiros:
            # 1.234,56
            if (
                "," in value
                and "." in value
            ):

                value = (
                    value
                    .replace(".", "")
                    .replace(",", ".")
                )

            elif "," in value:

                value = value.replace(
                    ",",
                    ".",
                )

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def to_int(
    value: Any,
    default: int = 0,
) -> int:

    try:

        return int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# PREÇO
# ============================================================

def format_money(
    value: Any,
    symbol: str = "R$",
) -> str:
    """
    Formata valor no padrão brasileiro.
    """

    value = to_float(
        value
    )

    formatted = (
        f"{value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"{symbol} {formatted}"


def format_price(
    value: Any,
) -> str:

    return format_money(
        value
    )


def format_discount(
    value: Any,
) -> str:
    """
    Formata percentual de desconto.
    """

    value = to_float(
        value
    )

    return (
        f"{value:.0f}%"
    )


def calculate_discount_percent(
    original_price: Any,
    current_price: Any,
) -> float:
    """
    Calcula o percentual de desconto.
    """

    original = to_float(
        original_price
    )

    current = to_float(
        current_price
    )

    if original <= 0:

        return 0.0

    discount = (
        (original - current)
        / original
        * 100
    )

    return max(
        0.0,
        discount,
    )


# ============================================================
# NÚMEROS DE VENDA
# ============================================================

def format_quantity(
    value: Any,
) -> str:
    """
    Formata quantidade usando separador brasileiro.
    """

    value = to_int(
        value
    )

    return (
        f"{value:,}"
        .replace(
            ",",
            ".",
        )
    )


def format_sold_quantity(
    value: Any,
) -> str:

    quantity = to_int(
        value
    )

    if quantity <= 0:

        return "Nenhuma venda informada."

    if quantity == 1:

        return "1 venda"

    return (
        f"{format_quantity(quantity)} vendas"
    )


# ============================================================
# TEXTO
# ============================================================

def clean_text(
    value: Any,
) -> str:
    """
    Remove espaços duplicados.
    """

    if value is None:

        return ""

    value = str(
        value
    ).strip()

    return re.sub(
        r"\s+",
        " ",
        value,
    )


def truncate_text(
    value: Any,
    maximum: int = 120,
    suffix: str = "...",
) -> str:
    """
    Limita o tamanho de um texto.
    """

    text = clean_text(
        value
    )

    try:

        maximum = int(
            maximum
        )

    except (
        TypeError,
        ValueError,
    ):

        maximum = 120

    if maximum <= 0:

        return ""

    if len(text) <= maximum:

        return text

    if len(suffix) >= maximum:

        return text[
            :maximum
        ]

    return (
        text[
            :maximum - len(suffix)
        ].rstrip()
        + suffix
    )


def title_case(
    value: Any,
) -> str:

    return clean_text(
        value
    ).title()


# ============================================================
# CATEGORIAS
# ============================================================

CATEGORY_LABELS = {

    "suplementos":
        "Suplementos",

    "fitness_feminino":
        "Fitness Feminino",

    "fitness_masculino":
        "Fitness Masculino",

    "celulares":
        "Celulares",

    "roupas":
        "Roupas",

    "relogios":
        "Relógios",

    "eletronicos":
        "Eletrônicos",

    "informatica":
        "Informática",

    "beleza":
        "Beleza",

    "esportes":
        "Esportes",

}


def format_category(
    value: Any,
) -> str:

    category = clean_text(
        value
    ).lower()

    if not category:

        return "Outros"

    return CATEGORY_LABELS.get(
        category,
        title_case(
            category.replace(
                "_",
                " ",
            )
        ),
    )


# ============================================================
# STATUS
# ============================================================

STATUS_LABELS = {

    "online":
        "Online",

    "offline":
        "Offline",

    "ok":
        "OK",

    "erro":
        "Erro",

    "error":
        "Erro",

    "pendente":
        "Pendente",

    "pending":
        "Pendente",

    "processando":
        "Processando",

    "processing":
        "Processando",

    "concluido":
        "Concluído",

    "completed":
        "Concluído",

}


def format_status(
    value: Any,
) -> str:

    status = clean_text(
        value
    ).lower()

    if not status:

        return "Desconhecido"

    return STATUS_LABELS.get(
        status,
        title_case(
            status.replace(
                "_",
                " ",
            )
        ),
    )


# ============================================================
# DATAS
# ============================================================

def format_datetime(
    value: Any,
    output_format: str = "%d/%m/%Y %H:%M",
) -> str:
    """
    Formata datetime ou string ISO.
    """

    if value is None:

        return ""

    if isinstance(
        value,
        datetime,
    ):

        return value.strftime(
            output_format
        )

    value = str(
        value
    ).strip()

    if not value:

        return ""

    try:

        normalized = value.replace(
            "Z",
            "+00:00",
        )

        parsed = datetime.fromisoformat(
            normalized
        )

        return parsed.strftime(
            output_format
        )

    except (
        TypeError,
        ValueError,
    ):

        return value


# ============================================================
# PRODUTO
# ============================================================

def product_title(
    product: dict,
    maximum: int = 100,
) -> str:

    if not isinstance(
        product,
        dict,
    ):

        return "Produto"

    title = (
        product.get("titulo")
        or product.get("title")
        or product.get("name")
        or "Produto"
    )

    return truncate_text(
        title,
        maximum,
    )


def product_price(
    product: dict,
) -> str:

    if not isinstance(
        product,
        dict,
    ):

        return format_money(
            0
        )

    price = (
        product.get("preco")
        if "preco" in product
        else product.get("price")
    )

    return format_money(
        price
    )


def product_category(
    product: dict,
) -> str:

    if not isinstance(
        product,
        dict,
    ):

        return "Outros"

    return format_category(
        product.get(
            "categoria"
        )
    )


# ============================================================
# OFERTA
# ============================================================

def format_offer(
    product: dict,
) -> dict:
    """
    Cria uma representação formatada da oferta.
    """

    if not isinstance(
        product,
        dict,
    ):

        return {}

    price = (
        product.get("preco")
        if "preco" in product
        else product.get("price")
    )

    original_price = (
        product.get(
            "preco_original"
        )
        or product.get(
            "original_price"
        )
        or price
    )

    discount = calculate_discount_percent(
        original_price,
        price,
    )

    return {

        "titulo":
            product_title(
                product
            ),

        "preco":
            to_float(
                price
            ),

        "preco_formatado":
            format_money(
                price
            ),

        "preco_original":
            to_float(
                original_price
            ),

        "preco_original_formatado":
            format_money(
                original_price
            ),

        "desconto":
            discount,

        "desconto_formatado":
            format_discount(
                discount
            ),

        "categoria":
            product_category(
                product
            ),

        "vendidos":
            to_int(
                product.get(
                    "vendidos",
                    0,
                )
            ),

        "vendidos_formatado":
            format_sold_quantity(
                product.get(
                    "vendidos",
                    0,
                )
            ),

        "link":
            clean_text(
                product.get(
                    "link"
                )
                or product.get(
                    "url"
                )
            ),

    }


# ============================================================
# WHATSAPP
# ============================================================

def whatsapp_price(
    value: Any,
) -> str:

    return format_money(
        value
    )


def whatsapp_offer_text(
    product: dict,
) -> str:
    """
    Gera texto simples para divulgação no WhatsApp.
    """

    offer = format_offer(
        product
    )

    title = offer.get(
        "titulo",
        "Oferta",
    )

    price = offer.get(
        "preco_formatado",
        "R$ 0,00",
    )

    category = offer.get(
        "categoria",
        "Outros",
    )

    link = offer.get(
        "link",
        "",
    )

    discount = offer.get(
        "desconto",
        0,
    )

    lines = [
        "🔥 OFERTA ESPECIAL 🔥",
        "",
        f"🏷️ {title}",
        "",
        f"📂 {category}",
        f"💰 {price}",
    ]

    if discount > 0:

        lines.append(
            f"🔥 {format_discount(discount)} OFF"
        )

    if link:

        lines.extend(
            [
                "",
                "🛒 COMPRAR AGORA 👇",
                link,
            ]
        )

    lines.extend(
        [
            "",
            "⚠️ Preço e disponibilidade "
            "podem mudar no Mercado Livre.",
        ]
    )

    return "\n".join(
        lines
    )


# ============================================================
# EXPORTAÇÃO
# ============================================================

__all__ = [
    "to_float",
    "to_int",
    "format_money",
    "format_price",
    "format_discount",
    "calculate_discount_percent",
    "format_quantity",
    "format_sold_quantity",
    "clean_text",
    "truncate_text",
    "title_case",
    "format_category",
    "format_status",
    "format_datetime",
    "product_title",
    "product_price",
    "product_category",
    "format_offer",
    "whatsapp_price",
    "whatsapp_offer_text",
]
