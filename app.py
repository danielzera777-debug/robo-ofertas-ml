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
# SESSÃO
# ============================================================

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ============================================================
# FUNÇÕES
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


# ============================================================
# OAUTH
# ============================================================

@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500

    if not REDIRECT_URI:
        return "ML_REDIRECT_URI não configurado no Render.", 500

    # ========================================================
    # CALLBACK
    # ========================================================

    if code:

        saved_state = session.get("state")

        if not saved_state:

            return """
            <h2>Erro: sessão expirada.</h2>

            <p>
                Volte e conecte novamente sua conta.
            </p>

            <a href="/">
                Voltar
            </a>
            """, 400

        if state != saved_state:

            return """
            <h2>Erro: state inválido.</h2>

            <a href="/">
                Voltar
            </a>
            """, 400

        code_verifier = session.get(
            "code_verifier"
        )

        if not code_verifier:

            return """
            <h2>
                Erro: code_verifier não encontrado.
            </h2>

            <a href="/">
                Voltar
            </a>
            """, 400

        # ====================================================
        # TOKEN
        # ====================================================

        try:

            response = requests.post(

                "https://api.mercadolibre.com/oauth/token",

                data={
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "code_verifier": code_verifier,
                },

                timeout=30,
            )

        except requests.RequestException as e:

            return f"""
            <h1>Erro de conexão</h1>

            <pre>{escapar(e)}</pre>

            <a href="/">
                Voltar
            </a>
            """, 500

        if response.status_code != 200:

            return f"""
            <h1>Erro ao obter token</h1>

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
                Voltar
            </a>
            """, 400

        try:

            token_data = response.json()

        except Exception:

            return """
            <h2>
                Resposta inválida do Mercado Livre.
            </h2>

            <a href="/">
                Voltar
            </a>
            """, 400

        access_token = token_data.get(
            "access_token"
        )

        if not access_token:

            return """
            <h2>
                Access Token não recebido.
            </h2>

            <a href="/">
                Voltar
            </a>
            """, 400

        session["access_token"] = access_token

        session["refresh_token"] = token_data.get(
            "refresh_token"
        )

        session["expires_in"] = token_data.get(
            "expires_in"
        )

        session["token_type"] = token_data.get(
            "token_type"
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

        try:

            user_response = requests.get(

                "https://api.mercadolibre.com/users/me",

                headers=headers_api(),

                timeout=30,
            )

        except requests.RequestException as e:

            return f"""
            <h1>
                Erro ao consultar usuário
            </h1>

            <pre>
{escapar(e)}
            </pre>

            <a href="/">
                Voltar
            </a>
            """, 500

        if user_response.status_code != 200:

            return f"""
            <h1>
                Erro ao consultar conta
            </h1>

            <p>
                Status:
                {user_response.status_code}
            </p>

            <pre>
{escapar(user_response.text)}
            </pre>

            <a href="/">
                Voltar
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

    session["code_verifier"] = code_verifier
    session["state"] = state

    params = {

        "response_type": "code",

        "client_id": CLIENT_ID,

        "redirect_uri": REDIRECT_URI,

        "state": state,

        "code_challenge": code_challenge,

        "code_challenge_method": "S256",
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
            content="width=device-width, initial-scale=1.0"
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
            content="width=device-width, initial-scale=1.0"
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
                padding:14px;
                font-size:17px;
                border:1px solid #ccc;
                border-radius:8px;
                margin-bottom:10px;
            }}

            button {{
                width:100%;
                padding:14px;
                font-size:17px;
                border:0;
                border-radius:8px;
                background:#3483fa;
                color:white;
            }}

            .link {{
                display:block;
                margin-top:20px;
                color:#3483fa;
                text-decoration:none;
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
                🔎 Buscar produtos
            </h2>

            <form
                action="/buscar"
                method="get"
            >

                <input
                    type="text"
                    name="q"
                    placeholder="Ex: celular, iPhone 13, Samsung..."
                    required
                >

                <button type="submit">
                    🔎 Buscar
                </button>

            </form>

            <a
                class="link"
                href="/diagnostico"
            >
                🧪 Diagnóstico
            </a>

        </div>

    </body>

    </html>
    """


# ============================================================
# BUSCA DE PRODUTOS DE CATÁLOGO
# ============================================================

def buscar_produtos_catalogo(
    termo,
    offset=0,
    limit=10
):

    url = (
        "https://api.mercadolibre.com/"
        "products/search"
    )

    params = {

        "status": "active",

        "site_id": "MLB",

        "q": termo,

        "offset": offset,

        "limit": limit,
    }

    try:

        response = requests.get(

            url,

            params=params,

            headers=headers_api(),

            timeout=30,
        )

        return response

    except requests.RequestException:

        return None


# ============================================================
# BUSCAR ANÚNCIOS DE UM PRODUTO DE CATÁLOGO
# ============================================================

def buscar_itens_produto(
    product_id,
    offset=0,
    limit=20
):

    url = (
        "https://api.mercadolibre.com/"
        f"products/{product_id}/items"
    )

    params = {

        "offset": offset,

        "limit": limit,
    }

    try:

        response = requests.get(

            url,

            params=params,

            headers=headers_api(),

            timeout=30,
        )

        return response

    except requests.RequestException:

        return None


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
            Digite um produto.
        </h2>

        <a href="/">
            Voltar
        </a>
        """, 400

    if not session.get("access_token"):

        return """
        <h1>
            ❌ Mercado Livre não conectado
        </h1>

        <a href="/">
            🔐 Conectar
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
    # PRODUTOS DE CATÁLOGO
    # ========================================================

    response = buscar_produtos_catalogo(
        termo,
        offset,
        10
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
            Voltar
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

        <a href="/">
            Voltar
        </a>
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
    # HTML
    # ========================================================

    pagina = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
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
                margin-bottom:15px;
                border-radius:12px;
                box-shadow:
                    0 2px 8px rgba(0,0,0,.08);
            }}

            .produto h2 {{
                margin-top:0;
            }}

            .anuncio {{
                border-top:1px solid #ddd;
                margin-top:15px;
                padding-top:15px;
            }}

            .preco {{
                font-size:24px;
                font-weight:bold;
                color:#008000;
                margin:8px 0;
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

            .info {{
                color:#555;
                margin:6px 0;
            }}

            .sem-anuncios {{
                background:#fff7d6;
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
                Produtos de catálogo encontrados:
                <strong>
                    {total_produtos}
                </strong>
            </p>

            <p>
                📦 Agora procurando as publicações
                disponíveis em cada produto.
            </p>

            <a href="/">
                ← Nova pesquisa
            </a>

        </div>
    """

    if not produtos:

        pagina += """

        <div class="produto">

            <h2>
                Nenhum produto encontrado.
            </h2>

            <p>
                Tente pesquisar por um modelo específico,
                por exemplo:
            </p>

            <ul>
                <li>iPhone 13</li>
                <li>Samsung Galaxy S23</li>
                <li>Motorola G84</li>
            </ul>

        </div>

        """

    # ========================================================
    # CADA PRODUTO
    # ========================================================

    for produto in produtos:

        product_id = produto.get(
            "id",
            ""
        )

        nome = produto.get(
            "name",
            "Produto sem nome"
        )

        permalink = produto.get(
            "permalink",
            ""
        )

        domain_id = produto.get(
            "domain_id",
            ""
        )

        # ====================================================
        # BUSCA ANÚNCIOS
        # ====================================================

        itens_response = buscar_itens_produto(
            product_id,
            0,
            20
        )

        itens = []

        if (
            itens_response
            and itens_response.status_code == 200
        ):

            try:

                itens_data = itens_response.json()

                itens = itens_data.get(
                    "results",
                    []
                )

            except Exception:

                itens = []

        pagina += f"""

        <div class="produto">

            <h2>
                📱 {escapar(nome)}
            </h2>

            <div class="info">
                🆔 Produto:
                {escapar(product_id)}
            </div>

            <div class="info">
                📂 Domínio:
                {escapar(domain_id)}
            </div>

        """

        # ====================================================
        # ANÚNCIOS
        # ====================================================

        if not itens:

            pagina += """

            <div class="sem-anuncios">

                ℹ️ Nenhuma publicação encontrada
                para este produto.

            </div>

            """

        else:

            pagina += f"""

            <h3>
                🛒 {len(itens)} anúncios encontrados
            </h3>

            """

            for anuncio in itens:

                item_id = anuncio.get(
                    "item_id",
                    ""
                )

                preco = anuncio.get(
                    "price"
                )

                moeda = anuncio.get(
                    "currency_id",
                    "BRL"
                )

                vendedor = anuncio.get(
                    "seller_id",
                    ""
                )

                condicao = anuncio.get(
                    "condition",
                    "não informado"
                )

                categoria = anuncio.get(
                    "category_id",
                    ""
                )

                link = (
                    "https://www.mercadolivre.com.br/"
                    "p/"
                    + product_id
                )

                pagina += f"""

                <div class="anuncio">

                    <h3>
                        🛒 {escapar(item_id)}
                    </h3>

                    <div class="preco">
                        {formatar_preco(preco)}
                    </div>

                    <div class="info">
                        💰 Moeda:
                        {escapar(moeda)}
                    </div>

                    <div class="info">
                        👤 Vendedor:
                        {escapar(vendedor)}
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
                        🛒 Ver produto
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
            offset - 10
        )

        pagina += f"""

        <a href="/buscar?q={escapar(termo)}&offset={anterior}">
            ← Anterior
        </a>

        """

    else:

        pagina += "<span></span>"

    if offset + 10 < total_produtos:

        proximo = offset + 10

        pagina += f"""

        <a href="/buscar?q={escapar(termo)}&offset={proximo}">
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

    if not session.get("access_token"):

        return """
        <h1>
            ❌ Conta não conectada
        </h1>

        <a href="/">
            Voltar
        </a>
        """, 401

    testes = [

        (
            "1️⃣ Usuário",

            "https://api.mercadolibre.com/users/me",

            {}
        ),

        (
            "2️⃣ Busca antiga",

            "https://api.mercadolibre.com/sites/MLB/search",

            {
                "q": "celular",
                "limit": 5
            }
        ),

        (
            "3️⃣ Domain Discovery",

            "https://api.mercadolibre.com/sites/MLB/domain_discovery/search",

            {
                "q": "celular",
                "limit": 5
            }
        ),

        (
            "4️⃣ Busca de produtos",

            "https://api.mercadolibre.com/products/search",

            {
                "status": "active",
                "site_id": "MLB",
                "q": "celular",
                "limit": 5
            }
        ),

    ]

    blocos = []

    for nome, url, params in testes:

        try:

            r = requests.get(

                url,

                params=params,

                headers=headers_api(),

                timeout=30,
            )

            blocos.append(f"""

            <div style="
                background:#f8f8f8;
                padding:15px;
                margin-bottom:15px;
                border-radius:10px;
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
{escapar(r.text[:6000])}
                </pre>

            </div>

            """)

        except Exception as e:

            blocos.append(f"""

            <div>

                <h2>
                    {escapar(nome)}
                </h2>

                <pre>
{escapar(e)}
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
            content="width=device-width, initial-scale=1.0"
        >

        <title>
            Diagnóstico Mercado Livre
        </title>

    </head>

    <body style="
        font-family:Arial;
        background:#f5f5f5;
        padding:20px;
    ">

    <div style="
        max-width:900px;
        margin:auto;
        background:white;
        padding:20px;
        border-radius:12px;
    ">

        <h1>
            🧪 Diagnóstico Mercado Livre
        </h1>

        <p>
            O Access Token não é exibido.
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
# CONFIGURAÇÃO
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
