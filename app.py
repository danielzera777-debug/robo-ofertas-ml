from flask import Flask, request, session
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode
import os

app = Flask(__name__)

# =========================================================
# CONFIGURAÇÕES
# =========================================================

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "troque-essa-chave")

CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")

REDIRECT_URI = "https://robo-ofertas-ml.onrender.com/"

# =========================================================
# PÁGINA INICIAL / LOGIN MERCADO LIVRE
# =========================================================

@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    # -----------------------------------------------------
    # VERIFICA CONFIGURAÇÕES
    # -----------------------------------------------------

    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500

    # -----------------------------------------------------
    # RETORNO DO MERCADO LIVRE
    # -----------------------------------------------------

    if code:

        saved_state = session.get("state")

        if state != saved_state:
            return "Erro: state inválido.", 400

        code_verifier = session.get("code_verifier")

        if not code_verifier:
            return "Erro: code_verifier não encontrado.", 400

        # -------------------------------------------------
        # TROCA CODE POR ACCESS TOKEN
        # -------------------------------------------------

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

        if response.status_code != 200:
            return f"""
            <h1>Erro ao obter token</h1>
            <pre>{response.text}</pre>
            """, 400

        token_data = response.json()

        access_token = token_data.get("access_token")

        refresh_token = token_data.get("refresh_token")

        if not access_token:
            return "Erro: Access Token não recebido.", 400

        # -------------------------------------------------
        # TESTA /users/me
        # -------------------------------------------------

        user_response = requests.get(
            "https://api.mercadolibre.com/users/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=30,
        )

        if user_response.status_code != 200:
            return f"""
            <h1>Erro ao consultar conta</h1>
            <pre>{user_response.text}</pre>
            """, 400

        user_data = user_response.json()

        nickname = user_data.get("nickname", "usuário")
        user_id = user_data.get("id", "não informado")

        # -------------------------------------------------
        # GUARDA TOKENS NA SESSÃO
        # -------------------------------------------------

        session["access_token"] = access_token
        session["refresh_token"] = refresh_token
        session["user_id"] = user_id

        return f"""
        <!DOCTYPE html>
        <html>

        <head>
            <meta charset="UTF-8">
            <title>Robô Ofertas ML</title>
        </head>

        <body>

            <h1>✅ Mercado Livre conectado!</h1>

            <p>
                Usuário:
                <strong>{nickname}</strong>
            </p>

            <p>
                ID:
                <strong>{user_id}</strong>
            </p>

            <hr>

            <h2>🔎 Buscar produtos</h2>

            <form action="/buscar" method="get">

                <input
                    type="text"
                    name="q"
                    placeholder="Digite um produto"
                    style="
                        padding:10px;
                        width:250px;
                        font-size:16px;
                    "
                    required
                >

                <button
                    type="submit"
                    style="
                        padding:10px 20px;
                        font-size:16px;
                    "
                >
                    Buscar
                </button>

            </form>

            <br>

            <a href="/teste-produtos">
                🧪 Testar API de produtos
            </a>

        </body>

        </html>
        """

    # -----------------------------------------------------
    # GERA PKCE
    # -----------------------------------------------------

    code_verifier = secrets.token_urlsafe(64)

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(
            code_verifier.encode()
        ).digest()
    ).rstrip(b"=").decode()

    state = secrets.token_urlsafe(32)

    session["code_verifier"] = code_verifier
    session["state"] = state

    # -----------------------------------------------------
    # URL DE AUTORIZAÇÃO
    # -----------------------------------------------------

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
        <title>Robô Ofertas ML</title>
    </head>

    <body>

        <h1>🤖 Robô Ofertas ML</h1>

        <p>
            Conecte sua conta do Mercado Livre:
        </p>

        <a href="{auth_url}">
            <button style="
                padding:15px 25px;
                font-size:18px;
            ">
                Conectar Mercado Livre
            </button>
        </a>

    </body>

    </html>
    """


# =========================================================
# TESTE DA API DE PRODUTOS
# =========================================================

@app.route("/teste-produtos")
def teste_produtos():

    access_token = session.get("access_token")

    if not access_token:
        return """
        <h1>❌ Token não encontrado</h1>
        <p>Faça login no Mercado Livre novamente.</p>
        <a href="/">Voltar</a>
        """, 401

    response = requests.get(
        "https://api.mercadolibre.com/products/search",
        params={
            "q": "Celular",
            "site_id": "MLB",
            "status": "active",
            "limit": 5,
        },
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        timeout=30,
    )

    return f"""
    <!DOCTYPE html>
    <html>

    <head>
        <meta charset="UTF-8">
        <title>Teste Produtos</title>
    </head>

    <body>

        <h1>🧪 Teste /products/search</h1>

        <p>
            <strong>Status da API:</strong>
            {response.status_code}
        </p>

        <pre style="
            white-space:pre-wrap;
            word-wrap:break-word;
        ">{response.text}</pre>

        <hr>

        <a href="/">
            ← Voltar
        </a>

    </body>

    </html>
    """


# =========================================================
# BUSCAR PRODUTOS
# =========================================================

@app.route("/buscar")
def buscar():

    termo = request.args.get("q", "").strip()

    if not termo:
        return "Digite um produto para pesquisar.", 400

    access_token = session.get("access_token")

    if not access_token:
        return """
        <h1>❌ Mercado Livre não conectado</h1>
        <a href="/">Conectar Mercado Livre</a>
        """, 401

    # -----------------------------------------------------
    # NOVA BUSCA DE PRODUTOS
    # -----------------------------------------------------

    response = requests.get(
        "https://api.mercadolibre.com/products/search",
        params={
            "q": termo,
            "site_id": "MLB",
            "status": "active",
            "limit": 10,
        },
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        timeout=30,
    )

    if response.status_code != 200:

        return f"""
        <!DOCTYPE html>
        <html>

        <head>
            <meta charset="UTF-8">
            <title>Erro na busca</title>
        </head>

        <body>

        <h1>❌ Erro na busca</h1>

        <p>
            <strong>Status da API:</strong>
            {response.status_code}
        </p>

        <pre style="
            white-space:pre-wrap;
            word-wrap:break-word;
        ">{response.text}</pre>

        <br>

        <a href="/">
            ← Voltar
        </a>

        </body>
        </html>
        """, response.status_code

    data = response.json()

    produtos = data.get("results", [])

    # -----------------------------------------------------
    # HTML DOS RESULTADOS
    # -----------------------------------------------------

    html = f"""
    <!DOCTYPE html>
    <html>

    <head>
        <meta charset="UTF-8">

        <title>
            Busca - {termo}
        </title>

    </head>

    <body>

    <h1>
        🔎 Resultados para: {termo}
    </h1>

    <a href="/">
        ← Voltar
    </a>

    <hr>
    """

    if not produtos:

        html += """
        <h2>
            Nenhum produto encontrado.
        </h2>
        """

    # -----------------------------------------------------
    # PRODUTOS
    # -----------------------------------------------------

    for produto in produtos:

        produto_id = produto.get(
            "id",
            "N/A"
        )

        titulo = produto.get(
            "name",
            "Sem título"
        )

        imagem = ""

        pictures = produto.get(
            "pictures",
            []
        )

        if pictures:

            imagem = pictures[0].get(
                "url",
                ""
            )

        html += f"""

        <div style="
            border:1px solid #ddd;
            border-radius:10px;
            padding:15px;
            margin:15px 0;
            max-width:600px;
        ">

            <p>
                <strong>ID:</strong>
                {produto_id}
            </p>

        """

        if imagem:

            html += f"""
            <img
                src="{imagem}"
                style="
                    width:180px;
                    height:180px;
                    object-fit:contain;
                "
            >
            """

        html += f"""

            <h3>
                {titulo}
            </h3>

            <p>
                Produto de catálogo
            </p>

        </div>

        """

    html += """
    </body>
    </html>
    """

    return html


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
