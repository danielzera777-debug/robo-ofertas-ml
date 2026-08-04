import os
import secrets
import hashlib
import base64
import requests
import html

from urllib.parse import urlencode, quote
from flask import Flask, request, session

app = Flask(__name__)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)

app.secret_key = SECRET_KEY

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

API_BASE = "https://api.mercadolibre.com"

SITE_ID = "MLB"

# ============================================================
# CONFIGURAÇÕES DA REVENDA
# ============================================================

MARGEM_PADRAO = 10
LUCRO_MINIMO_PADRAO = 20

# Quantos produtos serão pesquisados por página
PRODUTOS_POR_PAGINA = 20


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def escapar(valor):

    return html.escape(
        str(valor or "")
    )


def numero(valor):

    try:
        return float(valor)

    except Exception:
        return 0.0


def formatar_preco(valor):

    if valor is None:
        return "Preço indisponível"

    try:

        valor = float(valor)

        return (
            f"R$ {valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except Exception:

        return "Preço indisponível"


def imagem_segura(url):

    if not url:
        return ""

    url = str(url)

    # Algumas respostas podem vir com http.
    # O navegador pode bloquear conteúdo misto.
    if url.startswith("http://"):
        url = url.replace(
            "http://",
            "https://",
            1
        )

    return url


# ============================================================
# HEADERS
# ============================================================

def headers_api():

    headers = {
        "Accept": "application/json",
        "User-Agent": "Robo-Ofertas-ML/2.0"
    }

    token = session.get(
        "access_token"
    )

    if token:

        headers["Authorization"] = (
            f"Bearer {token}"
        )

    return headers


# ============================================================
# REQUEST GET
# ============================================================

def requisicao_get(
    url,
    params=None
):

    try:

        return requests.get(

            url,

            params=params,

            headers=headers_api(),

            timeout=30

        )

    except requests.RequestException as erro:

        print(
            "ERRO REQUEST:",
            erro
        )

        return None


# ============================================================
# LOGIN
# ============================================================

@app.route("/")
def home():

    code = request.args.get(
        "code"
    )

    state = request.args.get(
        "state"
    )

    if not CLIENT_ID:

        return (
            "ML_CLIENT_ID não configurado.",
            500
        )

    if not CLIENT_SECRET:

        return (
            "ML_CLIENT_SECRET não configurado.",
            500
        )

    if not REDIRECT_URI:

        return (
            "ML_REDIRECT_URI não configurado.",
            500
        )

    # ========================================================
    # CALLBACK DO MERCADO LIVRE
    # ========================================================

    if code:

        saved_state = session.get(
            "state"
        )

        if not saved_state:

            return """
            <h2>❌ Sessão expirada.</h2>
            <p>Conecte novamente sua conta.</p>
            <a href="/">Voltar</a>
            """, 400

        if state != saved_state:

            return """
            <h2>❌ State inválido.</h2>
            <a href="/">Voltar</a>
            """, 400

        code_verifier = session.get(
            "code_verifier"
        )

        if not code_verifier:

            return """
            <h2>
            ❌ Code verifier não encontrado.
            </h2>
            """, 400

        try:

            response = requests.post(

                f"{API_BASE}/oauth/token",

                data={

                    "grant_type":
                    "authorization_code",

                    "client_id":
                    CLIENT_ID,

                    "client_secret":
                    CLIENT_SECRET,

                    "code":
                    code,

                    "redirect_uri":
                    REDIRECT_URI,

                    "code_verifier":
                    code_verifier
                },

                timeout=30
            )

        except requests.RequestException as erro:

            return f"""
            <h1>❌ Erro de conexão</h1>

            <pre>
            {escapar(erro)}
            </pre>

            <a href="/">Voltar</a>
            """, 500

        if response.status_code != 200:

            return f"""
            <h1>❌ Erro ao obter token</h1>

            <p>
            Status:
            {response.status_code}
            </p>

            <pre>
            {escapar(response.text)}
            </pre>

            <a href="/">Voltar</a>
            """, 400

        try:

            token_data = response.json()

        except Exception:

            return """
            <h2>
            ❌ Resposta inválida.
            </h2>
            """, 400

        access_token = token_data.get(
            "access_token"
        )

        if not access_token:

            return """
            <h2>
            ❌ Access Token não recebido.
            </h2>
            """, 400

        session["access_token"] = (
            access_token
        )

        session["refresh_token"] = (
            token_data.get(
                "refresh_token"
            )
        )

        session.pop(
            "code_verifier",
            None
        )

        session.pop(
            "state",
            None
        )

        # ====================================================
        # CONSULTAR USUÁRIO
        # ====================================================

        user_response = requisicao_get(
            f"{API_BASE}/users/me"
        )

        if user_response is None:

            return """
            <h1>
            ❌ Erro ao consultar usuário.
            </h1>
            """, 500

        if user_response.status_code != 200:

            return f"""
            <h1>
            ❌ Erro ao consultar conta.
            </h1>

            <pre>
            {escapar(user_response.text)}
            </pre>

            <a href="/">
            Voltar
            </a>
            """, 400

        user_data = (
            user_response.json()
        )

        nickname = user_data.get(
            "nickname",
            "usuário"
        )

        user_id = user_data.get(
            "id",
            ""
        )

        session["user_id"] = (
            user_id
        )

        return pagina_principal(
            nickname,
            user_id
        )

    # ========================================================
    # PKCE
    # ========================================================

    code_verifier = (
        secrets.token_urlsafe(64)
    )

    code_challenge = (
        base64.urlsafe_b64encode(

            hashlib.sha256(

                code_verifier.encode()

            ).digest()

        )
        .rstrip(b"=")
        .decode()
    )

    state = (
        secrets.token_urlsafe(32)
    )

    session["code_verifier"] = (
        code_verifier
    )

    session["state"] = state

    params = {

        "response_type":
        "code",

        "client_id":
        CLIENT_ID,

        "redirect_uri":
        REDIRECT_URI,

        "state":
        state,

        "code_challenge":
        code_challenge,

        "code_challenge_method":
        "S256"
    }

    auth_url = (
        "https://auth.mercadolivre.com.br/authorization?"
        + urlencode(params)
    )

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
    >

    <title>Robô Ofertas ML</title>

    </head>

    <body style="
    font-family:Arial;
    background:#f5f5f5;
    padding:30px;
    text-align:center;
    ">

    <h1>
    🤖 Robô Ofertas ML
    </h1>

    <p>
    Conecte sua conta do Mercado Livre
    </p>

    <a href="{escapar(auth_url)}">

    <button style="
    padding:15px 25px;
    font-size:18px;
    border:0;
    border-radius:8px;
    background:#3483fa;
    color:white;
    ">

    🔐 Conectar Mercado Livre

    </button>

    </a>

    </body>

    </html>
    """


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

def pagina_principal(
    nickname,
    user_id
):

    return f"""

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
    >

    <title>
    Robô Ofertas ML
    </title>

    <style>

    body {{
        font-family:Arial;
        background:#f5f5f5;
        margin:0;
        padding:20px;
    }}

    .container {{
        max-width:700px;
        margin:auto;
        background:white;
        padding:25px;
        border-radius:15px;
    }}

    input {{
        width:100%;
        box-sizing:border-box;
        padding:15px;
        font-size:17px;
        border:1px solid #ccc;
        border-radius:8px;
        margin-bottom:10px;
    }}

    button {{
        width:100%;
        padding:15px;
        font-size:17px;
        border:0;
        border-radius:8px;
        background:#3483fa;
        color:white;
    }}

    .atalhos {{
        display:grid;
        grid-template-columns:repeat(2, 1fr);
        gap:10px;
        margin-top:15px;
    }}

    .atalho {{
        padding:12px;
        background:#f5f5f5;
        border-radius:8px;
        text-align:center;
        cursor:pointer;
    }}

    .info {{
        background:#f5f5f5;
        padding:15px;
        border-radius:10px;
        margin-top:15px;
    }}

    </style>

    </head>

    <body>

    <div class="container">

    <h1>
    🤖 Robô Ofertas ML
    </h1>

    <p>
    ✅ Mercado Livre conectado!
    </p>

    <p>
    Usuário:
    <strong>
    {escapar(nickname)}
    </strong>
    </p>

    <hr>

    <h2>
    🔎 Buscar produto
    </h2>

    <form
    action="/buscar"
    method="get"
    >

    <input
    type="text"
    id="produto"
    name="q"
    placeholder="Ex: iPhone 13, relógio, camisa..."
    required
    >

    <div class="atalhos">

        <div
        class="atalho"
        onclick="produto.value='iPhone 13'"
        >
        📱 Celulares
        </div>

        <div
        class="atalho"
        onclick="produto.value='relógio masculino'"
        >
        ⌚ Relógios
        </div>

        <div
        class="atalho"
        onclick="produto.value='camisa masculina'"
        >
        👕 Roupas
        </div>

        <div
        class="atalho"
        onclick="produto.value='tênis masculino'"
        >
        👟 Tênis
        </div>

    </div>

    <br>

    <label>
    📈 Margem de lucro (%)
    </label>

    <input
    type="number"
    name="margem"
    value="{MARGEM_PADRAO}"
    min="0"
    max="100"
    step="1"
    >

    <label>
    💰 Lucro mínimo
    </label>

    <input
    type="number"
    name="lucro_minimo"
    value="{LUCRO_MINIMO_PADRAO}"
    min="0"
    step="1"
    >

    <button type="submit">
    🔎 Encontrar oportunidades
    </button>

    </form>

    <div class="info">

    <strong>
    💡 Como funciona
    </strong>

    <p>
    O robô pesquisa produtos do Mercado Livre,
    encontra publicações disponíveis e mostra
    a foto do produto junto com preço e oportunidade
    de revenda.
    </p>

    </div>

    <br>

    <a href="/diagnostico">
    🧪 Diagnóstico
    </a>

    <br><br>

    <a href="/logout">
    🔓 Desconectar
    </a>

    </div>

    </body>

    </html>

    """


# ============================================================
# BUSCAR PRODUTOS NO CATÁLOGO
# ============================================================

def buscar_produtos_catalogo(
    termo,
    offset=0,
    limit=20
):

    url = (
        f"{API_BASE}/products/search"
    )

    params = {

        "status":
        "active",

        "site_id":
        SITE_ID,

        "q":
        termo,

        "offset":
        offset,

        "limit":
        limit
    }

    return requisicao_get(
        url,
        params
    )


# ============================================================
# PUBLICAÇÕES DO PRODUTO
# ============================================================

def buscar_publicacoes(
    product_id
):

    url = (
        f"{API_BASE}/products/"
        f"{product_id}/items"
    )

    response = requisicao_get(

        url,

        {
            "offset": 0,
            "limit": 100
        }

    )

    if response is None:
        return []

    if response.status_code != 200:
        return []

    try:

        data = response.json()

        return data.get(
            "results",
            []
        )

    except Exception:

        return []


# ============================================================
# DETALHES DOS ANÚNCIOS
# ============================================================

def buscar_detalhes_itens(
    item_ids
):

    if not item_ids:
        return []

    resultados = []

    item_ids = list(
        dict.fromkeys(
            item_ids
        )
    )

    for inicio in range(
        0,
        len(item_ids),
        20
    ):

        bloco = item_ids[
            inicio:
            inicio + 20
        ]

        ids = ",".join(
            bloco
        )

        response = requisicao_get(

            f"{API_BASE}/items",

            {
                "ids": ids
            }

        )

        if response is None:
            continue

        if response.status_code != 200:
            continue

        try:

            data = response.json()

        except Exception:

            continue

        for resultado in data:

            if resultado.get(
                "code"
            ) != 200:

                continue

            body = resultado.get(
                "body"
            )

            if body:

                resultados.append(
                    body
                )

    return resultados


# ============================================================
# VENDEDORES
# ============================================================

def buscar_vendedores(
    seller_ids
):

    vendedores = {}

    seller_ids = list(
        dict.fromkeys(
            str(x)
            for x in seller_ids
            if x
        )
    )

    for seller_id in seller_ids:

        response = requisicao_get(
            f"{API_BASE}/users/{seller_id}"
        )

        if response is None:
            continue

        if response.status_code != 200:
            continue

        try:

            data = response.json()

        except Exception:

            continue

        vendedores[
            seller_id
        ] = data.get(
            "nickname",
            f"Vendedor {seller_id}"
        )

    return vendedores


# ============================================================
# BUSCA PRINCIPAL
# ============================================================

@app.route("/buscar")
def buscar():

    termo = request.args.get(
        "q",
        ""
    ).strip()

    if not termo:

        return """
        <h2>
        ❌ Digite um produto.
        </h2>

        <a href="/">
        ← Voltar
        </a>
        """, 400

    if not session.get(
        "access_token"
    ):

        return """
        <h1>
        ❌ Mercado Livre não conectado
        </h1>

        <a href="/">
        🔐 Conectar
        </a>
        """, 401

    # ========================================================
    # MARGEM
    # ========================================================

    try:

        margem = float(
            request.args.get(
                "margem",
                MARGEM_PADRAO
            )
        )

    except Exception:

        margem = MARGEM_PADRAO

    margem = max(
        0,
        min(
            margem,
            100
        )
    )

    # ========================================================
    # LUCRO MÍNIMO
    # ========================================================

    try:

        lucro_minimo = float(
            request.args.get(
                "lucro_minimo",
                LUCRO_MINIMO_PADRAO
            )
        )

    except Exception:

        lucro_minimo = (
            LUCRO_MINIMO_PADRAO
        )

    lucro_minimo = max(
        0,
        lucro_minimo
    )

    # ========================================================
    # OFFSET
    # ========================================================

    try:

        offset = int(
            request.args.get(
                "offset",
                0
            )
        )

    except Exception:

        offset = 0

    offset = max(
        0,
        offset
    )

    # ========================================================
    # BUSCA
    # ========================================================

    response = buscar_produtos_catalogo(

        termo,

        offset,

        PRODUTOS_POR_PAGINA

    )

    if response is None:

        return """
        <h1>
        ❌ Erro de conexão
        </h1>

        <a href="/">
        ← Voltar
        </a>
        """, 500

    if response.status_code != 200:

        return f"""

        <h1>
        ❌ Erro na busca
        </h1>

        <p>
        Status:
        {response.status_code}
        </p>

        <pre>
        {escapar(response.text)}
        </pre>

        <a href="/diagnostico">
        🧪 Diagnóstico
        </a>

        <br><br>

        <a href="/">
        ← Voltar
        </a>

        """, response.status_code

    try:

        data = response.json()

    except Exception:

        return """
        <h1>
        ❌ Resposta inválida
        </h1>
        """, 500

    produtos = data.get(
        "results",
        []
    )

    paging = data.get(
        "paging",
        {}
    )

    total_produtos = paging.get(
        "total",
        0
    )

    # ========================================================
    # ANÚNCIOS
    # ========================================================

    anuncios = []

    for produto in produtos:

        product_id = produto.get(
            "id",
            ""
        )

        if not product_id:
            continue

        # ----------------------------------------------------
        # Informações do catálogo
        # ----------------------------------------------------

        nome_produto = produto.get(
            "name",
            "Produto"
        )

        domain_id = produto.get(
            "domain_id",
            ""
        )

        # ----------------------------------------------------
        # Imagem do catálogo
        # ----------------------------------------------------

        imagem_catalogo = ""

        pictures = produto.get(
            "pictures",
            []
        )

        if pictures:

            primeira = pictures[0]

            if isinstance(
                primeira,
                dict
            ):

                imagem_catalogo = (
                    primeira.get(
                        "url"
                    )
                    or
                    primeira.get(
                        "secure_url"
                    )
                    or
                    primeira.get(
                        "src"
                    )
                    or
                    ""
                )

        # ----------------------------------------------------
        # Publicações
        # ----------------------------------------------------

        itens = buscar_publicacoes(
            product_id
        )

        for item in itens:

            item_id = (

                item.get(
                    "item_id"
                )

                or

                item.get(
                    "id"
                )
            )

            if not item_id:
                continue

            custo = numero(
                item.get(
                    "price"
                )
            )

            if custo <= 0:
                continue

            # ------------------------------------------------
            # Preço de revenda
            # ------------------------------------------------

            preco_venda = (

                custo *

                (
                    1 +
                    margem / 100
                )
            )

            lucro = (

                preco_venda -
                custo
            )

            if lucro < lucro_minimo:
                continue

            imagem = (

                item.get(
                    "thumbnail"
                )

                or

                item.get(
                    "secure_thumbnail"
                )

                or

                imagem_catalogo

                or

                ""
            )

            imagem = imagem_segura(
                imagem
            )

            titulo = (

                item.get(
                    "title"
                )

                or

                nome_produto

                or

                "Produto"
            )

            anuncios.append({

                "product_id":
                product_id,

                "product_name":
                nome_produto,

                "domain_id":
                domain_id,

                "item_id":
                item_id,

                "price":
                custo,

                "preco_venda":
                preco_venda,

                "lucro":
                lucro,

                "seller_id":
                item.get(
                    "seller_id"
                ),

                "condition":
                item.get(
                    "condition",
                    "Não informado"
                ),

                "category_id":
                item.get(
                    "category_id",
                    ""
                ),

                "sold_quantity":
                item.get(
                    "sold_quantity",
                    0
                ),

                "available_quantity":
                item.get(
                    "available_quantity"
                ),

                "permalink":
                item.get(
                    "permalink",
                    ""
                ),

                "thumbnail":
                imagem,

                "title":
                titulo,

                "pictures":
                item.get(
                    "pictures",
                    []
                )
            })


    # ========================================================
    # DETALHES DOS ITENS
    # ========================================================

    ids = [

        anuncio[
            "item_id"
        ]

        for anuncio in anuncios
    ]

    detalhes = (
        buscar_detalhes_itens(
            ids
        )
    )

    detalhes_map = {}

    for detalhe in detalhes:

        item_id = detalhe.get(
            "id"
        )

        if item_id:

            detalhes_map[
                item_id
            ] = detalhe

    # ========================================================
    # ATUALIZAR INFORMAÇÕES
    # ========================================================

    for anuncio in anuncios:

        detalhe = detalhes_map.get(
            anuncio["item_id"]
        )

        if not detalhe:
            continue

        # ----------------------------------------------------
        # Preço
        # ----------------------------------------------------

        if detalhe.get(
            "price"
        ) is not None:

            anuncio["price"] = numero(
                detalhe.get(
                    "price"
                )
            )

        # ----------------------------------------------------
        # Campos
        # ----------------------------------------------------

        for campo in [

            "title",
            "seller_id",
            "condition",
            "category_id",
            "sold_quantity",
            "available_quantity",
            "permalink",
            "thumbnail"

        ]:

            if detalhe.get(
                campo
            ) is not None:

                anuncio[campo] = (
                    detalhe.get(
                        campo
                    )
                )

        # ----------------------------------------------------
        # Imagem
        # ----------------------------------------------------

        if detalhe.get(
            "pictures"
        ):

            anuncio["pictures"] = (
                detalhe.get(
                    "pictures"
                )
            )

        imagem = (

            detalhe.get(
                "secure_thumbnail"
            )

            or

            detalhe.get(
                "thumbnail"
            )

            or

            anuncio.get(
                "thumbnail"
            )

        )

        anuncio["thumbnail"] = (
            imagem_segura(
                imagem
            )
        )

        # ----------------------------------------------------
        # Recalcular
        # ----------------------------------------------------

        custo = numero(
            anuncio.get(
                "price"
            )
        )

        anuncio["preco_venda"] = (

            custo *

            (
                1 +
                margem / 100
            )
        )

        anuncio["lucro"] = (

            anuncio["preco_venda"] -
            custo
        )

    # ========================================================
    # FILTRO
    # ========================================================

    anuncios = [

        anuncio

        for anuncio in anuncios

        if anuncio.get(
            "lucro",
            0
        ) >= lucro_minimo

    ]

    # ========================================================
    # REMOVER DUPLICADOS
    # ========================================================

    unicos = {}

    for anuncio in anuncios:

        unicos[
            anuncio["item_id"]
        ] = anuncio

    anuncios = list(
        unicos.values()
    )

    # ========================================================
    # ORDENAR PELO MAIOR LUCRO
    # ========================================================

    anuncios.sort(

        key=lambda anuncio:
        anuncio.get(
            "lucro",
            0
        ),

        reverse=True
    )

    # ========================================================
    # VENDEDORES
    # ========================================================

    seller_ids = [

        anuncio.get(
            "seller_id"
        )

        for anuncio in anuncios

    ]

    vendedores = (
        buscar_vendedores(
            seller_ids
        )
    )

    # ========================================================
    # HTML
    # ========================================================

    pagina = f"""

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
    >

    <title>
    Oportunidades
    </title>

    <style>

    * {{
        box-sizing:border-box;
    }}

    body {{
        font-family:Arial,sans-serif;
        background:#f5f5f5;
        margin:0;
        padding:15px;
    }}

    .container {{
        max-width:900px;
        margin:auto;
    }}

    .top {{
        background:white;
        padding:20px;
        border-radius:15px;
        margin-bottom:15px;
    }}

    .card {{
        background:white;
        padding:18px;
        border-radius:15px;
        margin-bottom:18px;
        box-shadow:
        0 3px 12px rgba(0,0,0,.08);
    }}

    .produto-imagem {{
        width:100%;
        max-width:320px;
        height:320px;
        object-fit:contain;
        display:block;
        margin:0 auto 18px auto;
        border-radius:12px;
        background:#fafafa;
    }}

    .sem-imagem {{
        width:100%;
        max-width:320px;
        height:320px;
        display:flex;
        align-items:center;
        justify-content:center;
        margin:0 auto 18px auto;
        border-radius:12px;
        background:#f0f0f0;
        color:#777;
        font-size:20px;
    }}

    .titulo {{
        font-size:22px;
        margin-bottom:15px;
    }}

    .custo {{
        color:#555;
        font-size:18px;
        margin:8px 0;
    }}

    .venda {{
        color:#008000;
        font-size:29px;
        font-weight:bold;
        margin:12px 0;
    }}

    .lucro {{
        background:#d4edda;
        color:#155724;
        padding:13px;
        border-radius:9px;
        font-size:21px;
        font-weight:bold;
        margin:12px 0;
    }}

    .margem {{
        background:#e7f1ff;
        padding:11px;
        border-radius:9px;
        margin:10px 0;
    }}

    .info {{
        color:#555;
        margin:8px 0;
    }}

    .botao {{
        display:block;
        text-align:center;
        background:#3483fa;
        color:white;
        padding:14px 20px;
        border-radius:9px;
        text-decoration:none;
        margin-top:12px;
        font-weight:bold;
    }}

    .whatsapp {{
        display:block;
        text-align:center;
        background:#25D366;
        color:white;
        padding:14px 20px;
        border-radius:9px;
        text-decoration:none;
        margin-top:10px;
        font-weight:bold;
    }}

    .melhor {{
        background:#fff3cd;
        color:#856404;
        padding:11px;
        border-radius:9px;
        display:block;
        text-align:center;
        font-weight:bold;
        margin-bottom:15px;
    }}

    .produto-id {{
        background:#f5f5f5;
        padding:8px;
        border-radius:6px;
        font-size:13px;
        color:#777;
        margin-top:10px;
    }}

    .paginacao {{
        background:white;
        padding:20px;
        border-radius:12px;
        text-align:center;
        margin-top:20px;
    }}

    .pagina-btn {{
        display:inline-block;
        background:#3483fa;
        color:white;
        padding:12px 18px;
        border-radius:8px;
        text-decoration:none;
        margin:5px;
    }}

    </style>

    </head>

    <body>

    <div class="container">

    <div class="top">

    <h1>
    🔥 Oportunidades de revenda
    </h1>

    <h2>
    🔎 {escapar(termo)}
    </h2>

    <p>
    📦 Produtos encontrados:
    <strong>
    {total_produtos}
    </strong>
    </p>

    <p>
    🛒 Oportunidades encontradas:
    <strong>
    {len(anuncios)}
    </strong>
    </p>

    <p>
    📈 Margem:
    <strong>
    {margem:.0f}%
    </strong>
    </p>

    <p>
    💰 Lucro mínimo:
    <strong>
    {formatar_preco(lucro_minimo)}
    </strong>
    </p>

    </div>

    """

    # ========================================================
    # NENHUM RESULTADO
    # ========================================================

    if not anuncios:

        pagina += f"""

        <div class="card">

        <h2>
        😕 Nenhuma oportunidade encontrada
        </h2>

        <p>
        Não encontramos anúncios com lucro
        mínimo de
        <strong>
        {formatar_preco(lucro_minimo)}
        </strong>.
        </p>

        <p>
        Tente diminuir o lucro mínimo ou
        pesquisar outro produto.
        </p>

        </div>

        """

    # ========================================================
    # CARDS
    # ========================================================

    for indice, anuncio in enumerate(
        anuncios
    ):

        titulo = anuncio.get(
            "title",
            "Produto"
        )

        item_id = anuncio.get(
            "item_id",
            ""
        )

        custo = anuncio.get(
            "price",
            0
        )

        preco_venda = anuncio.get(
            "preco_venda",
            0
        )

        lucro = anuncio.get(
            "lucro",
            0
        )

        seller_id = anuncio.get(
            "seller_id"
        )

        seller_nome = vendedores.get(

            str(seller_id),

            f"Vendedor {seller_id}"
        )

        vendidos = anuncio.get(
            "sold_quantity",
            0
        )

        condicao = anuncio.get(
            "condition",
            "Não informado"
        )

        categoria = anuncio.get(
            "category_id",
            "Não informada"
        )

        link = anuncio.get(
            "permalink",
            ""
        )

        imagem = anuncio.get(
            "thumbnail",
            ""
        )

        imagem = imagem_segura(
            imagem
        )

        if not link:

            link = (
                "https://www.mercadolivre.com.br/"
                + item_id
            )

        # ----------------------------------------------------
        # TEXTO PARA WHATSAPP
        # ----------------------------------------------------

        mensagem = (

            f"🔥 OFERTA ENCONTRADA!\n\n"

            f"📦 {titulo}\n\n"

            f"💰 Por apenas "
            f"{formatar_preco(preco_venda)}\n\n"

            f"🛒 Comprar agora:\n"
            f"{link}"
        )

        whatsapp_url = (

            "https://wa.me/?text="

            + quote(
                mensagem
            )
        )

        pagina += """

        <div class="card">

        """

        if indice == 0:

            pagina += """

            <div class="melhor">

            🏆 MELHOR OPORTUNIDADE

            </div>

            """

        # ----------------------------------------------------
        # FOTO
        # ----------------------------------------------------

        if imagem:

            pagina += f"""

            <img
                class="produto-imagem"
                src="{escapar(imagem)}"
                alt="{escapar(titulo)}"
                loading="lazy"
            >

            """

        else:

            pagina += """

            <div class="sem-imagem">

            📦
            <br>
            Sem imagem disponível

            </div>

            """

        # ----------------------------------------------------
        # INFORMAÇÕES
        # ----------------------------------------------------

        pagina += f"""

        <div class="titulo">

        {escapar(titulo)}

        </div>

        <div class="custo">

        💵 Preço encontrado:

        <strong>
        {formatar_preco(custo)}
        </strong>

        </div>

        <div class="margem">

        📈 Margem configurada:

        <strong>
        {margem:.0f}%
        </strong>

        </div>

        <div class="venda">

        🏷️ Preço sugerido:

        {formatar_preco(preco_venda)}

        </div>

        <div class="lucro">

        💰 Lucro estimado:

        {formatar_preco(lucro)}

        </div>

        <div class="info">

        👤 Vendedor:

        <strong>
        {escapar(seller_nome)}
        </strong>

        </div>

        <div class="info">

        🔥 Vendidos:

        <strong>
        {escapar(vendidos)}
        </strong>

        </div>

        <div class="info">

        🏷️ Condição:

        {escapar(condicao)}

        </div>

        <div class="info">

        📂 Categoria:

        {escapar(categoria)}

        </div>

        <div class="produto-id">

        🆔 Produto:
        {escapar(anuncio.get("product_id"))}

        <br>

        🛒 Anúncio:
        {escapar(item_id)}

        </div>

        <a
            class="botao"
            href="{escapar(link)}"
            target="_blank"
            rel="noopener noreferrer"
        >

        🛒 Ver anúncio original

        </a>

        <a
            class="whatsapp"
            href="{escapar(whatsapp_url)}"
            target="_blank"
            rel="noopener noreferrer"
        >

        📲 Enviar oferta pelo WhatsApp

        </a>

        </div>

        """

    # ========================================================
    # PAGINAÇÃO
    # ========================================================

    pagina += """

    <div class="paginacao">

    """

    if offset > 0:

        anterior = max(
            0,
            offset - PRODUTOS_POR_PAGINA
        )

        url_anterior = (
            "/buscar?"
            + urlencode({

                "q":
                termo,

                "margem":
                margem,

                "lucro_minimo":
                lucro_minimo,

                "offset":
                anterior
            })
        )

        pagina += f"""

        <a
        class="pagina-btn"
        href="{escapar(url_anterior)}"
        >

        ← Anterior

        </a>

        """

    proximo = (
        offset +
        PRODUTOS_POR_PAGINA
    )

    if proximo < total_produtos:

        url_proximo = (
            "/buscar?"
            + urlencode({

                "q":
                termo,

                "margem":
                margem,

                "lucro_minimo":
                lucro_minimo,

                "offset":
                proximo
            })
        )

        pagina += f"""

        <a
        class="pagina-btn"
        href="{escapar(url_proximo)}"
        >

        Mais produtos →

        </a>

        """

    pagina += """

    </div>

    <br>

    <a href="/">
    ← Nova pesquisa
    </a>

    <br><br>

    <a href="/diagnostico">
    🧪 Diagnóstico
    </a>

    </div>

    </body>

    </html>

    """

    return pagina


# ============================================================
# DIAGNÓSTICO
# ============================================================

@app.route("/diagnostico")
def diagnostico():

    if not session.get(
        "access_token"
    ):

        return """
        <h1>
        ❌ Conta não conectada
        </h1>

        <a href="/">
        ← Voltar
        </a>
        """, 401

    testes = [

        (
            "1️⃣ /users/me",

            f"{API_BASE}/users/me",

            None
        ),

        (
            "2️⃣ Busca de produtos",

            f"{API_BASE}/products/search",

            {
                "status":
                "active",

                "site_id":
                "MLB",

                "q":
                "iPhone 13",

                "limit":
                5
            }
        ),

        (
            "3️⃣ Produto MLB18500856",

            f"{API_BASE}/products/MLB18500856",

            None
        ),

        (
            "4️⃣ Publicações MLB18500856",

            f"{API_BASE}/products/MLB18500856/items",

            {
                "offset":
                0,

                "limit":
                100
            }
        )

    ]

    blocos = []

    for nome, url, params in testes:

        response = requisicao_get(
            url,
            params
        )

        if response is None:

            blocos.append(f"""

            <div style="
            background:#f8d7da;
            padding:15px;
            margin-bottom:15px;
            border-radius:10px;
            ">

            <h2>
            {escapar(nome)}
            </h2>

            <p>
            ❌ Falha de conexão
            </p>

            </div>

            """)

            continue

        texto = response.text

        if len(texto) > 10000:

            texto = (
                texto[:10000]
                + "\n\n... cortado ..."
            )

        blocos.append(f"""

        <div style="
        background:#f8f8f8;
        padding:15px;
        margin-bottom:15px;
        border-radius:10px;
        overflow:auto;
        ">

        <h2>
        {escapar(nome)}
        </h2>

        <p>
        Status:
        <strong>
        {response.status_code}
        </strong>
        </p>

        <pre>
        {escapar(texto)}
        </pre>

        </div>

        """)

    return f"""

    <!DOCTYPE html>

    <html>

    <head>

    <meta charset="UTF-8">

    <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
    >

    <title>
    Diagnóstico
    </title>

    </head>

    <body style="
    font-family:Arial;
    background:#f5f5f5;
    padding:20px;
    ">

    <div style="
    max-width:950px;
    margin:auto;
    background:white;
    padding:20px;
    border-radius:12px;
    ">

    <h1>
    🧪 Diagnóstico Mercado Livre
    </h1>

    {"".join(blocos)}

    <a href="/">
    ← Voltar
    </a>

    </div>

    </body>

    </html>

    """


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return """

    <h1>
    🔓 Desconectado
    </h1>

    <p>
    Sessão encerrada.
    </p>

    <a href="/">
    🔐 Conectar novamente
    </a>

    """


# ============================================================
# TESTE DE CONFIGURAÇÃO
# ============================================================

@app.route("/teste-config")
def teste_config():

    return f"""

    <h1>
    🧪 Configuração
    </h1>

    <p>
    CLIENT_ID:
    <strong>
    {"OK" if CLIENT_ID else "FALTANDO"}
    </strong>
    </p>

    <p>
    CLIENT_SECRET:
    <strong>
    {"OK" if CLIENT_SECRET else "FALTANDO"}
    </strong>
    </p>

    <p>
    REDIRECT_URI:
    <strong>
    {
        escapar(REDIRECT_URI)
        if REDIRECT_URI
        else "FALTANDO"
    }
    </strong>
    </p>

    <p>
    SECRET_KEY:
    <strong>
    {"OK" if SECRET_KEY else "FALTANDO"}
    </strong>
    </p>

    <hr>

    <a href="/">
    ← Voltar
    </a>

    """


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.getenv(
                "PORT",
                10000
            )
        )

    )
