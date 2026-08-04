from flask import Flask, request, session
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode
import os

app = Flask(__name__)

# Chave usada para proteger a sessão
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "chave-temporaria-altere-no-render"
)

# Credenciais do Mercado Livre
CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")

# IMPORTANTE:
# Esta URL precisa ser exatamente igual à cadastrada
# na aplicação do Mercado Livre.
REDIRECT_URI = os.environ.get(
    "ML_REDIRECT_URI",
    "https://robo-ofertas-ml.onrender.com/"
)


@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    # Verifica configurações antes de iniciar o OAuth
    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500

    # --------------------------------------------------
    # RETORNO DO MERCADO LIVRE COM O CODE
    # --------------------------------------------------

    if code:

        # Verifica o state
        if state != session.get("state"):
            return "Erro: state inválido.", 400

        # Recupera o code_verifier usado no PKCE
        code_verifier = session.get("code_verifier")

        if not code_verifier:
            return "Erro: code_verifier não encontrado.", 400

        # --------------------------------------------------
        # TROCA O CODE PELO ACCESS TOKEN
        # --------------------------------------------------

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

        # --------------------------------------------------
        # CONSULTA A CONTA
        # --------------------------------------------------

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

        # --------------------------------------------------
        # SALVA OS TOKENS NA SESSÃO
        # --------------------------------------------------

        session["access_token"] = access_token

        if refresh_token:
            session["refresh_token"] = refresh_token

        session["user_id"] = user_id
        session["nickname"] = nickname

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

        </body>
        </html>
        """


    # --------------------------------------------------
    # INICIA O LOGIN NO MERCADO LIVRE
    # --------------------------------------------------

    code_verifier = secrets.token_urlsafe(64)

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(
            code_verifier.encode()
        ).digest()
    ).rstrip(b"=").decode()

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


@app.route("/buscar")
def buscar():

    termo = request.args.get("q", "").strip()

    if not termo:
        return "Digite um produto para pesquisar.", 400

    # --------------------------------------------------
    # RECUPERA O ACCESS TOKEN
    # --------------------------------------------------

    access_token = session.get("access_token")

    if not access_token:
        return """
        <h1>Conta não conectada</h1>

        <p>
            Conecte sua conta do Mercado Livre novamente.
        </p>

        <a href="/">
            Conectar Mercado Livre
        </a>
        """, 401

    # --------------------------------------------------
    # ENVIA O TOKEN PARA A API
    # --------------------------------------------------

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(
        "https://api.mercadolibre.com/sites/MLB/search",
        headers=headers,
        params={
            "q": termo,
            "limit": 10,
        },
        timeout=30,
    )

    # --------------------------------------------------
    # DIAGNÓSTICO
    # --------------------------------------------------

    print("================================")
    print("TESTE API MERCADO LIVRE")
    print("Endpoint: /sites/MLB/search")
    print("Termo:", termo)
    print("Status:", response.status_code)
    print("Resposta:", response.text)
    print("================================")

    # --------------------------------------------------
    # ERRO DA API
    # --------------------------------------------------

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
            Status da API:
            <strong>{response.status_code}</strong>
        </p>

        <pre>{response.text}</pre>

        <br>

        <a href="/">
            ← Voltar
        </a>

        </body>
        </html>
        """, response.status_code

    # --------------------------------------------------
    # PROCESSA RESULTADOS
    # --------------------------------------------------

    data = response.json()

    produtos = data.get("results", [])

    html = f"""
    <!DOCTYPE html>
    <html>

    <head>
        <meta charset="UTF-8">
        <title>Busca - {termo}</title>

        <style>

            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: auto;
                padding: 20px;
            }}

            .produto {{
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 15px;
                margin: 15px 0;
            }}

            .produto img {{
                width: 150px;
                height: 150px;
                object-fit: contain;
            }}

            .preco {{
                font-size: 20px;
                font-weight: bold;
            }}

        </style>

    </head>

    <body>

    <h1>🔎 Resultados para: {termo}</h1>

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

    for produto in produtos:

        titulo = produto.get(
            "title",
            "Sem título"
        )

        preco = produto.get(
            "price",
            "N/A"
        )

        link = produto.get(
            "permalink",
            "#"
        )

        imagem = produto.get(
            "thumbnail",
            ""
        )

        html += f"""
        <div class="produto">

            <img
                src="{imagem}"
                alt="{titulo}"
            >

            <h3>
                {titulo}
            </h3>

            <p class="preco">
                R$ {preco}
            </p>

            <a
                href="{link}"
                target="_blank"
            >
                Ver anúncio
            </a>

        </div>
        """

    html += """
    </body>
    </html>
    """

    return html


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
