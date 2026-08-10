"""
Rotas principais do Robo Ofertas PRO.

Foco atual:
- Roupas fitness femininas
- Busca no Mercado Livre
- Ofertas
- Posts
- Imagens
- WhatsApp
- Publicações
- Configurações
- Diagnóstico
"""

from __future__ import annotations

import logging
import re
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
# NICHO ÚNICO
# ============================================================

NICHO = "fitness_feminino"

TERMOS_FITNESS_FEMININO = [
    "legging fitness feminina",
    "calça legging feminina academia",
    "conjunto fitness feminino",
    "conjunto academia feminino",
    "top fitness feminino",
    "top academia feminino",
    "short fitness feminino",
    "short academia feminino",
    "bermuda fitness feminina",
    "bermuda academia feminina",
    "blusa fitness feminina",
    "camiseta fitness feminina",
    "regata fitness feminina",
    "cropped fitness feminino",
    "macacão fitness feminino",
    "macacao academia feminino",
    "roupa academia feminina",
    "roupa fitness feminina",
    "look academia feminino",
    "vestido fitness feminino",
]


# ============================================================
# PALAVRAS PROIBIDAS
# ============================================================

PALAVRAS_PROIBIDAS = [
    "masculino",
    "masculina",
    "masculinos",
    "masculinas",
    "homem",
    "homens",
    "menino",
    "infantil",
    "bebê",
    "bebe",
    "menino",
    "masc.",
    "masc",
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
    Compatibilidade com versões em português
    e inglês do config.py.
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
                "Erro verificando configuração do Mercado Livre."
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
                "Erro verificando configuração do Mercado Livre."
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


def texto_normalizado(
    texto,
):

    texto = str(
        texto or ""
    ).lower()

    texto = re.sub(
        r"[^\w\s]",
        " ",
        texto,
        flags=re.UNICODE,
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def produto_e_feminino(
    titulo,
):

    texto = texto_normalizado(
        titulo
    )

    for palavra in PALAVRAS_PROIBIDAS:

        if palavra in texto.split():

            return False

    palavras_femininas = [
        "feminina",
        "feminino",
        "mulher",
        "women",
        "woman",
        "lady",
        "academia",
        "fitness",
        "legging",
        "top",
        "cropped",
        "conjunto",
        "short",
    ]

    return any(
        palavra in texto
        for palavra in palavras_femininas
    )


def produto_e_fitness(
    titulo,
):

    texto = texto_normalizado(
        titulo
    )

    termos = [
        "fitness",
        "academia",
        "legging",
        "top",
        "conjunto",
        "short",
        "bermuda",
        "cropped",
        "regata",
        "treino",
        "gym",
        "esportiva",
        "esportivo",
        "macacao",
        "roupa fitness",
    ]

    return any(
        termo in texto
        for termo in termos
    )


def produto_valido(
    titulo,
):

    return (
        produto_e_feminino(titulo)
        and
        produto_e_fitness(titulo)
    )


def preparar_produto(
    item,
):

    titulo = (
        item.get(
            "title"
        )
        or
        ""
    )

    preco = item.get(
        "price",
        0,
    )

    link = (
        item.get(
            "permalink"
        )
        or
        item.get(
            "secure_thumbnail"
        )
        or
        ""
    )

    thumbnail = (
        item.get(
            "thumbnail"
        )
        or
        ""
    )

    if thumbnail.startswith(
        "http://"
    ):

        thumbnail = (
            thumbnail
            .replace(
                "http://",
                "https://",
                1,
            )
        )

    return {

        "id":
            item.get(
                "id"
            ),

        "titulo":
            titulo,

        "title":
            titulo,

        "preco":
            preco,

        "price":
            preco,

        "preco_formatado":
            (
                f"R$ {float(preco):,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            if preco
            else
            "R$ 0,00",

        "link":
            link,

        "permalink":
            link,

        "imagem":
            thumbnail,

        "thumbnail":
            thumbnail,

        "categoria":
            NICHO,

        "nicho":
            NICHO,

        "fitness_feminino":
            True,

        "seller_id":
            item.get(
                "seller",
                {}
            ).get(
                "id"
            )
            if isinstance(
                item.get(
                    "seller"
                ),
                dict,
            )
            else None,

        "condicao":
            item.get(
                "condition"
            ),

        "disponibilidade":
            item.get(
                "available_quantity"
            ),

        "cidade":
            (
                item.get(
                    "seller_address",
                    {}
                ).get(
                    "city"
                )
                if isinstance(
                    item.get(
                        "seller_address"
                    ),
                    dict,
                )
                else ""
            ),

    }


# ============================================================
# BUSCA MERCADO LIVRE
# ============================================================

def buscar_mercado_livre(
    consulta,
    limite=20,
):
    """
    Busca diretamente na API do Mercado Livre.

    A busca é sempre limitada ao nicho:
    ROUPAS FITNESS FEMININAS.
    """

    token = token_mercado_livre()

    if not token:

        raise RuntimeError(
            "Mercado Livre não está conectado."
        )

    api_base = getattr(
        Config,
        "ML_API_BASE",
        "https://api.mercadolibre.com",
    )

    site_id = getattr(
        Config,
        "ML_SITE_ID",
        "MLB",
    )

    limite = max(
        1,
        min(
            int(limite),
            50,
        ),
    )

    consulta = str(
        consulta or ""
    ).strip()

    if not consulta:

        consulta = (
            "legging fitness feminina"
        )

    # --------------------------------------------------------
    # Força o nicho feminino
    # --------------------------------------------------------

    consulta_final = (
        f"{consulta} feminina fitness academia"
    )

    url = (
        f"{api_base}/sites/"
        f"{site_id}/search"
    )

    headers = {

        "Accept":
            "application/json",

        "Authorization":
            f"Bearer {token}",

        "User-Agent":
            getattr(
                Config,
                "ML_USER_AGENT",
                "Robo-Ofertas-ML/10.0",
            ),

    }

    params = {

        "q":
            consulta_final,

        "limit":
            limite,

        "offset":
            0,

    }

    timeout = (

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

    )

    logger.info(
        "Buscando Mercado Livre: %s",
        consulta_final,
    )

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=timeout,
    )

    if not response.ok:

        try:
            payload = response.json()

        except ValueError:

            payload = {
                "resposta":
                    response.text
            }

        logger.error(
            "Mercado Livre retornou HTTP %s: %s",
            response.status_code,
            payload,
        )

        if response.status_code == 401:

            raise RuntimeError(
                "A conexão com o Mercado Livre expirou. "
                "Desconecte e conecte novamente."
            )

        if response.status_code == 403:

            raise RuntimeError(
                "O Mercado Livre recusou a consulta (403). "
                "Verifique as permissões da aplicação."
            )

        raise RuntimeError(
            f"Erro Mercado Livre HTTP "
            f"{response.status_code}."
        )

    data = response.json()

    resultados = data.get(
        "results",
        [],
    )

    produtos = []

    for item in resultados:

        if not isinstance(
            item,
            dict,
        ):
            continue

        titulo = item.get(
            "title",
            "",
        )

        if not produto_valido(
            titulo
        ):
            continue

        produto = preparar_produto(
            item
        )

        produtos.append(
            produto
        )

        if len(produtos) >= limite:
            break

    return produtos


# ============================================================
# API DE BUSCA
# ============================================================

@routes.route(
    "/api/buscar",
    methods=["GET", "POST"],
)
def buscar():

    """
    Endpoint utilizado pelo aplicativo.

    Exemplos:

    /api/buscar?produto=Leggings&limite=20

    /api/buscar?produto=Roupas%20fitness&limite=20

    Mesmo que o usuário informe outro termo,
    o sistema mantém o filtro de roupas fitness
    femininas.
    """

    if request.method == "POST":

        dados = request.get_json(
            silent=True
        )

        if not isinstance(
            dados,
            dict,
        ):
            dados = {}

        produto = (
            dados.get(
                "produto"
            )
            or
            dados.get(
                "busca"
            )
            or
            dados.get(
                "q"
            )
            or
            ""
        )

        limite = inteiro(
            dados.get(
                "limite",
                20,
            ),
            20,
        )

    else:

        produto = (
            request.args.get(
                "produto"
            )
            or
            request.args.get(
                "busca"
            )
            or
            request.args.get(
                "q"
            )
            or
            ""
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

    if not token_mercado_livre():

        return resposta_erro(
            "Mercado Livre não conectado.",
            401,
            mensagem=(
                "Conecte sua conta do Mercado Livre "
                "antes de pesquisar."
            ),
        )

    try:

        produtos = buscar_mercado_livre(
            consulta=produto,
            limite=limite,
        )

    except Exception as exc:

        logger.exception(
            "Erro na busca de produtos."
        )

        return resposta_erro(
            "Erro ao buscar produtos.",
            500,
            detalhe=str(exc),
            nicho=NICHO,
        )

    return jsonify({

        "sucesso":
            True,

        "nicho":
            NICHO,

        "categoria":
            "Roupas Fitness Femininas",

        "consulta":
            produto
            or
            "Roupas fitness femininas",

        "total":
            len(produtos),

        "produtos":
            produtos,

        "ofertas":
            produtos,

    })


# ============================================================
# BUSCA AUTOMÁTICA DO NICHO
# ============================================================

@routes.route(
    "/api/buscar/fitness-feminino",
    methods=["GET"],
)
def buscar_fitness_feminino():

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

    produtos = []

    consultas = TERMOS_FITNESS_FEMININO[
        :5
    ]

    try:

        for consulta in consultas:

            restantes = (
                limite
                - len(produtos)
            )

            if restantes <= 0:
                break

            encontrados = (
                buscar_mercado_livre(
                    consulta,
                    restantes,
                )
            )

            ids_existentes = {
                item.get(
                    "id"
                )
                for item in produtos
            }

            for item in encontrados:

                if item.get(
                    "id"
                ) in ids_existentes:

                    continue

                produtos.append(
                    item
                )

                if len(produtos) >= limite:
                    break

    except Exception as exc:

        logger.exception(
            "Erro na busca automática fitness feminina."
        )

        return resposta_erro(
            "Erro ao buscar roupas fitness femininas.",
            500,
            detalhe=str(exc),
        )

    return jsonify({

        "sucesso":
            True,

        "nicho":
            NICHO,

        "categoria":
            "Roupas Fitness Femininas",

        "total":
            len(produtos),

        "produtos":
            produtos,

        "ofertas":
            produtos,

    })


# ============================================================
# STATUS DA APLICAÇÃO
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
                "Robo Ofertas PRO",
            ),

        "versao":
            getattr(
                Config,
                "APP_VERSION",
                "10.0.0",
            ),

        "nicho":
            NICHO,

        "categoria":
            "Roupas Fitness Femininas",

        "mercado_livre":
            bool(
                token_mercado_livre()
            ),

        "mercado_livre_configurado":
            mercado_livre_configurado(),

        "whatsapp":
            whatsapp_service.configurado(),

        "database":
            estatisticas,

    })


# ============================================================
# STATUS AUTENTICAÇÃO
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
        or dados
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
        or dados
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
        or dados
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
                    "Robo Ofertas PRO",
                ),

            "versao":
                getattr(
                    Config,
                    "APP_VERSION",
                    "10.0.0",
                ),

            "nicho":
                NICHO,

            "categoria":
                "Roupas Fitness Femininas",

            "site_id":
                getattr(
                    Config,
                    "ML_SITE_ID",
                    "MLB",
                ),

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
# SALVAR CONFIGURAÇÕES
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

    ml_token = (
        token_mercado_livre()
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

        "nicho":
            NICHO,

        "categoria":
            "Roupas Fitness Femininas",

        "mercado_livre": {

            "configurado":
                mercado_livre_configurado(),

            "token_disponivel":
                bool(
                    ml_token
                ),

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

        "busca": {

            "endpoint":
                "/api/buscar",

            "endpoint_automatico":
                "/api/buscar/fitness-feminino",

            "categoria":
                "Roupas Fitness Femininas",

            "termos":
                TERMOS_FITNESS_FEMININO,

        },

        "whatsapp": {

            "configurado":
                whatsapp_service.configurado(),

        },

        "database":
            estatisticas,

    })


# ============================================================
# SAÚDE
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
                "Robo Ofertas PRO",
            ),

        "version":
            getattr(
                Config,
                "APP_VERSION",
                "10.0.0",
            ),

        "nicho":
            NICHO,

        "categoria":
            "Roupas Fitness Femininas",

    })


# ============================================================
# EXPORTAÇÃO
# ============================================================

__all__ = [
    "routes",
]
