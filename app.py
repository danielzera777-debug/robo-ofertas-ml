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
# APP
# ============================================================

app = Flask(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)

app.secret_key = SECRET_KEY

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True


# ============================================================
# MERCADO LIVRE
# ============================================================

CLIENT_ID = os.getenv(
    "ML_CLIENT_ID"
)

CLIENT_SECRET = os.getenv(
    "ML_CLIENT_SECRET"
)

REDIRECT_URI = os.getenv(
    "ML_REDIRECT_URI"
)

API_BASE = (
    "https://api.mercadolibre.com"
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

LIMITE_PADRAO = 20

MARGEM_PADRAO = 10


# ============================================================
# FUNÇÕES AUXILIARES
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


# ============================================================
# HEADERS
# ============================================================

def headers_api():

    headers = {
        "Accept":
            "application/json",

        "User-Agent":
            "Robo-Ofertas-ML/4.0"
    }

    token = session.get(
        "access_token"
    )

    if token:

        headers["Authorization"] = (
            f"Bearer {token}"
        )

    return headers


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
# LOGIN MERCADO LIVRE
# ============================================================

@app.route("/login")
def login():

    if not CLIENT_ID:

        return (
            "ERRO: ML_CLIENT_ID não configurado no Render.",
            500
        )


    if not CLIENT_SECRET:

        return (
            "ERRO: ML_CLIENT_SECRET não configurado no Render.",
            500
        )


    if not REDIRECT_URI:

        return (
            "ERRO: ML_REDIRECT_URI não configurado no Render.",
            500
        )


    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    state = secrets.token_urlsafe(
        32
    )


    # --------------------------------------------------------
    # PKCE
    # --------------------------------------------------------

    code_verifier = (
        secrets.token_urlsafe(
            64
        )
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
        .decode(
            "utf-8"
        )
        .rstrip("=")

    )


    # --------------------------------------------------------
    # SALVAR NA SESSÃO
    # --------------------------------------------------------

    session["oauth_state"] = state

    session["code_verifier"] = (
        code_verifier
    )


    session.modified = True


    # --------------------------------------------------------
    # URL DO MERCADO LIVRE
    # --------------------------------------------------------

    parametros = {

        "response_type":
            "code",

        "client_id":
            CLIENT_ID,

        "redirect_uri":
            REDIRECT_URI,

        "state":
            state,

        "code_challenge":
            code_challenge,

        "code_challenge_method":
            "S256"

    }


    url = (

        "https://auth.mercadolivre.com.br/authorization?"

        +
        urlencode(
            parametros
        )

    )


    print(
        "INICIANDO LOGIN MERCADO LIVRE"
    )

    print(
        "REDIRECT_URI:",
        REDIRECT_URI
    )


    return redirect(
        url
    )


# ============================================================
# CALLBACK
# ============================================================

@app.route("/callback")
def callback():

    # --------------------------------------------------------
    # ERRO
    # --------------------------------------------------------

    erro = request.args.get(
        "error"
    )


    if erro:

        descricao = request.args.get(
            "error_description",
            erro
        )


        return (
            "Mercado Livre retornou erro: "
            + descricao,
            400
        )


    # --------------------------------------------------------
    # CODE
    # --------------------------------------------------------

    code = request.args.get(
        "code"
    )


    if not code:

        return (
            "Código de autorização não recebido.",
            400
        )


    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    state_recebido = request.args.get(
        "state"
    )


    state_salvo = session.get(
        "oauth_state"
    )


    if not state_salvo:

        return (
            "Sessão OAuth perdida. "
            "Clique novamente em Conectar Mercado Livre.",
            400
        )


    if state_recebido != state_salvo:

        return (
            "State OAuth inválido.",
            400
        )


    # --------------------------------------------------------
    # CODE VERIFIER
    # --------------------------------------------------------

    code_verifier = session.get(
        "code_verifier"
    )


    if not code_verifier:

        return (
            "code_verifier não encontrado. "
            "Inicie a conexão novamente.",
            400
        )


    # --------------------------------------------------------
    # TROCAR CODE POR TOKEN
    # --------------------------------------------------------

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


    print(
        "TROCANDO CODE POR TOKEN..."
    )


    try:

        resposta = requests.post(

            f"{API_BASE}/oauth/token",

            data=dados,

            headers={
                "Accept":
                    "application/json"
            },

            timeout=30

        )

    except requests.exceptions.RequestException as erro:

        print(
            "ERRO OAUTH:",
            erro
        )

        return (
            "Erro de conexão com "
            "o Mercado Livre.",
            502
        )


    print(
        "OAUTH STATUS:",
        resposta.status_code
    )

    print(
        "OAUTH RESPOSTA:",
        resposta.text[:2000]
    )


    if resposta.status_code != 200:

        return (

            "Mercado Livre recusou "
            "a autorização.<br><br>"

            "<pre>"

            +
            resposta.text

            +
            "</pre>"

        ), 400


    try:

        token_data = (
            resposta.json()
        )

    except ValueError:

        return (
            "Resposta inválida do Mercado Livre.",
            502
        )


    access_token = token_data.get(
        "access_token"
    )


    refresh_token = token_data.get(
        "refresh_token"
    )


    if not access_token:

        return (
            "Mercado Livre não retornou access_token.",
            400
        )


    # --------------------------------------------------------
    # SALVAR TOKEN
    # --------------------------------------------------------

    session["access_token"] = (
        access_token
    )


    if refresh_token:

        session["refresh_token"] = (
            refresh_token
        )


    if token_data.get(
        "user_id"
    ):

        session["user_id"] = (
            token_data.get(
                "user_id"
            )
        )


    session.pop(
        "oauth_state",
        None
    )


    session.pop(
        "code_verifier",
        None
    )


    session.modified = True


    print(
        "MERCADO LIVRE CONECTADO!"
    )


    # --------------------------------------------------------
    # TESTAR TOKEN
    # --------------------------------------------------------

    try:

        teste = requests.get(

            f"{API_BASE}/users/me",

            headers={
                "Authorization":
                    f"Bearer {access_token}",

                "Accept":
                    "application/json",

                "User-Agent":
                    "Robo-Ofertas-ML/4.0"
            },

            timeout=20

        )


        print(
            "TESTE TOKEN:",
            teste.status_code
        )


        print(
            "TESTE RESPOSTA:",
            teste.text[:1000]
        )


    except Exception as erro:

        print(
            "ERRO TESTANDO TOKEN:",
            erro
        )


    return redirect(
        "/"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        "/"
    )


# ============================================================
# STATUS
# ============================================================

@app.route("/api/status")
def api_status():

    token = session.get(
        "access_token"
    )


    return jsonify({

        "ok":
            True,

        "app":
            "Robo de Ofertas",

        "mercado_livre":
            bool(token),

        "versao":
            "4.0"

    })


# ============================================================
# TESTE DA CONTA
# ============================================================

@app.route("/api/me")
def api_me():

    token = session.get(
        "access_token"
    )


    if not token:

        return jsonify({

            "ok":
                False,

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

            "ok":
                False,

            "mensagem":
                str(erro)

        }), 502


    print(
        "USERS/ME:",
        resposta.status_code
    )

    print(
        resposta.text[:1000]
    )


    if resposta.status_code != 200:

        return jsonify({

            "ok":
                False,

            "mercado_livre":
                False,

            "status":
                resposta.status_code,

            "mensagem":
                resposta.text

        }), resposta.status_code


    try:

        dados = (
            resposta.json()
        )

    except ValueError:

        dados = {}


    return jsonify({

        "ok":
            True,

        "mercado_livre":
            True,

        "dados":
            dados

    })


# ============================================================
# BUSCAR PRODUTOS
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


    if not session.get(
        "access_token"
    ):

        raise RuntimeError(
            "Mercado Livre não está conectado."
        )


    try:

        limite = int(
            limite
        )

    except (TypeError, ValueError):

        limite = LIMITE_PADRAO


    limite = max(
        1,
        min(
            limite,
            50
        )
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
        "BUSCANDO:",
        termo
    )


    try:

        resposta = requests.get(

            url,

            params=parametros,

            headers=headers_api(),

            timeout=30

        )

    except requests.exceptions.RequestException as erro:

        raise RuntimeError(
            "Erro de conexão com Mercado Livre: "
            + str(erro)
        )


    print(
        "BUSCA STATUS:",
        resposta.status_code
    )


    print(
        "BUSCA RESPOSTA:",
        resposta.text[:2000]
    )


    if resposta.status_code != 200:

        raise RuntimeError(

            "Mercado Livre respondeu "

            +
            str(
                resposta.status_code
            )

            +
            ": "

            +
            resposta.text[:1000]

        )


    try:

        dados = (
            resposta.json()
        )

    except ValueError:

        raise RuntimeError(
            "Resposta inválida do Mercado Livre."
        )


    resultados = dados.get(
        "results",
        []
    )


    produtos = []


    for item in resultados:

        preco = numero(
            item.get(
                "price"
            )
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


        revenda = (
            preco + lucro
        )


        produtos.append({

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
                preco,

            "preco_formatado":
                formatar_preco(
                    preco
                ),

            "revenda":
                revenda,

            "revenda_formatada":
                formatar_preco(
                    revenda
                ),

            "lucro":
                lucro,

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

            "categoria":
                item.get(
                    "category_id",
                    ""
                ),

            "condicao":
                item.get(
                    "condition",
                    ""
                ),

            "vendidos":
                item.get(
                    "sold_quantity",
                    0
                )

        })


    return produtos


# ============================================================
# API BUSCAR
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

            "ok":
                False,

            "produtos":
                [],

            "mensagem":
                "Digite um produto."

        }), 400


    try:

        produtos = buscar_produtos(

            termo,

            limite

        )


        return jsonify({

            "ok":
                True,

            "termo":
                termo,

            "quantidade":
                len(produtos),

            "produtos":
                produtos

        })


    except Exception as erro:

        print(
            "ERRO BUSCA:",
            erro
        )


        return jsonify({

            "ok":
                False,

            "produtos":
                [],

            "mensagem":
                str(erro)

        }), 502


# ============================================================
# OFERTAS
# ============================================================

@app.route("/ofertas/<termo>")
def ofertas(termo):

    try:

        produtos = buscar_produtos(
            termo
        )


        return jsonify({

            "ok":
                True,

            "termo":
                termo,

            "quantidade":
                len(produtos),

            "produtos":
                produtos

        })


    except Exception as erro:

        return jsonify({

            "ok":
                False,

            "produtos":
                [],

            "mensagem":
                str(erro)

        }), 502


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


    mensagem = f"""🔥 OFERTA 🔥

📦 {titulo}

💰 {preco}

🛒 Confira:
{link}

⚡ Aproveite!
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

Receba ofertas e promoções todos os dias.

📱 Produtos de várias categorias
💰 Achadinhos
⚡ Promoções

👉 Entre no nosso grupo do WhatsApp.

#ofertas #promocoes #descontos
"""


    return jsonify({

        "ok":
            True,

        "mensagem":
            mensagem

    })


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
            "online"

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
# 404
# ============================================================

@app.errorhandler(404)
def erro_404(erro):

    if request.path.startswith(
        "/api/"
    ):

        return jsonify({

            "ok":
                False,

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
# 500
# ============================================================

@app.errorhandler(500)
def erro_500(erro):

    print(
        "ERRO 500:",
        erro
    )


    return jsonify({

        "ok":
            False,

        "mensagem":
            "Erro interno no aplicativo."

    }), 500


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
