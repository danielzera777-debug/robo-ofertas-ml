import os
from flask import Flask, redirect

app = Flask(__name__)

CLIENT_ID = os.getenv("ML_CLIENT_ID")
REDIRECT_URI = "https://robo-ofertas-ml.onrender.com"

@app.route("/")
def home():
    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    auth_url = (
        "https://auth.mercadolivre.com.br/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )

    return f"""
    <html>
        <head>
            <title>Robô Ofertas ML</title>
        </head>
        <body>
            <h1>🤖 Robô Ofertas ML</h1>
            <p>Conecte sua conta do Mercado Livre:</p>
            <a href="{auth_url}">
                <button>Conectar Mercado Livre</button>
            </a>
        </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
