import os
import time
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
# APLICAÇÃO
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

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

API_BASE = "https://api.mercadolibre.com"

AUTH_URL = (
    "https://auth.mercadolivre.com.br/authorization"
)


# ============================================================
# TOKEN DO ROBÔ
#
# Como este robô é de uso próprio, mantemos também uma cópia
# no processo do servidor.
#
# Isso evita que uma rota veja a sessão e outra não veja.
# ============================================================

ML_TOKEN = None

ML_REFRESH_TOKEN = None

ML_USER_ID = None

ML_TOKEN_EXPIRES_AT = 0


# ============================================================
# CONFIGURAÇÕES
# ============================================================

LIMITE_PADRAO = 20

MARGEM_PADRAO = 10


# ============================================================
# UTILITÁRIOS
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
# TOKEN ATUAL
# ============================================================

def obter_token():

    global ML_TOKEN

    # Primeiro tenta a memória do servidor.
    if ML_TOKEN:

        return ML_TOKEN

    # Depois tenta a sessão.
    token = session.get(
        "access_token"
    )

    if token:

        ML_TOKEN = token

        return token

    return None


# ============================================================
# SALVAR TOKEN
# ============================================================

def salvar_tokens(dados):

    global ML_TOKEN
    global ML_REFRESH_TOKEN
    global ML_USER_ID
    global ML_TOKEN_EXPIRES_AT

    access_token = dados.get(
        "access_token"
    )

    refresh_token = dados.get(
        "refresh_token"
    )

    user_id = dados.get(
        "user_id"
    )

    expires_in = numero(
        dados.get(
            "expires_in",
            21600
        )
    )


    if not access_token:

        raise RuntimeError(
            "Mercado Livre não retornou access_token."
        )


    # Memória do servidor
    ML_TOKEN = access_token

    ML_REFRESH_TOKEN = (
        refresh_token
    )

    ML_USER_ID = user_id

    ML_TOKEN_EXPIRES_AT = (
        time.time()
        +
        expires_in
        -
        60
    )


    # Sessão
    session["access_token"] = (
        access_token
    )

    if refresh_token:

        session["refresh_token"] = (
            refresh_token
        )

    if user_id:

        session["user_id"] = (
            user_id
        )

    session["token_expires_at"] = (
        ML_TOKEN_EXPIRES_AT
    )

    session.modified = True


    print(
        "TOKEN SALVO COM SUCESSO."
    )

    print(
        "USER ID:",
        user_id
    )

    print(
        "EXPIRA EM:",
        int(expires_in),
        "segundos"
    )


# ============================================================
# REFRESH TOKEN
# ============================================================

def renovar_token():

    global ML_REFRESH_TOKEN

    refresh_token = (
        ML_REFRESH_TOKEN
        or
        session.get(
            "refresh_token"
        )
    )


    if not refresh_token:

        return False


    dados = {

        "grant_type":
            "refresh_token",

        "client_id":
            CLIENT_ID,

        "client_secret":
            CLIENT_SECRET,

        "refresh_token":
            refresh_token

    }


    try:

        resposta = requests.post(

            f"{API_BASE}/oauth/token",

            data=dados,

            headers={
                "Accept":
                    "application/json",

                "Content-Type":
                    "application/x-www-form-urlencoded"
            },

            timeout=30

        )

    except requests.exceptions.RequestException as erro:

        print(
            "ERRO REFRESH:",
            erro
        )

        return False


    print(
        "REFRESH STATUS:",
        resposta.status_code
    )


    if resposta.status_code != 200:

        print(
            "REFRESH RESPOSTA:",
            resposta.text[:1000]
        )

        return False


    try:

        dados_token = (
            resposta.json()
        )

    except ValueError:

        return False


    salvar_tokens(
        dados_token
    )

    return True


# ============================================================
# GARANTIR TOKEN
# ============================================================

def garantir_token():

    token = obter_token()


    if not token:

        return None


    # Verifica expiração conhecida.
    if (
        ML_TOKEN_EXPIRES_AT
        and
        time.time()
        >=
        ML_TOKEN_EXPIRES_AT
    ):

        print(
            "ACCESS TOKEN EXPIRADO. RENOVANDO..."
        )

        if renovar_token():

            return obter_token()

        return None


    return token


# ============================================================
# HEADERS API
# ============================================================

def headers_api():

    token = garantir_token()


    headers = {

        "Accept":
            "application/json",

        "User-Agent":
            "Robo-Ofertas-ML/5.0"

    }


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

    token = garantir_token()

    conectado = bool(
        token
    )


    return render_template(

        "index.html",

        conectado=conectado

    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login")
def login():

    if not CLIENT_ID:

        return (
            "ML_CLIENT_ID não configurado no Render.",
            500
        )


    if not CLIENT_SECRET:

        return (
            "ML_CLIENT_SECRET não configurado no Render.",
            500
        )


    if not REDIRECT_URI:

        return (
            "ML_REDIRECT_URI não configurado no Render.",
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

    code_verifier = secrets.token_urlsafe(
        64
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


    session["oauth_state"] = state

    session["code_verifier"] = (
        code_verifier
    )

    session.modified = True


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
        AUTH_URL
        +
        "?"
        +
        urlencode(
            parametros
        )
    )


    print(
        "LOGIN MERCADO LIVRE"
    )

    print(
        "REDIRECT:",
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

    erro = request.args.get(
        "error"
    )


    if erro:

        descricao = request.args.get(
            "error_description",
            erro
        )

        return (

            "<h2>Erro no Mercado Livre</h2>"

            "<p>"

            +
            descricao

            +
            "</p>"

        ), 400


    code = request.args.get(
        "code"
    )


    if not code:

        return (
            "Código de autorização não recebido.",
            400
        )


    state_recebido = request.args.get(
        "state"
    )

    state_salvo = session.get(
        "oauth_state"
    )


    if not state_salvo:

        return (

            "Sessão OAuth perdida. "
            "Volte ao robô e clique novamente "
            "em Conectar Mercado Livre."

        ), 400


    if state_recebido != state_salvo:

        return (
            "State OAuth inválido.",
            400
        )


    code_verifier = session.get(
        "code_verifier"
    )


    if not code_verifier:

        return (
            "code_verifier não encontrado.",
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


    print(
        "TROCANDO CODE POR TOKEN..."
    )


    try:

        resposta = requests.post(

            f"{API_BASE}/oauth/token",

            data=dados,

            headers={
                "Accept":
                    "application/json",

                "Content-Type":
                    "application/x-www-form-urlencoded"
            },

            timeout=30

        )

    except requests.exceptions.RequestException as erro:

        print(
            "ERRO OAUTH:",
            erro
        )

        return (
            "Não foi possível conectar ao Mercado Livre.",
            502
        )


    print(
        "OAUTH STATUS:",
        resposta.status_code
    )


    if resposta.status_code != 200:

        print(
            "OAUTH ERRO:",
            resposta.text[:1500]
        )

        return (

            "<h2>Mercado Livre recusou a conexão</h2>"

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


    try:

        salvar_tokens(
            token_data
        )

    except Exception as erro:

        print(
            "ERRO SALVANDO TOKEN:",
            erro
        )

        return (
            "Token recebido, mas não foi possível salvá-lo.",
            500
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


    # --------------------------------------------------------
    # TESTE IMEDIATO
    # --------------------------------------------------------

    token = obter_token()


    if not token:

        return (
            "O Mercado Livre autorizou, "
            "mas o token não ficou disponível.",
            500
        )


    try:

        teste = requests.get(

            f"{API_BASE}/users/me",

            headers={
                "Authorization":
                    f"Bearer {token}",

                "Accept":
                    "application/json",

                "User-Agent":
                    "Robo-Ofertas-ML/5.0"
            },

            timeout=30

        )


        print(
            "TESTE USERS/ME:",
            teste.status_code
        )


        if teste.status_code in (
            200,
            206
        ):

            print(
                "MERCADO LIVRE CONECTADO!"
            )

        else:

            print(
                "USERS/ME:",
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
# STATUS
# ============================================================

@app.route("/api/status")
def api_status():

    token = garantir_token()


    return jsonify({

        "ok":
            True,

        "app":
            "Robo de Ofertas",

        "mercado_livre":
            bool(token),

        "user_id":
            ML_USER_ID
            or
            session.get(
                "user_id"
            ),

        "versao":
            "5.0"

    })


# ============================================================
# MINHA CONTA
# ============================================================

@app.route("/api/me")
def api_me():

    token = garantir_token()


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

            timeout=30

        )

    except requests.exceptions.RequestException as erro:

        return jsonify({

            "ok":
                False,

            "mercado_livre":
                True,

            "mensagem":
                "Erro de conexão com Mercado Livre.",

            "detalhes":
                str(erro)

        }), 502


    print(
        "API /users/me:",
        resposta.status_code
    )


    if resposta.status_code in (
        401,
        403
    ):

        print(
            "TOKEN RECUSADO. TENTANDO REFRESH..."
        )


        if renovar_token():

            try:

                resposta = requests.get(

                    f"{API_BASE}/users/me",

                    headers=headers_api(),

                    timeout=30

                )

            except requests.exceptions.RequestException as erro:

                return jsonify({

                    "ok":
                        False,

                    "mensagem":
                        str(erro)

                }), 502


    if resposta.status_code not in (
        200,
        206
    ):

        return jsonify({

            "ok":
                False,

            "mercado_livre":
                True,

            "status":
                resposta.status_code,

            "mensagem":
                "Mercado Livre recusou a requisição.",

            "resposta":
                resposta.text[:2000]

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
# BUSCA DE PRODUTOS
# ============================================================

def buscar_produtos(
    termo,
    limite=20
):

    token = garantir_token()


    if not token:

        raise RuntimeError(
            "Mercado Livre não está conectado."
        )


    termo = str(
        termo or ""
    ).strip()


    if not termo:

        return []


    try:

        limite = int(
            limite
        )

    except (TypeError, ValueError):

        limite = 20


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


    params = {

        "q":
            termo,

        "limit":
            limite,

        "offset":
            0

    }


    try:

        resposta = requests.get(

            url,

            params=params,

            headers=headers_api(),

            timeout=30

        )

    except requests.exceptions.RequestException as erro:

        raise RuntimeError(
            "Erro de conexão com Mercado Livre: "
            +
            str(erro)
        )


    print(
        "BUSCA:",
        termo,
        "STATUS:",
        resposta.status_code
    )


    # --------------------------------------------------------
    # TOKEN EXPIRADO / RECUSADO
    # --------------------------------------------------------

    if resposta.status_code in (
        401,
        403
    ):

        print(
            "TOKEN RECUSADO NA BUSCA."
        )


        if renovar_token():

            try:

                resposta = requests.get(

                    url,

                    params=params,

                    headers=headers_api(),

                    timeout=30

                )

            except requests.exceptions.RequestException as erro:

                raise RuntimeError(
                    str(erro)
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
            preco
            +
            lucro
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
# API BUSCA
# ============================================================

@app.route("/api/buscar")
def api_buscar():

    termo = request.args.get(
        "produto",
        ""
    ).strip()


    limite = request.args.get(
        "limite",
        20
    )


    if not termo:

        return jsonify({

            "ok":
                False,

            "produtos":
                [],

            "mensagem":
                "Digite o nome de um produto."

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
# DESCONEXÃO
# ============================================================

@app.route("/logout")
def logout():

    global ML_TOKEN
    global ML_REFRESH_TOKEN
    global ML_USER_ID
    global ML_TOKEN_EXPIRES_AT

    ML_TOKEN = None

    ML_REFRESH_TOKEN = None

    ML_USER_ID = None

    ML_TOKEN_EXPIRES_AT = 0

    session.clear()


    return redirect(
        "/"
    )


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "ok":
            True,

        "status":
            "online",

        "versao":
            "5.0"

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
# ERRO 500
# ============================================================

@app.errorhandler(500)
def erro_500(erro):

    print(
        "ERRO 500:",
        erro
    )


    if request.path.startswith(
        "/api/"
    ):

        return jsonify({

            "ok":
                False,

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
