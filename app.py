import os
import secrets
import hashlib
import base64
import requests

from urllib.parse import urlencode

from flask import (
    Flask,
    request,
    session,
    redirect,
    jsonify,
    render_template
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True


# ============================================================
# MERCADO LIVRE
# ============================================================

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

API_BASE = "https://api.mercadolibre.com"


# ============================================================
# CONFIGURAÇÕES
# ============================================================

LIMITE_PADRAO = 20
MARGEM_PADRAO = 10


# ============================================================
# AUXILIARES
# ============================================================

def numero(valor):

    try:
        return float(valor)

    except (TypeError, ValueError):
        return 0.0


def formatar_preco(valor):

    valor = numero(valor)

    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def headers_api():

    headers = {
        "Accept": "application/json",
        "User-Agent": "Robo-Ofertas-ML/3.1"
    }

    token = session.get("access_token")

    if token:

        headers["Authorization"] = (
            f"Bearer {token}"
        )

    return headers


# ============================================================
# BUSCA DE PRODUTOS
# ============================================================

def buscar_produtos(
    termo,
    limite=LIMITE_PADRAO
):

    termo = str(
        termo or ""
    ).strip()


    if not termo:

        return []


    try:

        limite = int(limite)

    except (TypeError, ValueError):

        limite = LIMITE_PADRAO


    limite = max(
        1,
        min(limite, 50)
    )


    url = (
        f"{API_BASE}/sites/MLB/search"
    )


    parametros = {

        "q":
            termo,

        "limit":
            limite,

        "sort":
            "relevance"

    }


    print(
        "================================================"
    )

    print(
        "BUSCA MERCADO LIVRE"
    )

    print(
        "TERMO:",
        termo
    )

    print(
        "URL:",
        url
    )

    print(
        "TOKEN EXISTE:",
        bool(
            session.get(
                "access_token"
            )
        )
    )


    try:

        resposta = requests.get(

            url,

            params=parametros,

            headers=headers_api(),

            timeout=20

        )


    except requests.exceptions.RequestException as erro:

        print(
            "ERRO DE CONEXÃO:",
            erro
        )

        raise RuntimeError(
            "Não foi possível conectar "
            "ao Mercado Livre: "
            + str(erro)
        )


    print(
        "STATUS:",
        resposta.status_code
    )

    print(
        "RESPOSTA:",
        resposta.text[:2000]
    )


    # ========================================================
    # ERRO DA API
    # ========================================================

    if resposta.status_code != 200:

        raise RuntimeError(

            "Mercado Livre respondeu "

            + str(
                resposta.status_code
            )

            + ": "

            + resposta.text[:1000]

        )


    # ========================================================
    # JSON
    # ========================================================

    try:

        dados = resposta.json()

    except ValueError:

        raise RuntimeError(
            "O Mercado Livre retornou "
            "uma resposta que não é JSON."
        )


    resultados = dados.get(
        "results",
        []
    )


    ofertas = []


    for item in resultados:


        preco = numero(
            item.get("price")
        )


        if preco <= 0:

            continue


        lucro = (

            preco
            *
            MARGEM_PADRAO
            /
            100

        )


        preco_revenda = (
            preco + lucro
        )


        ofertas.append({

            "id":
                item.get(
                    "id"
                ),

            "titulo":
                item.get(
                    "title",
                    "Produto"
                ),

            "preco":
                round(
                    preco,
                    2
                ),

            "preco_formatado":
                formatar_preco(
                    preco
                ),

            "revenda":
                round(
                    preco_revenda,
                    2
                ),

            "revenda_formatada":
                formatar_preco(
                    preco_revenda
                ),

            "lucro":
                round(
                    lucro,
                    2
                ),

            "lucro_formatado":
                formatar_preco(
                    lucro
                ),

            "imagem":
                item.get(
                    "thumbnail",
                    ""
                ),

            "link":
                item.get(
                    "permalink",
                    ""
                ),

            "condicao":
                item.get(
                    "condition",
                    ""
                ),

            "categoria":
                item.get(
                    "category_id",
                    ""
                ),

            "vendidos":
                item.get(
                    "sold_quantity",
                    0
                )

        })


    print(
        "PRODUTOS ENCONTRADOS:",
        len(ofertas)
    )


    return ofertas


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route("/")
def inicio():

    conectado = bool(
        session.get(
            "access_token"
        )
    )

    return render_template(
        "index.html",
        conectado=conectado
    )


# ============================================================
# API DE BUSCA
# ============================================================

@app.route("/api/buscar")
def api_buscar():

    termo = request.args.get(
        "produto",
        ""
    ).strip()


    limite = request.args.get(
        "limite",
        LIMITE_PADRAO
    )


    if not termo:

        return jsonify({

            "ok": False,

            "produtos": [],

            "mensagem":
                "Digite o nome de um produto."

        }), 400


    try:

        produtos = buscar_produtos(

            termo,

            limite

        )


        return jsonify({

            "ok": True,

            "termo": termo,

            "quantidade":
                len(produtos),

            "produtos":
                produtos

        })


    except Exception as erro:

        print(
            "ERRO NA BUSCA:",
            erro
        )


        return jsonify({

            "ok": False,

            "produtos": [],

            "mensagem":
                str(erro)

        }), 502


# ============================================================
# LOGIN MERCADO LIVRE - PKCE
# ============================================================

@app.route("/login")
def login():

    if not CLIENT_ID:

        return (
            "ERRO: ML_CLIENT_ID não está configurado.",
            500
        )


    if not REDIRECT_URI:

        return (
            "ERRO: ML_REDIRECT_URI não está configurado.",
            500
        )


    code_verifier = (
        secrets.token_urlsafe(64)
    )


    digest = hashlib.sha256(

        code_verifier.encode(
            "utf-8"
        )

    ).digest()


    code_challenge = (

        base64.urlsafe_b64encode(
            digest
        )
        .decode("utf-8")
        .rstrip("=")

    )


    session["code_verifier"] = (
        code_verifier
    )


    parametros = {

        "response_type":
            "code",

        "client_id":
            CLIENT_ID,

        "redirect_uri":
            REDIRECT_URI,

        "code_challenge":
            code_challenge,

        "code_challenge_method":
            "S256"

    }


    url = (

        "https://auth.mercadolivre.com.br/authorization?"

        +

        urlencode(parametros)

    )


    return redirect(url)


# ============================================================
# CALLBACK
# ============================================================

@app.route("/callback")
def callback():

    erro = request.args.get(
        "error"
    )


    if erro:

        descricao = request.args.get(
            "error_description",
            erro
        )

        return (
            "Erro do Mercado Livre: "
            + descricao,
            400
        )


    code = request.args.get(
        "code"
    )


    if not code:

        return (
            "Código de autorização não recebido.",
            400
        )


    code_verifier = session.get(
        "code_verifier"
    )


    if not code_verifier:

        return (
            "code_verifier não encontrado. "
            "Faça a conexão novamente.",
            400
        )


    dados = {

        "grant_type":
            "authorization_code",

        "client_id":
            CLIENT_ID,

        "client_secret":
            CLIENT_SECRET,

        "code":
            code,

        "redirect_uri":
            REDIRECT_URI,

        "code_verifier":
            code_verifier

    }


    try:

        resposta = requests.post(

            f"{API_BASE}/oauth/token",

            data=dados,

            headers={
                "Accept":
                    "application/json"
            },

            timeout=20

        )


    except requests.exceptions.RequestException as erro:

        print(
            "ERRO AO OBTER TOKEN:",
            erro
        )

        return (
            "Erro de conexão ao obter "
            "token do Mercado Livre.",
            502
        )


    print(
        "TOKEN STATUS:",
        resposta.status_code
    )

    print(
        "TOKEN RESPOSTA:",
        resposta.text[:1000]
    )


    if resposta.status_code != 200:

        return (
            "Mercado Livre recusou "
            "a autorização: "
            + resposta.text,
            400
        )


    try:

        token = resposta.json()

    except ValueError:

        return (
            "Resposta inválida "
            "do Mercado Livre.",
            502
        )


    access_token = token.get(
        "access_token"
    )


    if not access_token:

        return (
            "O Mercado Livre não retornou "
            "access_token.",
            400
        )


    session["access_token"] = (
        access_token
    )


    refresh_token = token.get(
        "refresh_token"
    )


    if refresh_token:

        session["refresh_token"] = (
            refresh_token
        )


    session.pop(
        "code_verifier",
        None
    )


    return redirect("/")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ============================================================
# STATUS
# ============================================================

@app.route("/api/status")
def api_status():

    conectado = bool(
        session.get(
            "access_token"
        )
    )


    return jsonify({

        "ok": True,

        "app":
            "Robo de Ofertas",

        "mercado_livre":
            conectado,

        "versao":
            "3.1"

    })


# ============================================================
# TESTE DA CONTA MERCADO LIVRE
# ============================================================

@app.route("/api/me")
def api_me():

    token = session.get(
        "access_token"
    )


    if not token:

        return jsonify({

            "ok": False,

            "mercado_livre":
                False,

            "mensagem":
                "Mercado Livre não conectado."

        }), 401


    try:

        resposta = requests.get(

            f"{API_BASE}/users/me",

            headers=headers_api(),

            timeout=20

        )


    except requests.exceptions.RequestException as erro:

        return jsonify({

            "ok": False,

            "mensagem":
                str(erro)

        }), 502


    print(
        "USERS/ME STATUS:",
        resposta.status_code
    )


    if resposta.status_code != 200:

        return jsonify({

            "ok": False,

            "status":
                resposta.status_code,

            "mensagem":
                resposta.text

        }), resposta.status_code


    try:

        dados = resposta.json()

    except ValueError:

        dados = {}


    return jsonify({

        "ok": True,

        "mercado_livre":
            True,

        "dados":
            dados

    })


# ============================================================
# WHATSAPP
# ============================================================

@app.route("/api/whatsapp")
def api_whatsapp():

    titulo = request.args.get(
        "titulo",
        "Oferta"
    )


    preco = request.args.get(
        "preco",
        "0"
    )


    link = request.args.get(
        "link",
        ""
    )


    mensagem = f"""🔥 OFERTA ENCONTRADA 🔥

📦 {titulo}

💰 Preço:
{preco}

🛒 Confira:
{link}

⚡ Aproveite enquanto estiver disponível!
"""


    return jsonify({

        "ok":
            True,

        "mensagem":
            mensagem

    })


# ============================================================
# INSTAGRAM
# ============================================================

@app.route("/api/instagram")
def api_instagram():

    mensagem = """🔥 GRUPO VIP DE OFERTAS 🔥

Quer receber ofertas e promoções todos os dias?

📱 Produtos de várias categorias
💰 Achadinhos e oportunidades
⚡ Ofertas por tempo limitado

Entre no nosso grupo do WhatsApp.

👉 Link na bio

#ofertas #promocoes #achadinhos #descontos
"""


    return jsonify({

        "ok":
            True,

        "mensagem":
            mensagem

    })


# ============================================================
# SERVICE WORKER
# ============================================================

@app.route("/service-worker.js")
def service_worker():

    return app.send_static_file(
        "service-worker.js"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
            "online"

    })


# ============================================================
# ERRO 404
# ============================================================

@app.errorhandler(404)
def erro_404(erro):

    if request.path.startswith(
        "/api/"
    ):

        return jsonify({

            "ok": False,

            "mensagem":
                "Rota não encontrada.",

            "rota":
                request.path

        }), 404


    return (
        "Página não encontrada.",
        404
    )


# ============================================================
# ERRO 500
# ============================================================

@app.errorhandler(500)
def erro_500(erro):

    print(
        "ERRO INTERNO:",
        erro
    )


    if request.path.startswith(
        "/api/"
    ):

        return jsonify({

            "ok": False,

            "mensagem":
                "Erro interno no aplicativo."

        }), 500


    return (
        "Erro interno no aplicativo.",
        500
    )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    porta = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )


    app.run(

        host="0.0.0.0",

        port=porta,

        debug=False

    )
