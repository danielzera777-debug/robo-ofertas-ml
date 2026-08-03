import os
import base64
import hashlib
import secrets
from urllib.parse import urlencode

from flask import Flask, request, session

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "chave-temporaria")

CLIENT_ID = os.getenv("ML_CLIENT_ID")

REDIRECT_URI = "https://robo-ofertas-ml.onrender.com/"


@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    # Retorno do Mercado Livre
    if code:

        if state != session.get("state"):
            return "Erro: state inválido.", 400

        return """
        <h1>✅ Mercado Livre conectado!</h1>
        <p>Autorização recebida com sucesso.</p>
        """

    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    # PKCE
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

        <p>
            <a href="{auth_url}">
                <button style="
                    padding:15px 25px;
                    font-size:18px;
                ">
                    Conectar Mercado Livre
                </button>
            </a>
        </p>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
