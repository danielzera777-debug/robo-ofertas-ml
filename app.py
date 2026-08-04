import os
import secrets
import hashlib
import base64
import requests
import html

from urllib.parse import urlencode
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

# ============================================================
# MERCADO LIVRE
# ============================================================

API_BASE = "https://api.mercadolibre.com"

SITE_ID = "MLB"

DOMAIN_CELLPHONES = "MLB-CELLPHONES"

CATEGORY_CELLPHONES = "MLB1055"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def escapar(valor):

    return html.escape(
        str(valor or "")
    )


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


def headers_api():

    headers = {
        "Accept": "application/json",
        "User-Agent": "Robo-Ofertas-ML/1.0"
    }

    token = session.get(
        "access_token"
    )

    if token:

        headers["Authorization"] = (
            f"Bearer {token}"
        )

    return headers


def requisicao_get(
    url,
    params=None,
    timeout=30
):

    try:

        return requests.get(
            url,
            params=params,
            headers=headers_api(),
            timeout=timeout
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

    code = request.args.get("code")

    state = request.args.get("state")

    if not CLIENT_ID:

        return (
            "ML_CLIENT_ID não configurado no Render.",
            500
        )

    if not CLIENT_SECRET:

        return (
            "ML_CLIENT_SECRET não configurado no Render.",
            500
        )

    if not REDIRECT_URI:

        return (
            "ML_REDIRECT_URI não configurado no Render.",
            500
        )

    # ========================================================
    # CALLBACK
    # ========================================================

    if code:

        saved_state = session.get(
            "state"
        )

        if not saved_state:

            return """
            <h2>❌ Sessão expirada.</h2>

            <p>
            Conecte novamente sua conta.
            </p>

            <a href="/">
            ← Voltar
            </a>
            """, 400

        if state != saved_state:

            return """
            <h2>❌ State inválido.</h2>

            <a href="/">
            ← Voltar
            </a>
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

        # ====================================================
        # TOKEN
        # ====================================================

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

            <a href="/">
            ← Voltar
            </a>
            """, 500

        if response.status_code != 200:

            return f"""
            <h1>
            ❌ Erro ao obter token
            </h1>

            <p>
            Status:
            {response.status_code}
            </p>

            <pre>
{escapar(response.text)}
            </pre>

            <a href="/">
            ← Voltar
            </a>
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

        session["expires_in"] = (
            token_data.get(
                "expires_in"
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
        # USUÁRIO
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

        session["user_id"] = user_id

        return pagina_principal(
            nickname,
            user_id
        )

    # ========================================================
    # PKCE
    # ========================================================

    code_verifier = secrets.token_urlsafe(
        64
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

    state = secrets.token_urlsafe(
        32
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

    <title>
    Robô Ofertas ML
    </title>

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

    <a href="{auth_url}">

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

    a {{
        color:#3483fa;
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

    <p>
    ID:
    <strong>
    {escapar(user_id)}
    </strong>
    </p>

    <hr>

    <h2>
    🔎 Buscar celulares
    </h2>

    <form
    action="/buscar"
    method="get"
    >

    <input
    type="text"
    name="q"
    placeholder="Ex: iPhone 13, Galaxy S23..."
    required
    >

    <button type="submit">
    🔎 Buscar
    </button>

    </form>

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
# BUSCAR PRODUTOS DE CATÁLOGO
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

        "domain_id":
        DOMAIN_CELLPHONES,

        "offset":
        offset,

        "limit":
        limit
    }

    return requisicao_get(
        url,
        params=params
    )


# ============================================================
# BUSCAR PUBLICAÇÕES
# ============================================================

def buscar_publicacoes(
    product_id
):

    url = (
        f"{API_BASE}/products/"
        f"{product_id}/items"
    )

    params = {

        "offset":
        0,

        "limit":
        100
    }

    response = requisicao_get(
        url,
        params=params
    )

    if response is None:

        return [], "connection"

    if response.status_code == 200:

        try:

            data = response.json()

            return (
                data.get(
                    "results",
                    []
                ),
                None
            )

        except Exception:

            return [], "json"

    # 404 No winners found
    if response.status_code == 404:

        try:

            data = response.json()

            if data.get("error") == "not_found":

                return [], "no_winners"

        except Exception:
            pass

        return [], "not_found"

    return [], (
        f"http_{response.status_code}"
    )


# ============================================================
# BUSCAR DETALHES DOS ANÚNCIOS
# ============================================================

def buscar_detalhes_itens(
    item_ids
):

    if not item_ids:

        return []

    # Remove duplicados
    item_ids = list(
        dict.fromkeys(
            item_ids
        )
    )

    resultados = []

    # API aceita multiget.
    # Fazemos blocos de até 20.
    for inicio in range(
        0,
        len(item_ids),
        20
    ):

        bloco = item_ids[
            inicio:inicio + 20
        ]

        ids = ",".join(
            bloco
        )

        url = (
            f"{API_BASE}/items"
        )

        params = {
            "ids": ids
        }

        response = requisicao_get(
            url,
            params=params
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
# BUSCAR NOME DOS VENDEDORES
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
            str(seller_id)
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
        🔐 Conectar Mercado Livre
        </a>
        """, 401

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
    # PRODUTOS
    # ========================================================

    response = buscar_produtos_catalogo(
        termo,
        offset,
        20
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
        <strong>
        {response.status_code}
        </strong>
        </p>

        <pre>
{escapar(response.text)}
        </pre>

        <br>

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

    total_produtos = (
        data.get(
            "paging",
            {}
        ).get(
            "total",
            0
        )
    )

    # ========================================================
    # COLETA PUBLICAÇÕES
    # ========================================================

    anuncios_brutos = []

    produtos_sem_anuncio = 0

    for produto in produtos:

        product_id = produto.get(
            "id",
            ""
        )

        domain_id = produto.get(
            "domain_id",
            ""
        )

        # Segurança: somente celulares
        if domain_id != DOMAIN_CELLPHONES:

            continue

        itens, erro = (
            buscar_publicacoes(
                product_id
            )
        )

        if not itens:

            produtos_sem_anuncio += 1

            continue

        for item in itens:

            item_id = (
                item.get(
                    "item_id"
                )
                or item.get(
                    "id"
                )
            )

            if not item_id:
                continue

            anuncios_brutos.append({

                "product_id":
                product_id,

                "product_name":
                produto.get(
                    "name",
                    "Produto"
                ),

                "domain_id":
                domain_id,

                "item_id":
                item_id,

                "price":
                item.get(
                    "price"
                ),

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
                    CATEGORY_CELLPHONES
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
                item.get(
                    "thumbnail",
                    ""
                ),

                "title":
                item.get(
                    "title",
                    produto.get(
                        "name",
                        "Produto"
                    )
                ),

                "city":
                (
                    item.get(
                        "seller_address",
                        {}
                    ) or {}
                ).get(
                    "city",
                    {}
                ).get(
                    "name",
                    ""
                )
                if isinstance(
                    item.get(
                        "seller_address"
                    ),
                    dict
                )
                else "",

                "state":
                (
                    item.get(
                        "seller_address",
                        {}
                    ) or {}
                ).get(
                    "state",
                    {}
                ).get(
                    "name",
                    ""
                )
                if isinstance(
                    item.get(
                        "seller_address"
                    ),
                    dict
                )
                else ""
            })

    # ========================================================
    # DETALHAR ANÚNCIOS
    # ========================================================

    ids = [

        anuncio[
            "item_id"
        ]

        for anuncio in anuncios_brutos
    ]

    detalhes = buscar_detalhes_itens(
        ids
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
    # MESCLA DADOS
    # ========================================================

    anuncios = []

    for anuncio in anuncios_brutos:

        item_id = anuncio[
            "item_id"
        ]

        detalhe = detalhes_map.get(
            item_id
        )

        if detalhe:

            anuncio["title"] = (
                detalhe.get(
                    "title"
                )
                or anuncio["title"]
            )

            anuncio["price"] = (
                detalhe.get(
                    "price"
                )
                if detalhe.get(
                    "price"
                ) is not None
                else anuncio["price"]
            )

            anuncio["seller_id"] = (
                detalhe.get(
                    "seller_id"
                )
                or anuncio["seller_id"]
            )

            anuncio["condition"] = (
                detalhe.get(
                    "condition"
                )
                or anuncio["condition"]
            )

            anuncio["category_id"] = (
                detalhe.get(
                    "category_id"
                )
                or anuncio["category_id"]
            )

            anuncio["sold_quantity"] = (
                detalhe.get(
                    "sold_quantity"
                )
                if detalhe.get(
                    "sold_quantity"
                ) is not None
                else anuncio["sold_quantity"]
            )

            anuncio["available_quantity"] = (
                detalhe.get(
                    "available_quantity"
                )
                if detalhe.get(
                    "available_quantity"
                ) is not None
                else anuncio["available_quantity"]
            )

            anuncio["permalink"] = (
                detalhe.get(
                    "permalink"
                )
                or anuncio["permalink"]
            )

            anuncio["thumbnail"] = (
                detalhe.get(
                    "thumbnail"
                )
                or anuncio["thumbnail"]
            )

        anuncios.append(
            anuncio
        )

    # ========================================================
    # REMOVE DUPLICADOS
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
    # ORDENA MENOR PREÇO
    # ========================================================

    def chave_preco(anuncio):

        preco = anuncio.get(
            "price"
        )

        try:

            return float(
                preco
            )

        except Exception:

            return float(
                "inf"
            )

    anuncios.sort(
        key=chave_preco
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

    vendedores = buscar_vendedores(
        seller_ids
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
    Ofertas - {escapar(termo)}
    </title>

    <style>

    body {{
        font-family:Arial;
        background:#f5f5f5;
        margin:0;
        padding:15px;
    }}

    .container {{
        max-width:1000px;
        margin:auto;
    }}

    .top {{
        background:white;
        padding:20px;
        border-radius:12px;
        margin-bottom:15px;
    }}

    .card {{
        background:white;
        padding:18px;
        border-radius:12px;
        margin-bottom:15px;
        box-shadow:
        0 2px 8px rgba(0,0,0,.08);
    }}

    .card img {{
        max-width:220px;
        max-height:220px;
        object-fit:contain;
        display:block;
        margin-bottom:12px;
    }}

    .preco {{
        font-size:28px;
        font-weight:bold;
        color:#008000;
        margin:10px 0;
    }}

    .info {{
        color:#555;
        margin:7px 0;
    }}

    .menor {{
        background:#d4edda;
        color:#155724;
        padding:8px;
        border-radius:7px;
        display:inline-block;
        margin-bottom:10px;
        font-weight:bold;
    }}

    .botao {{
        display:inline-block;
        background:#3483fa;
        color:white;
        padding:13px 20px;
        border-radius:8px;
        text-decoration:none;
        margin-top:10px;
    }}

    .aviso {{
        background:#fff3cd;
        padding:15px;
        border-radius:8px;
    }}

    .paginas {{
        display:flex;
        justify-content:space-between;
        margin:20px 0;
    }}

    .paginas a {{
        background:#3483fa;
        color:white;
        padding:12px 18px;
        border-radius:8px;
        text-decoration:none;
    }}

    </style>

    </head>

    <body>

    <div class="container">

    <div class="top">

    <h1>
    🔎 {escapar(termo)}
    </h1>

    <p>
    📱 Produtos de catálogo encontrados:
    <strong>
    {total_produtos}
    </strong>
    </p>

    <p>
    🛒 Anúncios disponíveis:
    <strong>
    {len(anuncios)}
    </strong>
    </p>

    <p>
    💰 Ordenado do menor para o maior preço
    </p>

    <a href="/">
    ← Nova pesquisa
    </a>

    </div>

    """

    # ========================================================
    # SEM ANÚNCIOS
    # ========================================================

    if not anuncios:

        pagina += """

        <div class="card">

        <h2>
        😕 Nenhum anúncio disponível
        </h2>

        <p>
        Os produtos de catálogo foram encontrados,
        mas não há publicações disponíveis para
        esses produtos neste momento.
        </p>

        </div>

        """

    # ========================================================
    # ANÚNCIOS
    # ========================================================

    for indice, anuncio in enumerate(
        anuncios
    ):

        item_id = anuncio.get(
            "item_id",
            ""
        )

        titulo = anuncio.get(
            "title",
            "Produto"
        )

        preco = anuncio.get(
            "price"
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
            CATEGORY_CELLPHONES
        )

        link = anuncio.get(
            "permalink"
        )

        imagem = anuncio.get(
            "thumbnail"
        )

        if not link:

            link = (
                "https://www.mercadolivre.com.br/"
                + item_id
            )

        pagina += """

        <div class="card">

        """

        if indice == 0:

            pagina += """

            <div class="menor">
            🏆 MENOR PREÇO ENCONTRADO
            </div>

            """

        if imagem:

            pagina += f"""

            <img
            src="{escapar(imagem)}"
            alt="{escapar(titulo)}"
            loading="lazy"
            >

            """

        pagina += f"""

        <h2>
        📱 {escapar(titulo)}
        </h2>

        <div class="preco">
        {formatar_preco(preco)}
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

        <div class="info">
        🆔 Anúncio:
        {escapar(item_id)}
        </div>

        """

        if seller_id:

            pagina += f"""

            <div class="info">
            👤 ID vendedor:
            {escapar(seller_id)}
            </div>

            """

        pagina += f"""

        <a
        class="botao"
        href="{escapar(link)}"
        target="_blank"
        rel="noopener noreferrer"
        >
        🛒 Abrir anúncio
        </a>

        </div>

        """

    # ========================================================
    # PAGINAÇÃO
    # ========================================================

    pagina += """

    <div class="paginas">

    """

    if offset > 0:

        anterior = max(
            0,
            offset - 20
        )

        pagina += f"""

        <a
        href="/buscar?q={escapar(termo)}&offset={anterior}"
        >
        ← Anterior
        </a>

        """

    else:

        pagina += """
        <span></span>
        """

    if offset + 20 < total_produtos:

        proximo = offset + 20

        pagina += f"""

        <a
        href="/buscar?q={escapar(termo)}&offset={proximo}"
        >
        Próximos →
        </a>

        """

    pagina += """

    </div>

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

                "domain_id":
                DOMAIN_CELLPHONES,

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
            params=params
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

    <p>
    O token não é exibido.
    </p>

    {"".join(blocos)}

    <a href="/">
    ← Voltar
    </a>

    </div>

    </body>

    </html>

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
