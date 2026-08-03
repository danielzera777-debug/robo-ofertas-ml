import os
import base64
import hashlib
import secrets
from flask import Flask, redirect, request, session

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave-temporaria")

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")

REDIRECT_URI = "https://robo-ofertas-ml.onrender.com/"

@app.route("/")
def home():
    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

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


@app.route("/")
def oauth_callback():
    return "Callback"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
