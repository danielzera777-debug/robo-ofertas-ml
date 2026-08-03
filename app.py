import os
import base64
import hashlib
import secrets
from urllib.parse import urlencode

import requests
from flask import Flask, request, session

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave-temporaria")

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")

REDIRECT_URI = "https://robo-ofertas-ml.onrender.com/"


@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    # Retorno do Mercado Livre
    if code:

        if state != session.get("state"):
            return "Erro: state inválido.", 400

        code_verifier = session.get("code_verifier")

        if not code_verifier:
            return "Erro: code_verifier não encontrado.", 400

        # Troca o código pelo Access Token
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
            return f"Erro ao obter token: {response.text}", 400

        token_data = response.json()

        access_token = token_data.get("access_token")

        if not access_token:
            return "Erro: Access Token não recebido.", 400

        # Consulta a conta do Mercado Livre
        user_response = requests.get(
            "https://api.mercadolibre.com/users/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=30,
        )

        if user_response.status_code != 200:
            return (
                "Erro ao consultar a conta: "
                + user_response.text
            ), 400

        user_data = user_response.json()

        nickname = user_data.get("nickname", "usuário")
        user_id = user_data.get("id", "não informado")

        return f"""
        <!DOCTYPE html>
        <html>

        <head>
            <meta charset="UTF-8">
            <title>Teste Mercado Livre</title>
        </head>

        <body>

            <h1>✅ API funcionando!</h1>

            <h2>Conta conectada</h2>

            <p>
                Usuário:
                <strong>{nickname}</strong>
            </p>

            <p>
                ID da conta:
                <strong>{user_id}</strong>
            </p>

            <hr>

            <p>
                ✅ OAuth funcionando
            </p>

            <p>
                ✅ PKCE funcionando
            </p>

            <p>
                ✅ Access Token obtido
            </p>

            <p>
                ✅ API respondeu corretamente
            </p>

            <p>
                Próximo passo: configurar a busca de produtos.
            </p>

        </body>

        </html>
        """

    # Verificação das variáveis
    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500

    # -------------------------
    # PKCE
    # -------------------------

    code_verifier = secrets.token_urlsafe(64)

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
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

        <p>Conecte sua conta do Mercado Livre:</p>

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


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000
    )
