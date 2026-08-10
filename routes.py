"""
ROUTES.PY
Robo de Ofertas ML
Versão 11.1

FOCO:
    Roupas Fitness Femininas

ROTAS PRINCIPAIS:
    /api/status
    /api/auth/status
    /api/diagnostico
    /api/diagnostico/ml
    /api/buscar
    /api/buscar-fitness
    /api/ofertas
    /api/publicacoes
    /health

IMPORTANTE:
    A autenticação OAuth fica no auth.py.
    Este arquivo NÃO registra o blueprint "auth".
"""

from __future__ import annotations

import logging
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
)

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
# NICHO
# ============================================================

NICHO = "Roupas Fitness Femininas"


TERMOS_FITNESS = [
    "legging fitness feminina",
    "legging academia feminina",
    "calça legging feminina",
    "calca legging feminina",
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
    "macacão fitness feminino",
    "macacao fitness feminino",
    "calça fitness feminina",
    "calca fitness feminina",
]


TERMOS_BLOQUEADOS = [
    "masculino",
    "masculina",
    "homem",
    "homens",
    "menino",
    "meninos",
    "infantil masculino",
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


def token_mercado_livre():
    """
    Obtém o access token da sessão.

    NÃO exibe o token no log nem nas respostas.
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
    Compatibilidade com config.py em português
    ou inglês.
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
    Headers padrão da API Mercado Livre.
    """

    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "Robo-Ofertas-ML/11.1"
        ),
    }

    token = token_mercado_livre()

    if token:
        headers[
            "Authorization"
        ] = (
            f"Bearer {token}"
        )

    return headers


def produto_feminino(
    titulo,
):
    """
    Verifica se o produto pertence ao nicho
    de roupas fitness femininas.
    """

    titulo = (
        str(titulo or "")
        .lower()
        .strip()
    )

    # --------------------------------------------------------
    # BLOQUEIA MASCULINO
    # --------------------------------------------------------

    for termo in TERMOS_BLOQUEADOS:

        if termo in titulo:
            return False

    # --------------------------------------------------------
    # PROCURA TERMOS FITNESS/FEMININOS
    # --------------------------------------------------------

    termos_validos = [
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
        "macacão",
        "calca",
        "calça",
    ]

    return any(
        termo in titulo
        for termo in termos_validos
    )


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
# TESTE DO TOKEN — /users/me
# ============================================================

def testar_token_ml():
    """
    Testa o access_token diretamente no endpoint
    /users/me.

    Este é o primeiro diagnóstico para o 403.
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

        response = requests.get(
            url,
            headers=headers_ml(),
            timeout=30,
        )

    except requests.RequestException as exc:

        logger.exception(
            "Erro conectando ao /users/me."
        )

        return {
            "ok": False,
            "status": None,
            "erro": "conexao",
            "mensagem": str(exc),
        }

    try:

        payload = response.json()

    except ValueError:

        payload = {
            "resposta": response.text[:500]
        }

    # --------------------------------------------------------
    # TOKEN OK
    # --------------------------------------------------------

    if response.status_code == 200:

        return {

            "ok": True,

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

    # --------------------------------------------------------
    # TOKEN NEGADO
    # --------------------------------------------------------

    if response.status_code == 403:

        return {

            "ok": False,

            "status":
                403,

            "erro":
                "forbidden",

            "mensagem": (
                "O Mercado Livre recusou o "
                "access_token no endpoint /users/me."
            ),

            "resposta":
                payload,

            "acao": (
                "Verificar permissões/scopes, "
                "usuário autorizado, IP permitido "
                "e estado da aplicação no DevCenter."
            ),

        }

    # --------------------------------------------------------
    # OUTROS ERROS
    # --------------------------------------------------------

    return {

        "ok": False,

        "status":
            response.status_code,

        "erro":
            "mercado_livre",

        "resposta":
            payload,

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
        f"{ML_API_BASE}/sites/"
        f"{ML_SITE_ID}/search"
    )

    params = {
        "q": consulta,
        "limit": limite,
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers_ml(),
            timeout=30,
        )

    except requests.RequestException as exc:

        logger.exception(
            "Erro de conexão com Mercado Livre."
        )

        raise RuntimeError(
            f"Erro de conexão: {exc}"
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

        raise RuntimeError(
            f"Mercado Livre HTTP "
            f"{response.status_code}: "
            f"{payload}"
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
        estatisticas = db.estatisticas()
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
                "11.1.0",
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

    })


# ============================================================
# DIAGNÓSTICO COMPLETO
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
        estatisticas = db.estatisticas()
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
                "11.1.0",
            ),

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

        "database":
            estatisticas,

    })


# ============================================================
# DIAGNÓSTICO ESPECÍFICO DO MERCADO LIVRE
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

    consulta = (
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

    if not consulta:

        consulta = (
            "legging fitness feminina"
        )

    # --------------------------------------------------------
    # REMOVE TERMOS MASCULINOS
    # --------------------------------------------------------

    consulta_lower = (
        consulta.lower()
    )

    for termo in TERMOS_BLOQUEADOS:

        consulta_lower = (
            consulta_lower
            .replace(
                termo,
                "",
            )
        )

    consulta = " ".join(
        consulta_lower.split()
    )

    # --------------------------------------------------------
    # GARANTE O NICHO
    # --------------------------------------------------------

    termos_validos = [
        "legging",
        "fitness",
        "academia",
        "top",
        "cropped",
        "conjunto",
        "short",
        "bermuda",
        "calca",
        "calça",
    ]

    if not any(
        termo in consulta.lower()
        for termo in termos_validos
    ):

        consulta = (
            f"{consulta} "
            "fitness feminina"
        )

    # --------------------------------------------------------
    # CONFIGURAÇÃO
    # --------------------------------------------------------

    if not mercado_livre_configurado():

        return resposta_erro(
            "Mercado Livre não configurado.",
            503,
            mensagem=(
                "Configure as credenciais "
                "do Mercado Livre no Render."
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
    # PRIMEIRO TESTA TOKEN
    # --------------------------------------------------------

    teste_token = (
        testar_token_ml()
    )

    if not teste_token.get(
        "ok"
    ):

        if teste_token.get(
            "status"
        ) == 403:

            return resposta_erro(

                "Mercado Livre recusou o access_token.",

                403,

                diagnostico=teste_token,

                mensagem=(
                    "A autenticação visualmente foi "
                    "concluída, mas o token não está "
                    "autorizado para a API."
                ),

            )

        return resposta_erro(

            "Token Mercado Livre inválido ou indisponível.",

            401,

            diagnostico=teste_token,

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

    except Exception as exc:

        logger.exception(
            "Erro realizando busca."
        )

        return resposta_erro(
            "Erro ao buscar produtos.",
            502,
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
# BUSCA AUTOMÁTICA
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

    consultas = [
        "legging fitness feminina",
        "conjunto fitness feminino",
        "top academia feminino",
        "short fitness feminino",
        "cropped fitness feminino",
    ]

    resultados = []

    vistos = set()

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    if not token_mercado_livre():

        return resposta_erro(
            "Mercado Livre não conectado.",
            401,
        )

    # --------------------------------------------------------
    # TESTE DO TOKEN
    # --------------------------------------------------------

    teste = testar_token_ml()

    if not teste.get(
        "ok"
    ):

        return resposta_erro(
            "Token do Mercado Livre não autorizado.",
            403,
            diagnostico=teste,
        )

    # --------------------------------------------------------
    # BUSCAS
    # --------------------------------------------------------

    try:

        for consulta in consultas:

            produtos = (
                buscar_mercado_livre(
                    consulta,
                    min(
                        limite,
                        20,
                    ),
                )
            )

            for produto in produtos:

                produto_id = produto.get(
                    "id"
                )

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

            if len(resultados) >= limite:
                break

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
                getattr(
                    Config,
                    "APP_VERSION",
                    "11.1.0",
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
                "11.1.0",
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
