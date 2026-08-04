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
# CONFIGURAÇÃO DA SESSÃO
# ============================================================

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ============================================================
# FORMATAÇÃO
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


# ============================================================
# HEADERS DA API
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
        return "ML_CLIENT_ID não configurado no Render.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500

    if not REDIRECT_URI:
        return "ML_REDIRECT_URI não configurado no Render.", 500

    # ========================================================
    # CALLBACK OAUTH
    # ========================================================

    if code:

        saved_state = session.get("state")

        if not saved_state:

            return """
            <h2>Erro: sessão expirada.</h2>

            <p>
                Volte para o início e conecte novamente.
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
        # TROCA CODE POR TOKEN
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
                Resposta inválida ao obter token.
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

        # ====================================================
        # SALVA TOKEN
        # ====================================================

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

        session.pop("code_verifier", None)
        session.pop("state", None)

        # ====================================================
        # CONSULTA USUÁRIO
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
                Erro ao consultar Mercado Livre
            </h1>

            <pre>{escapar(e)}</pre>

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
                <strong>
                    {user_response.status_code}
                </strong>
            </p>

            <pre>
{escapar(user_response.text)}
            </pre>

            <a href="/">
                Voltar
            </a>
            """, 400

        try:

            user_data = user_response.json()

        except Exception:

            return """
            <h2>
                Resposta inválida do usuário.
            </h2>

            <a href="/">
                Voltar
            </a>
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
    # URL DE AUTORIZAÇÃO
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
            Conecte sua conta do Mercado Livre.
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
                🔎 Pesquisar produto
            </h2>

            <form
                action="/buscar"
                method="get"
            >

                <input
                    type="text"
                    name="q"
                    placeholder="Ex: iPhone 13, tênis Nike..."
                    required
                >

                <button type="submit">
                    🔎 Pesquisar
                </button>

            </form>

            <a
                class="link"
                href="/diagnostico"
            >
                🧪 Diagnóstico da API
            </a>

        </div>

    </body>

    </html>
    """


# ============================================================
# BUSCA / DOMAIN DISCOVERY
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
            🔐 Conectar Mercado Livre
        </a>
        """, 401

    # ========================================================
    # PREDITOR DE CATEGORIA
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
        <h1>
            ❌ Erro de conexão
        </h1>

        <pre>
{escapar(e)}
        </pre>

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

        resultados = response.json()

    except Exception:

        return """
        <h1>
            ❌ Resposta inválida
        </h1>

        <a href="/">
            Voltar
        </a>
        """, 500

    if not resultados:

        return f"""
        <h1>
            🔎 {escapar(termo)}
        </h1>

        <p>
            Nenhuma categoria encontrada.
        </p>

        <a href="/">
            ← Nova pesquisa
        </a>
        """

    # ========================================================
    # MOSTRA CATEGORIAS
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
            {escapar(termo)}
        </title>

        <style>

            body {{
                font-family:Arial;
                background:#f5f5f5;
                padding:15px;
            }}

            .container {{
                max-width:800px;
                margin:auto;
            }}

            .top {{
                background:white;
                padding:20px;
                border-radius:12px;
                margin-bottom:15px;
            }}

            .resultado {{
                background:white;
                padding:20px;
                margin-bottom:15px;
                border-radius:12px;
                box-shadow:
                    0 2px 8px rgba(0,0,0,.08);
            }}

            .categoria {{
                font-size:20px;
                font-weight:bold;
            }}

            .codigo {{
                color:#666;
                margin-top:8px;
            }}

            .atributo {{
                background:#f5f5f5;
                padding:8px;
                border-radius:6px;
                margin:5px 0;
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
                Categorias encontradas:
                <strong>
                    {len(resultados)}
                </strong>
            </p>

            <a href="/">
                ← Nova pesquisa
            </a>

        </div>
    """

    for resultado in resultados:

        domain_id = resultado.get(
            "domain_id",
            ""
        )

        domain_name = resultado.get(
            "domain_name",
            ""
        )

        category_id = resultado.get(
            "category_id",
            ""
        )

        category_name = resultado.get(
            "category_name",
            ""
        )

        atributos = resultado.get(
            "attributes",
            []
        )

        pagina += f"""

        <div class="resultado">

            <div class="categoria">
                📦 {escapar(domain_name)}
            </div>

            <p>
                📂 Categoria:
                <strong>
                    {escapar(category_name)}
                </strong>
            </p>

            <div class="codigo">
                Domain:
                {escapar(domain_id)}
            </div>

            <div class="codigo">
                Categoria:
                {escapar(category_id)}
            </div>

        """

        if atributos:

            pagina += """
                <hr>

                <strong>
                    🔧 Características detectadas
                </strong>
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

                if valor:

                    pagina += f"""

                    <div class="atributo">

                        {escapar(nome)}:
                        <strong>
                            {escapar(valor)}
                        </strong>

                    </div>

                    """

        pagina += """

        </div>
        """

    pagina += """

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
            "4️⃣ Categorias",
            "https://api.mercadolibre.com/sites/MLB/categories",
            {}
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
{escapar(r.text[:4000])}
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
            Diagnóstico ML
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
