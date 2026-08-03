import os
import base64
import hashlib
import secrets
import requests

from flask import Flask, redirect, request, session

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave-temporaria")

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")

REDIRECT_URI = "https://robo-ofertas-ml.onrender.com/"


@app.route("/")
def home():
    # Se o Mercado Livre acabou de retornar com um código
    code = request.args.get("code")
    state = request.args.get("state")

    if code:
        if state != session.get("state"):
            return "Erro: state inválido.", 400

        code_verifier = session.get("code_verifier")

        if not code_verifier:
            return "Erro: code_verifier não encontrado.", 400

        # Troca o código por um access token
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

        # Guarda os tokens temporariamente na sessão
        session["access_token"] = token_data.get("access_token")
        session["refresh_token"] = token_data.get("refresh_token")

        return """
        <h1>✅ Mercado Livre conectado!</h1>
        <p>Autorização concluída com sucesso.</p>
        """

    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    # Gera PKCE
    code_verifier = secrets.token_urlsafe(64)

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    state = secrets.token_urlsafe(32)

    session["code_verifier"] = code_verifier
    session["state"] = state

    auth_url = (
        "https://auth.mercadolivre.com.br/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
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
                padding: 15px 25px;
                font-size: 18px;
                cursor: pointer;
            ">
                Conectar Mercado Livre
            </button>
        </a>
    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
