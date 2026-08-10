"""
Rotas principais do Robô de Ofertas ML.

FOCO ATUAL:
- Somente roupas fitness femininas.
- Busca no Mercado Livre.
- Autenticação fica no auth.py.
- Não registra Blueprint de autenticação aqui.

Rotas principais:
    /api/status
    /api/auth/status
    /api/buscar
    /api/ofertas
    /api/ofertas/preparar
    /api/post
    /api/imagem
    /api/whatsapp/status
    /api/whatsapp/enviar
    /api/publicacoes
    /api/config
    /api/diagnostico
    /health
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import requests

from flask import (
    Blueprint,
    jsonify,
    request,
    session,
)

from config import get_config
from database import db

from services.affiliate_service import (
    AffiliateService,
)

from services.offer_service import (
    OfferService,
)

from services.post_service import (
    PostService,
)

from services.image_service import (
    ImageService,
)

from services.whatsapp_service import (
    WhatsAppService,
)


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
# SERVIÇOS
# ============================================================

affiliate_service = AffiliateService()
offer_service = OfferService()
post_service = PostService()
image_service = ImageService()
whatsapp_service = WhatsAppService()


# ============================================================
# CONFIGURAÇÃO DO NICHO
# ============================================================

NICHO_FITNESS_FEMININO = [

    "legging fitness feminina",
    "conjunto fitness feminino",
    "top fitness feminino",
    "short fitness feminino",
    "camiseta fitness feminina",
    "blusa fitness feminina",
    "cropped fitness feminino",
    "calça fitness feminina",
    "macacão fitness feminino",
    "bermuda fitness feminina",
    "regata fitness feminina",
    "body fitness feminino",
    "shorts academia feminino",
    "legging academia feminina",
    "conjunto academia feminino",
]


# ============================================================
# TERMOS OBRIGATÓRIOS
# ============================================================

TERMOS_FEMININOS = [

    "feminina",
    "feminino",
    "mulher",
    "women",
    "woman",
    "girl",
]


TERMOS_ROUPA = [

    "legging",
    "conjunto",
    "top",
    "short",
    "shorts",
    "camiseta",
    "camisa",
    "blusa",
    "cropped",
    "calça",
    "macacão",
    "bermuda",
    "regata",
    "body",
]


# ============================================================
# TERMOS QUE DEVEM SER BLOQUEADOS
# ============================================================

TERMOS_BLOQUEADOS = [

    # Masculino
    "masculino",
    "masculina",
    "homem",
    "homens",
    "men",
    "man",

    # Suplementos
    "whey",
    "creatina",
    "creatine",
    "hipercalorico",
    "hipercalórico",
    "bcaa",
    "glutamina",
    "pré treino",
    "pre treino",
    "pré-treino",
    "pre-treino",
    "suplemento",
    "suplementos",
    "vitamina",
    "vitaminas",

    # Eletrônicos
    "celular",
    "smartphone",
    "iphone",
    "samsung",
    "xiaomi",
    "tablet",
    "notebook",
    "computador",
    "fone",
    "headset",
    "smartwatch",

    # Outros
    "kit whey",
    "barra de proteína",
    "barra proteica",
]


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

    return jsonify(
        resposta
    ), status


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


def inteiro(
    valor,
    padrao=0,
):

    try:
        return int(valor)

    except (
        ValueError,
        TypeError,
    ):
        return int(padrao)


def mercado_livre_configurado():
    """
    Compatibilidade com versões diferentes do config.py.
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
                "Erro verificando configuração ML."
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
                "Erro verificando configuração ML."
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


def token_mercado_livre():

    return (

        session.get(
            "access_token"
        )

        or

        getattr(
            Config,
            "ML_ACCESS_TOKEN",
            "",
        )
    )


def texto_produto(produto):

    if not isinstance(
        produto,
        dict,
    ):
        return ""

    campos = [

        produto.get(
            "titulo"
        ),

        produto.get(
            "title"
        ),

        produto.get(
            "nome"
        ),

        produto.get(
            "name"
        ),

        produto.get(
            "category_name"
        ),

    ]

    return " ".join(
        str(x or "")
        for x in campos
    ).lower()


def produto_fitness_feminino(produto):
    """
    Verifica se o produto pertence ao nicho
    roupas fitness femininas.
    """

    texto = texto_produto(
        produto
    )

    if not texto:
        return False

    # Primeiro elimina produtos proibidos.
    for termo in TERMOS_BLOQUEADOS:

        if termo.lower() in texto:
            return False

    # Precisa ser uma peça de roupa.
    possui_roupa = any(

        termo.lower() in texto

        for termo in TERMOS_ROUPA

    )

    if not possui_roupa:
        return False

    # Precisa possuir indicação feminina.
    possui_feminino = any(

        termo.lower() in texto

        for termo in TERMOS_FEMININOS

    )

    return possui_feminino


def normalizar_produto(
    produto
):

    if not isinstance(
        produto,
        dict,
    ):
        return None

    titulo = (

        produto.get(
            "titulo"
        )

        or

        produto.get(
            "title"
        )

        or

        produto.get(
            "nome"
        )

        or

        produto.get(
            "name"
        )

        or

        "Produto fitness feminino"
    )

    imagem = (

        produto.get(
            "imagem"
        )

        or

        produto.get(
            "thumbnail"
        )

        or

        produto.get(
            "picture"
        )

        or

        ""
    )

    link = (

        produto.get(
            "link"
        )

        or

        produto.get(
            "permalink"
        )

        or

        produto.get(
            "url"
        )

        or

        "#"
    )

    preco = (

        produto.get(
            "preco"
        )

        or

        produto.get(
            "price"
        )

        or

        0
    )

    try:
        preco = float(
            preco
        )

    except (
        ValueError,
        TypeError,
    ):
        preco = 0.0

    resultado = dict(
        produto
    )

    resultado.update({

        "titulo":
            str(titulo),

        "imagem":
            str(imagem),

        "link":
            str(link),

        "preco":
            preco,

        "categoria":
            "fitness_feminino",

        "nicho":
            "Roupas Fitness Femininas",

    })

    return resultado


# ============================================================
# BUSCA MERCADO LIVRE
# ============================================================

def buscar_mercado_livre(
    termo,
    limite=20,
):
    """
    Busca diretamente na API pública de pesquisa do Mercado Livre.

    O access_token, quando disponível, é enviado.
    """

    base = getattr(
        Config,
        "ML_API_BASE",
        "https://api.mercadolibre.com",
    )

    site_id = getattr(
        Config,
        "ML_SITE_ID",
        "MLB",
    )

    url = (
        base.rstrip("/")
        + "/sites/"
        + site_id
        + "/search"
    )

    headers = {

        "Accept":
            "application/json",

        "User-Agent":
            getattr(
                Config,
                "ML_USER_AGENT",
                "Robo-Ofertas-ML/10.0",
            ),

    }

    token = token_mercado_livre()

    if token:

        headers[
            "Authorization"
        ] = (
            "Bearer "
            + str(token)
        )

    params = {

        "q":
            termo,

        "limit":
            min(
                max(
                    limite,
                    1,
                ),
                50,
            ),

    }

    response = requests.get(

        url,

        params=params,

        headers=headers,

        timeout=(

            getattr(
                Config,
                "ML_CONNECT_TIMEOUT",
                10,
            ),

            getattr(
                Config,
                "ML_READ_TIMEOUT",
                30,
            ),

        ),
    )

    if not response.ok:

        logger.error(

            "Mercado Livre retornou HTTP %s: %s",

            response.status_code,

            response.text[:1000],

        )

        raise RuntimeError(

            "Mercado Livre retornou HTTP "
            + str(
                response.status_code
            )
        )

    dados = response.json()

    resultados = dados.get(
        "results",
        []
    )

    if not isinstance(
        resultados,
        list,
    ):
        return []

    return resultados


# ============================================================
# BUSCAR PRODUTOS
# ============================================================

@routes.route(
    "/api/buscar",
    methods=["GET"],
)
def buscar():

    termo = (

        request.args.get(
            "produto"
        )

        or

        request.args.get(
            "q"
        )

        or

        ""
    ).strip()

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

    if not termo:

        return resposta_erro(
            "Digite um produto para pesquisar."
        )

    # --------------------------------------------------------
    # A busca é sempre direcionada ao nicho feminino.
    # O termo digitado pelo usuário é combinado com fitness
    # feminino.
    # --------------------------------------------------------

    termo_busca = (
        termo
        + " fitness feminino"
    )

    try:

        produtos = (
            buscar_mercado_livre(
                termo_busca,
                limite=50,
            )
        )

    except requests.RequestException as exc:

        logger.exception(
            "Erro comunicando com Mercado Livre."
        )

        return resposta_erro(

            "Não foi possível consultar o Mercado Livre.",

            502,

            detalhe=str(exc),

        )

    except Exception as exc:

        logger.exception(
            "Erro na busca."
        )

        return resposta_erro(

            "Erro ao buscar produtos.",

            500,

            detalhe=str(exc),

        )

    filtrados = []

    for produto in produtos:

        item = normalizar_produto(
            produto
        )

        if not item:
            continue

        if not produto_fitness_feminino(
            item
        ):
            continue

        filtrados.append(
            item
        )

        if len(
            filtrados
        ) >= limite:
            break

    return jsonify({

        "sucesso":
            True,

        "total":
            len(filtrados),

        "produtos":
            filtrados,

        "nicho":
            "fitness_feminino",

        "categoria":
            "Roupas Fitness Femininas",

    })


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
                "Robo Ofertas ML",
            ),

        "versao":
            getattr(
                Config,
                "APP_VERSION",
                "10.0.0",
            ),

        "mercado_livre":
            bool(
                token_mercado_livre()
            ),

        "mercado_livre_configurado":
            mercado_livre_configurado(),

        "nicho":
            "Roupas Fitness Femininas",

        "whatsapp":
            whatsapp_service.configurado(),

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
                bool(
                    session.get(
                        "access_token"
                    )
                ),

            "site_id":
                getattr(
                    Config,
                    "ML_SITE_ID",
                    "MLB",
                ),

        },

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

    status_filtro = (
        request.args.get(
            "status"
        )
    )

    try:

        dados = db.buscar_ofertas(

            limite=limite,

            status=status_filtro,

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

    oferta = (

        dados.get(
            "oferta"
        )

        or

        dados
    )

    try:

        oferta_id = (
            db.salvar_oferta(
                oferta
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

    if not oferta_id:

        return resposta_erro(
            "Não foi possível salvar a oferta."
        )

    return jsonify({

        "sucesso":
            True,

        "id":
            oferta_id,

    })


# ============================================================
# PREPARAR OFERTAS
# ============================================================

@routes.route(
    "/api/ofertas/preparar",
    methods=["POST"],
)
def preparar_ofertas():

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

    produtos = dados.get(
        "produtos",
        [],
    )

    margem = numero(

        dados.get(

            "margem",

            getattr(
                Config,
                "MARGEM_PADRAO",
                10,
            ),

        ),

        getattr(
            Config,
            "MARGEM_PADRAO",
            10,
        ),

    )

    lucro_minimo = numero(

        dados.get(

            "lucro_minimo",

            getattr(
                Config,
                "LUCRO_MINIMO_PADRAO",
                20,
            ),

        ),

        getattr(
            Config,
            "LUCRO_MINIMO_PADRAO",
            20,
        ),

    )

    desconto_minimo = numero(

        dados.get(

            "desconto_minimo",

            getattr(
                Config,
                "DESCONTO_MINIMO_PADRAO",
                0,
            ),

        ),

        getattr(
            Config,
            "DESCONTO_MINIMO_PADRAO",
            0,
        ),

    )

    limite = inteiro(

        dados.get(

            "limite",

            getattr(
                Config,
                "LIMITE_OFERTAS",
                50,
            ),

        ),

        getattr(
            Config,
            "LIMITE_OFERTAS",
            50,
        ),

    )

    limite = max(
        1,
        min(
            limite,
            500,
        ),
    )

    try:

        ofertas = (
            affiliate_service
            .melhores_ofertas(

                produtos=produtos,

                limite=limite,

                margem=margem,

                lucro_minimo=lucro_minimo,

                desconto_minimo=desconto_minimo,

            )
        )

    except Exception as exc:

        logger.exception(
            "Erro preparando ofertas."
        )

        return resposta_erro(

            "Erro ao preparar ofertas.",

            500,

            detalhe=str(exc),

        )

    return jsonify({

        "sucesso":
            True,

        "total":
            len(ofertas),

        "ofertas":
            ofertas,

    })


# ============================================================
# GERAR POST
# ============================================================

@routes.route(
    "/api/post",
    methods=["POST"],
)
def gerar_post():

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

    oferta = (

        dados.get(
            "oferta"
        )

        or

        dados
    )

    try:

        post = (
            post_service
            .criar_post(
                oferta
            )
        )

    except Exception as exc:

        logger.exception(
            "Erro gerando post."
        )

        return resposta_erro(

            "Erro ao gerar post.",

            500,

            detalhe=str(exc),

        )

    if not post:

        return resposta_erro(
            "Não foi possível gerar o post."
        )

    return jsonify({

        "sucesso":
            True,

        "post":
            post,

    })


# ============================================================
# GERAR IMAGEM
# ============================================================

@routes.route(
    "/api/imagem",
    methods=["POST"],
)
def gerar_imagem():

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

    oferta = (

        dados.get(
            "oferta"
        )

        or

        dados
    )

    try:

        caminho = (
            image_service
            .criar_imagem(
                oferta
            )
        )

    except Exception as exc:

        logger.exception(
            "Erro gerando imagem."
        )

        return resposta_erro(

            "Erro ao gerar imagem.",

            500,

            detalhe=str(exc),

        )

    if not caminho:

        return resposta_erro(
            "Não foi possível gerar a imagem."
        )

    return jsonify({

        "sucesso":
            True,

        "arquivo":
            caminho,

    })


# ============================================================
# WHATSAPP STATUS
# ============================================================

@routes.route(
    "/api/whatsapp/status",
    methods=["GET"],
)
def whatsapp_status():

    try:

        resultado = (
            whatsapp_service
            .testar_conexao()
        )

    except Exception as exc:

        logger.exception(
            "Erro verificando WhatsApp."
        )

        return resposta_erro(

            "Erro verificando WhatsApp.",

            500,

            detalhe=str(exc),

        )

    return jsonify(
        resultado
    )


# ============================================================
# WHATSAPP ENVIAR
# ============================================================

@routes.route(
    "/api/whatsapp/enviar",
    methods=["POST"],
)
def whatsapp_enviar():

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

    numero_destino = (

        dados.get(
            "numero"
        )

        or

        dados.get(
            "destinatario"
        )

    )

    oferta = dados.get(
        "oferta"
    )

    try:

        if oferta:

            resultado = (
                whatsapp_service
                .enviar_oferta(

                    numero=numero_destino,

                    oferta=oferta,

                )
            )

        else:

            mensagem = dados.get(
                "mensagem"
            )

            if not mensagem:

                return resposta_erro(

                    "Informe a mensagem ou a oferta."

                )

            resultado = (
                whatsapp_service
                .enviar_texto(

                    numero=numero_destino,

                    mensagem=mensagem,

                )
            )

    except Exception as exc:

        logger.exception(
            "Erro enviando WhatsApp."
        )

        return resposta_erro(

            "Erro ao enviar WhatsApp.",

            500,

            detalhe=str(exc),

        )

    return jsonify(
        resultado
    )


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
                    "Robo Ofertas ML",
                ),

            "site_id":
                getattr(
                    Config,
                    "ML_SITE_ID",
                    "MLB",
                ),

            "nicho":
                "fitness_feminino",

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

            "desconto_minimo":
                getattr(
                    Config,
                    "DESCONTO_MINIMO_PADRAO",
                    0,
                ),

            "limite_ofertas":
                getattr(
                    Config,
                    "LIMITE_OFERTAS",
                    50,
                ),

            "intervalo":
                getattr(
                    Config,
                    "INTERVALO_OFERTAS",
                    0,
                ),

        },

    })


# ============================================================
# SALVAR CONFIG
# ============================================================

@routes.route(
    "/api/config",
    methods=["POST"],
)
def salvar_config():

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

    permitidos = {

        "margem_padrao",
        "lucro_minimo",
        "desconto_minimo",
        "limite_ofertas",
        "intervalo",

    }

    alterados = []

    for chave in permitidos:

        if chave not in dados:
            continue

        try:

            db.salvar_configuracao(

                chave,

                dados[chave],

            )

            alterados.append(
                chave
            )

        except Exception as exc:

            logger.exception(

                "Erro salvando configuração %s.",

                chave,

            )

            return resposta_erro(

                "Erro ao salvar configuração.",

                500,

                detalhe=str(exc),

            )

    return jsonify({

        "sucesso":
            True,

        "alterados":
            alterados,

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
                getattr(
                    Config,
                    "ML_SITE_ID",
                    "MLB",
                ),

            "api":
                getattr(
                    Config,
                    "ML_API_BASE",
                    "https://api.mercadolibre.com",
                ),

            "redirect_uri_configurado":
                bool(
                    getattr(
                        Config,
                        "ML_REDIRECT_URI",
                        "",
                    )
                ),

        },

        "nicho": {

            "codigo":
                "fitness_feminino",

            "nome":
                "Roupas Fitness Femininas",

            "categorias":
                NICHO_FITNESS_FEMININO,

        },

        "whatsapp": {

            "configurado":
                whatsapp_service.configurado(),

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
                "Robo Ofertas ML",
            ),

        "version":
            getattr(
                Config,
                "APP_VERSION",
                "10.0.0",
            ),

        "nicho":
            "Roupas Fitness Femininas",

    })


# ============================================================
# EXPORTAÇÃO
# ============================================================

__all__ = [
    "routes",
]
