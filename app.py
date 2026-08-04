from flask import Flask, request, session
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode
import os
import html
app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "troque-essa-chave"
)
CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")
REDIRECT_URI = "https://robo-ofertas-ml.onrender.com/"
# =========================================================
# FUNÇÕES
# =========================================================
def esc(valor):
    return html.escape(str(valor or ""))
def api_get(url, token, params=None):
    return requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}"
        },
        params=params or {},
        timeout=30
    )
# =========================================================
# TELA DE LOGIN
# =========================================================
@app.route("/")
def home():
    code = request.args.get("code")
    state = request.args.get("state")
    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500
    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500
    # =====================================================
    # RETORNO DO MERCADO LIVRE
    # =====================================================
    if code:
        if state != session.get("state"):
            return "Erro: state inválido.", 400
        code_verifier = session.get("code_verifier")
        if not code_verifier:
            return "Erro: code_verifier não encontrado.", 400
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
            timeout=30
        )
        if response.status_code != 200:
            return f"""
            <h1>Erro ao obter token</h1>
            <pre>{esc(response.text)}</pre>
            """, 400
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        if not access_token:
            return "Access Token não recebido.", 400
        # =================================================
        # TESTAR CONTA
        # =================================================
        user_response = api_get(
            "https://api.mercadolibre.com/users/me",
            access_token
        )
        if user_response.status_code != 200:
            return f"""
            <h1>Erro /users/me</h1>
            <pre>{esc(user_response.text)}</pre>
            """, 400
        user_data = user_response.json()
        nickname = user_data.get(
            "nickname",
            "usuário"
        )
        user_id = user_data.get(
            "id",
            ""
        )
        session["access_token"] = access_token
        session["refresh_token"] = refresh_token
        session["user_id"] = user_id
        return pagina_principal(
            nickname,
            user_id
        )
    # =====================================================
    # JÁ CONECTADO
    # =====================================================
    if session.get("access_token"):
        return pagina_principal(
            "Mercado Livre",
            session.get("user_id", "")
        )
    # =====================================================
    # PKCE
    # =====================================================
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
        "code_challenge_method": "S256"
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
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >
        <title>Achadosnews7</title>
        <style>
            body {{
                margin:0;
                font-family:Arial;
                background:#f5f5f5;
            }}
            .box {{
                max-width:500px;
                margin:80px auto;
                background:white;
                padding:30px;
                border-radius:18px;
                text-align:center;
            }}
            .btn {{
                display:inline-block;
                padding:15px 25px;
                background:#3483fa;
                color:white;
                text-decoration:none;
                border-radius:10px;
                font-weight:bold;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>
                🤖 Achadosnews7
            </h1>
            <p>
                Conecte sua conta do Mercado Livre.
            </p>
            <br>
            <a
                class="btn"
                href="{auth_url}"
            >
                Conectar Mercado Livre
            </a>
        </div>
    </body>
    </html>
    """
# =========================================================
# PÁGINA PRINCIPAL
# =========================================================
def pagina_principal(
    nickname,
    user_id
):
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >
        <title>Achadosnews7</title>
        <style>
            body {{
                margin:0;
                font-family:Arial;
                background:#f5f5f5;
            }}
            header {{
                background:#3483fa;
                color:white;
                padding:20px;
            }}
            .container {{
                max-width:900px;
                margin:auto;
                padding:20px;
            }}
            .card {{
                background:white;
                padding:20px;
                border-radius:15px;
                margin-bottom:20px;
            }}
            form {{
                display:flex;
                gap:10px;
            }}
            input {{
                flex:1;
                padding:14px;
                border:1px solid #ddd;
                border-radius:10px;
                font-size:16px;
            }}
            button {{
                padding:14px 22px;
                border:0;
                border-radius:10px;
                background:#3483fa;
                color:white;
                font-weight:bold;
            }}
            @media(max-width:600px) {{
                form {{
                    flex-direction:column;
                }}
            }}
        </style>
    </head>
    <body>
        <header>
            <div class="container">
                <h1>
                    🤖 Achadosnews7
                </h1>
            </div>
        </header>
        <div class="container">
            <div class="card">
                <strong>
                    Mercado Livre conectado ✅
                </strong>
                <p>
                    Usuário: {esc(nickname)}
                </p>
                <p>
                    ID: {esc(user_id)}
                </p>
            </div>
            <div class="card">
                <h2>
                    🔎 Procurar ofertas
                </h2>
                <form
                    action="/buscar"
                    method="get"
                >
                    <input
                        name="q"
                        placeholder="Ex: celular"
                        required
                    >
                    <button>
                        Buscar
                    </button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """
# =========================================================
# BUSCAR PRODUTOS
# =========================================================
@app.route("/buscar")
def buscar():
    termo = request.args.get(
        "q",
        ""
    ).strip()
    if not termo:
        return "Digite um produto.", 400
    token = session.get("access_token")
    if not token:
        return """
        <h1>Mercado Livre não conectado.</h1>
        <a href="/">Voltar</a>
        """, 401
    # =====================================================
    # PRODUCTS SEARCH
    # =====================================================
    response = api_get(
        "https://api.mercadolibre.com/products/search",
        token,
        {
            "q": termo,
            "site_id": "MLB",
            "status": "active",
            "limit": 10
        }
    )
    if response.status_code != 200:
        return f"""
        <h1>Erro na busca</h1>
        <p>
        Status: {response.status_code}
        </p>
        <pre>
        {esc(response.text)}
        </pre>
        <a href="/">Voltar</a>
        """, response.status_code
    data = response.json()
    produtos = data.get(
        "results",
        []
    )
    cards = ""
    for produto in produtos:
        product_id = produto.get(
            "id"
        )
        nome = produto.get(
            "name",
            "Produto"
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
        # =================================================
        # BUSCAR ANÚNCIOS DO PRODUTO
        # =================================================
        anuncios_response = api_get(
            "https://api.mercadolibre.com/products/"
            + str(product_id)
            + "/items",
            token
        )
        anuncios = []
        if anuncios_response.status_code == 200:
            anuncios_data = anuncios_response.json()
            anuncios = anuncios_data.get(
                "results",
                []
            )
        # =================================================
        # PEGAR MELHOR PREÇO
        # =================================================
        melhor_preco = None
        melhor_item = None
        for item in anuncios:
            preco = item.get(
                "price"
            )
            if preco is None:
                continue
            try:
                preco_num = float(preco)
            except:
                continue
            if (
                melhor_preco is None
                or preco_num < melhor_preco
            ):
                melhor_preco = preco_num
                melhor_item = item
        # =================================================
        # CARD
        # =================================================
        if melhor_preco is not None:
            preco_html = f"""
            <div class="preco">
                R$ {melhor_preco:,.2f}
            </div>
            """.replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            preco_html = """
            <div class="sem-preco">
                Preço não disponível
            </div>
            """
        if imagem:
            imagem_html = f"""
            <img
                src="{esc(imagem)}"
                alt="{esc(nome)}"
            >
            """
        else:
            imagem_html = """
            <div class="sem-imagem">
                📦
            </div>
            """
        link_html = ""
        if melhor_item:
            permalink = melhor_item.get(
                "permalink"
            )
            if permalink:
                link_html = f"""
                <a
                    class="btn"
                    href="{esc(permalink)}"
                    target="_blank"
                >
                    Ver anúncio
                </a>
                """
        cards += f"""
        <div class="produto">
            <div class="foto">
                {imagem_html}
            </div>
            <div class="info">
                <small>
                    {esc(product_id)}
                </small>
                <h2>
                    {esc(nome)}
                </h2>
                {preco_html}
                <p>
                    Anúncios encontrados:
                    <strong>
                        {len(anuncios)}
                    </strong>
                </p>
                {link_html}
            </div>
        </div>
        """
    if not cards:
        cards = """
        <div class="produto">
            <h2>
                Nenhum produto encontrado.
            </h2>
        </div>
        """
    # =====================================================
    # HTML FINAL
    # =====================================================
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
            Achadosnews7 - {esc(termo)}
        </title>
        <style>
            body {{
                margin:0;
                font-family:Arial;
                background:#f5f5f5;
                color:#222;
            }}
            header {{
                background:#3483fa;
                color:white;
                padding:20px;
            }}
            .container {{
                max-width:1000px;
                margin:auto;
                padding:20px;
            }}
            .top {{
                background:white;
                padding:20px;
                border-radius:15px;
                margin-bottom:20px;
            }}
            .top a {{
                color:#3483fa;
                text-decoration:none;
            }}
            .produto {{
                background:white;
                border-radius:15px;
                padding:20px;
                margin-bottom:18px;
                display:flex;
                gap:25px;
                box-shadow:
                    0 3px 15px rgba(0,0,0,.06);
            }}
            .foto {{
                width:220px;
                min-width:220px;
                height:220px;
                display:flex;
                align-items:center;
                justify-content:center;
            }}
            .foto img {{
                max-width:100%;
                max-height:100%;
                object-fit:contain;
            }}
            .sem-imagem {{
                font-size:70px;
            }}
            .info {{
                flex:1;
            }}
            .info h2 {{
                margin-top:8px;
            }}
            .preco {{
                font-size:28px;
                font-weight:bold;
                color:#00a650;
                margin:15px 0;
            }}
            .sem-preco {{
                color:#777;
                margin:15px 0;
            }}
            .btn {{
                display:inline-block;
                padding:12px 18px;
                background:#3483fa;
                color:white;
                text-decoration:none;
                border-radius:9px;
                font-weight:bold;
            }}
            @media(max-width:600px) {{
                .produto {{
                    flex-direction:column;
                }}
                .foto {{
                    width:100%;
                    min-width:100%;
                }}
            }}
        </style>
    </head>
    <body>
        <header>
            <div class="container">
                <h1>
                    🤖 Achadosnews7
                </h1>
            </div>
        </header>
        <div class="container">
            <div class="top">
                <a href="/">
                    ← Voltar
                </a>
                <h2>
                    🔎 {esc(termo)}
                </h2>
            </div>
            {cards}
        </div>
    </body>
    </html>
    """
# =========================================================
# SERVIDOR
# =========================================================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000
    )
