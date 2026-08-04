import os
import secrets
import hashlib
import base64
import requests
import html

from urllib.parse import urlencode
from flask import Flask, request, session

app = Flask(__name__)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

app.secret_key = SECRET_KEY

# ============================================================
# CONFIGURAÇÃO DE SESSÃO
# ============================================================

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ============================================================
# FORMATAÇÃO
# ============================================================

def formatar_preco(valor):

    if valor is None:
        return "Preço indisponível"

    try:

        valor = float(valor)

        return (
            f"R$ {valor:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except Exception:

        return "Preço indisponível"


def escapar(valor):

    return html.escape(str(valor or ""))


# ============================================================
# REQUISIÇÃO AO MERCADO LIVRE
# ============================================================

def buscar_mercado_livre(termo, limit=50, offset=0):

    url = "https://api.mercadolibre.com/sites/MLB/search"

    params = {
        "q": termo,
        "limit": limit,
        "offset": offset,
    }

    access_token = session.get("access_token")

    headers = {
        "Accept": "application/json",
        "User-Agent": "Robô-Ofertas-ML/1.0",
    }

    # ========================================================
    # USA O TOKEN DA CONTA CONECTADA
    # ========================================================

    if access_token:

        headers["Authorization"] = (
            f"Bearer {access_token}"
        )

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30,
        )

        return response

    except requests.RequestException as e:

        print("ERRO DE CONEXÃO COM MERCADO LIVRE:")
        print(str(e))

        return None


# ============================================================
# PÁGINA INICIAL
# ============================================================

@app.route("/")
def home():

    code = request.args.get("code")
    state = request.args.get("state")

    if not CLIENT_ID:
        return "ML_CLIENT_ID não configurado no Render.", 500

    if not CLIENT_SECRET:
        return "ML_CLIENT_SECRET não configurado no Render.", 500

    if not REDIRECT_URI:
        return "ML_REDIRECT_URI não configurado no Render.", 500

    # ========================================================
    # CALLBACK OAUTH
    # ========================================================

    if code:

        saved_state = session.get("state")

        if not saved_state:

            return """
            <h2>Erro: sessão expirada.</h2>

            <p>
                Volte e conecte novamente sua conta.
            </p>

            <a href="/">
                Voltar
            </a>
            """, 400

        if state != saved_state:

            return """
            <h2>Erro: state inválido.</h2>

            <a href="/">
                Voltar
            </a>
            """, 400

        code_verifier = session.get("code_verifier")

        if not code_verifier:

            return """
            <h2>Erro: code_verifier não encontrado.</h2>

            <a href="/">
                Voltar
            </a>
            """, 400

        # ====================================================
        # TROCA CODE POR TOKEN
        # ====================================================

        try:

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

        except requests.RequestException as e:

            return f"""
            <h1>Erro de conexão</h1>

            <pre>{escapar(e)}</pre>

            <a href="/">
                Voltar
            </a>
            """, 500

        if response.status_code != 200:

            return f"""
            <h1>Erro ao obter token</h1>

            <p>
                Status:
                <strong>{response.status_code}</strong>
            </p>

            <pre>{escapar(response.text)}</pre>

            <a href="/">
                Voltar
            </a>
            """, 400

        try:

            token_data = response.json()

        except Exception:

            return """
            <h2>Resposta inválida ao obter token.</h2>

            <a href="/">
                Voltar
            </a>
            """, 400

        access_token = token_data.get(
            "access_token"
        )

        if not access_token:

            return """
            <h2>Access Token não recebido.</h2>

            <a href="/">
                Voltar
            </a>
            """, 400

        # ====================================================
        # SALVA TOKEN
        # ====================================================

        session["access_token"] = access_token

        # Guarda também informações úteis do token
        session["token_type"] = token_data.get(
            "token_type"
        )

        session["expires_in"] = token_data.get(
            "expires_in"
        )

        session["user_id"] = token_data.get(
            "user_id"
        )

        # Limpa PKCE
        session.pop("code_verifier", None)
        session.pop("state", None)

        # ====================================================
        # CONSULTA USUÁRIO
        # ====================================================

        try:

            user_response = requests.get(

                "https://api.mercadolibre.com/users/me",

                headers={
                    "Authorization":
                        f"Bearer {access_token}",

                    "Accept":
                        "application/json",

                    "User-Agent":
                        "Robô-Ofertas-ML/1.0",
                },

                timeout=30,
            )

        except requests.RequestException as e:

            return f"""
            <h1>Erro de conexão com Mercado Livre</h1>

            <pre>{escapar(e)}</pre>

            <a href="/">
                Voltar
            </a>
            """, 500

        if user_response.status_code != 200:

            return f"""
            <h1>Erro ao consultar conta</h1>

            <p>
                Status:
                <strong>{user_response.status_code}</strong>
            </p>

            <pre>{escapar(user_response.text)}</pre>

            <a href="/">
                Voltar
            </a>
            """, 400

        try:

            user_data = user_response.json()

        except Exception:

            return """
            <h2>Resposta inválida do usuário.</h2>

            <a href="/">
                Voltar
            </a>
            """, 400

        nickname = user_data.get(
            "nickname",
            "usuário"
        )

        user_id = user_data.get(
            "id",
            "não informado"
        )

        session["user_id"] = user_id

        return pagina_principal(
            nickname,
            user_id
        )

    # ========================================================
    # CRIA PKCE
    # ========================================================

    code_verifier = secrets.token_urlsafe(64)

    code_challenge = (
        base64.urlsafe_b64encode(
            hashlib.sha256(
                code_verifier.encode()
            ).digest()
        )
        .rstrip(b"=")
        .decode()
    )

    state = secrets.token_urlsafe(32)

    session["code_verifier"] = code_verifier
    session["state"] = state

    # ========================================================
    # URL DE AUTORIZAÇÃO
    # ========================================================

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

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>Robô Ofertas ML</title>

    </head>

    <body style="
        font-family:Arial;
        background:#f5f5f5;
        padding:30px;
        text-align:center;
    ">

        <h1>🤖 Robô Ofertas ML</h1>

        <p>
            Conecte sua conta do Mercado Livre
        </p>

        <a href="{auth_url}">

            <button style="
                padding:15px 25px;
                font-size:18px;
                border:0;
                border-radius:8px;
                background:#3483fa;
                color:white;
            ">
                🔐 Conectar Mercado Livre
            </button>

        </a>

    </body>

    </html>
    """


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

def pagina_principal(nickname, user_id):

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>Robô Ofertas ML</title>

        <style>

            body {{
                font-family: Arial;
                background: #f5f5f5;
                margin: 0;
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
                width: 100%;
                box-sizing: border-box;
                padding: 14px;
                font-size: 17px;
                border: 1px solid #ccc;
                border-radius: 8px;
                margin-bottom: 10px;
            }}

            button {{
                width: 100%;
                padding: 14px;
                font-size: 17px;
                border: 0;
                border-radius: 8px;
                background: #3483fa;
                color: white;
            }}

            .diagnostico {{
                display: block;
                margin-top: 20px;
                text-decoration: none;
                color: #3483fa;
            }}

        </style>

    </head>

    <body>

        <div class="container">

            <h1>🤖 Robô Ofertas ML</h1>

            <p>✅ Mercado Livre conectado!</p>

            <p>
                Usuário:
                <strong>{escapar(nickname)}</strong>
            </p>

            <p>
                ID:
                <strong>{escapar(user_id)}</strong>
            </p>

            <hr>

            <h2>🔎 Buscar produtos atuais</h2>

            <form action="/buscar" method="get">

                <input
                    type="text"
                    name="q"
                    placeholder="Ex: celular, tênis, relógio..."
                    required
                >

                <button type="submit">
                    🔎 Buscar produtos
                </button>

            </form>

            <a
                class="diagnostico"
                href="/diagnostico"
            >
                🧪 Diagnóstico da API
            </a>

        </div>

    </body>

    </html>
    """


# ============================================================
# BUSCA
# ============================================================

@app.route("/buscar")
def buscar():

    termo = request.args.get(
        "q",
        ""
    ).strip()

    if not termo:

        return """
        <h2>Digite um produto para pesquisar.</h2>

        <a href="/">
            Voltar
        </a>
        """, 400

    try:

        offset = int(
            request.args.get(
                "offset",
                0
            )
        )

    except Exception:

        offset = 0

    # Limite máximo
    limit = 50

    # Evita valores negativos
    offset = max(0, offset)

    # ========================================================
    # VERIFICA TOKEN
    # ========================================================

    access_token = session.get(
        "access_token"
    )

    if not access_token:

        return """
        <h1>❌ Mercado Livre não conectado</h1>

        <p>
            Conecte sua conta antes de fazer uma busca.
        </p>

        <a href="/">
            🔐 Conectar Mercado Livre
        </a>
        """, 401

    # ========================================================
    # BUSCA
    # ========================================================

    response = buscar_mercado_livre(
        termo,
        limit,
        offset
    )

    if response is None:

        return """
        <h1>❌ Erro na busca</h1>

        <p>
            Não foi possível conectar ao Mercado Livre.
        </p>

        <a href="/">
            ← Voltar
        </a>
        """, 500

    # ========================================================
    # ERRO DA API
    # ========================================================

    if response.status_code != 200:

        return f"""
        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>Erro Mercado Livre</title>

        </head>

        <body style="
            font-family:Arial;
            background:#f5f5f5;
            padding:20px;
        ">

        <div style="
            max-width:800px;
            margin:auto;
            background:white;
            padding:25px;
            border-radius:12px;
        ">

            <h1>❌ Erro na busca</h1>

            <p>
                Status da API:
                <strong>{response.status_code}</strong>
            </p>

            <p>
                Resposta do Mercado Livre:
            </p>

            <pre>{escapar(response.text)}</pre>

            <hr>

            <p>
                Se o status for 403, abra a página de diagnóstico
                para verificar token, usuário e acesso à API.
            </p>

            <a href="/diagnostico">
                🧪 Abrir diagnóstico
            </a>

            <br><br>

            <a href="/">
                ← Voltar
            </a>

        </div>

        </body>

        </html>
        """, response.status_code

    # ========================================================
    # JSON
    # ========================================================

    try:

        data = response.json()

    except Exception:

        return """
        <h1>❌ Resposta inválida</h1>

        <a href="/">
            ← Voltar
        </a>
        """, 500

    produtos = data.get(
        "results",
        []
    )

    paging = data.get(
        "paging",
        {}
    )

    total = paging.get(
        "total",
        0
    )

    # ========================================================
    # HTML
    # ========================================================

    html_page = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>
            Busca - {escapar(termo)}
        </title>

        <style>

            body {{
                font-family: Arial;
                background: #f5f5f5;
                margin: 0;
                padding: 15px;
            }}

            .container {{
                max-width: 1000px;
                margin: auto;
            }}

            .top {{
                background: white;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 15px;
            }}

            .produto {{
                background: white;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 15px;
                box-shadow:
                    0 2px 8px rgba(0,0,0,.08);
            }}

            .produto img {{
                width: 220px;
                height: 220px;
                object-fit: contain;
                display: block;
                margin-bottom: 10px;
            }}

            .preco {{
                font-size: 25px;
                font-weight: bold;
                color: #008000;
                margin: 8px 0;
            }}

            .vendidos {{
                color: #555;
                margin: 8px 0;
            }}

            .info {{
                color: #555;
                margin: 6px 0;
            }}

            .botao {{
                display: inline-block;
                background: #3483fa;
                color: white;
                padding: 12px 18px;
                border-radius: 8px;
                text-decoration: none;
                margin-top: 10px;
            }}

            .paginas {{
                display: flex;
                justify-content: space-between;
                gap: 10px;
                margin: 20px 0;
            }}

            .paginas a {{
                background: #3483fa;
                color: white;
                padding: 12px 18px;
                border-radius: 8px;
                text-decoration: none;
            }}

        </style>

    </head>

    <body>

    <div class="container">

        <div class="top">

            <h1>
                🔎 {escapar(termo)}
            </h1>

            <p>
                <strong>
                    {total}
                </strong>
                anúncios encontrados
            </p>

            <p>
                Mostrando:
                <strong>{offset + 1}</strong>
                até
                <strong>
                    {min(offset + len(produtos), total)}
                </strong>
            </p>

            <p>
                🟢 Anúncios ativos
            </p>

            <a href="/">
                ← Nova pesquisa
            </a>

        </div>
    """

    # ========================================================
    # NENHUM PRODUTO
    # ========================================================

    if not produtos:

        html_page += """
        <div class="produto">

            <h2>
                Nenhum produto encontrado.
            </h2>

        </div>
        """

    # ========================================================
    # PRODUTOS
    # ========================================================

    for produto in produtos:

        item_id = produto.get(
            "id",
            ""
        )

        titulo = produto.get(
            "title",
            "Produto sem título"
        )

        preco = produto.get(
            "price"
        )

        vendidos = produto.get(
            "sold_quantity",
            0
        )

        link = produto.get(
            "permalink",
            "#"
        )

        imagem = produto.get(
            "thumbnail",
            ""
        )

        categoria = produto.get(
            "category_id",
            "Não informada"
        )

        condicao = produto.get(
            "condition",
            "Não informada"
        )

        # ====================================================
        # LOCALIZAÇÃO
        # ====================================================

        endereco = produto.get(
            "address",
            {}
        ) or {}

        cidade = endereco.get(
            "city_name",
            ""
        )

        estado = endereco.get(
            "state_name",
            ""
        )

        localizacao = (
            f"{cidade} - {estado}"
            if cidade
            else "Localização não informada"
        )

        # ====================================================
        # ESCAPE
        # ====================================================

        titulo_html = escapar(titulo)
        link_html = escapar(link)
        imagem_html = escapar(imagem)
        categoria_html = escapar(categoria)
        condicao_html = escapar(condicao)
        localizacao_html = escapar(localizacao)
        item_id_html = escapar(item_id)
        vendidos_html = escapar(vendidos)

        preco_texto = formatar_preco(
            preco
        )

        html_page += f"""

        <div class="produto">

            <img
                src="{imagem_html}"
                alt="{titulo_html}"
                loading="lazy"
            >

            <h2>
                {titulo_html}
            </h2>

            <div class="preco">
                {preco_texto}
            </div>

            <div class="vendidos">
                🔥
                <strong>{vendidos_html}</strong>
                vendidos
            </div>

            <div class="info">
                📂 Categoria:
                {categoria_html}
            </div>

            <div class="info">
                📍
                {localizacao_html}
            </div>

            <div class="info">
                🏷️
                {condicao_html}
            </div>

            <div class="info">
                🆔
                {item_id_html}
            </div>

            <a
                class="botao"
                href="{link_html}"
                target="_blank"
                rel="noopener noreferrer"
            >
                🛒 Ver anúncio
            </a>

        </div>

        """

    # ========================================================
    # PAGINAÇÃO
    # ========================================================

    html_page += """
        <div class="paginas">
    """

    if offset > 0:

        anterior = max(
            0,
            offset - limit
        )

        html_page += f"""
            <a
                href="/buscar?q={escapar(termo)}&offset={anterior}"
            >
                ← Anterior
            </a>
        """

    else:

        html_page += "<span></span>"

    if offset + limit < total:

        proximo = offset + limit

        html_page += f"""
            <a
                href="/buscar?q={escapar(termo)}&offset={proximo}"
            >
                Próximos 50 →
            </a>
        """

    html_page += """
        </div>
    </div>

    </body>

    </html>
    """

    return html_page


# ============================================================
# DIAGNÓSTICO DO MERCADO LIVRE
# ============================================================

@app.route("/diagnostico")
def diagnostico():

    access_token = session.get(
        "access_token"
    )

    if not access_token:

        return """
        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>Diagnóstico</title>

        </head>

        <body style="
            font-family:Arial;
            background:#f5f5f5;
            padding:20px;
        ">

        <div style="
            max-width:900px;
            margin:auto;
            background:white;
            padding:20px;
            border-radius:12px;
        ">

            <h1>❌ Sem Access Token</h1>

            <p>
                Conecte sua conta do Mercado Livre primeiro.
            </p>

            <a href="/">
                Voltar
            </a>

        </div>

        </body>

        </html>
        """, 401

    resultado = []

    # ========================================================
    # 1 - USERS/ME
    # ========================================================

    try:

        r_user = requests.get(

            "https://api.mercadolibre.com/users/me",

            headers={
                "Authorization":
                    f"Bearer {access_token}",

                "Accept":
                    "application/json",

                "User-Agent":
                    "Robô-Ofertas-ML/1.0",
            },

            timeout=30,
        )

        resultado.append(f"""
        <div style="
            background:#f8f8f8;
            padding:15px;
            border-radius:10px;
            margin-bottom:20px;
        ">

            <h2>1️⃣ /users/me</h2>

            <p>
                Status:
                <strong>
                    {r_user.status_code}
                </strong>
            </p>

            <pre>
{escapar(r_user.text[:5000])}
            </pre>

        </div>
        """)

    except Exception as e:

        resultado.append(f"""
        <div>

            <h2>1️⃣ /users/me</h2>

            <pre>{escapar(e)}</pre>

        </div>
        """)

    # ========================================================
    # 2 - BUSCA SEM TOKEN
    # ========================================================

    try:

        r_publica = requests.get(

            "https://api.mercadolibre.com/sites/MLB/search",

            params={
                "q": "celular",
                "limit": 5
            },

            headers={
                "Accept":
                    "application/json",

                "User-Agent":
                    "Robô-Ofertas-ML/1.0",
            },

            timeout=30,
        )

        resultado.append(f"""
        <div style="
            background:#f8f8f8;
            padding:15px;
            border-radius:10px;
            margin-bottom:20px;
        ">

            <h2>2️⃣ Busca SEM token</h2>

            <p>
                Status:
                <strong>
                    {r_publica.status_code}
                </strong>
            </p>

            <pre>
{escapar(r_publica.text[:5000])}
            </pre>

        </div>
        """)

    except Exception as e:

        resultado.append(f"""
        <div>

            <h2>2️⃣ Busca SEM token</h2>

            <pre>{escapar(e)}</pre>

        </div>
        """)

    # ========================================================
    # 3 - BUSCA COM TOKEN
    # ========================================================

    try:

        r_token = requests.get(

            "https://api.mercadolibre.com/sites/MLB/search",

            params={
                "q": "celular",
                "limit": 5
            },

            headers={
                "Accept":
                    "application/json",

                "Authorization":
                    f"Bearer {access_token}",

                "User-Agent":
                    "Robô-Ofertas-ML/1.0",
            },

            timeout=30,
        )

        resultado.append(f"""
        <div style="
            background:#f8f8f8;
            padding:15px;
            border-radius:10px;
            margin-bottom:20px;
        ">

            <h2>3️⃣ Busca COM token</h2>

            <p>
                Status:
                <strong>
                    {r_token.status_code}
                </strong>
            </p>

            <pre>
{escapar(r_token.text[:5000])}
            </pre>

        </div>
        """)

    except Exception as e:

        resultado.append(f"""
        <div>

            <h2>3️⃣ Busca COM token</h2>

            <pre>{escapar(e)}</pre>

        </div>
        """)

    # ========================================================
    # RESULTADO
    # ========================================================

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>Diagnóstico Mercado Livre</title>

    </head>

    <body style="
        font-family:Arial;
        background:#f5f5f5;
        padding:20px;
    ">

    <div style="
        max-width:900px;
        margin:auto;
        background:white;
        padding:20px;
        border-radius:12px;
    ">

        <h1>
            🧪 Diagnóstico Mercado Livre
        </h1>

        <p>
            Não envie seu Access Token para ninguém.
        </p>

        {"".join(resultado)}

        <hr>

        <a href="/">
            ← Voltar
        </a>

    </div>

    </body>

    </html>
    """


# ============================================================
# TESTE DE CONFIGURAÇÃO
# ============================================================

@app.route("/teste-config")
def teste_config():

    return f"""
    <h1>🧪 Configuração</h1>

    <p>
        CLIENT_ID:
        <strong>
            {"OK" if CLIENT_ID else "FALTANDO"}
        </strong>
    </p>

    <p>
        CLIENT_SECRET:
        <strong>
            {"OK" if CLIENT_SECRET else "FALTANDO"}
        </strong>
    </p>

    <p>
        REDIRECT_URI:
        <strong>
            {escapar(REDIRECT_URI) if REDIRECT_URI else "FALTANDO"}
        </strong>
    </p>

    <p>
        SECRET_KEY:
        <strong>
            {"OK" if SECRET_KEY else "FALTANDO"}
        </strong>
    </p>

    <hr>

    <a href="/">
        ← Voltar
    </a>
    """


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.getenv(
                "PORT",
                10000
            )
        )
    )
