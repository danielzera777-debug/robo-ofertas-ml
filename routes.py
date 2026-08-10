"""
ROUTES.PY
Robo de Ofertas ML
Versão 11.2

FOCO EXCLUSIVO:
    ROUPAS FITNESS FEMININAS

Não registra o blueprint de autenticação.
A autenticação OAuth fica no auth.py.

Principais rotas:
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
    "bermuda academia feminina",
    "cropped fitness feminino",
    "cropped academia feminino",
    "blusa fitness feminina",
    "blusa academia feminina",
    "camiseta fitness feminina",
    "camiseta academia feminina",
    "regata fitness feminina",
    "regata academia feminina",
    "macacão fitness feminino",
    "macacao fitness feminino",
    "calça fitness feminina",
    "calca fitness feminina",
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
# AUXILIARES
# ============================================================

def resposta_erro(
    mensagem,
    status=400,
    **extra,
):
    """
    Retorna erro JSON.

    IMPORTANTE:
    Não passar mensagem= dentro de **extra,
    pois mensagem já é argumento desta função.
    """

    resposta = {
        "sucesso": False,
        "erro": mensagem,
    }

    resposta.update(extra)

    return jsonify(resposta), status


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


def remover_acentos(texto):
    texto = str(texto or "")

    return "".join(
        caractere
        for caractere in unicodedata.normalize(
            "NFD",
            texto,
        )
        if unicodedata.category(
            caractere
        ) != "Mn"
    )


def texto_normalizado(texto):
    return (
        remover_acentos(texto)
        .lower()
        .strip()
    )


# ============================================================
# TOKEN
# ============================================================

def token_mercado_livre():
    """
    Primeiro procura o token OAuth na sessão.

    Não mostra o token em logs ou respostas.
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


# ============================================================
# CONFIGURAÇÃO MERCADO LIVRE
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


# ============================================================
# HEADERS MERCADO LIVRE
# ============================================================

def headers_ml():

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


# ============================================================
# FILTRO FEMININO
# ============================================================

def produto_feminino(
    titulo,
):
    """
    Aceita somente produtos relacionados
    a roupas fitness femininas.

    Produtos masculinos são rejeitados.
    """

    texto = texto_normalizado(
        titulo
    )

    if not texto:
        return False

    # --------------------------------------------------------
    # BLOQUEIO MASCULINO
    # --------------------------------------------------------

    for termo in TERMOS_BLOQUEADOS:

        if texto_normalizado(
            termo
        ) in texto:

            return False

    # --------------------------------------------------------
    # PALAVRAS DE ROUPA
    # --------------------------------------------------------

    palavras_roupa = [
        "legging",
        "calca",
        "calça",
        "top",
        "cropped",
        "conjunto",
        "short",
        "bermuda",
        "regata",
        "camiseta",
        "blusa",
        "macacao",
        "macacão",
    ]

    tem_roupa = any(
        texto_normalizado(
            termo
        ) in texto
        for termo in palavras_roupa
    )

    if not tem_roupa:
        return False

    # --------------------------------------------------------
    # CONTEXTO FITNESS
    # --------------------------------------------------------

    contexto_fitness = [
        "fitness",
        "academia",
        "treino",
        "treino feminino",
        "esportiva",
        "esportivo",
        "gym",
        "corrida",
        "pilates",
        "crossfit",
    ]

    tem_fitness = any(
        texto_normalizado(
            termo
        ) in texto
        for termo in contexto_fitness
    )

    # --------------------------------------------------------
    # PRODUTOS CLARAMENTE FEMININOS
    # --------------------------------------------------------

    feminino = [
        "feminina",
        "feminino",
        "mulher",
        "mulheres",
    ]

    tem_feminino = any(
        texto_normalizado(
            termo
        ) in texto
        for termo in feminino
    )

    # Legging/top/conjunto etc. podem aparecer
    # sem "feminina" no título. Nesses casos,
    # aceitamos se o produto tiver contexto fitness.
    if tem_fitness:
        return True

    if tem_feminino:
        return True

    return False


# ============================================================
# PREÇO
# ============================================================

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
            and preco
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
            item.get("id"),

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
# REQUISIÇÃO MERCADO LIVRE
# ============================================================

def requisicao_ml(
    url,
    params=None,
):

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
            f"Erro de conexão com Mercado Livre: {exc}"
        ) from exc

    try:

        payload = response.json()

    except ValueError:

        payload = {
            "resposta":
                response.text[:500]
        }

    if response.status_code == 401:

        raise PermissionError(
            "Mercado Livre retornou HTTP 401. "
            "O access_token é inválido ou expirou."
        )

    if response.status_code == 403:

        logger.error(
            "Mercado Livre HTTP 403: %s",
            payload,
        )

        raise PermissionError(
            "Mercado Livre recusou a requisição "
            "(HTTP 403). Verifique as permissões "
            "da aplicação/token e o acesso à API."
        )

    if response.status_code != 200:

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
            "resposta":
                response.text[:500]
        }

    if response.status_code == 200:

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

    if response.status_code == 401:

        return {

            "ok":
                False,

            "status":
                401,

            "erro":
                "unauthorized",

            "mensagem":
                "Access token inválido ou expirado.",

            "resposta":
                payload,

        }

    if response.status_code == 403:

        return {

            "ok":
                False,

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
                "Verifique as permissões da aplicação "
                "no Mercado Livre e faça uma nova "
                "autorização OAuth."
            ),

        }

    return {

        "ok":
            False,

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
# CONSTRUIR CONSULTA
# ============================================================

def preparar_consulta(
    consulta,
):

    consulta = (
        str(consulta or "")
        .strip()
    )

    if not consulta:

        return (
            "legging fitness feminina"
        )

    consulta_normalizada = (
        texto_normalizado(
            consulta
        )
    )

    # Remove termos masculinos.
    for termo in TERMOS_BLOQUEADOS:

        consulta_normalizada = (
            consulta_normalizada
            .replace(
                texto_normalizado(
                    termo
                ),
                "",
            )
        )

    consulta_normalizada = (
        " ".join(
            consulta_normalizada.split()
        )
    )

    # --------------------------------------------------------
    # GARANTE ROUPA FITNESS FEMININA
    # --------------------------------------------------------

    palavras_roupa = [
        "legging",
        "calca",
        "top",
        "cropped",
        "conjunto",
        "short",
        "bermuda",
        "regata",
        "camiseta",
        "blusa",
        "macacao",
    ]

    tem_roupa = any(
        palavra in consulta_normalizada
        for palavra in palavras_roupa
    )

    if not tem_roupa:

        consulta_normalizada = (
            f"{consulta_normalizada} "
            "roupa fitness feminina"
        )

    if "fitness" not in consulta_normalizada:

        consulta_normalizada = (
            f"{consulta_normalizada} fitness"
        )

    if "feminina" not in consulta_normalizada:

        consulta_normalizada = (
            f"{consulta_normalizada} feminina"
        )

    return " ".join(
        consulta_normalizada.split()
    )


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

    consulta = preparar_consulta(
        consulta_original
    )

    # --------------------------------------------------------
    # CONFIG
    # --------------------------------------------------------

    if not mercado_livre_configurado():

        return resposta_erro(
            "Mercado Livre não configurado.",
            503,
            detalhe=(
                "Configure ML_CLIENT_ID, "
                "ML_CLIENT_SECRET e ML_REDIRECT_URI."
            ),
        )

    # --------------------------------------------------------
    # TOKEN
    # --------------------------------------------------------

    if not token_mercado_livre():

        return resposta_erro(
            "Mercado Livre não conectado.",
            401,
            detalhe=(
                "Conecte o Mercado Livre "
                "antes de realizar a busca."
            ),
        )

    # --------------------------------------------------------
    # TESTE TOKEN
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

            # CORREÇÃO IMPORTANTE:
            # não usar mensagem= aqui.
            return resposta_erro(
                "Mercado Livre recusou o access_token.",
                403,
                diagnostico=teste_token,
                detalhe=(
                    "O OAuth terminou, mas o token "
                    "não está autorizado pela API."
                ),
            )

        if teste_token.get(
            "status"
        ) == 401:

            return resposta_erro(
                "Access token Mercado Livre inválido.",
                401,
                diagnostico=teste_token,
            )

        return resposta_erro(
            "Não foi possível validar o token Mercado Livre.",
            502,
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

    except PermissionError as exc:

        logger.error(
            "Mercado Livre recusou a busca: %s",
            exc,
        )

        return resposta_erro(
            "Mercado Livre recusou a busca.",
            403,
            detalhe=str(exc),
            diagnostico={
                "nicho": NICHO,
                "consulta": consulta,
                "acao": (
                    "Verifique as permissões da aplicação "
                    "e faça novamente o OAuth."
                ),
            },
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

    consultas = [
        "legging fitness feminina",
        "conjunto fitness feminino",
        "top academia feminino",
        "short fitness feminino",
        "cropped fitness feminino",
    ]

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

    teste = (
        testar_token_ml()
    )

    if not teste.get(
        "ok"
    ):

        return resposta_erro(
            "Token do Mercado Livre não autorizado.",
            teste.get(
                "status"
            ) or 502,
            diagnostico=teste,
        )

    resultados = []

    vistos = set()

    try:

        for consulta in consultas:

            quantidade_restante = (
                limite - len(resultados)
            )

            if quantidade_restante <= 0:
                break

            produtos = (
                buscar_mercado_livre(
                    consulta,
                    min(
                        quantidade_restante,
                        20,
                    ),
                )
            )

            for produto in produtos:

                produto_id = (
                    produto.get("id")
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

        logger.error(
            "Mercado Livre recusou a busca fitness: %s",
            exc,
        )

        return resposta_erro(
            "Mercado Livre recusou a busca.",
            403,
            detalhe=str(exc),
            diagnostico=teste,
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
