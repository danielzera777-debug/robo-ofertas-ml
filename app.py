from flask import Flask, request, session
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode
import os
import html

app = Flask(__name__)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "troque-esta-chave")

CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")

REDIRECT_URI = os.environ.get(
    "ML_REDIRECT_URI",
    "https://robo-ofertas-ml.onrender.com/"
)

ML_API = "https://api.mercadolibre.com"

# ============================================================
# PÁGINA INICIAL / LOGIN
# ============================================================

@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    # --------------------------------------------------------
    # RETORNO DO MERCADO LIVRE
    # --------------------------------------------------------

    if code:

        if state != session.get("state"):
            return "Erro: state inválido.", 400

        code_verifier = session.get("code_verifier")

        if not code_verifier:
            return "Erro: code_verifier não encontrado.", 400

        # Troca o CODE pelo ACCESS TOKEN
        response = requests.post(
            f"{ML_API}/oauth/token",
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
            <pre>{html.escape(response.text)}</pre>
            """, 400

        token_data = response.json()

        access_token = token_data.get("access_token")

        if not access_token:
            return "Erro: Access Token não recebido.", 400

        # Testa o token
        user_response = requests.get(
            f"{ML_API}/users/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=30,
        )

        if user_response.status_code != 200:
            return f"""
            <h1>Erro ao consultar conta</h1>
            <pre>{html.escape(user_response.text)}</pre>
            """, 400

        user_data = user_response.json()

        nickname = user_data.get("nickname", "usuário")
        user_id = user_data.get("id", "não informado")

        # Guarda token
        session["access_token"] = access_token

        return pagina_busca(nickname, user_id)

    # --------------------------------------------------------
    # VALIDA CONFIGURAÇÕES
    # --------------------------------------------------------

    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500

    # --------------------------------------------------------
    # PKCE
    # --------------------------------------------------------

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
    <html lang="pt-BR">

    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <title>Robô Ofertas ML</title>

        <style>

            body {{
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                margin: 0;
                padding: 30px;
                text-align: center;
            }}

            .container {{
                max-width: 600px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 2px 10px #ddd;
            }}

            button {{
                background: #ffe600;
                border: none;
                padding: 15px 25px;
                border-radius: 8px;
                font-size: 17px;
                cursor: pointer;
            }}

        </style>

    </head>

    <body>

        <div class="container">

            <h1>🤖 Robô Ofertas ML</h1>

            <p>
                Conecte sua conta do Mercado Livre
                para começar.
            </p>

            <a href="{auth_url}">
                <button>
                    🔗 Conectar Mercado Livre
                </button>
            </a>

        </div>

    </body>

    </html>
    """


# ============================================================
# PÁGINA DE BUSCA
# ============================================================

def pagina_busca(nickname, user_id):

    return f"""
    <!DOCTYPE html>

    <html lang="pt-BR">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <title>Robô Ofertas ML</title>

        <style>

            body {{
                font-family: Arial;
                background: #f5f5f5;
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
                width: 70%;
                padding: 12px;
                font-size: 16px;
                border: 1px solid #ccc;
                border-radius: 8px;
            }}

            button {{
                padding: 12px 18px;
                border: none;
                border-radius: 8px;
                background: #ffe600;
                cursor: pointer;
                font-size: 16px;
            }}

        </style>

    </head>

    <body>

        <div class="container">

            <h1>🤖 Robô Ofertas ML</h1>

            <p>
                ✅ Mercado Livre conectado
            </p>

            <p>
                Usuário:
                <strong>{html.escape(str(nickname))}</strong>
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

                <button>
                    🔎 Buscar
                </button>

            </form>

        </div>

    </body>

    </html>
    """


# ============================================================
# BUSCA DE PRODUTOS
# ============================================================

@app.route("/buscar")
def buscar():

    termo = request.args.get("q", "").strip()

    if not termo:
        return "Digite um produto para pesquisar.", 400

    # --------------------------------------------------------
    # USA /products/search
    # --------------------------------------------------------

    response = requests.get(
        f"{ML_API}/products/search",
        params={
            "q": termo,
            "limit": 20,
        },
        timeout=30,
    )

    if response.status_code != 200:

        return f"""
        <!DOCTYPE html>

        <html>

        <body>

            <h1>❌ Erro na busca</h1>

            <p>
                Status da API:
                {response.status_code}
            </p>

            <pre>
{html.escape(response.text)}
            </pre>

            <a href="/">
                ← Voltar
            </a>

        </body>

        </html>
        """, response.status_code

    data = response.json()

    produtos = data.get("results", [])

    # --------------------------------------------------------
    # MONTA RESULTADOS
    # --------------------------------------------------------

    cards = ""

    for produto in produtos:

        produto_id = produto.get("id", "")

        nome = produto.get(
            "name",
            "Produto sem nome"
        )

        imagens = produto.get("pictures", [])

        imagem = ""

        if imagens:

            imagem = imagens[0].get(
                "url",
                ""
            )

        nome_html = html.escape(
            str(nome)
        )

        produto_id_html = html.escape(
            str(produto_id)
        )

        cards += f"""

        <div class="card">

            <div class="imagem">

                <img
                    src="{html.escape(imagem)}"
                    alt="{nome_html}"
                >

            </div>

            <div class="info">

                <h3>
                    {nome_html}
                </h3>

                <p>
                    ID do produto:
                    <strong>
                        {produto_id_html}
                    </strong>
                </p>

                <p>
                    Status:
                    <strong>
                        {html.escape(
                            str(
                                produto.get(
                                    "status",
                                    "N/A"
                                )
                            )
                        )}
                    </strong>
                </p>

                <a
                    href="https://www.mercadolivre.com.br/p/{produto_id_html}"
                    target="_blank"
                >
                    Ver produto
                </a>

            </div>

        </div>

        """

    if not produtos:

        cards = """
        <h2>
            Nenhum produto encontrado.
        </h2>
        """

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    return f"""

    <!DOCTYPE html>

    <html lang="pt-BR">

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >

        <title>
            Busca - {html.escape(termo)}
        </title>

        <style>

            body {{
                font-family: Arial;
                background: #f5f5f5;
                margin: 0;
                padding: 20px;
            }}

            .container {{
                max-width: 900px;
                margin: auto;
            }}

            .top {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
            }}

            .card {{
                background: white;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 15px;

                display: flex;
                gap: 20px;

                box-shadow:
                    0 2px 8px rgba(
                        0,0,0,0.08
                    );
            }}

            .imagem {{
                width: 180px;
                min-width: 180px;
                height: 180px;

                display: flex;
                align-items: center;
                justify-content: center;
            }}

            .imagem img {{
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            }}

            .info {{
                flex: 1;
            }}

            .info h3 {{
                margin-top: 0;
            }}

            .info a {{
                display: inline-block;
                margin-top: 10px;
                padding: 10px 15px;

                background: #ffe600;
                color: #111;

                text-decoration: none;

                border-radius: 7px;
            }}

            @media(max-width:600px) {{

                body {{
                    padding: 10px;
                }}

                .card {{
                    flex-direction: column;
                }}

                .imagem {{
                    width: 100%;
                    height: 220px;
                }}

            }}

        </style>

    </head>

    <body>

        <div class="container">

            <div class="top">

                <h1>
                    🔎 Busca de produtos
                </h1>

                <p>
                    Termo:
                    <strong>
                        {html.escape(termo)}
                    </strong>
                </p>

                <p>
                    Produtos encontrados:
                    <strong>
                        {len(produtos)}
                    </strong>
                </p>

                <a href="/">
                    ← Nova busca
                </a>

            </div>

            {cards}

        </div>

    </body>

    </html>

    """


# ============================================================
# TESTE DO TOKEN
# ============================================================

@app.route("/teste")
def teste():

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
        """

    response = requests.get(
        f"{ML_API}/users/me",
        headers={
            "Authorization":
            f"Bearer {access_token}"
        },
        timeout=30,
    )

    return f"""
    <h1>🧪 Teste /users/me</h1>

    <p>
        Status da API:
        <strong>
            {response.status_code}
        </strong>
    </p>

    <pre>
{html.escape(response.text)}
    </pre>

    <a href="/">
        ← Voltar
    </a>
    """


# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
