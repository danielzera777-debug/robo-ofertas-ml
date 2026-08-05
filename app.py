import os
import time
import secrets
import hashlib
import base64
import html
import logging
from urllib.parse import urlencode

import requests

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

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)

app.secret_key = SECRET_KEY

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    level=logging.INFO
)

logger = logging.getLogger(
    "robo-ofertas"
)


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

AUTH_URL = (
    "https://auth.mercadolivre.com.br/authorization"
)

SITE_ID = "MLB"


# ============================================================
# CONFIGURAÇÕES DO ROBÔ
# ============================================================

VERSAO = "6.0"

LIMITE_BUSCA = 20

MARGEM_PADRAO = 20.0

LUCRO_MINIMO_PADRAO = 10.0


# ============================================================
# TOKEN
#
# Mantemos uma cópia em memória para evitar depender
# somente da sessão do navegador.
# ============================================================

ACCESS_TOKEN = None

REFRESH_TOKEN = None

TOKEN_EXPIRA_EM = 0

USUARIO_ML = None


# ============================================================
# CATEGORIAS DO NICHO
# ============================================================

NICHOS = {

    "suplementos": {

        "nome": "🥤 Suplementos",

        "termos": [

            "whey protein",

            "whey",

            "creatina",

            "creatina monohidratada",

            "pré treino",

            "pre treino",

            "hipercalórico",

            "hipercalorico",

            "bcaa",

            "glutamina",

            "multivitamínico",

            "multivitaminico",

            "vitamina fitness",

            "barra proteica",

            "proteína",

            "proteina",

            "shaker"

        ]

    },


    "fitness_feminino": {

        "nome": "👩 Fitness Feminino",

        "termos": [

            "legging feminina academia",

            "top fitness feminino",

            "conjunto fitness feminino",

            "conjunto academia feminino",

            "short feminino academia",

            "short fitness feminino",

            "cropped fitness feminino",

            "macacão fitness feminino",

            "macacao fitness feminino",

            "calça fitness feminina",

            "calca fitness feminina",

            "camiseta fitness feminina",

            "jaqueta fitness feminina"

        ]

    },


    "fitness_masculino": {

        "nome": "👨 Fitness Masculino",

        "termos": [

            "camiseta dry fit masculina",

            "camiseta academia masculina",

            "regata academia masculina",

            "bermuda fitness masculina",

            "short academia masculino",

            "calça fitness masculina",

            "calca fitness masculina",

            "conjunto fitness masculino",

            "camiseta compressão masculina",

            "camiseta compressao masculina",

            "blusa academia masculina",

            "jaqueta fitness masculina"

        ]

    }

}


# ============================================================
# TODAS AS CATEGORIAS
# ============================================================

def todas_categorias():

    return list(
        NICHOS.keys()
    )


# ============================================================
# UTILITÁRIOS
# ============================================================

def numero(valor):

    try:

        return float(
            valor
        )

    except (
        TypeError,
        ValueError
    ):

        return 0.0


def inteiro(valor, padrao=20):

    try:

        return int(
            valor
        )

    except (
        TypeError,
        ValueError
    ):

        return padrao


def escapar(valor):

    return html.escape(
        str(
            valor or ""
        )
    )


def formatar_preco(valor):

    valor = numero(
        valor
    )

    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


# ============================================================
# CLASSIFICAÇÃO DO PRODUTO
# ============================================================

def classificar_produto(
    titulo
):

    texto = (
        str(
            titulo or ""
        )
        .lower()
    )


    # --------------------------------------------------------
    # SUPLEMENTOS
    # --------------------------------------------------------

    palavras_suplementos = [

        "whey",

        "creatina",

        "pré treino",

        "pre treino",

        "hipercalórico",

        "hipercalorico",

        "bcaa",

        "glutamina",

        "multivitamínico",

        "multivitaminico",

        "proteína",

        "proteina",

        "barra proteica"

    ]


    for palavra in palavras_suplementos:

        if palavra in texto:

            return "suplementos"


    # --------------------------------------------------------
    # FEMININO
    # --------------------------------------------------------

    palavras_feminino = [

        "legging feminina",

        "top fitness",

        "conjunto fitness feminino",

        "conjunto academia feminino",

        "short feminino",

        "cropped fitness",

        "macacão fitness",

        "macacao fitness",

        "calça fitness feminina",

        "calca fitness feminina"

    ]


    for palavra in palavras_feminino:

        if palavra in texto:

            return "fitness_feminino"


    # --------------------------------------------------------
    # MASCULINO
    # --------------------------------------------------------

    palavras_masculino = [

        "camiseta masculina",

        "camiseta dry fit",

        "regata masculina",

        "bermuda masculina",

        "short masculino",

        "calça fitness masculina",

        "calca fitness masculina",

        "conjunto fitness masculino",

        "compressão masculina",

        "compressao masculina"

    ]


    for palavra in palavras_masculino:

        if palavra in texto:

            return "fitness_masculino"


    return None


# ============================================================
# TOKEN
# ============================================================

def obter_access_token():

    global ACCESS_TOKEN

    if ACCESS_TOKEN:

        return ACCESS_TOKEN


    token = session.get(
        "access_token"
    )


    if token:

        ACCESS_TOKEN = token

        return token


    return None


# ============================================================
# SALVAR TOKENS
# ============================================================

def salvar_tokens(
    dados
):

    global ACCESS_TOKEN
    global REFRESH_TOKEN
    global TOKEN_EXPIRA_EM
    global USUARIO_ML


    access_token = dados.get(
        "access_token"
    )

    refresh_token = dados.get(
        "refresh_token"
    )

    expires_in = inteiro(
        dados.get(
            "expires_in",
            21600
        ),
        21600
    )


    if not access_token:

        raise RuntimeError(
            "O Mercado Livre não retornou access_token."
        )


    ACCESS_TOKEN = (
        access_token
    )


    if refresh_token:

        REFRESH_TOKEN = (
            refresh_token
        )


    TOKEN_EXPIRA_EM = (
        time.time()
        +
        expires_in
        -
        120
    )


    session[
        "access_token"
    ] = access_token


    if refresh_token:

        session[
            "refresh_token"
        ] = refresh_token


    session[
        "token_expires_at"
    ] = TOKEN_EXPIRA_EM


    session.modified = True


    logger.info(
        "Token Mercado Livre salvo."
    )


# ============================================================
# REFRESH TOKEN
# ============================================================

def renovar_token():

    global REFRESH_TOKEN


    refresh = (

        REFRESH_TOKEN

        or

        session.get(
            "refresh_token"
        )

    )


    if not refresh:

        return False


    if not CLIENT_ID:

        return False


    if not CLIENT_SECRET:

        return False


    dados = {

        "grant_type":
            "refresh_token",

        "client_id":
            CLIENT_ID,

        "client_secret":
            CLIENT_SECRET,

        "refresh_token":
            refresh

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


    except requests.RequestException as erro:

        logger.error(
            "Erro ao renovar token: %s",
            erro
        )

        return False


    if resposta.status_code != 200:

        logger.error(
            "Refresh recusado: %s",
            resposta.text[:500]
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

    token = (
        obter_access_token()
    )


    if not token:

        return None


    if (

        TOKEN_EXPIRA_EM

        and

        time.time()
        >=
        TOKEN_EXPIRA_EM

    ):

        if renovar_token():

            return (
                obter_access_token()
            )


        return None


    return token


# ============================================================
# HEADERS
# ============================================================

def headers_api():

    token = (
        garantir_token()
    )


    headers = {

        "Accept":
            "application/json",

        "User-Agent":
            "Robo-Ofertas-ML/6.0"

    }


    if token:

        headers[
            "Authorization"
        ] = (

            "Bearer "
            +
            token

        )


    return headers


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login"
)
def login():

    if not CLIENT_ID:

        return (
            "ERRO: ML_CLIENT_ID não configurado.",
            500
        )


    if not CLIENT_SECRET:

        return (
            "ERRO: ML_CLIENT_SECRET não configurado.",
            500
        )


    if not REDIRECT_URI:

        return (
            "ERRO: ML_REDIRECT_URI não configurado.",
            500
        )


    state = (
        secrets.token_urlsafe(
            32
        )
    )


    verifier = (
        secrets.token_urlsafe(
            64
        )
    )


    digest = hashlib.sha256(
        verifier.encode(
            "utf-8"
        )
    ).digest()


    challenge = (
        base64.urlsafe_b64encode(
            digest
        )
        .decode(
            "utf-8"
        )
        .rstrip("=")
    )


    session[
        "oauth_state"
    ] = state


    session[
        "code_verifier"
    ] = verifier


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
            challenge,

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


    return redirect(
        url
    )


# ============================================================
# CALLBACK
# ============================================================

@app.route(
    "/callback"
)
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
            escapar(
                descricao
            )
            +
            "</p>"

        ), 400


    code = request.args.get(
        "code"
    )


    if not code:

        return (
            "Código do Mercado Livre não recebido.",
            400
        )


    state = request.args.get(
        "state"
    )


    state_salvo = session.get(
        "oauth_state"
    )


    if not state_salvo:

        return (

            "Sessão OAuth expirada. "
            "Clique novamente em Conectar Mercado Livre."

        ), 400


    if state != state_salvo:

        return (
            "State OAuth inválido.",
            400
        )


    verifier = session.get(
        "code_verifier"
    )


    if not verifier:

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
            verifier

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


    except requests.RequestException as erro:

        logger.error(
            "OAuth erro: %s",
            erro
        )

        return (
            "Erro de conexão com Mercado Livre.",
            502
        )


    if resposta.status_code != 200:

        logger.error(
            "OAuth recusado: %s",
            resposta.text[:1000]
        )


        return (

            "<h2>Mercado Livre recusou o login</h2>"

            "<pre>"
            +
            escapar(
                resposta.text
            )
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

        logger.error(
            "Erro salvando token: %s",
            erro
        )

        return (
            "Erro ao salvar conexão.",
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
    # TESTE DO TOKEN
    # --------------------------------------------------------

    token = (
        obter_access_token()
    )


    if not token:

        return (
            "Token não disponível após login.",
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
                    "Robo-Ofertas-ML/6.0"

            },

            timeout=30

        )


        if teste.status_code in (
            200,
            206
        ):

            try:

                usuario = (
                    teste.json()
                )

                global USUARIO_ML

                USUARIO_ML = usuario.get(
                    "id"
                )

                session[
                    "user_id"
                ] = USUARIO_ML

                session.modified = True

            except ValueError:

                pass


            logger.info(
                "Mercado Livre conectado."
            )


        else:

            logger.warning(
                "Token recebido, mas /users/me retornou %s.",
                teste.status_code
            )


    except requests.RequestException as erro:

        logger.warning(
            "Teste do token falhou: %s",
            erro
        )


    return redirect(
        "/"
    )


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route("/")
def inicio():

    conectado = bool(
        garantir_token()
    )


    return render_template(

        "index.html",

        conectado=conectado,

        versao=VERSAO,

        nichos=NICHOS

    )


# ============================================================
# STATUS
# ============================================================

@app.route(
    "/api/status"
)
def api_status():

    token = (
        garantir_token()
    )


    return jsonify({

        "ok":
            True,

        "app":
            "Robo de Ofertas",

        "versao":
            VERSAO,

        "mercado_livre":
            bool(token),

        "usuario":
            USUARIO_ML
            or
            session.get(
                "user_id"
            ),

        "nichos":
            list(
                NICHOS.keys()
            )

    })


# ============================================================
# MINHA CONTA
# ============================================================

@app.route(
    "/api/me"
)
def api_me():

    token = (
        garantir_token()
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

            timeout=30

        )


    except requests.RequestException as erro:

        return jsonify({

            "ok":
                False,

            "mensagem":
                "Erro de conexão.",

            "detalhes":
                str(erro)

        }), 502


    if resposta.status_code in (
        401,
        403
    ):

        if renovar_token():

            try:

                resposta = requests.get(

                    f"{API_BASE}/users/me",

                    headers=headers_api(),

                    timeout=30

                )

            except requests.RequestException as erro:

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
                "Mercado Livre recusou a consulta.",

            "resposta":
                resposta.text[:1000]

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
# BUSCA NO MERCADO LIVRE
# ============================================================

def buscar_mercado_livre(
    termo,
    limite=20
):

    token = (
        garantir_token()
    )


    if not token:

        raise RuntimeError(
            "Mercado Livre não conectado."
        )


    termo = str(
        termo or ""
    ).strip()


    if not termo:

        return []


    limite = max(
        1,
        min(
            inteiro(
                limite,
                LIMITE_BUSCA
            ),
            50
        )
    )


    url = (
        f"{API_BASE}/sites/{SITE_ID}/search"
    )


    parametros = {

        "q":
            termo,

        "limit":
            limite,

        "offset":
            0,

        "sort":
            "relevance"

    }


    try:

        resposta = requests.get(

            url,

            params=parametros,

            headers=headers_api(),

            timeout=30

        )


    except requests.RequestException as erro:

        raise RuntimeError(
            "Erro de conexão com Mercado Livre: "
            +
            str(erro)
        )


    # --------------------------------------------------------
    # RETENTATIVA COM REFRESH
    # --------------------------------------------------------

    if resposta.status_code in (
        401,
        403
    ):

        if renovar_token():

            try:

                resposta = requests.get(

                    url,

                    params=parametros,

                    headers=headers_api(),

                    timeout=30

                )

            except requests.RequestException as erro:

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


    return dados.get(
        "results",
        []
    )


# ============================================================
# CALCULAR OFERTA
# ============================================================

def calcular_oferta(
    preco
):

    preco = numero(
        preco
    )


    if preco <= 0:

        return {

            "lucro":
                0,

            "preco_venda":
                0,

            "margem":
                0

        }


    lucro = (

        preco
        *
        MARGEM_PADRAO
        /
        100

    )


    preco_venda = (

        preco
        +
        lucro

    )


    return {

        "lucro":
            lucro,

        "preco_venda":
            preco_venda,

        "margem":
            MARGEM_PADRAO

    }


# ============================================================
# TRANSFORMAR PRODUTO
# ============================================================

def transformar_produto(
    item,
    categoria_busca=None
):

    titulo = (
        item.get(
            "title",
            "Produto"
        )
    )


    preco = numero(
        item.get(
            "price"
        )
    )


    if preco <= 0:

        return None


    categoria = (
        classificar_produto(
            titulo
        )
    )


    if not categoria:

        categoria = (
            categoria_busca
        )


    if not categoria:

        return None


    oferta = calcular_oferta(
        preco
    )


    if (
        oferta["lucro"]
        <
        LUCRO_MINIMO_PADRAO
    ):

        return None


    thumbnail = (
        item.get(
            "thumbnail",
            ""
        )
    )


    permalink = (
        item.get(
            "permalink",
            ""
        )
    )


    vendedor = (
        item.get(
            "seller",
            {}
        )
    )


    if not isinstance(
        vendedor,
        dict
    ):

        vendedor = {}


    vendedor_id = (
        vendedor.get(
            "id"
        )
    )


    vendidos = numero(
        item.get(
            "sold_quantity",
            0
        )
    )


    condicao = (
        item.get(
            "condition",
            ""
        )
    )


    frete = item.get(
        "shipping",
        {}
    )


    if not isinstance(
        frete,
        dict
    ):

        frete = {}


    frete_gratis = bool(
        frete.get(
            "free_shipping",
            False
        )
    )


    return {

        "id":
            item.get(
                "id"
            ),

        "titulo":
            titulo,

        "preco":
            preco,

        "preco_formatado":
            formatar_preco(
                preco
            ),

        "preco_venda":
            oferta[
                "preco_venda"
            ],

        "preco_venda_formatado":
            formatar_preco(
                oferta[
                    "preco_venda"
                ]
            ),

        "lucro":
            oferta[
                "lucro"
            ],

        "lucro_formatado":
            formatar_preco(
                oferta[
                    "lucro"
                ]
            ),

        "margem":
            oferta[
                "margem"
            ],

        "imagem":
            thumbnail,

        "link":
            permalink,

        "categoria":
            categoria,

        "vendedor_id":
            vendedor_id,

        "vendidos":
            vendidos,

        "condicao":
            condicao,

        "frete_gratis":
            frete_gratis,

        "whatsapp":
            gerar_texto_whatsapp(
                titulo,
                preco,
                oferta[
                    "lucro"
                ],
                permalink,
                categoria
            )

    }


# ============================================================
# TEXTO PARA WHATSAPP
# ============================================================

def gerar_texto_whatsapp(
    titulo,
    preco,
    lucro,
    link,
    categoria
):

    if categoria == "suplementos":

        chamada = (
            "🥤 OFERTA DE SUPLEMENTO"
        )

        emoji = "💪"

    elif categoria == "fitness_feminino":

        chamada = (
            "👩 OFERTA FITNESS FEMININA"
        )

        emoji = "👟"

    else:

        chamada = (
            "👨 OFERTA FITNESS MASCULINA"
        )

        emoji = "🏋️"


    texto = (

        f"🔥 {chamada} 🔥\n\n"

        f"{emoji} {titulo}\n\n"

        f"💰 Por apenas: "
        f"{formatar_preco(preco)}\n\n"

        f"📈 Oportunidade de lucro: "
        f"{formatar_preco(lucro)}\n\n"

        f"🛒 COMPRAR AGORA 👇\n"
        f"{link}\n\n"

        "⚠️ Preço e disponibilidade "
        "podem mudar no Mercado Livre."

    )


    return texto


# ============================================================
# BUSCAR POR TERMO
# ============================================================

def buscar_por_termo(
    termo,
    categoria=None,
    limite=20
):

    resultados = (
        buscar_mercado_livre(
            termo,
            limite
        )
    )


    produtos = []


    for item in resultados:

        produto = transformar_produto(

            item,

            categoria

        )


        if produto:

            produtos.append(
                produto
            )


    return produtos


# ============================================================
# BUSCA ESPECÍFICA
# ============================================================

def buscar_categoria(
    categoria,
    limite=20
):

    if categoria not in NICHOS:

        raise ValueError(
            "Categoria inválida."
        )


    configuracao = (
        NICHOS[
            categoria
        ]
    )


    termos = (
        configuracao[
            "termos"
        ]
    )


    produtos = []

    vistos = set()


    limite_por_termo = max(
        3,
        min(
            10,
            limite
        )
    )


    for termo in termos:

        try:

            encontrados = (
                buscar_por_termo(

                    termo,

                    categoria,

                    limite_por_termo

                )
            )

        except Exception as erro:

            logger.warning(

                "Falha no termo %s: %s",

                termo,

                erro

            )

            continue


        for produto in encontrados:

            produto_id = (
                produto.get(
                    "id"
                )
            )


            if not produto_id:

                continue


            if produto_id in vistos:

                continue


            vistos.add(
                produto_id
            )


            produtos.append(
                produto
            )


            if len(produtos) >= limite:

                return ordenar_ofertas(
                    produtos
                )


    return ordenar_ofertas(
        produtos
    )


# ============================================================
# ORDENAR OFERTAS
# ============================================================

def ordenar_ofertas(
    produtos
):

    return sorted(

        produtos,

        key=lambda produto: (

            numero(
                produto.get(
                    "vendidos",
                    0
                )
            ),

            numero(
                produto.get(
                    "lucro",
                    0
                )
            )

        ),

        reverse=True

    )


# ============================================================
# FIM DA PARTE 1
## ============================================================
# PARTE 2/2
# ROTAS, OFERTAS, WHATSAPP E INICIALIZAÇÃO
# ============================================================


# ============================================================
# BUSCA DE TODAS AS CATEGORIAS
# ============================================================

def buscar_todas_ofertas(limite=30):

    limite = max(
        1,
        min(
            inteiro(limite, 30),
            100
        )
    )

    resultado = []

    vistos = set()

    # Quantidade aproximada para cada nicho
    por_categoria = max(
        5,
        limite // len(NICHOS)
    )

    for categoria in NICHOS:

        try:

            produtos = buscar_categoria(
                categoria,
                por_categoria
            )

        except Exception as erro:

            logger.warning(
                "Erro na categoria %s: %s",
                categoria,
                erro
            )

            continue

        for produto in produtos:

            produto_id = produto.get(
                "id"
            )

            if not produto_id:
                continue

            if produto_id in vistos:
                continue

            vistos.add(
                produto_id
            )

            resultado.append(
                produto
            )

            if len(resultado) >= limite:
                break

        if len(resultado) >= limite:
            break

    return ordenar_ofertas(
        resultado
    )


# ============================================================
# ROTA DE BUSCA
# ============================================================

@app.route(
    "/api/buscar"
)
def api_buscar():

    categoria = (
        request.args.get(
            "categoria",
            "todos"
        )
        .strip()
        .lower()
    )

    limite = inteiro(
        request.args.get(
            "limite",
            30
        ),
        30
    )

    if not garantir_token():

        return jsonify({

            "ok": False,

            "mercado_livre": False,

            "mensagem":
                "Mercado Livre não está conectado.",

            "produtos": []

        }), 401


    try:

        if categoria in (
            "",
            "todos",
            "todas"
        ):

            produtos = (
                buscar_todas_ofertas(
                    limite
                )
            )

        else:

            if categoria not in NICHOS:

                return jsonify({

                    "ok": False,

                    "mensagem":
                        "Categoria inválida.",

                    "categorias":
                        list(
                            NICHOS.keys()
                        )

                }), 400


            produtos = (
                buscar_categoria(
                    categoria,
                    limite
                )
            )


        return jsonify({

            "ok": True,

            "mercado_livre": True,

            "categoria":
                categoria,

            "quantidade":
                len(produtos),

            "produtos":
                produtos

        })


    except Exception as erro:

        logger.exception(
            "Erro na busca."
        )

        return jsonify({

            "ok": False,

            "mercado_livre": True,

            "mensagem":
                "Não foi possível realizar a busca.",

            "erro":
                str(erro),

            "produtos": []

        }), 502


# ============================================================
# ROTA DE OFERTAS POR CATEGORIA
# ============================================================

@app.route(
    "/ofertas/<categoria>"
)
def ofertas_categoria(
    categoria
):

    categoria = (
        categoria
        .strip()
        .lower()
    )

    if categoria not in NICHOS:

        return jsonify({

            "ok": False,

            "mensagem":
                "Categoria não encontrada.",

            "categorias":
                list(
                    NICHOS.keys()
                )

        }), 404


    if not garantir_token():

        return jsonify({

            "ok": False,

            "mercado_livre": False,

            "mensagem":
                "Mercado Livre não está conectado.",

            "produtos": []

        }), 401


    limite = inteiro(

        request.args.get(
            "limite",
            20
        ),

        20

    )


    try:

        produtos = (
            buscar_categoria(
                categoria,
                limite
            )
        )


        return jsonify({

            "ok": True,

            "categoria":
                categoria,

            "nome_categoria":
                NICHOS[
                    categoria
                ]["nome"],

            "quantidade":
                len(produtos),

            "produtos":
                produtos

        })


    except Exception as erro:

        logger.exception(
            "Erro em /ofertas/%s",
            categoria
        )


        return jsonify({

            "ok": False,

            "mensagem":
                "Erro ao buscar ofertas.",

            "erro":
                str(erro),

            "produtos": []

        }), 502


# ============================================================
# MELHORES OFERTAS
#
# Mantida para evitar o 404 que apareceu anteriormente.
# ============================================================

@app.route(
    "/melhores"
)
def melhores():

    categoria = (
        request.args.get(
            "categoria",
            "todos"
        )
        .strip()
        .lower()
    )


    limite = inteiro(

        request.args.get(
            "limite",
            20
        ),

        20

    )


    if not garantir_token():

        return jsonify({

            "ok": False,

            "mensagem":
                "Mercado Livre não está conectado.",

            "produtos": []

        }), 401


    try:

        if categoria in (
            "",
            "todos",
            "todas"
        ):

            produtos = (
                buscar_todas_ofertas(
                    limite
                )
            )

        elif categoria in NICHOS:

            produtos = (
                buscar_categoria(
                    categoria,
                    limite
                )
            )

        else:

            return jsonify({

                "ok": False,

                "mensagem":
                    "Categoria inválida.",

                "produtos": []

            }), 400


        return jsonify({

            "ok": True,

            "categoria":
                categoria,

            "produtos":
                produtos,

            "quantidade":
                len(produtos)

        })


    except Exception as erro:

        logger.exception(
            "Erro na rota /melhores."
        )


        return jsonify({

            "ok": False,

            "mensagem":
                "Erro ao carregar melhores ofertas.",

            "erro":
                str(erro),

            "produtos": []

        }), 502


# ============================================================
# GERAR TEXTO WHATSAPP DE UM PRODUTO
# ============================================================

@app.route(
    "/api/whatsapp/<produto_id>"
)
def api_whatsapp(
    produto_id
):

    if not produto_id:

        return jsonify({

            "ok": False,

            "mensagem":
                "Produto não informado."

        }), 400


    token = garantir_token()


    if not token:

        return jsonify({

            "ok": False,

            "mensagem":
                "Mercado Livre não está conectado."

        }), 401


    try:

        resposta = requests.get(

            f"{API_BASE}/items/{produto_id}",

            headers=headers_api(),

            timeout=30

        )


    except requests.RequestException as erro:

        return jsonify({

            "ok": False,

            "mensagem":
                "Erro de conexão.",

            "erro":
                str(erro)

        }), 502


    if resposta.status_code != 200:

        return jsonify({

            "ok": False,

            "status":
                resposta.status_code,

            "mensagem":
                "Não foi possível carregar o produto.",

            "resposta":
                resposta.text[:500]

        }), resposta.status_code


    try:

        item = resposta.json()

    except ValueError:

        return jsonify({

            "ok": False,

            "mensagem":
                "Resposta inválida."

        }), 502


    produto = transformar_produto(
        item
    )


    if not produto:

        return jsonify({

            "ok": False,

            "mensagem":
                "Produto não pertence ao nicho configurado."

        }), 400


    return jsonify({

        "ok": True,

        "produto":
            produto,

        "mensagem":
            produto["whatsapp"]

    })


# ============================================================
# COMPARTILHAMENTO WHATSAPP
# ============================================================

@app.route(
    "/api/whatsapp"
)
def whatsapp_generico():

    titulo = request.args.get(
        "titulo",
        "Oferta Fitness"
    )

    preco = numero(
        request.args.get(
            "preco",
            0
        )
    )

    lucro = numero(
        request.args.get(
            "lucro",
            0
        )
    )

    link = request.args.get(
        "link",
        ""
    )

    categoria = request.args.get(
        "categoria",
        "suplementos"
    )


    if not link:

        return jsonify({

            "ok": False,

            "mensagem":
                "Link do produto não informado."

        }), 400


    texto = gerar_texto_whatsapp(

        titulo,

        preco,

        lucro,

        link,

        categoria

    )


    return jsonify({

        "ok": True,

        "mensagem":
            texto,

        "whatsapp_url":
            (
                "https://wa.me/?text="
                +
                requests.utils.quote(
                    texto
                )
            )

    })


# ============================================================
# DESCONEXÃO
# ============================================================

@app.route(
    "/logout"
)
def logout():

    global ACCESS_TOKEN
    global REFRESH_TOKEN
    global TOKEN_EXPIRA_EM
    global USUARIO_ML


    ACCESS_TOKEN = None

    REFRESH_TOKEN = None

    TOKEN_EXPIRA_EM = 0

    USUARIO_ML = None


    session.clear()


    return redirect(
        "/"
    )


# ============================================================
# DIAGNÓSTICO
# ============================================================

@app.route(
    "/diagnostico"
)
def diagnostico():

    token = (
        garantir_token()
    )


    dados = {

        "app":
            "Robo de Ofertas",

        "versao":
            VERSAO,

        "mercado_livre":
            bool(token),

        "client_id_configurado":
            bool(CLIENT_ID),

        "client_secret_configurado":
            bool(CLIENT_SECRET),

        "redirect_uri_configurado":
            bool(REDIRECT_URI),

        "token_configurado":
            bool(token),

        "categorias":
            list(
                NICHOS.keys()
            )

    }


    return jsonify(
        dados
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/health"
)
def health():

    return jsonify({

        "ok":
            True,

        "app":
            "Robo de Ofertas",

        "versao":
            VERSAO

    })


# ============================================================
# ERRO 404
# ============================================================

@app.errorhandler(
    404
)
def pagina_nao_encontrada(
    erro
):

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

        "<h1>Rota não encontrada</h1>"
        "<p>Volte para a página inicial.</p>"

    ), 404


# ============================================================
# ERRO 500
# ============================================================

@app.errorhandler(
    500
)
def erro_interno(
    erro
):

    logger.exception(
        "Erro interno."
    )


    if request.path.startswith(
        "/api/"
    ):

        return jsonify({

            "ok": False,

            "mensagem":
                "Erro interno do servidor.",

            "erro":
                str(erro)

        }), 500


    return (

        "<h1>Erro interno</h1>"
        "<p>O servidor encontrou um problema.</p>"

    ), 500


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":

    porta = inteiro(

        os.getenv(
            "PORT",
            5000
        ),

        5000

    )


    app.run(

        host="0.0.0.0",

        port=porta,

        debug=False

    ) ============================================================
