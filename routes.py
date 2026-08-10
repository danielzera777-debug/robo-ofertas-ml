"""
ROUTES.PY
Robo de Ofertas ML
Versão 11.2

FOCO EXCLUSIVO:
    Roupas Fitness Femininas

ROTAS:
    /api/status
    /api/auth/status
    /api/diagnostico
    /api/diagnostico/ml
    /api/buscar
    /api/buscar-fitness
    /api/ofertas
    /api/publicacoes
    /api/config
    /health

IMPORTANTE:
    A autenticação OAuth fica no auth.py.
    Este arquivo NÃO registra o blueprint "auth".
"""

from __future__ import annotations

import logging
import unicodedata

import requests

from flask import (
    Blueprint,
    jsonify,
    request,
    session,
)

from config import get_config
from database import db


# ============================================================
# LOG
# ============================================================

logger = logging.getLogger(
    "robo-ofertas.routes"
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

Config = get_config()

ML_API_BASE = getattr(
    Config,
    "ML_API_BASE",
    "https://api.mercadolibre.com",
).rstrip("/")

ML_SITE_ID = getattr(
    Config,
    "ML_SITE_ID",
    "MLB",
)


APP_VERSION = getattr(
    Config,
    "APP_VERSION",
    "11.2.0",
)


# ============================================================
# BLUEPRINT
# ============================================================

routes = Blueprint(
    "routes",
    __name__,
)


# ============================================================
# NICHO
# ============================================================

NICHO = "Roupas Fitness Femininas"


TERMOS_FITNESS = [
    "legging fitness feminina",
    "legging academia feminina",
    "calca legging feminina",
    "calça legging feminina",
    "conjunto fitness feminino",
    "conjunto academia feminino",
    "top fitness feminino",
    "top academia feminino",
    "short fitness feminino",
    "short academia feminino",
    "bermuda fitness feminina",
    "cropped fitness feminino",
    "blusa fitness feminina",
    "camiseta fitness feminina",
    "regata fitness feminina",
    "macacao fitness feminino",
    "macacão fitness feminino",
    "calca fitness feminina",
    "calça fitness feminina",
]


# ============================================================
# TERMOS QUE DEVEM SER BLOQUEADOS
# ============================================================

TERMOS_BLOQUEADOS = [
    "masculino",
    "masculina",
    "masculinos",
    "masculinas",
    "homem",
    "homens",
    "menino",
    "meninos",
    "infantil masculino",
]


# ============================================================
# TERMOS VÁLIDOS
# ============================================================

TERMOS_VALIDOS = [
    "legging",
    "fitness",
    "academia",
    "top",
    "cropped",
    "conjunto",
    "short",
    "bermuda",
    "regata",
    "macacao",
    "calca",
]


# ============================================================
# AUXILIAR
# ============================================================

def remover_acentos(valor):
    """
    Remove acentos para facilitar a comparação
    dos títulos dos produtos.
    """

    texto = str(
        valor or ""
    )

    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    return "".join(
        caractere
        for caractere in texto
        if unicodedata.category(
            caractere
        ) != "Mn"
    )


def texto_normalizado(valor):
    return remover_acentos(
        valor
    ).lower().strip()


# ============================================================
# RESPOSTA DE ERRO
# ============================================================

def resposta_erro(
    mensagem,
    status=400,
    **extra,
):
    """
    Retorna erros de forma segura.

    IMPORTANTE:
    Não usar:
        resposta_erro(
            "...",
            mensagem="..."
        )

    pois isso gera:
        got multiple values for argument 'mensagem'
    """

    resposta = {
        "sucesso": False,
        "erro": str(mensagem),
    }

    resposta.update(
        extra
    )

    return jsonify(
        resposta
    ), status


# ============================================================
# INTEIRO
# ============================================================

def inteiro(
    valor,
    padrao=20,
):

    try:

        return int(
            valor
        )

    except (
        ValueError,
        TypeError,
    ):

        return padrao


# ============================================================
# TOKEN
# ============================================================

def token_mercado_livre():
    """
    Obtém o token somente da sessão ou da configuração.

    O token nunca é colocado no log.
    """

    token = session.get(
        "access_token"
    )

    if token:
        return str(
            token
        ).strip()

    token = getattr(
        Config,
        "ML_ACCESS_TOKEN",
        "",
    )

    return str(
        token or ""
    ).strip()


# ============================================================
# CONFIGURAÇÃO ML
# ============================================================

def mercado_livre_configurado():

    metodo = getattr(
        Config,
        "mercado_livre_configured",
        None,
    )

    if callable(metodo):

        try:

            return bool(
                metodo()
            )

        except Exception:

            logger.exception(
                "Erro em mercado_livre_configured."
            )

    metodo = getattr(
        Config,
        "mercado_livre_configurado",
        None,
    )

    if callable(metodo):

        try:

            return bool(
                metodo()
            )

        except Exception:

            logger.exception(
                "Erro em mercado_livre_configurado."
            )

    return bool(

        getattr(
            Config,
            "ML_CLIENT_ID",
            "",
        )

        and

        getattr(
            Config,
            "ML_CLIENT_SECRET",
            "",
        )

        and

        getattr(
            Config,
            "ML_REDIRECT_URI",
            "",
        )

    )


# ============================================================
# HEADERS MERCADO LIVRE
# ============================================================

def headers_ml():

    headers = {

        "Accept":
            "application/json",

        "Content-Type":
            "application/json",

        "User-Agent":
            "Robo-Ofertas-ML/11.2",

    }

    token = token_mercado_livre()

    if token:

        headers[
            "Authorization"
        ] = (
            "Bearer "
            + token
        )

    return headers


# ============================================================
# FILTRO FEMININO
# ============================================================

def produto_feminino(
    titulo,
):

    texto = texto_normalizado(
        titulo
    )

    if not texto:
        return False

    # --------------------------------------------------------
    # BLOQUEIA PRODUTO MASCULINO
    # --------------------------------------------------------

    for termo in TERMOS_BLOQUEADOS:

        if termo in texto:

            return False

    # --------------------------------------------------------
    # DEVE SER PRODUTO DE VESTUÁRIO FITNESS
    # --------------------------------------------------------

    possui_termo = any(

        termo in texto

        for termo in TERMOS_VALIDOS

    )

    if not possui_termo:

        return False

    # --------------------------------------------------------
    # EVITA ALGUNS FALSOS POSITIVOS
    # --------------------------------------------------------

    termos_indesejados = [

        "suplemento",
        "whey",
        "creatina",
        "vitamina",
        "celular",
        "tenis masculino",
        "sapato masculino",
        "relogio",
        "relógio",

    ]

    for termo in termos_indesejados:

        if termo in texto:

            return False

    return True


# ============================================================
# FORMATAR PREÇO
# ============================================================

def formatar_preco(
    valor,
):

    try:

        numero_valor = float(
            valor
        )

        return (

            f"R$ {numero_valor:,.2f}"

            .replace(
                ",",
                "X",
            )

            .replace(
                ".",
                ",",
            )

            .replace(
                "X",
                ".",
            )

        )

    except (
        ValueError,
        TypeError,
    ):

        return "R$ 0,00"


# ============================================================
# NORMALIZAR PRODUTO
# ============================================================

def normalizar_produto(
    item,
):

    preco = item.get(
        "price"
    )

    preco_original = item.get(
        "original_price"
    )

    desconto = 0

    try:

        if (

            preco_original

            and

            preco is not None

            and

            float(
                preco_original
            ) > 0

            and

            float(
                preco
            )
            <
            float(
                preco_original
            )

        ):

            desconto = round(

                (

                    1

                    -

                    (
                        float(preco)
                        /
                        float(
                            preco_original
                        )
                    )

                )

                * 100

            )

    except (
        ValueError,
        TypeError,
    ):

        desconto = 0

    seller = item.get(
        "seller"
    ) or {}

    return {

        "id":
            item.get(
                "id"
            ),

        "titulo":
            item.get(
                "title",
                "",
            ),

        "preco":
            preco,

        "preco_formatado":
            formatar_preco(
                preco
            ),

        "preco_original":
            preco_original,

        "desconto":
            desconto,

        "link":
            item.get(
                "permalink"
            ),

        "imagem":
            item.get(
                "thumbnail"
            ),

        "thumbnail":
            item.get(
                "thumbnail"
            ),

        "categoria":
            NICHO,

        "vendedor":
            seller.get(
                "nickname"
            ),

    }


# ============================================================
# REQUISIÇÃO ML
# ============================================================

def requisicao_ml(
    url,
    params=None,
    timeout=30,
):

    try:

        response = requests.get(

            url,

            params=params,

            headers=headers_ml(),

            timeout=timeout,

        )

    except requests.RequestException as exc:

        logger.exception(
            "Erro de conexão com Mercado Livre."
        )

        raise ConnectionError(
            f"Erro de conexão com Mercado Livre: {exc}"
        ) from exc

    try:

        payload = response.json()

    except ValueError:

        payload = {
            "resposta":
                response.text[
                    :1000
                ]
        }

    # --------------------------------------------------------
    # SUCESSO
    # --------------------------------------------------------

    if 200 <= response.status_code < 300:

        return payload

    # --------------------------------------------------------
    # 401
    # --------------------------------------------------------

    if response.status_code == 401:

        logger.error(
            "Mercado Livre HTTP 401."
        )

        raise PermissionError(
            "Mercado Livre rejeitou o access_token "
            "(HTTP 401). Faça uma nova autenticação."
        )

    # --------------------------------------------------------
    # 403
    # --------------------------------------------------------

    if response.status_code == 403:

        logger.error(
            "Mercado Livre HTTP 403: %s",
            payload,
        )

        erro = RuntimeError(
            "Mercado Livre recusou a requisição "
            "(HTTP 403)."
        )

        setattr(
            erro,
            "status_code",
            403,
        )

        setattr(
            erro,
            "payload",
            payload,
        )

        raise erro

    # --------------------------------------------------------
    # 429
    # --------------------------------------------------------

    if response.status_code == 429:

        logger.error(
            "Mercado Livre HTTP 429."
        )

        erro = RuntimeError(
            "Mercado Livre limitou temporariamente "
            "as requisições (HTTP 429)."
        )

        setattr(
            erro,
            "status_code",
            429,
        )

        setattr(
            erro,
            "payload",
            payload,
        )

        raise erro

    # --------------------------------------------------------
    # OUTROS
    # --------------------------------------------------------

    logger.error(
        "Mercado Livre HTTP %s: %s",
        response.status_code,
        payload,
    )

    erro = RuntimeError(

        f"Mercado Livre retornou HTTP "
        f"{response.status_code}."

    )

    setattr(
        erro,
        "status_code",
        response.status_code,
    )

    setattr(
        erro,
        "payload",
        payload,
    )

    raise erro


# ============================================================
# TESTAR TOKEN
# ============================================================

def testar_token_ml():

    token = token_mercado_livre()

    if not token:

        return {

            "ok":
                False,

            "status":
                None,

            "erro":
                "access_token_ausente",

            "mensagem":
                "Access token não encontrado.",

        }

    url = (
        f"{ML_API_BASE}/users/me"
    )

    try:

        payload = requisicao_ml(
            url
        )

    except Exception as exc:

        status_code = getattr(
            exc,
            "status_code",
            None,
        )

        payload = getattr(
            exc,
            "payload",
            None,
        )

        # ----------------------------------------------------
        # 403
        # ----------------------------------------------------

        if status_code == 403:

            return {

                "ok":
                    False,

                "status":
                    403,

                "erro":
                    "forbidden",

                "mensagem":
                    (
                        "O Mercado Livre recusou "
                        "o access token no endpoint "
                        "/users/me."
                    ),

                "resposta":
                    payload,

                "possiveis_causas": [

                    "scope/permissão da aplicação",

                    "usuário não autorizado",

                    "access token incompatível",

                    "IP não permitido",

                    "aplicação bloqueada ou desabilitada",

                    "usuário inativo ou suspenso",

                ],

            }

        # ----------------------------------------------------
        # 401
        # ----------------------------------------------------

        if status_code == 401:

            return {

                "ok":
                    False,

                "status":
                    401,

                "erro":
                    "unauthorized",

                "mensagem":
                    (
                        "O access token "
                        "foi rejeitado."
                    ),

            }

        # ----------------------------------------------------
        # CONEXÃO
        # ----------------------------------------------------

        return {

            "ok":
                False,

            "status":
                status_code,

            "erro":
                "erro_api",

            "mensagem":
                str(exc),

            "resposta":
                payload,

        }

    # --------------------------------------------------------
    # TOKEN VÁLIDO
    # --------------------------------------------------------

    return {

        "ok":
            True,

        "status":
            200,

        "usuario": {

            "id":
                payload.get(
                    "id"
                ),

            "nickname":
                payload.get(
                    "nickname"
                ),

            "country_id":
                payload.get(
                    "country_id"
                ),

            "site_id":
                payload.get(
                    "site_id"
                ),

        },

    }


# ============================================================
# BUSCA MERCADO LIVRE
# ============================================================

def buscar_mercado_livre(
    consulta,
    limite=20,
):

    limite = max(
        1,
        min(
            int(limite),
            50,
        ),
    )

    url = (

        f"{ML_API_BASE}"

        f"/sites/"

        f"{ML_SITE_ID}"

        "/search"

    )

    params = {

        "q":
            consulta,

        "limit":
            limite,

    }

    payload = requisicao_ml(
        url,
        params=params,
    )

    resultados = []

    vistos = set()

    for item in payload.get(
        "results",
        [],
    ):

        titulo = item.get(
            "title",
            "",
        )

        # ----------------------------------------------------
        # FILTRO FEMININO
        # ----------------------------------------------------

        if not produto_feminino(
            titulo
        ):

            continue

        produto = normalizar_produto(
            item
        )

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

        resultados.append(
            produto
        )

        if len(resultados) >= limite:

            break

    return resultados


# ============================================================
# STATUS
# ============================================================

@routes.route(
    "/api/status",
    methods=["GET"],
)
def status():

    try:

        estatisticas = (
            db.estatisticas()
        )

    except Exception:

        logger.exception(
            "Erro obtendo estatísticas."
        )

        estatisticas = {}

    return jsonify({

        "sucesso":
            True,

        "app":
            getattr(
                Config,
                "APP_NAME",
                "Robo de Ofertas ML",
            ),

        "versao":
            APP_VERSION,

        "nicho":
            NICHO,

        "mercado_livre":
            bool(
                token_mercado_livre()
            ),

        "mercado_livre_configurado":
            mercado_livre_configurado(),

        "database":
            estatisticas,

    })


# ============================================================
# AUTH STATUS
# ============================================================

@routes.route(
    "/api/auth/status",
    methods=["GET"],
)
def auth_status():

    token = token_mercado_livre()

    return jsonify({

        "sucesso":
            True,

        "conectado":
            bool(token),

        "mercado_livre": {

            "configurado":
                mercado_livre_configurado(),

            "conectado":
                bool(token),

            "site_id":
                ML_SITE_ID,

        },

        "nicho":
            NICHO,

    })


# ============================================================
# DIAGNÓSTICO
# ============================================================

@routes.route(
    "/api/diagnostico",
    methods=["GET"],
)
def diagnostico():

    token = token_mercado_livre()

    resultado_token = None

    if token:

        resultado_token = (
            testar_token_ml()
        )

    try:

        estatisticas = (
            db.estatisticas()
        )

    except Exception:

        logger.exception(
            "Erro obtendo estatísticas."
        )

        estatisticas = {}

    return jsonify({

        "sucesso":
            True,

        "app":
            getattr(
                Config,
                "APP_NAME",
                "Robo de Ofertas ML",
            ),

        "versao":
            APP_VERSION,

        "nicho":
            NICHO,

        "mercado_livre": {

            "configurado":
                mercado_livre_configurado(),

            "token_disponivel":
                bool(token),

            "conectado":
                bool(
                    session.get(
                        "access_token"
                    )
                ),

            "site_id":
                ML_SITE_ID,

            "api":
                ML_API_BASE,

            "teste_users_me":
                resultado_token,

        },

        "filtro": {

            "foco":
                NICHO,

            "termos":
                TERMOS_FITNESS,

            "bloqueados":
                TERMOS_BLOQUEADOS,

        },

        "database":
            estatisticas,

    })


# ============================================================
# DIAGNÓSTICO ML
# ============================================================

@routes.route(
    "/api/diagnostico/ml",
    methods=["GET"],
)
def diagnostico_ml():

    if not mercado_livre_configurado():

        return resposta_erro(

            "Mercado Livre não configurado.",

            503,

            diagnostico={

                "client_id":
                    bool(
                        getattr(
                            Config,
                            "ML_CLIENT_ID",
                            "",
                        )
                    ),

                "client_secret":
                    bool(
                        getattr(
                            Config,
                            "ML_CLIENT_SECRET",
                            "",
                        )
                    ),

                "redirect_uri":
                    bool(
                        getattr(
                            Config,
                            "ML_REDIRECT_URI",
                            "",
                        )
                    ),

            },

        )

    resultado = testar_token_ml()

    return jsonify({

        "sucesso":
            True,

        "nicho":
            NICHO,

        "mercado_livre":
            resultado,

    })


# ============================================================
# BUSCAR
# ============================================================

@routes.route(
    "/api/buscar",
    methods=["GET"],
)
def buscar():

    consulta_original = (
        request.args.get(
            "produto",
            "",
        )
        .strip()
    )

    limite = inteiro(
        request.args.get(
            "limite",
            20,
        ),
        20,
    )

    limite = max(
        1,
        min(
            limite,
            50,
        ),
    )

    # --------------------------------------------------------
    # CONSULTA PADRÃO
    # --------------------------------------------------------

    if not consulta_original:

        consulta_original = (
            "legging fitness feminina"
        )

    consulta = texto_normalizado(
        consulta_original
    )

    # --------------------------------------------------------
    # REMOVE TERMOS MASCULINOS
    # --------------------------------------------------------

    for termo in TERMOS_BLOQUEADOS:

        consulta = consulta.replace(
            texto_normalizado(
                termo
            ),
            " ",
        )

    consulta = " ".join(
        consulta.split()
    )

    # --------------------------------------------------------
    # GARANTE O NICHO
    # --------------------------------------------------------

    if not any(

        termo in consulta

        for termo in TERMOS_VALIDOS

    ):

        consulta = (

            f"{consulta} "
            "fitness feminina"

        )

    # --------------------------------------------------------
    # GARANTE FEMININO
    # --------------------------------------------------------

    if "feminina" not in consulta:

        consulta += " feminina"

    # --------------------------------------------------------
    # CONFIGURAÇÃO
    # --------------------------------------------------------

    if not mercado_livre_configurado():

        return resposta_erro(

            "Mercado Livre não configurado.",

            503,

            orientacao=(
                "Configure ML_CLIENT_ID, "
                "ML_CLIENT_SECRET e "
                "ML_REDIRECT_URI."
            ),

        )

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    if not token_mercado_livre():

        return resposta_erro(

            "Mercado Livre não conectado.",

            401,

            orientacao=(
                "Conecte o Mercado Livre "
                "antes de realizar a busca."
            ),

        )

    # --------------------------------------------------------
    # BUSCA
    # --------------------------------------------------------

    try:

        produtos = (
            buscar_mercado_livre(
                consulta,
                limite,
            )
        )

    except PermissionError as exc:

        logger.error(
            "Mercado Livre recusou a busca: %s",
            exc,
        )

        return resposta_erro(

            "Mercado Livre recusou o access token.",

            401,

            diagnostico={

                "tipo":
                    "token_nao_autorizado",

                "mensagem":
                    str(exc),

                "acao":
                    (
                        "Abra /api/diagnostico/ml "
                        "para verificar o token."
                    ),

            },

        )

    except RuntimeError as exc:

        status_code = getattr(
            exc,
            "status_code",
            None,
        )

        payload = getattr(
            exc,
            "payload",
            None,
        )

        logger.error(
            "Mercado Livre recusou a busca: %s",
            exc,
        )

        # ----------------------------------------------------
        # 403
        # ----------------------------------------------------

        if status_code == 403:

            return resposta_erro(

                "Mercado Livre recusou a busca.",

                403,

                diagnostico={

                    "http_status":
                        403,

                    "resposta_mercado_livre":
                        payload,

                    "possiveis_causas": [

                        "Permissões/scopes",

                        "Access token de usuário incorreto",

                        "Usuário inativo ou suspenso",

                        "IP não permitido",

                        "Aplicação bloqueada ou desabilitada",

                    ],

                    "proximo_passo":
                        (
                            "Abra /api/diagnostico/ml "
                            "e veja o resultado de /users/me."
                        ),

                },

            )

        # ----------------------------------------------------
        # 429
        # ----------------------------------------------------

        if status_code == 429:

            return resposta_erro(

                "Mercado Livre limitou temporariamente as requisições.",

                429,

                diagnostico={

                    "http_status":
                        429,

                    "mensagem":
                        str(exc),

                },

            )

        # ----------------------------------------------------
        # OUTROS
        # ----------------------------------------------------

        return resposta_erro(

            "Erro retornado pelo Mercado Livre.",

            502,

            diagnostico={

                "http_status":
                    status_code,

                "mensagem":
                    str(exc),

                "resposta":
                    payload,

            },

        )

    except ConnectionError as exc:

        logger.error(
            "Erro de conexão: %s",
            exc,
        )

        return resposta_erro(

            "Erro de conexão com Mercado Livre.",

            502,

            detalhe=str(exc),

        )

    except Exception as exc:

        logger.exception(
            "Erro realizando busca."
        )

        return resposta_erro(

            "Erro interno ao buscar produtos.",

            500,

            detalhe=str(exc),

        )

    # --------------------------------------------------------
    # RESPOSTA
    # --------------------------------------------------------

    return jsonify({

        "sucesso":
            True,

        "nicho":
            NICHO,

        "consulta":
            consulta,

        "total":
            len(produtos),

        "produtos":
            produtos,

        "ofertas":
            produtos,

    })


# ============================================================
# BUSCA AUTOMÁTICA FITNESS FEMININA
# ============================================================

@routes.route(
    "/api/buscar-fitness",
    methods=["GET"],
)
def buscar_fitness():

    limite = inteiro(
        request.args.get(
            "limite",
            20,
        ),
        20,
    )

    limite = max(
        1,
        min(
            limite,
            50,
        ),
    )

    if not token_mercado_livre():

        return resposta_erro(

            "Mercado Livre não conectado.",

            401,

        )

    consultas = [

        "legging fitness feminina",

        "conjunto fitness feminino",

        "top academia feminino",

        "short fitness feminino",

        "cropped fitness feminino",

        "calca legging feminina",

        "bermuda fitness feminina",

        "macacao fitness feminino",

    ]

    resultados = []

    vistos = set()

    try:

        for consulta in consultas:

            restantes = (
                limite
                -
                len(resultados)
            )

            if restantes <= 0:

                break

            quantidade = min(
                restantes,
                20,
            )

            produtos = (
                buscar_mercado_livre(
                    consulta,
                    quantidade,
                )
            )

            for produto in produtos:

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

                resultados.append(
                    produto
                )

                if len(resultados) >= limite:

                    break

    except RuntimeError as exc:

        status_code = getattr(
            exc,
            "status_code",
            None,
        )

        payload = getattr(
            exc,
            "payload",
            None,
        )

        logger.error(
            "Erro na busca fitness feminina: %s",
            exc,
        )

        if status_code == 403:

            return resposta_erro(

                "Mercado Livre recusou a busca.",

                403,

                diagnostico={

                    "http_status":
                        403,

                    "resposta_mercado_livre":
                        payload,

                    "nicho":
                        NICHO,

                },

            )

        return resposta_erro(

            "Erro buscando roupas fitness femininas.",

            502,

            detalhe=str(exc),

        )

    except Exception as exc:

        logger.exception(
            "Erro na busca fitness feminina."
        )

        return resposta_erro(

            "Erro buscando roupas fitness femininas.",

            500,

            detalhe=str(exc),

        )

    return jsonify({

        "sucesso":
            True,

        "nicho":
            NICHO,

        "total":
            len(resultados),

        "produtos":
            resultados,

        "ofertas":
            resultados,

    })


# ============================================================
# OFERTAS
# ============================================================

@routes.route(
    "/api/ofertas",
    methods=["GET"],
)
def ofertas():

    limite = inteiro(
        request.args.get(
            "limite",
            50,
        ),
        50,
    )

    limite = max(
        1,
        min(
            limite,
            500,
        ),
    )

    try:

        dados = db.buscar_ofertas(

            limite=limite,

            status=request.args.get(
                "status"
            ),

        )

    except Exception as exc:

        logger.exception(
            "Erro buscando ofertas."
        )

        return resposta_erro(

            "Erro ao buscar ofertas.",

            500,

            detalhe=str(exc),

        )

    return jsonify({

        "sucesso":
            True,

        "total":
            len(dados),

        "ofertas":
            dados,

    })


# ============================================================
# PUBLICAÇÕES
# ============================================================

@routes.route(
    "/api/publicacoes",
    methods=["GET"],
)
def publicacoes():

    limite = inteiro(
        request.args.get(
            "limite",
            100,
        ),
        100,
    )

    limite = max(
        1,
        min(
            limite,
            500,
        ),
    )

    try:

        dados = db.buscar_publicacoes(
            limite=limite
        )

    except Exception as exc:

        logger.exception(
            "Erro buscando publicações."
        )

        return resposta_erro(

            "Erro ao buscar publicações.",

            500,

            detalhe=str(exc),

        )

    return jsonify({

        "sucesso":
            True,

        "total":
            len(dados),

        "publicacoes":
            dados,

    })


# ============================================================
# CONFIG
# ============================================================

@routes.route(
    "/api/config",
    methods=["GET"],
)
def obter_config():

    return jsonify({

        "sucesso":
            True,

        "config": {

            "app_name":
                getattr(
                    Config,
                    "APP_NAME",
                    "Robo de Ofertas ML",
                ),

            "versao":
                APP_VERSION,

            "nicho":
                NICHO,

            "site_id":
                ML_SITE_ID,

            "limite_ofertas":
                getattr(
                    Config,
                    "LIMITE_OFERTAS",
                    50,
                ),

        },

    })


# ============================================================
# HEALTH
# ============================================================

@routes.route(
    "/health",
    methods=["GET"],
)
def health():

    return jsonify({

        "status":
            "ok",

        "app":
            getattr(
                Config,
                "APP_NAME",
                "Robo de Ofertas ML",
            ),

        "version":
            APP_VERSION,

        "nicho":
            NICHO,

    })


# ============================================================
# EXPORTAÇÃO
# ============================================================

__all__ = [
    "routes",
]
