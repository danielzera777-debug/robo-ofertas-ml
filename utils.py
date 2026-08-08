import os
import re
import secrets
import hashlib
from urllib.parse import urlparse


def limpar_texto(valor):
    if valor is None:
        return ""

    texto = str(valor)

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def numero(valor, padrao=0.0):
    try:
        if valor is None:
            return float(padrao)

        if isinstance(valor, str):
            valor = (
                valor
                .replace("R$", "")
                .replace(" ", "")
                .replace(".", "")
                .replace(",", ".")
            )

        return float(valor)

    except (
        ValueError,
        TypeError
    ):
        return float(padrao)


def inteiro(valor, padrao=0):
    try:
        return int(float(valor))
    except (
        ValueError,
        TypeError
    ):
        return int(padrao)


def formatar_preco(valor):
    valor = numero(valor)

    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formatar_percentual(valor):
    valor = numero(valor)

    return f"{valor:.2f}%".replace(
        ".",
        ","
    )


def calcular_desconto(
    preco_original,
    preco
):
    original = numero(
        preco_original
    )

    atual = numero(
        preco
    )

    if original <= 0:
        return 0.0

    if atual < 0:
        atual = 0.0

    if atual >= original:
        return 0.0

    desconto = (
        (original - atual)
        / original
    ) * 100

    return round(
        desconto,
        2
    )


def calcular_lucro(
    custo,
    venda
):
    custo = numero(custo)
    venda = numero(venda)

    return round(
        venda - custo,
        2
    )


def calcular_margem(
    custo,
    venda
):
    custo = numero(custo)
    venda = numero(venda)

    if custo <= 0:
        return 0.0

    margem = (
        (venda - custo)
        / custo
    ) * 100

    return round(
        margem,
        2
    )


def gerar_token(tamanho=32):
    try:
        tamanho = int(tamanho)
    except (
        ValueError,
        TypeError
    ):
        tamanho = 32

    if tamanho < 16:
        tamanho = 16

    return secrets.token_urlsafe(
        tamanho
    )


def gerar_hash(valor):
    texto = str(
        valor or ""
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        texto
    ).hexdigest()


def validar_url(url):
    if not url:
        return False

    try:
        resultado = urlparse(
            str(url)
        )

        return (
            resultado.scheme
            in (
                "http",
                "https"
            )
            and bool(
                resultado.netloc
            )
        )

    except (
        ValueError,
        TypeError
    ):
        return False


def nome_arquivo_seguro(
    nome,
    extensao=None
):
    nome = limpar_texto(
        nome
    )

    nome = re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        nome
    )

    nome = nome.strip(
        "._"
    )

    if not nome:
        nome = "arquivo"

    if extensao:

        extensao = str(
            extensao
        ).strip()

        if not extensao.startswith(
            "."
        ):
            extensao = (
                "." + extensao
            )

        nome = (
            os.path.splitext(
                nome
            )[0]
            + extensao
        )

    return nome


def garantir_pasta(
    caminho
):
    if not caminho:
        return None

    os.makedirs(
        caminho,
        exist_ok=True
    )

    return caminho


def obter_variavel(
    nome,
    padrao=None,
    obrigatoria=False
):
    valor = os.getenv(
        nome,
        padrao
    )

    if obrigatoria and not valor:

        raise RuntimeError(
            f"Variável de ambiente "
            f"obrigatória não configurada: "
            f"{nome}"
        )

    return valor


def limitar_texto(
    texto,
    limite=500
):
    texto = str(
        texto or ""
    )

    try:
        limite = int(
            limite
        )
    except (
        ValueError,
        TypeError
    ):
        limite = 500

    if limite < 1:
        return ""

    if len(texto) <= limite:
        return texto

    if limite <= 3:
        return texto[:limite]

    return (
        texto[:limite - 3]
        + "..."
    )


def extrair_id_mercadolivre(
    valor
):
    if not valor:
        return None

    texto = str(
        valor
    ).strip()

    padrao = re.search(
        r"\bMLB[-_]?\d+\b",
        texto,
        re.IGNORECASE
    )

    if not padrao:
        return None

    return (
        padrao.group(0)
        .upper()
        .replace("_", "-")
    )


def normalizar_item_mercadolivre(
    produto
):
    if not isinstance(
        produto,
        dict
    ):
        return {}

    item_id = (
        produto.get("id")
        or produto.get(
            "item_id"
        )
    )

    titulo = (
        produto.get("title")
        or produto.get(
            "titulo"
        )
        or "Produto"
    )

    preco = (
        produto.get("price")
        if produto.get("price")
        is not None
        else produto.get(
            "preco",
            0
        )
    )

    preco_original = (
        produto.get(
            "original_price"
        )
        if produto.get(
            "original_price"
        ) is not None
        else produto.get(
            "preco_original",
            0
        )
    )

    imagem = (
        produto.get(
            "thumbnail"
        )
        or produto.get(
            "secure_thumbnail"
        )
        or produto.get(
            "imagem"
        )
        or ""
    )

    link = (
        produto.get(
            "permalink"
        )
        or produto.get(
            "link"
        )
        or ""
    )

    desconto = calcular_desconto(
        preco_original,
        preco
    )

    return {
        "id": item_id,
        "titulo": limpar_texto(
            titulo
        ),
        "preco": numero(
            preco
        ),
        "preco_original": numero(
            preco_original
        ),
        "desconto": desconto,
        "imagem": imagem,
        "link": link,
        "categoria": produto.get(
            "category_id"
        )
    }


def ordenar_por_preco(
    produtos,
    reverso=False
):
    if not isinstance(
        produtos,
        list
    ):
        return []

    return sorted(
        produtos,
        key=lambda produto:
            numero(
                produto.get(
                    "preco",
                    produto.get(
                        "price",
                        0
                    )
                )
            ),
        reverse=reverso
    )


def ordenar_por_desconto(
    produtos
):
    if not isinstance(
        produtos,
        list
    ):
        return []

    return sorted(
        produtos,
        key=lambda produto:
            numero(
                produto.get(
                    "desconto",
                    0
                )
            ),
        reverse=True
    )


def remover_duplicados(
    itens,
    chave="id"
):
    if not isinstance(
        itens,
        list
    ):
        return []

    resultado = []
    vistos = set()

    for item in itens:

        if not isinstance(
            item,
            dict
        ):
            continue

        valor = item.get(
            chave
        )

        if valor is None:

            resultado.append(
                item
            )

            continue

        if valor in vistos:
            continue

        vistos.add(
            valor
        )

        resultado.append(
            item
        )

    return resultado
