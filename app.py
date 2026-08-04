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
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

app.secret_key = SECRET_KEY

# ============================================================
# SESSÃO
# ============================================================

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ============================================================
# FORMATAÇÃO
# ============================================================

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


def escapar(valor):

    return html.escape(str(valor or ""))


# ============================================================
# HEADERS
# ============================================================

def headers_api():

    headers = {
        "Accept": "application/json",
        "User-Agent": "Robo-Ofertas-ML/1.0",
    }

    access_token = session.get("access_token")

    if access_token:

        headers["Authorization"] = (
            f"Bearer {access_token}"
        )

    return headers


# ============================================================
# PÁGINA INICIAL
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
            <h2>Erro: sessão expirada.</h2>
            <p>Volte e conecte novamente sua conta.</p>
            <a href="/">Voltar</a>
            """, 400

        if state != saved_state:

            return """
            <h2>Erro: state inválido.</h2>
            <a href="/">Voltar</a>
            """, 400

        code_verifier = session.get(
            "code_verifier"
        )

        if not code_verifier:

            return """
            <h2>Erro: code_verifier não encontrado.</h2>
            <a href="/">Voltar</a>
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
            <a href="/">Voltar</a>
            """, 500

        if response.status_code != 200:

            return f"""
            <h1>Erro ao obter token</h1>

            <p>
                Status:
                <strong>{response.status_code}</strong>
            </p>

            <pre>{escapar(response.text)}</pre>

            <a href="/">Voltar</a>
            """, 400

        try:

            token_data = response.json()

        except Exception:

            return """
            <h2>Resposta inválida ao obter token.</h2>
            <a href="/">Voltar</a>
            """, 400

        access_token = token_data.get(
            "access_token"
        )

        if not access_token:

            return """
            <h2>Access Token não recebido.</h2>
            <a href="/">Voltar</a>
            """, 400

        # ====================================================
        # SALVAR SESSÃO
        # ====================================================

        session["access_token"] = access_token

        session["token_type"] = token_data.get(
            "token_type"
        )

        session["expires_in"] = token_data.get(
            "expires_in"
        )

        session["refresh_token"] = token_data.get(
            "refresh_token"
        )

        session.pop("code_verifier", None)
        session.pop("state", None)

        # ====================================================
        # TESTAR USUÁRIO
        # ====================================================

        try:

            user_response = requests.get(

                "https://api.mercadolibre.com/users/me",

                headers={
                    "Authorization":
                        f"Bearer {access_token}",

                    "Accept":
                        "application/json",

                    "User-Agent":
                        "Robo-Ofertas-ML/1.0",
                },

                timeout=30,
            )

        except requests.RequestException as e:

            return f"""
            <h1>Erro de conexão com Mercado Livre</h1>

            <pre>{escapar(e)}</pre>

            <a href="/">Voltar</a>
            """, 500

        if user_response.status_code != 200:

            return f"""
            <h1>Erro ao consultar conta</h1>

            <p>
                Status:
                <strong>{user_response.status_code}</strong>
            </p>

            <pre>{escapar(user_response.text)}</pre>

            <a href="/">Voltar</a>
            """, 400

        try:

            user_data = user_response.json()

        except Exception:

            return """
            <h2>Resposta inválida do usuário.</h2>
            <a href="/">Voltar</a>
            """, 400

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

    # ========================================================
    # AUTORIZAÇÃO
    # ========================================================

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

        <title>Robô Ofertas ML</title>

    </head>

    <body style="
        font-family:Arial;
        background:#f5f5f5;
        padding:30px;
        text-align:center;
    ">

        <h1>🤖 Robô Ofertas ML</h1>

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

def pagina_principal(nickname, user_id):

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>Robô Ofertas ML</title>

        <style>

            body {{
                font-family: Arial;
                background: #f5f5f5;
                margin: 0;
                padding: 20px;
            }}

            .container {{
                max-width: 700px;
                margin: auto;
                background: white;
                padding: 25px;
                border-radius: 15px;
            }}

            input {{
                width: 100%;
                box-sizing: border-box;
                padding: 14px;
                font-size: 17px;
                border: 1px solid #ccc;
                border-radius: 8px;
                margin-bottom: 10px;
            }}

            button {{
                width: 100%;
                padding: 14px;
                font-size: 17px;
                border: 0;
                border-radius: 8px;
                background: #3483fa;
                color: white;
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

            <h1>🤖 Robô Ofertas ML</h1>

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

            <h2>🔎 Buscar produtos</h2>

            <form action="/buscar" method="get">

                <input
                    type="text"
                    name="q"
                    placeholder="Ex: celular, tênis, relógio..."
                    required
                >

                <button type="submit">
                    🔎 Buscar produtos
                </button>

            </form>

            <a
                class="link"
                href="/teste-api"
            >
                🧪 Testar API
            </a>

            <a
                class="link"
                href="/diagnostico"
            >
                🔧 Diagnóstico completo
            </a>

        </div>

    </body>

    </html>
    """


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
        <h2>Digite um produto para pesquisar.</h2>
        <a href="/">Voltar</a>
        """, 400

    access_token = session.get(
        "access_token"
    )

    if not access_token:

        return """
        <h1>❌ Mercado Livre não conectado</h1>

        <p>
            Conecte sua conta antes de pesquisar.
        </p>

        <a href="/">
            🔐 Conectar
        </a>
        """, 401

    # ========================================================
    # DOMAIN DISCOVERY
    # ========================================================

    url = (
        "https://api.mercadolibre.com/"
        "sites/MLB/domain_discovery/search"
    )

    try:

        response = requests.get(

            url,

            params={
                "q": termo,
                "limit": 8,
            },

            headers=headers_api(),

            timeout=30,
        )

    except requests.RequestException as e:

        return f"""
        <h1>❌ Erro de conexão</h1>

        <pre>{escapar(e)}</pre>

        <a href="/">Voltar</a>
        """, 500

    if response.status_code != 200:

        return f"""
        <h1>❌ Erro na busca</h1>

        <p>
            Status da API:
            <strong>{response.status_code}</strong>
        </p>

        <pre>{escapar(response.text)}</pre>

        <hr>

        <a href="/teste-api">
            🧪 Testar outros endpoints
        </a>

        <br><br>

        <a href="/diagnostico">
            🔧 Diagnóstico
        </a>

        <br><br>

        <a href="/">
            ← Voltar
        </a>
        """, response.status_code

    try:

        dados = response.json()

    except Exception:

        return """
        <h1>❌ Resposta inválida</h1>
        <a href="/">Voltar</a>
        """, 500

    # ========================================================
    # MOSTRAR RESULTADO DO DOMAIN DISCOVERY
    # ========================================================

    html_page = f"""
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
                padding:15px;
            }}

            .container {{
                max-width:900px;
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
                padding:20px;
                margin-bottom:15px;
                border-radius:12px;
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

            .codigo {{
                color:#555;
                font-size:14px;
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
                Resultados encontrados:
                <strong>{len(dados)}</strong>
            </p>

            <a href="/">
                ← Nova pesquisa
            </a>

        </div>
    """

    if not dados:

        html_page += """
        <div class="produto">

            <h2>
                Nenhum resultado encontrado.
            </h2>

            <p>
                Tente outro nome de produto.
            </p>

        </div>
        """

    for item in dados:

        domain_id = item.get(
            "domain_id",
            ""
        )

        domain_name = item.get(
            "domain_name",
            "Não informado"
        )

        category_id = item.get(
            "category_id",
            ""
        )

        category_name = item.get(
            "category_name",
            "Não informado"
        )

        atributos = item.get(
            "attributes",
            []
        )

        html_page += f"""

        <div class="produto">

            <h2>
                {escapar(domain_name)}
            </h2>

            <p>
                📂 Categoria:
                <strong>
                    {escapar(category_name)}
                </strong>
            </p>

            <p class="codigo">
                Domain:
                {escapar(domain_id)}
            </p>

            <p class="codigo">
                Categoria:
                {escapar(category_id)}
            </p>

        """

        if atributos:

            html_page += """
            <h3>Características</h3>
            <ul>
            """

            for atributo in atributos:

                nome = atributo.get(
                    "id",
                    ""
                )

                valor = atributo.get(
                    "value_name",
                    ""
                )

                html_page += f"""
                <li>
                    {escapar(nome)}:
                    {escapar(valor)}
                </li>
                """

            html_page += """
            </ul>
            """

        html_page += """
        </div>
        """

    html_page += """

    </div>

    </body>

    </html>
    """

    return html_page


# ============================================================
# TESTE DOS ENDPOINTS
# ============================================================

@app.route("/teste-api")
def teste_api():

    endpoints = [

        (
            "1️⃣ Busca /sites/MLB/search",
            "https://api.mercadolibre.com/sites/MLB/search",
            {
                "q": "celular",
                "limit": 5
            }
        ),

        (
            "2️⃣ Domain Discovery",
            "https://api.mercadolibre.com/sites/MLB/domain_discovery/search",
            {
                "q": "celular",
                "limit": 5
            }
        ),

        (
            "3️⃣ Categorias",
            "https://api.mercadolibre.com/sites/MLB/categories",
            {}
        ),

    ]

    resultado = []

    for nome, url, params in endpoints:

        try:

            response = requests.get(

                url,

                params=params,

                headers=headers_api(),

                timeout=30,
            )

            resultado.append(f"""

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
                        {response.status_code}
                    </strong>
                </p>

                <pre>
{escapar(response.text[:3000])}
                </pre>

            </div>

            """)

        except Exception as e:

            resultado.append(f"""

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

        <title>Teste API</title>

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
            🧪 Teste da API Mercado Livre
        </h1>

        <p>
            A página testa os endpoints usando a conta conectada.
        </p>

        {"".join(resultado)}

        <a href="/">
            ← Voltar
        </a>

    </div>

    </body>

    </html>

    """


# ============================================================
# DIAGNÓSTICO COMPLETO
# ============================================================

@app.route("/diagnostico")
def diagnostico():

    access_token = session.get(
        "access_token"
    )

    if not access_token:

        return """
        <h1>❌ Sem Access Token</h1>

        <p>
            Conecte sua conta primeiro.
        </p>

        <a href="/">
            Voltar
        </a>
        """, 401

    resultado = []

    # ========================================================
    # USERS/ME
    # ========================================================

    try:

        r_user = requests.get(

            "https://api.mercadolibre.com/users/me",

            headers=headers_api(),

            timeout=30,
        )

        resultado.append(f"""

        <div style="
            background:#f8f8f8;
            padding:15px;
            margin-bottom:15px;
            border-radius:10px;
        ">

            <h2>
                1️⃣ /users/me
            </h2>

            <p>
                Status:
                <strong>
                    {r_user.status_code}
                </strong>
            </p>

            <pre>
{escapar(r_user.text[:5000])}
            </pre>

        </div>

        """)

    except Exception as e:

        resultado.append(f"""

        <h2>
            1️⃣ /users/me
        </h2>

        <pre>
{escapar(e)}
        </pre>

        """)

    # ========================================================
    # SEARCH
    # ========================================================

    try:

        r_search = requests.get(

            "https://api.mercadolibre.com/sites/MLB/search",

            params={
                "q": "celular",
                "limit": 5
            },

            headers=headers_api(),

            timeout=30,
        )

        resultado.append(f"""

        <div style="
            background:#f8f8f8;
            padding:15px;
            margin-bottom:15px;
            border-radius:10px;
        ">

            <h2>
                2️⃣ /sites/MLB/search
            </h2>

            <p>
                Status:
                <strong>
                    {r_search.status_code}
                </strong>
            </p>

            <pre>
{escapar(r_search.text[:5000])}
            </pre>

        </div>

        """)

    except Exception as e:

        resultado.append(f"""

        <h2>
            2️⃣ /sites/MLB/search
        </h2>

        <pre>
{escapar(e)}
        </pre>

        """)

    # ========================================================
    # DOMAIN DISCOVERY
    # ========================================================

    try:

        r_domain = requests.get(

            "https://api.mercadolibre.com/sites/MLB/domain_discovery/search",

            params={
                "q": "celular",
                "limit": 5
            },

            headers=headers_api(),

            timeout=30,
        )

        resultado.append(f"""

        <div style="
            background:#f8f8f8;
            padding:15px;
            margin-bottom:15px;
            border-radius:10px;
        ">

            <h2>
                3️⃣ /domain_discovery/search
            </h2>

            <p>
                Status:
                <strong>
                    {r_domain.status_code}
                </strong>
            </p>

            <pre>
{escapar(r_domain.text[:5000])}
            </pre>

        </div>

        """)

    except Exception as e:

        resultado.append(f"""

        <h2>
            3️⃣ /domain_discovery/search
        </h2>

        <pre>
{escapar(e)}
        </pre>

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

        <title>Diagnóstico ML</title>

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
            O Access Token não é mostrado nesta página.
        </p>

        {"".join(resultado)}

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
