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
    O OAuth do Mercado Livre fica no auth.py.
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


# ============================================================
# BLUEPRINT
# ============================================================

routes = Blueprint(
    "routes",
    __name__,
)


# ============================================================
# NICHO ÚNICO
# ============================================================

NICHO = "Roupas Fitness Femininas"


# Termos usados nas buscas automáticas.
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
# TERMOS PROIBIDOS
# ============================================================

TERMOS_MASCULINOS = [
    "masculino",
    "masculina",
    "masculinos",
    "masculinas",
    "homem",
    "homens",
    "men",
    "male",
]


TERMOS_INFANTIS = [
    "infantil",
    "infanto juvenil",
    "infanto-juvenil",
    "menina infantil",
    "menino infantil",
    "kids",
    "kid",
]


TERMOS_NAO_FITNESS = [
    "suplemento",
    "whey",
    "creatina",
    "vitamina",
    "pré treino",
    "pre treino",
    "termogenico",
    "termogênico",
    "barra proteica",
    "albumina",
]


# ============================================================
# AUXILIARES
# ============================================================

def resposta_erro(
    mensagem,
    status=400,
    **extra,
):
    resposta = {
        "sucesso": False,
        "erro": mensagem,
    }

    resposta.update(extra)

    return jsonify(
        resposta
    ), status


def inteiro(
    valor,
    padrao=20,
):
    try:
        return int(valor)
    except (
        ValueError,
        TypeError,
    ):
        return padrao


def normalizar_texto(
    valor,
):
    """
    Remove acentos e deixa o texto em minúsculo.
    """

    texto = str(
        valor or ""
    ).lower().strip()

    texto = unicodedata.normalize(
        "NFKD",
        texto,
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(
            caractere
        )
    )

    return texto


def token_mercado_livre():
    """
    Recupera o access_token da sessão.

    Nunca registra o token no log.
    """

    token = session.get(
        "access_token"
    )

    if token:
        return token

    return getattr(
        Config,
        "ML_ACCESS_TOKEN",
        "",
    )


def mercado_livre_configurado():
    """
    Compatível com config.py usando:
        mercado_livre_configured()
    ou:
        mercado_livre_configurado()
    """

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
                "Erro verificando mercado_livre_configured."
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
                "Erro verificando mercado_livre_configurado."
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


def headers_ml():
    """
    Headers utilizados nas chamadas à API.
    """

    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "Robo-Ofertas-ML/11.2"
        ),
    }

    token = token_mercado_livre()

    if token:
        headers["Authorization"] = (
            f"Bearer {token}"
        )

    return headers


def formatar_preco(
    valor,
):
    try:

        numero = float(
            valor
        )

        return (
            f"R$ {numero:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except (
        ValueError,
        TypeError,
    ):

        return "R$ 0,00"


# ============================================================
# FILTRO DO NICHO
# ============================================================

def produto_feminino(
    titulo,
):
    """
    Retorna True somente quando o produto
    aparenta pertencer ao nicho feminino fitness.
    """

    texto = normalizar_texto(
        titulo
    )

    if not texto:
        return False

    # --------------------------------------------------------
    # BLOQUEIA MASCULINO
    # --------------------------------------------------------

    for termo in TERMOS_MASCULINOS:

        if normalizar_texto(
            termo
        ) in texto:

            return False

    # --------------------------------------------------------
    # BLOQUEIA INFANTIL
    # --------------------------------------------------------

    for termo in TERMOS_INFANTIS:

        if normalizar_texto(
            termo
        ) in texto:

            return False

    # --------------------------------------------------------
    # BLOQUEIA SUPLEMENTOS
    # --------------------------------------------------------

    for termo in TERMOS_NAO_FITNESS:

        if normalizar_texto(
            termo
        ) in texto:

            return False

    # --------------------------------------------------------
    # PRECISA SER ROUPA
    # --------------------------------------------------------

    termos_roupa = [
        "legging",
        "calca",
        "calca fitness",
        "conjunto",
        "top",
        "cropped",
        "short",
        "bermuda",
        "blusa",
        "camiseta",
        "regata",
        "macacao",
        "vestido fitness",
        "saia fitness",
    ]

    possui_roupa = any(
        normalizar_texto(
            termo
        ) in texto
        for termo in termos_roupa
    )

    if not possui_roupa:
        return False

    # --------------------------------------------------------
    # PRECISA INDICAR FITNESS/FEMININO
    # --------------------------------------------------------

    termos_femininos = [
        "feminina",
        "feminino",
        "fitness",
        "academia",
        "legging",
        "top",
        "cropped",
        "conjunto",
        "short",
        "bermuda",
        "regata",
        "macacao",
        "calca",
    ]

    return any(
        normalizar_texto(
            termo
        ) in texto
        for termo in termos_femininos
    )


# ============================================================
# NORMALIZAÇÃO DO PRODUTO
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
            and preco is not None
            and float(preco_original) > 0
            and float(preco)
            < float(preco_original)
        ):

            desconto = round(
                (
                    1
                    -
                    (
                        float(preco)
                        /
                        float(preco_original)
                    )
                )
                * 100
            )

    except (
        ValueError,
        TypeError,
    ):

        desconto = 0

    seller = (
        item.get("seller")
        or {}
    )

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

        "nicho":
            NICHO,

        "vendedor":
            seller.get(
                "nickname"
            ),

        "fonte":
            "Mercado Livre",

    }


# ============================================================
# CHAMADA GENÉRICA À API
# ============================================================

def requisicao_ml(
    url,
    params=None,
    timeout=30,
):
    """
    Executa uma requisição GET ao Mercado Livre.

    Não expõe access_token em mensagens de erro.
    """

    try:

        response = requests.get(
            url,
            params=params or {},
            headers=headers_ml(),
            timeout=timeout,
        )

    except requests.RequestException as exc:

        logger.exception(
            "Erro de conexão com Mercado Livre."
        )

        raise RuntimeError(
            f"Erro de conexão com Mercado Livre: {exc}"
        )

    try:

        payload = response.json()

    except ValueError:

        payload = {
            "resposta":
                response.text[:500]
        }

    if response.status_code != 200:

        logger.error(
            "Mercado Livre HTTP %s: %s",
            response.status_code,
            payload,
        )

        if response.status_code == 401:

            raise PermissionError(
                "Mercado Livre recusou o access_token "
                "(HTTP 401)."
            )

        if response.status_code == 403:

            raise PermissionError(
                "Mercado Livre recusou a requisição "
                "(HTTP 403). Verifique as permissões "
                "da aplicação/token e o acesso à API."
            )

        raise RuntimeError(
            f"Mercado Livre HTTP "
            f"{response.status_code}: "
            f"{payload}"
        )

    return payload


# ============================================================
# TESTE DO TOKEN
# ============================================================

def testar_token_ml():
    """
    Testa o access_token usando /users/me.
    """

    token = token_mercado_livre()

    if not token:

        return {
            "ok": False,
            "status": None,
            "erro": "access_token_ausente",
            "mensagem": (
                "Não existe access_token na sessão."
            ),
        }

    url = (
        f"{ML_API_BASE}/users/me"
    )

    try:

        payload = requisicao_ml(
            url
        )

    except PermissionError as exc:

        mensagem = str(
            exc
        )

        status = 403

        if "401" in mensagem:
            status = 401

        return {

            "ok": False,

            "status":
                status,

            "erro":
                "token_nao_autorizado",

            "mensagem":
                mensagem,

        }

    except Exception as exc:

        return {

            "ok": False,

            "status":
                None,

            "erro":
                "erro_api",

            "mensagem":
                str(exc),

        }

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

        },

    }


# ============================================================
# BUSCA MERCADO LIVRE
# ============================================================

def buscar_mercado_livre(
    consulta,
    limite=20,
):
    """
    Busca produtos no Mercado Livre e aplica
    o filtro exclusivo de roupas fitness femininas.
    """

    limite = max(
        1,
        min(
            int(limite),
            50,
        ),
    )

    url = (
        f"{ML_API_BASE}/sites/"
        f"{ML_SITE_ID}/search"
    )

    # Faz uma busca maior para compensar
    # produtos rejeitados pelo filtro.
    limite_api = min(
        50,
        max(
            limite * 3,
            30,
        ),
    )

    params = {
        "q": consulta,
        "limit": limite_api,
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
            getattr(
                Config,
                "APP_VERSION",
                "11.2.0",
            ),

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

    token = (
        token_mercado_livre()
    )

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

    })


# ============================================================
# DIAGNÓSTICO
# ============================================================

@routes.route(
    "/api/diagnostico",
    methods=["GET"],
)
def diagnostico():

    token = (
        token_mercado_livre()
    )

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
            getattr(
                Config,
                "APP_VERSION",
                "11.2.0",
            ),

        "nicho":
            NICHO,

        "foco_exclusivo":
            "roupas_fitness_femininas",

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

        "filtros": {

            "masculino":
                True,

            "infantil":
                True,

            "suplementos":
                True,

        },

        "database":
            estatisticas,

    })


# ============================================================
# DIAGNÓSTICO MERCADO LIVRE
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
        )

    resultado = (
        testar_token_ml()
    )

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

        consulta = (
            "legging fitness feminina"
        )

    else:

        consulta = (
            consulta_original
        )

    # --------------------------------------------------------
    # REMOVE TERMOS PROIBIDOS DA CONSULTA
    # --------------------------------------------------------

    consulta_normalizada = (
        normalizar_texto(
            consulta
        )
    )

    for termo in (
        TERMOS_MASCULINOS
        +
        TERMOS_INFANTIS
        +
        TERMOS_NAO_FITNESS
    ):

        termo_normalizado = (
            normalizar_texto(
                termo
            )
        )

        consulta_normalizada = (
            consulta_normalizada
            .replace(
                termo_normalizado,
                "",
            )
        )

    consulta_normalizada = " ".join(
        consulta_normalizada.split()
    )

    # --------------------------------------------------------
    # GARANTE ROUPA FITNESS FEMININA
    # --------------------------------------------------------

    termos_busca = [
        "legging",
        "fitness",
        "academia",
        "top",
        "cropped",
        "conjunto",
        "short",
        "bermuda",
        "calca",
        "macacao",
        "regata",
    ]

    possui_termo = any(
        termo in consulta_normalizada
        for termo in termos_busca
    )

    if not possui_termo:

        consulta_normalizada = (
            f"{consulta_normalizada} "
            "fitness feminina"
        )

    # Sempre reforça feminino.
    if "feminina" not in consulta_normalizada:

        consulta_normalizada = (
            f"{consulta_normalizada} feminina"
        )

    consulta = " ".join(
        consulta_normalizada.split()
    )

    # --------------------------------------------------------
    # CONFIGURAÇÃO
    # --------------------------------------------------------

    if not mercado_livre_configurado():

        return resposta_erro(
            "Mercado Livre não configurado.",
            503,
            mensagem=(
                "Configure ML_CLIENT_ID, "
                "ML_CLIENT_SECRET e "
                "ML_REDIRECT_URI no Render."
            ),
        )

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    if not token_mercado_livre():

        return resposta_erro(
            "Mercado Livre não conectado.",
            401,
            mensagem=(
                "Conecte o Mercado Livre antes "
                "de realizar a busca."
            ),
        )

    # --------------------------------------------------------
    # BUSCA
    #
    # Não fazemos /users/me antes da busca.
    # A própria busca será usada para verificar
    # se o token possui acesso.
    # --------------------------------------------------------

    try:

        produtos = (
            buscar_mercado_livre(
                consulta,
                limite,
            )
        )

    except PermissionError as exc:

        logger.exception(
            "Mercado Livre recusou a busca."
        )

        return resposta_erro(
            "Mercado Livre recusou a busca.",
            403,
            nicho=NICHO,
            consulta=consulta,
            mensagem=str(exc),
            acao=(
                "Verifique no Mercado Livre "
                "se a aplicação possui acesso "
                "à API e se o usuário autorizado "
                "está correto."
            ),
        )

    except Exception as exc:

        logger.exception(
            "Erro realizando busca."
        )

        return resposta_erro(
            "Erro ao buscar produtos.",
            502,
            nicho=NICHO,
            consulta=consulta,
            detalhe=str(exc),
        )

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

    if not mercado_livre_configurado():

        return resposta_erro(
            "Mercado Livre não configurado.",
            503,
        )

    if not token_mercado_livre():

        return resposta_erro(
            "Mercado Livre não conectado.",
            401,
        )

    resultados = []

    vistos = set()

    # Cada consulta busca exclusivamente
    # roupas fitness femininas.
    consultas = TERMOS_FITNESS.copy()

    try:

        for consulta in consultas:

            faltam = (
                limite
                -
                len(resultados)
            )

            if faltam <= 0:
                break

            quantidade = min(
                max(
                    faltam * 2,
                    10,
                ),
                50,
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

    except PermissionError as exc:

        logger.exception(
            "Mercado Livre recusou a busca fitness."
        )

        return resposta_erro(
            "Mercado Livre recusou a busca.",
            403,
            nicho=NICHO,
            mensagem=str(exc),
        )

    except Exception as exc:

        logger.exception(
            "Erro na busca fitness feminina."
        )

        return resposta_erro(
            "Erro buscando roupas fitness femininas.",
            502,
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
# OFERTAS SALVAS
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

        dados = (
            db.buscar_publicacoes(
                limite=limite
            )
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
                getattr(
                    Config,
                    "APP_VERSION",
                    "11.2.0",
                ),

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

            "foco":
                "roupas_fitness_femininas",

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
            getattr(
                Config,
                "APP_VERSION",
                "11.2.0",
            ),

        "nicho":
            NICHO,

    })


# ============================================================
# EXPORTAÇÃO
# ============================================================

__all__ = [
    "routes",
]
