"""
ROTAS PRINCIPAIS — ROBO DE OFERTAS ML
Versão: 11.0

Foco atual:
- Roupas fitness femininas
- Integração Mercado Livre
- Busca de produtos
- Ofertas
- Status
- Diagnóstico
- Autenticação já existente em auth.py

A rota principal de busca é:
GET /api/buscar?produto=Leggings&limite=20
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


# ============================================================
# BLUEPRINT
# ============================================================

routes = Blueprint(
    "routes",
    __name__,
)


# ============================================================
# CATEGORIA — ROUPAS FITNESS FEMININAS
# ============================================================

CATEGORIA_FITNESS_FEMININA = {
    "nome": "Roupas Fitness Femininas",

    "termos": [
        "legging fitness feminina",
        "calca legging feminina academia",
        "conjunto fitness feminino",
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
        "vestido fitness feminino",
        "calca academia feminina",
        "roupa academia feminina",
    ],
}


# ============================================================
# URL API MERCADO LIVRE
# ============================================================

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
# FUNÇÕES AUXILIARES
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


def numero(
    valor,
    padrao=0,
):
    try:
        return float(valor)
    except (
        ValueError,
        TypeError,
    ):
        return float(padrao)


def token_mercado_livre():
    """
    Recupera o access_token da sessão.
    """

    return session.get(
        "access_token"
    ) or getattr(
        Config,
        "ML_ACCESS_TOKEN",
        "",
    )


def mercado_livre_configurado():
    """
    Compatibilidade com as duas versões possíveis
    do config.py.
    """

    metodo = getattr(
        Config,
        "mercado_livre_configured",
        None,
    )

    if callable(metodo):
        try:
            return bool(metodo())
        except Exception:
            logger.exception(
                "Erro em mercado_livre_configured()."
            )

    metodo = getattr(
        Config,
        "mercado_livre_configurado",
        None,
    )

    if callable(metodo):
        try:
            return bool(metodo())
        except Exception:
            logger.exception(
                "Erro em mercado_livre_configurado()."
            )

    return bool(
        getattr(
            Config,
            "ML_CLIENT_ID",
            "",
        )
        and getattr(
            Config,
            "ML_CLIENT_SECRET",
            "",
        )
        and getattr(
            Config,
            "ML_REDIRECT_URI",
            "",
        )
    )


def headers_mercado_livre():
    """
    Monta os headers da API do Mercado Livre.
    """

    headers = {
        "Accept": "application/json",
        "User-Agent": "Robo-Ofertas-ML/11.0",
    }

    token = token_mercado_livre()

    if token:
        headers[
            "Authorization"
        ] = f"Bearer {token}"

    return headers


# ============================================================
# FILTRO — SOMENTE FEMININO
# ============================================================

def produto_e_feminino(titulo):
    """
    Impede que produtos masculinos ou genéricos
    entrem na busca de roupas fitness femininas.
    """

    titulo = (
        str(titulo or "")
        .lower()
        .strip()
    )

    palavras_bloqueadas = [
        "masculino",
        "masculina",
        "homem",
        "menino",
        "infantil masculino",
        "juvenil masculino",
    ]

    for palavra in palavras_bloqueadas:
        if palavra in titulo:
            return False

    palavras_femininas = [
        "feminina",
        "feminino",
        "mulher",
        "legging",
        "top fitness",
        "top academia",
        "conjunto fitness",
        "short fitness",
        "cropped fitness",
        "calça fitness",
        "calca fitness",
        "academia",
        "fitness",
    ]

    return any(
        palavra in titulo
        for palavra in palavras_femininas
    )


# ============================================================
# BUSCA DIRETA NO MERCADO LIVRE
# ============================================================

def buscar_mercado_livre(
    consulta,
    limite=20,
):
    """
    Faz a busca diretamente na API pública/autenticada
    do Mercado Livre.

    Não depende dos services do projeto.
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

    params = {
        "q": consulta,
        "limit": limite,
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers_mercado_livre(),
            timeout=30,
        )

    except requests.RequestException as exc:

        logger.exception(
            "Erro de conexão com Mercado Livre."
        )

        raise RuntimeError(
            f"Erro de conexão com Mercado Livre: {exc}"
        )

    if response.status_code != 200:

        try:
            detalhe = response.json()
        except ValueError:
            detalhe = response.text

        logger.error(
            "Mercado Livre retornou HTTP %s: %s",
            response.status_code,
            detalhe,
        )

        raise RuntimeError(
            f"Mercado Livre retornou HTTP "
            f"{response.status_code}: {detalhe}"
        )

    try:
        dados = response.json()
    except ValueError:
        raise RuntimeError(
            "Resposta inválida do Mercado Livre."
        )

    resultados = []

    for item in dados.get(
        "results",
        [],
    ):

        titulo = item.get(
            "title",
            "",
        )

        if not produto_e_feminino(
            titulo
        ):
            continue

        preco = item.get(
            "price",
            0,
        )

        original = item.get(
            "original_price"
        )

        desconto = 0

        try:

            if (
                original
                and float(original) > 0
                and float(preco) < float(original)
            ):

                desconto = round(
                    (
                        1
                        - (
                            float(preco)
                            / float(original)
                        )
                    )
                    * 100
                )

        except (
            ValueError,
            TypeError,
        ):
            desconto = 0

        resultados.append({

            "id":
                item.get(
                    "id"
                ),

            "titulo":
                titulo,

            "preco":
                preco,

            "preco_formatado":
                f"R$ {float(preco):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", "."),

            "preco_original":
                original,

            "desconto":
                desconto,

            "link":
                item.get(
                    "permalink"
                ),

            "thumbnail":
                item.get(
                    "thumbnail"
                ),

            "imagem":
                item.get(
                    "thumbnail"
                ),

            "categoria":
                "Roupas Fitness Femininas",

            "vendedor":
                (
                    item.get(
                        "seller",
                        {}
                    )
                    .get(
                        "nickname"
                    )
                ),

        })

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

        "sucesso": True,

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
                "11.0.0",
            ),

        "nicho":
            "Roupas Fitness Femininas",

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

        "sucesso": True,

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
# BUSCAR — ROTA PRINCIPAL
# ============================================================

@routes.route(
    "/api/buscar",
    methods=["GET"],
)
def buscar():

    """
    Busca SOMENTE roupas fitness femininas.

    Exemplos:

    /api/buscar?produto=Leggings&limite=20

    /api/buscar?produto=Roupas%20fitness&limite=20

    /api/buscar?produto=Top%20fitness&limite=20
    """

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

    # --------------------------------------------------------
    # SEM CONSULTA
    # --------------------------------------------------------

    if not consulta:

        consulta = (
            "legging fitness feminina"
        )

    # --------------------------------------------------------
    # FORÇA O FOCO FEMININO
    # --------------------------------------------------------

    consulta_lower = (
        consulta.lower()
    )

    termos_femininos = [
        "feminina",
        "feminino",
        "mulher",
        "legging",
        "top",
        "fitness",
        "academia",
        "cropped",
        "conjunto",
        "short",
        "calça",
        "calca",
    ]

    tem_foco = any(
        termo in consulta_lower
        for termo in termos_femininos
    )

    if not tem_foco:

        consulta = (
            f"{consulta} "
            "fitness feminina"
        )

    # --------------------------------------------------------
    # REMOVE BUSCA MASCULINA
    # --------------------------------------------------------

    termos_masculinos = [
        "masculino",
        "masculina",
        "homem",
        "menino",
    ]

    for termo in termos_masculinos:

        consulta = consulta.replace(
            termo,
            "",
        )

    consulta = " ".join(
        consulta.split()
    )

    # --------------------------------------------------------
    # TOKEN
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
    # BUSCA
    # --------------------------------------------------------

    try:

        produtos = buscar_mercado_livre(
            consulta=consulta,
            limite=limite,
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

        "categoria":
            "Roupas Fitness Femininas",

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

    consultas = [
        "legging fitness feminina",
        "conjunto fitness feminino",
        "top academia feminino",
        "short fitness feminino",
        "cropped fitness feminino",
    ]

    resultados = []

    vistos = set()

    try:

        for consulta in consultas:

            produtos = buscar_mercado_livre(
                consulta,
                min(limite, 20),
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
            "Erro na busca automática fitness feminina."
        )

        return resposta_erro(
            "Erro ao buscar roupas fitness femininas.",
            502,
            detalhe=str(exc),
        )

    return jsonify({

        "sucesso":
            True,

        "categoria":
            "Roupas Fitness Femininas",

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
# SALVAR OFERTA
# ============================================================

@routes.route(
    "/api/ofertas",
    methods=["POST"],
)
def salvar_oferta():

    dados = request.get_json(
        silent=True
    )

    if not isinstance(
        dados,
        dict,
    ):
        return resposta_erro(
            "Dados inválidos."
        )

    try:

        oferta_id = db.salvar_oferta(
            dados.get(
                "oferta",
                dados,
            )
        )

    except Exception as exc:

        logger.exception(
            "Erro salvando oferta."
        )

        return resposta_erro(
            "Erro ao salvar oferta.",
            500,
            detalhe=str(exc),
        )

    return jsonify({

        "sucesso":
            True,

        "id":
            oferta_id,

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
# CONFIGURAÇÕES
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
                    "11.0.0",
                ),

            "site_id":
                ML_SITE_ID,

            "categoria":
                "Roupas Fitness Femininas",

            "margem_padrao":
                getattr(
                    Config,
                    "MARGEM_PADRAO",
                    10,
                ),

            "lucro_minimo":
                getattr(
                    Config,
                    "LUCRO_MINIMO_PADRAO",
                    20,
                ),

            "limite_ofertas":
                getattr(
                    Config,
                    "LIMITE_OFERTAS",
                    50,
                ),

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

    token = token_mercado_livre()

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
                "11.0.0",
            ),

        "categoria":
            "Roupas Fitness Femininas",

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

            "redirect_uri_configurado":
                bool(
                    getattr(
                        Config,
                        "ML_REDIRECT_URI",
                        "",
                    )
                ),

        },

        "database":
            estatisticas,

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
                "11.0.0",
            ),

        "categoria":
            "Roupas Fitness Femininas",

    })


# ============================================================
# EXPORTAÇÃO
# ============================================================

__all__ = [
    "routes",
]
