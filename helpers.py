"""
Funções auxiliares gerais do Robo de Ofertas ML.

Este módulo concentra operações pequenas e reutilizáveis
para evitar duplicação de código entre rotas e serviços.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Iterable, Optional
from urllib.parse import urlparse


# ============================================================
# TEXTO
# ============================================================

def clean_text(
    value: Any,
    maximum: Optional[int] = None,
) -> str:
    """
    Limpa espaços e, opcionalmente, limita o tamanho.
    """

    if value is None:

        return ""

    text = str(
        value
    ).strip()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    if maximum is not None:

        try:

            maximum = int(
                maximum
            )

        except (
            TypeError,
            ValueError,
        ):

            maximum = 0

        if maximum > 0:

            text = text[
                :maximum
            ]

    return text


def normalize_text(
    value: Any,
) -> str:
    """
    Normaliza texto para comparações e classificações.
    """

    text = clean_text(
        value
    ).lower()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(
            char
        )
    )

    return text


def slugify(
    value: Any,
) -> str:
    """
    Converte texto em slug.
    """

    text = normalize_text(
        value
    )

    text = re.sub(
        r"[^a-z0-9]+",
        "-",
        text,
    )

    return text.strip(
        "-"
    )


def truncate(
    value: Any,
    length: int = 100,
    suffix: str = "...",
) -> str:
    """
    Limita um texto sem cortar além do necessário.
    """

    text = clean_text(
        value
    )

    try:

        length = int(
            length
        )

    except (
        TypeError,
        ValueError,
    ):

        length = 100

    if length <= 0:

        return ""

    if len(text) <= length:

        return text

    if len(suffix) >= length:

        return text[
            :length
        ]

    return (
        text[
            :length - len(suffix)
        ].rstrip()
        + suffix
    )


# ============================================================
# NÚMEROS
# ============================================================

def to_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Converte valores brasileiros ou numéricos para float.
    """

    try:

        if isinstance(
            value,
            str,
        ):

            value = (
                value
                .strip()
                .replace(
                    "R$",
                    "",
                )
                .replace(
                    " ",
                    "",
                )
            )

            if (
                "," in value
                and "." in value
            ):

                value = (
                    value
                    .replace(
                        ".",
                        "",
                    )
                    .replace(
                        ",",
                        ".",
                    )
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
    """
    Converte um valor para inteiro.
    """

    try:

        return int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


def clamp(
    value: Any,
    minimum: float,
    maximum: float,
) -> float:
    """
    Mantém um número dentro de um intervalo.
    """

    value = to_float(
        value
    )

    minimum = to_float(
        minimum
    )

    maximum = to_float(
        maximum
    )

    if minimum > maximum:

        minimum, maximum = (
            maximum,
            minimum,
        )

    return max(
        minimum,
        min(
            value,
            maximum,
        ),
    )


# ============================================================
# PREÇO
# ============================================================

def format_money(
    value: Any,
) -> str:
    """
    Formata moeda brasileira.
    """

    value = to_float(
        value
    )

    return (
        f"R$ {value:,.2f}"
        .replace(
            ",",
            "X",
        )
        .replace(
            ".",
            ",",
        )
        .replace(
            "X",
            ".",
        )
    )


def calculate_margin(
    cost: Any,
    sale_price: Any,
) -> float:
    """
    Calcula a margem percentual sobre o custo.
    """

    cost = to_float(
        cost
    )

    sale_price = to_float(
        sale_price
    )

    if cost <= 0:

        return 0.0

    return (
        (sale_price - cost)
        / cost
        * 100
    )


def calculate_profit(
    cost: Any,
    sale_price: Any,
) -> float:
    """
    Calcula lucro bruto.
    """

    return (
        to_float(
            sale_price
        )
        -
        to_float(
            cost
        )
    )


# ============================================================
# URL
# ============================================================

def is_url(
    value: Any,
) -> bool:
    """
    Verifica se existe uma URL HTTP/HTTPS válida.
    """

    if not value:

        return False

    try:

        parsed = urlparse(
            str(value).strip()
        )

        return (
            parsed.scheme.lower()
            in (
                "http",
                "https",
            )
            and bool(
                parsed.netloc
            )
        )

    except Exception:

        return False


def get_domain(
    value: Any,
) -> str:
    """
    Extrai o domínio de uma URL.
    """

    if not is_url(
        value
    ):

        return ""

    try:

        return urlparse(
            str(value)
        ).netloc.lower()

    except Exception:

        return ""


# ============================================================
# HASH
# ============================================================

def make_hash(
    value: Any,
    algorithm: str = "sha256",
) -> str:
    """
    Gera hash hexadecimal de uma informação.
    """

    text = str(
        value
    ).encode(
        "utf-8"
    )

    try:

        hasher = hashlib.new(
            algorithm
        )

    except ValueError:

        hasher = hashlib.sha256()

    hasher.update(
        text
    )

    return hasher.hexdigest()


def product_hash(
    product: dict,
) -> str:
    """
    Gera identificador estável para um produto.
    """

    if not isinstance(
        product,
        dict,
    ):

        return make_hash(
            ""
        )

    identifier = (
        product.get("id")
        or product.get("item_id")
        or product.get("link")
        or product.get("url")
        or product.get("titulo")
        or product.get("title")
        or ""
    )

    return make_hash(
        normalize_text(
            identifier
        )
    )


# ============================================================
# LISTAS
# ============================================================

def unique_list(
    values: Iterable[Any],
) -> list:
    """
    Remove duplicados preservando a ordem.
    """

    result = []

    seen = set()

    for value in values:

        try:

            marker = (
                value
                if isinstance(
                    value,
                    (
                        str,
                        int,
                        float,
                        bool,
                        type(None),
                    ),
                )
                else repr(value)
            )

        except Exception:

            marker = repr(
                value
            )

        if marker in seen:

            continue

        seen.add(
            marker
        )

        result.append(
            value
        )

    return result


def chunked(
    values: Iterable[Any],
    size: int,
) -> list:
    """
    Divide uma coleção em grupos.
    """

    try:

        size = int(
            size
        )

    except (
        TypeError,
        ValueError,
    ):

        size = 1

    size = max(
        1,
        size,
    )

    values = list(
        values
    )

    return [
        values[index:index + size]
        for index in range(
            0,
            len(values),
            size,
        )
    ]


# ============================================================
# DICIONÁRIOS
# ============================================================

def get_first(
    data: Any,
    keys: Iterable[str],
    default: Any = None,
) -> Any:
    """
    Retorna o primeiro valor existente entre várias chaves.
    """

    if not isinstance(
        data,
        dict,
    ):

        return default

    for key in keys:

        if key in data:

            value = data.get(
                key
            )

            if value is not None:

                return value

    return default


def merge_dicts(
    first: Optional[dict],
    second: Optional[dict],
) -> dict:
    """
    Mescla dois dicionários.
    """

    result = {}

    if isinstance(
        first,
        dict,
    ):

        result.update(
            first
        )

    if isinstance(
        second,
        dict,
    ):

        result.update(
            second
        )

    return result


# ============================================================
# CATEGORIAS
# ============================================================

def normalize_category(
    value: Any,
) -> str:
    """
    Normaliza o nome de uma categoria.
    """

    category = normalize_text(
        value
    )

    category = category.replace(
        " ",
        "_",
    )

    return category


# ============================================================
# BOOLEANS
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

    value = normalize_text(
        value
    )

    if value in (
        "true",
        "1",
        "sim",
        "yes",
        "on",
        "ativo",
        "enabled",
    ):

        return True

    if value in (
        "false",
        "0",
        "nao",
        "não",
        "no",
        "off",
        "inativo",
        "disabled",
    ):

        return False

    return default


# ============================================================
# EXPORTAÇÕES
# ============================================================

__all__ = [
    "clean_text",
    "normalize_text",
    "slugify",
    "truncate",
    "to_float",
    "to_int",
    "clamp",
    "format_money",
    "calculate_margin",
    "calculate_profit",
    "is_url",
    "get_domain",
    "make_hash",
    "product_hash",
    "unique_list",
    "chunked",
    "get_first",
    "merge_dicts",
    "normalize_category",
    "to_bool",
]
