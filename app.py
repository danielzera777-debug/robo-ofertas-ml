from flask import Flask, request, session
import requests
import secrets
import hashlib
import base64
from urllib.parse import urlencode
import os
import html
app = Flask(__name__)
# =========================================================
# CONFIGURAÇÕES
# =========================================================
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "troque-essa-chave"
)
CLIENT_ID = os.environ.get("ML_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET")
REDIRECT_URI = "https://robo-ofertas-ml.onrender.com/"
# =========================================================
# PÁGINA INICIAL
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
        saved_state = session.get("state")
        if state != saved_state:
            return "Erro: state inválido.", 400
        code_verifier = session.get("code_verifier")
        if not code_verifier:
            return "Erro: code_verifier não encontrado.", 400
        # -------------------------------------------------
        # TROCA CODE POR TOKEN
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
            <pre>{html.escape(response.text)}</pre>
            """, 400
        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        if not access_token:
            return "Erro: Access Token não recebido.", 400
        # -------------------------------------------------
        # TESTA USUÁRIO
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
            <pre>{html.escape(user_response.text)}</pre>
            """, 400
        user_data = user_response.json()
        nickname = user_data.get(
            "nickname",
            "usuário"
        )
        user_id = user_data.get(
            "id",
            "não informado"
        )
        # -------------------------------------------------
        # SALVA TOKEN
        # -------------------------------------------------
        session["access_token"] = access_token
        session["refresh_token"] = refresh_token
        session["user_id"] = user_id
        return tela_principal(
            nickname,
            user_id
        )
    # =====================================================
    # JÁ ESTÁ CONECTADO?
    # =====================================================
    access_token = session.get("access_token")
    if access_token:
        return tela_principal(
            "Mercado Livre",
            session.get("user_id", "")
        )
    # =====================================================
    # GERAR PKCE
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
    # =====================================================
    # AUTORIZAÇÃO
    # =====================================================
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
              content="width=device-width, initial-scale=1.0">
        <title>Achadosnews7</title>
        <style>
            * {{
                box-sizing: border-box;
            }}
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                color: #222;
            }}
            .container {{
                max-width: 600px;
                margin: 80px auto;
                padding: 20px;
            }}
            .card {{
                background: white;
                border-radius: 18px;
                padding: 30px;
                text-align: center;
                box-shadow:
                    0 5px 25px rgba(0,0,0,0.08);
            }}
            h1 {{
                margin-bottom: 10px;
            }}
            .logo {{
                font-size: 42px;
                margin-bottom: 10px;
            }}
            .btn {{
                display: inline-block;
                margin-top: 25px;
                padding: 15px 25px;
                border-radius: 10px;
                background: #3483fa;
                color: white;
                text-decoration: none;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <div class="logo">
                    🤖
                </div>
                <h1>
                    Achadosnews7
                </h1>
                <p>
                    Conecte sua conta do Mercado Livre
                    para começar.
                </p>
                <a
                    class="btn"
                    href="{auth_url}"
                >
                    Conectar Mercado Livre
                </a>
            </div>
        </div>
    </body>
    </html>
    """
# =========================================================
# TELA PRINCIPAL
# =========================================================
def tela_principal(nickname, user_id):
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >
        <title>Achadosnews7</title>
        <style>
            * {{
                box-sizing: border-box;
            }}
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                color: #222;
            }}
            header {{
                background: #3483fa;
                color: white;
                padding: 20px;
            }}
            header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .container {{
                max-width: 900px;
                margin: auto;
                padding: 20px;
            }}
            .user {{
                background: white;
                padding: 15px;
                border-radius: 12px;
                margin-bottom: 20px;
            }}
            .search {{
                background: white;
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 20px;
            }}
            .search form {{
                display: flex;
                gap: 10px;
            }}
            .search input {{
                flex: 1;
                padding: 14px;
                border: 1px solid #ddd;
                border-radius: 10px;
                font-size: 16px;
            }}
            .search button {{
                border: 0;
                border-radius: 10px;
                padding: 14px 22px;
                background: #3483fa;
                color: white;
                font-weight: bold;
                cursor: pointer;
            }}
            .test {{
                display: inline-block;
                margin-top: 10px;
                color: #3483fa;
            }}
            @media(max-width:600px) {{
                .search form {{
                    flex-direction: column;
                }}
                .search button {{
                    width: 100%;
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
            <div class="user">
                <strong>
                    Mercado Livre conectado ✅
                </strong>
                <br><br>
                Usuário:
                <strong>
                    {html.escape(str(nickname))}
                </strong>
                <br>
                ID:
                {html.escape(str(user_id))}
            </div>
            <div class="search">
                <h2>
                    🔎 Buscar produtos
                </h2>
                <form
                    action="/buscar"
                    method="get"
                >
                    <input
                        type="text"
                        name="q"
                        placeholder="Ex: celular, relógio, tênis..."
                        required
                    >
                    <button type="submit">
                        Buscar
                    </button>
                </form>
                <a
                    class="test"
                    href="/teste-produtos"
                >
                    🧪 Testar API
                </a>
            </div>
        </div>
    </body>
    </html>
    """
# =========================================================
# BUSCA
# =========================================================
@app.route("/buscar")
def buscar():
    termo = request.args.get(
        "q",
        ""
    ).strip()
    if not termo:
        return "Digite um produto para pesquisar.", 400
    access_token = session.get(
        "access_token"
    )
    if not access_token:
        return """
        <h1>❌ Mercado Livre não conectado</h1>
        <a href="/">
            Conectar Mercado Livre
        </a>
        """, 401
    # =====================================================
    # API PRODUCTS SEARCH
    # =====================================================
    response = requests.get(
        "https://api.mercadolibre.com/products/search",
        params={
            "q": termo,
            "site_id": "MLB",
            "status": "active",
            "limit": 20,
        },
        headers={
            "Authorization":
                f"Bearer {access_token}"
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
        </body>
        </html>
        """, response.status_code
    data = response.json()
    produtos = data.get(
        "results",
        []
    )
    total = data.get(
        "paging",
        {}
    ).get(
        "total",
        0
    )
    # =====================================================
    # HTML
    # =====================================================
    resultado_html = ""
    for produto in produtos:
        produto_id = produto.get(
            "id",
            ""
        )
        nome = produto.get(
            "name",
            "Produto sem nome"
        )
        nome = html.escape(
            str(nome)
        )
        marca = "Não informado"
        gtin = "Não informado"
        for atributo in produto.get(
            "attributes",
            []
        ):
            atributo_id = atributo.get(
                "id"
            )
            valor = atributo.get(
                "value_name"
            )
            if atributo_id == "BRAND":
                marca = valor or marca
            if atributo_id == "GTIN":
                gtin = valor or gtin
        marca = html.escape(
            str(marca)
        )
        gtin = html.escape(
            str(gtin)
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
        if imagem:
            imagem_html = f"""
            <img
                src="{html.escape(imagem)}"
                alt="{nome}"
            >
            """
        else:
            imagem_html = """
            <div class="sem-imagem">
                📦
            </div>
            """
        resultado_html += f"""
        <div class="produto">
            <div class="imagem">
                {imagem_html}
            </div>
            <div class="info">
                <div class="produto-id">
                    {produto_id}
                </div>
                <h3>
                    {nome}
                </h3>
                <p>
                    <strong>
                        Marca:
                    </strong>
                    {marca}
                </p>
                <p>
                    <strong>
                        GTIN:
                    </strong>
                    {gtin}
                </p>
                <p class="catalogo">
                    📦 Produto de catálogo
                </p>
            </div>
        </div>
        """
    # =====================================================
    # PÁGINA
    # =====================================================
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >
        <title>
            Busca - {html.escape(termo)}
        </title>
        <style>
            * {{
                box-sizing: border-box;
            }}
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f5f5f5;
                color: #222;
            }}
            header {{
                background: #3483fa;
                color: white;
                padding: 20px;
            }}
            header h1 {{
                margin: 0;
                font-size: 23px;
            }}
            .container {{
                max-width: 1000px;
                margin: auto;
                padding: 20px;
            }}
            .top {{
                background: white;
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 20px;
            }}
            .top a {{
                color: #3483fa;
                text-decoration: none;
            }}
            .top h2 {{
                margin-bottom: 5px;
            }}
            .contador {{
                color: #666;
            }}
            .produto {{
                background: white;
                border-radius: 15px;
                padding: 18px;
                margin-bottom: 15px;
                display: flex;
                gap: 20px;
                box-shadow:
                    0 3px 12px rgba(0,0,0,0.06);
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
            .sem-imagem {{
                font-size: 60px;
            }}
            .info {{
                flex: 1;
            }}
            .info h3 {{
                margin-top: 8px;
                margin-bottom: 15px;
                font-size: 18px;
            }}
            .produto-id {{
                color: #777;
                font-size: 13px;
            }}
            .catalogo {{
                display: inline-block;
                background: #e8f0fe;
                color: #3483fa;
                padding: 7px 10px;
                border-radius: 8px;
                font-size: 13px;
            }}
            @media(max-width:600px) {{
                .produto {{
                    flex-direction: column;
                }}
                .imagem {{
                    width: 100%;
                    min-width: 100%;
                    height: 220px;
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
                    🔎 {html.escape(termo)}
                </h2>
                <div class="contador">
                    Encontrados:
                    <strong>
                        {total}
                    </strong>
                    produtos
                </div>
            </div>
            {resultado_html}
        </div>
    </body>
    </html>
    """
# =========================================================
# TESTE DA API
# =========================================================
@app.route("/teste-produtos")
def teste_produtos():
    access_token = session.get(
        "access_token"
    )
    if not access_token:
        return """
        <h1>❌ Token não encontrado</h1>
        <a href="/">
            Fazer login
        </a>
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
            "Authorization":
                f"Bearer {access_token}"
        },
        timeout=30,
    )
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >
        <title>
            Teste API
        </title>
    </head>
    <body>
        <h1>
            🧪 Teste /products/search
        </h1>
        <p>
            API:
            <strong>
                {response.status_code}
            </strong>
        </p>
        <pre style="
            white-space:pre-wrap;
            word-wrap:break-word;
        ">{html.escape(response.text)}</pre>
        <br>
        <a href="/">
            ← Voltar
        </a>
    </body>
    </html>
    """
# =========================================================
# INICIAR
# =========================================================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000
    )
