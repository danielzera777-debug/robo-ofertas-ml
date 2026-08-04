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

# ============================================================
# CONFIGURAÇÃO DE SESSÃO
# ============================================================

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ============================================================
# CONFIGURAÇÕES DO MERCADO LIVRE
# ============================================================

SITE_ID = "MLB"

# Domínio de celulares
DOMAIN_CELLPHONES = "MLB-CELLPHONES"

# Categoria de celulares e smartphones
CATEGORY_CELLPHONES = "MLB1055"

API_BASE = "https://api.mercadolibre.com"

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def escapar(valor):
    return html.escape(str(valor or ""))


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
        "User-Agent": "Robo-Ofertas-ML/1.0",
    }

    token = session.get("access_token")

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
# OAUTH
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

        saved_state = session.get("state")

        if not saved_state:

            return """
            <h2>❌ Sessão expirada.</h2>

            <p>
                Volte para o início e conecte novamente
                sua conta do Mercado Livre.
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

            <a href="/">
                ← Voltar
            </a>
            """, 400

        # ====================================================
        # TROCA CODE POR TOKEN
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
                        code_verifier,
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
                <strong>
                    {response.status_code}
                </strong>
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
                ❌ Resposta inválida do Mercado Livre.
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

        session["access_token"] = access_token

        session["refresh_token"] = (
            token_data.get("refresh_token")
        )

        session["expires_in"] = (
            token_data.get("expires_in")
        )

        session["token_type"] = (
            token_data.get("token_type")
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
        # CONSULTA USUÁRIO
        # ====================================================

        user_response = requisicao_get(
            f"{API_BASE}/users/me"
        )

        if user_response is None:

            return """
            <h1>
                ❌ Erro ao consultar usuário
            </h1>
            """, 500

        if user_response.status_code != 200:

            return f"""
            <h1>
                ❌ Erro ao consultar conta
            </h1>

            <p>
                Status:
                {user_response.status_code}
            </p>

            <pre>
{escapar(user_response.text)}
            </pre>

            <a href="/">
                ← Voltar
            </a>
            """, 400

        user_data = user_response.json()

        nickname = user_data.get(
            "nickname",
            "usuário"
        )

        user_id = user_data.get(
            "id",
            "não informado"
        )

        session["user_id"] = user_id

        return pagina_principal(
            nickname,
            user_id
        )

    # ========================================================
    # PKCE
    # ========================================================

    code_verifier = secrets.token_urlsafe(64)

    code_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(
                code_verifier.encode()
            ).digest()
        )
        .rstrip(b"=")
        .decode()
    )

    state = secrets.token_urlsafe(32)

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
            "S256",
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
                cursor:pointer;
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
                cursor:pointer;
            }}

            .diagnostico {{
                display:block;
                margin-top:20px;
                text-decoration:none;
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
            🔎 Procurar produto
        </h2>

        <form
            action="/buscar"
            method="get"
        >

            <input
                type="text"
                name="q"
                placeholder="Ex: iPhone 13, Samsung S23..."
                required
            >

            <button type="submit">
                🔎 Buscar celulares
            </button>

        </form>

        <a
            class="diagnostico"
            href="/diagnostico"
        >
            🧪 Diagnóstico da API
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
            limit,
    }

    return requisicao_get(
        url,
        params=params
    )


# ============================================================
# PUBLICAÇÕES ASSOCIADAS AO PRODUTO
# ============================================================

def buscar_publicacoes_catalogo(
    product_id,
    offset=0,
    limit=100
):

    url = (
        f"{API_BASE}/products/"
        f"{product_id}/items"
    )

    params = {

        "offset":
            offset,

        "limit":
            limit,
    }

    return requisicao_get(
        url,
        params=params
    )


# ============================================================
# DETALHE DO PRODUTO
# ============================================================

def buscar_detalhe_produto(
    product_id
):

    url = (
        f"{API_BASE}/products/"
        f"{product_id}"
    )

    return requisicao_get(
        url
    )


# ============================================================
# BUSCA
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
    # BUSCA CATÁLOGO
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

        <p>
            Não foi possível conectar ao Mercado Livre.
        </p>

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
            🧪 Abrir diagnóstico
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
            ❌ JSON inválido
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

    total = paging.get(
        "total",
        0
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
            Busca - {escapar(termo)}
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

            .produto {{
                background:white;
                padding:18px;
                border-radius:12px;
                margin-bottom:15px;
                box-shadow:
                    0 2px 8px rgba(0,0,0,.08);
            }}

            .produto img {{
                max-width:220px;
                max-height:220px;
                object-fit:contain;
                display:block;
                margin-bottom:10px;
            }}

            .preco {{
                font-size:25px;
                font-weight:bold;
                color:#008000;
                margin:10px 0;
            }}

            .info {{
                color:#555;
                margin:7px 0;
            }}

            .anuncio {{
                border-top:1px solid #ddd;
                margin-top:15px;
                padding-top:15px;
            }}

            .botao {{
                display:inline-block;
                background:#3483fa;
                color:white;
                padding:12px 18px;
                border-radius:8px;
                text-decoration:none;
                margin-top:10px;
            }}

            .aviso {{
                background:#fff3cd;
                padding:12px;
                border-radius:8px;
                margin-top:10px;
            }}

            .erro {{
                background:#f8d7da;
                padding:12px;
                border-radius:8px;
                margin-top:10px;
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
                Produtos encontrados:
                <strong>
                    {total}
                </strong>
            </p>

            <p>
                📱 Categoria:
                <strong>
                    Celulares e Smartphones
                </strong>
            </p>

            <a href="/">
                ← Nova pesquisa
            </a>

        </div>
    """

    # ========================================================
    # NENHUM PRODUTO
    # ========================================================

    if not produtos:

        pagina += """

        <div class="produto">

            <h2>
                😕 Nenhum celular encontrado
            </h2>

            <p>
                Tente pesquisar pelo modelo completo.
            </p>

            <p>
                Exemplos:
            </p>

            <ul>
                <li>Apple iPhone 13 128GB</li>
                <li>Samsung Galaxy S23 128GB</li>
                <li>Motorola Moto G84 256GB</li>
            </ul>

        </div>

        """

    # ========================================================
    # PRODUTOS
    # ========================================================

    for produto in produtos:

        product_id = produto.get(
            "id",
            ""
        )

        domain_id = produto.get(
            "domain_id",
            ""
        )

        nome = produto.get(
            "name",
            "Produto sem nome"
        )

        # ----------------------------------------------------
        # FILTRO EXTRA
        # ----------------------------------------------------

        if domain_id != DOMAIN_CELLPHONES:

            continue

        # ----------------------------------------------------
        # IMAGEM
        # ----------------------------------------------------

        imagem = ""

        pictures = produto.get(
            "pictures",
            []
        )

        if pictures:

            primeira = pictures[0]

            imagem = primeira.get(
                "url",
                ""
            )

        # ----------------------------------------------------
        # ATRIBUTOS
        # ----------------------------------------------------

        atributos = produto.get(
            "attributes",
            []
        )

        marca = ""
        modelo = ""
        memoria = ""
        ram = ""
        cor = ""

        for atributo in atributos:

            aid = atributo.get(
                "id",
                ""
            )

            valor = atributo.get(
                "value_name",
                ""
            )

            if aid == "BRAND":
                marca = valor

            elif aid == "MODEL":
                modelo = valor

            elif aid in (
                "INTERNAL_MEMORY",
                "CAPACITY"
            ):
                memoria = valor

            elif aid in (
                "RAM",
                "RAM_MEMORY"
            ):
                ram = valor

            elif aid in (
                "COLOR",
                "MAIN_COLOR"
            ):
                cor = valor

        # ====================================================
        # PUBLICAÇÕES
        # ====================================================

        itens_response = (
            buscar_publicacoes_catalogo(
                product_id,
                0,
                100
            )
        )

        itens = []

        erro_itens = None

        if itens_response is None:

            erro_itens = (
                "Falha de conexão."
            )

        elif itens_response.status_code == 200:

            try:

                itens_data = (
                    itens_response.json()
                )

                itens = itens_data.get(
                    "results",
                    []
                )

            except Exception:

                erro_itens = (
                    "Resposta inválida."
                )

        else:

            erro_itens = (
                f"HTTP {itens_response.status_code}: "
                f"{itens_response.text}"
            )

        # ====================================================
        # CARD DO PRODUTO
        # ====================================================

        pagina += f"""

        <div class="produto">

        """

        if imagem:

            pagina += f"""

            <img
                src="{escapar(imagem)}"
                alt="{escapar(nome)}"
                loading="lazy"
            >

            """

        pagina += f"""

            <h2>
                📱 {escapar(nome)}
            </h2>

            <div class="info">
                🆔 Produto:
                <strong>
                    {escapar(product_id)}
                </strong>
            </div>

            <div class="info">
                📂 Domínio:
                {escapar(domain_id)}
            </div>

        """

        if marca:

            pagina += f"""

            <div class="info">
                🏷️ Marca:
                {escapar(marca)}
            </div>

            """

        if modelo:

            pagina += f"""

            <div class="info">
                📱 Modelo:
                {escapar(modelo)}
            </div>

            """

        if memoria:

            pagina += f"""

            <div class="info">
                💾 Memória:
                {escapar(memoria)}
            </div>

            """

        if ram:

            pagina += f"""

            <div class="info">
                🧠 RAM:
                {escapar(ram)}
            </div>

            """

        if cor:

            pagina += f"""

            <div class="info">
                🎨 Cor:
                {escapar(cor)}
            </div>

            """

        # ====================================================
        # ANÚNCIOS
        # ====================================================

        if erro_itens:

            pagina += f"""

            <div class="erro">

                ❌ Não foi possível consultar
                as publicações deste produto.

                <br><br>

                <small>
                    {escapar(erro_itens)}
                </small>

            </div>

            """

        elif not itens:

            pagina += """

            <div class="aviso">

                ℹ️ Este produto de catálogo
                não possui publicações associadas
                disponíveis para esta consulta.

            </div>

            """

        else:

            pagina += f"""

            <h3>
                🛒 {len(itens)}
                publicação(ões) encontrada(s)
            </h3>

            """

            for item in itens:

                item_id = item.get(
                    "item_id",
                    ""
                )

                seller_id = item.get(
                    "seller_id",
                    ""
                )

                preco = item.get(
                    "price"
                )

                moeda = item.get(
                    "currency_id",
                    "BRL"
                )

                condicao = item.get(
                    "condition",
                    "Não informado"
                )

                categoria = item.get(
                    "category_id",
                    CATEGORY_CELLPHONES
                )

                # --------------------------------------------
                # LINK
                # --------------------------------------------

                link = (
                    "https://www.mercadolivre.com.br/"
                    f"MLB-{item_id.replace('MLB', '')}"
                )

                pagina += f"""

                <div class="anuncio">

                    <h3>
                        🛒 Anúncio {escapar(item_id)}
                    </h3>

                    <div class="preco">
                        {formatar_preco(preco)}
                    </div>

                    <div class="info">
                        👤 Vendedor:
                        {escapar(seller_id)}
                    </div>

                    <div class="info">
                        🏷️ Condição:
                        {escapar(condicao)}
                    </div>

                    <div class="info">
                        📂 Categoria:
                        {escapar(categoria)}
                    </div>

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

        pagina += """

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

    if offset + 20 < total:

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
            "2️⃣ Busca antiga",

            f"{API_BASE}/sites/MLB/search",

            {
                "q":
                    "celular",

                "limit":
                    5
            }
        ),

        (
            "3️⃣ Domain Discovery",

            f"{API_BASE}/sites/MLB/domain_discovery/search",

            {
                "q":
                    "celular",

                "limit":
                    5
            }
        ),

        (
            "4️⃣ Busca de produtos",

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
            "5️⃣ Produto MLB74766111",

            f"{API_BASE}/products/MLB74766111",

            None
        ),

        (
            "6️⃣ Publicações MLB74766111",

            f"{API_BASE}/products/MLB74766111/items",

            {
                "offset":
                    0,

                "limit":
                    100
            }
        ),

    ]

    blocos = []

    for nome, url, params in testes:

        try:

            r = requisicao_get(
                url,
                params=params
            )

            if r is None:

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

            texto = r.text

            if len(texto) > 8000:

                texto = texto[:8000] + (
                    "\n\n... resposta cortada ..."
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
                        {r.status_code}
                    </strong>
                </p>

                <pre>
{escapar(texto)}
                </pre>

            </div>

            """)

        except Exception as erro:

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

                <pre>
{escapar(erro)}
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
            O token nunca é exibido nesta página.
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
        A sessão foi encerrada.
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
