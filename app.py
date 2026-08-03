import os
from flask import Flask, redirect, request

app = Flask(__name__)

CLIENT_ID = os.getenv("ML_CLIENT_ID")
REDIRECT_URI = "https://robo-ofertas-ml.onrender.com"

@app.route("/")
def home():
    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado.", 500

    auth_url = (
        "https://auth.mercadolivre.com.br/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )

    return f"""
    <h1>🤖 Robô Ofertas ML</h1>
    <p>Conecte sua conta do Mercado Livre:</p>
    <a href="{auth_url}">
        <button>Conectar Mercado Livre</button>
    </a>
    """

@app.route("/oauth/callback")
def callback():
    code = request.args.get("code")

    if not code:
        error = request.args.get("error", "desconhecido")
        return f"Erro na autorização: {error}", 400

    return "✅ Mercado Livre autorizado! Código recebido."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

