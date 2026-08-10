"""
Validadores centrais do Robo de Ofertas ML.
"""

import re
from typing import Any, Iterable, Optional
from urllib.parse import urlparse


# ============================================================
# VALIDAÇÃO DE TEXTO
# ============================================================

def is_non_empty_string(
    value: Any,
) -> bool:
    """
    Verifica se o valor é uma string não vazia.
    """

    return (
        isinstance(value, str)
        and bool(value.strip())
    )


def clean_text(
    value: Any,
    max_length: Optional[int] = None,
) -> str:
    """
    Limpa espaços desnecessários e limita o tamanho
    do texto quando solicitado.
    """

    if value is None:

        return ""

    value = str(
        value
    ).strip()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    if max_length is not None:

        try:

            max_length = int(
                max_length
            )

            if max_length > 0:

                value = value[
                    :max_length
                ]

        except (
            TypeError,
            ValueError,
        ):

            pass

    return value


# ============================================================
# NÚMEROS
# ============================================================

def is_number(
    value: Any,
) -> bool:
    """
    Verifica se o valor pode ser convertido para número.
    """

    if value is None:

        return False

    try:

        float(value)

        return True

    except (
        TypeError,
        ValueError,
    ):

        return False


def number(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Converte um valor para float com valor padrão.
    """

    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def positive_number(
    value: Any,
) -> bool:
    """
    Verifica se o número é maior que zero.
    """

    if not is_number(
        value
    ):

        return False

    return number(
        value
    ) > 0


def non_negative_number(
    value: Any,
) -> bool:
    """
    Verifica se o número é maior ou igual a zero.
    """

    if not is_number(
        value
    ):

        return False

    return number(
        value
    ) >= 0


# ============================================================
# INTEIROS
# ============================================================

def is_integer(
    value: Any,
) -> bool:
    """
    Verifica se o valor pode ser interpretado como inteiro.
    """

    if isinstance(
        value,
        bool,
    ):

        return False

    try:

        int(value)

        return True

    except (
        TypeError,
        ValueError,
    ):

        return False


def integer(
    value: Any,
    default: int = 0,
) -> int:
    """
    Converte um valor para inteiro.
    """

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# PREÇO
# ============================================================

def validate_price(
    value: Any,
    minimum: float = 0.01,
    maximum: float = 9999999.99,
) -> bool:
    """
    Valida um preço.
    """

    if not is_number(
        value
    ):

        return False

    price = number(
        value
    )

    return (
        minimum
        <= price
        <= maximum
    )


# ============================================================
# MARGEM
# ============================================================

def validate_margin(
    value: Any,
    minimum: float = 0,
    maximum: float = 1000,
) -> bool:
    """
    Valida uma margem percentual.
    """

    if not is_number(
        value
    ):

        return False

    margin = number(
        value
    )

    return (
        minimum
        <= margin
        <= maximum
    )


# ============================================================
# LIMITE
# ============================================================

def validate_limit(
    value: Any,
    minimum: int = 1,
    maximum: int = 100,
) -> bool:
    """
    Valida limite de resultados.
    """

    if not is_integer(
        value
    ):

        return False

    value = integer(
        value
    )

    return (
        minimum
        <= value
        <= maximum
    )


# ============================================================
# URL
# ============================================================

def is_valid_url(
    value: Any,
    allowed_schemes: Iterable[str] = (
        "http",
        "https",
    ),
) -> bool:
    """
    Verifica se uma URL possui estrutura válida.
    """

    if not is_non_empty_string(
        value
    ):

        return False

    try:

        parsed = urlparse(
            value.strip()
        )

    except Exception:

        return False

    schemes = {
        str(item).lower()
        for item in allowed_schemes
    }

    return (
        parsed.scheme.lower()
        in schemes
        and
        bool(parsed.netloc)
    )


# ============================================================
# ID
# ============================================================

def is_valid_id(
    value: Any,
) -> bool:
    """
    Valida IDs simples utilizados pelo sistema.
    """

    if value is None:

        return False

    value = str(
        value
    ).strip()

    if not value:

        return False

    return bool(
        re.fullmatch(
            r"[A-Za-z0-9_-]+",
            value,
        )
    )


# ============================================================
# CATEGORIA
# ============================================================

def is_valid_category(
    value: Any,
    allowed_categories: Optional[
        Iterable[str]
    ] = None,
) -> bool:
    """
    Valida uma categoria.
    """

    if not is_non_empty_string(
        value
    ):

        return False

    category = value.strip().lower()

    if allowed_categories is None:

        return True

    allowed = {
        str(item).strip().lower()
        for item in allowed_categories
    }

    return category in allowed


# ============================================================
# NÚCLEO
# ============================================================

def validate_product(
    product: Any,
) -> bool:
    """
    Valida a estrutura mínima de um produto.
    """

    if not isinstance(
        product,
        dict,
    ):

        return False

    title = (
        product.get("titulo")
        or product.get("title")
        or product.get("name")
    )

    price = (
        product.get("preco")
        if "preco" in product
        else product.get("price")
    )

    link = (
        product.get("link")
        if "link" in product
        else product.get("url")
    )

    if not is_non_empty_string(
        title
    ):

        return False

    if not validate_price(
        price
    ):

        return False

    if not is_valid_url(
        link
    ):

        return False

    return True


# ============================================================
# OFERTA
# ============================================================

def validate_offer(
    offer: Any,
) -> bool:
    """
    Valida uma oferta preparada pelo sistema.
    """

    if not isinstance(
        offer,
        dict,
    ):

        return False

    if not validate_product(
        offer
    ):

        return False

    category = offer.get(
        "categoria"
    )

    if category is not None:

        if not is_non_empty_string(
            category
        ):

            return False

    return True


# ============================================================
# BUSCA
# ============================================================

def validate_search_term(
    value: Any,
    minimum_length: int = 2,
    maximum_length: int = 100,
) -> bool:
    """
    Valida um termo de pesquisa.
    """

    if not is_non_empty_string(
        value
    ):

        return False

    value = clean_text(
        value
    )

    length = len(
        value
    )

    return (
        minimum_length
        <= length
        <= maximum_length
    )


# ============================================================
# E-MAIL
# ============================================================

def is_valid_email(
    value: Any,
) -> bool:
    """
    Valida um endereço de e-mail.
    """

    if not is_non_empty_string(
        value
    ):

        return False

    pattern = (
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )

    return bool(
        re.fullmatch(
            pattern,
            value.strip(),
        )
    )


# ============================================================
# TELEFONE
# ============================================================

def is_valid_phone(
    value: Any,
) -> bool:
    """
    Validação básica de telefone brasileiro.
    """

    if value is None:

        return False

    digits = re.sub(
        r"\D",
        "",
        str(value),
    )

    return len(
        digits
    ) in (
        10,
        11,
    )


# ============================================================
# BOOLEAN
# ============================================================

def to_bool(
    value: Any,
    default: bool = False,
) -> bool:
    """
    Converte valores comuns para booleano.
    """

    if isinstance(
        value,
        bool,
    ):

        return value

    if value is None:

        return default

    if isinstance(
        value,
        (int, float),
    ):

        return value != 0

    normalized = str(
        value
    ).strip().lower()

    if normalized in (
        "true",
        "1",
        "yes",
        "sim",
        "on",
        "ativo",
        "enabled",
    ):

        return True

    if normalized in (
        "false",
        "0",
        "no",
        "nao",
        "não",
        "off",
        "inativo",
        "disabled",
    ):

        return False

    return default


# ============================================================
# SANITIZAÇÃO DE BUSCA
# ============================================================

def sanitize_search_term(
    value: Any,
) -> str:
    """
    Remove caracteres desnecessários de um termo de busca.
    """

    value = clean_text(
        value,
        max_length=100,
    )

    value = re.sub(
        r"[<>\"'`]",
        "",
        value,
    )

    return value.strip()
