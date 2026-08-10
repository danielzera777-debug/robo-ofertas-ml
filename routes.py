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

Compatível com app.py, config.py e auth.py atuais.
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

from services.affiliate_service import AffiliateService
from services.offer_service import OfferService
from services.post_service import PostService
from services.image_service import ImageService
from services.whatsapp_service import WhatsAppService


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

NICHO = "fitness_feminino"

TERMOS_FITNESS_FEMININO = [
    "legging fitness feminina",
    "legging academia feminina",
    "calça legging feminina fitness",
    "top fitness feminino",
    "top academia feminino",
    "conjunto fitness feminino",
    "conjunto academia feminino",
    "short fitness feminino",
    "short academia feminino",
    "shorts fitness feminino",
    "bermuda fitness feminina",
    "camiseta fitness feminina",
    "camiseta academia feminina",
    "regata fitness feminina",
    "regata academia feminina",
    "blusa fitness feminina",
    "blusa academia feminina",
    "roupa fitness feminina",
    "roupa academia feminina",
]


# Palavras que indicam que o produto NÃO é o foco desejado.
PALAVRAS_EXCLUIDAS = [
    "masculino",
    "masculina",
    "homem",
    "homens",
    "infantil",
    "infantil feminino",
    "menino",
    "menina",
    "bebê",
    "bebe",
    "baby",
    "sapato",
    "tênis",
    "tenis",
    "sandália",
    "sandalia",
    "suplemento",
    "whey",
    "creatina",
    "vitamina",
    "halter",
    "halteres",
    "anilha",
    "barra",
    "academia aparelho",
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
    Compatibilidade com as duas nomenclaturas possíveis
    existentes no config.py.
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
    """
    Obtém o token da sessão.
    """

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


def texto_normalizado(valor):
    """
    Normaliza texto para comparação.
    """

    if not valor:
        return ""

    texto = str(valor).lower()

    substituicoes = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "ä": "a",
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "í": "i",
        "ì": "i",
        "î": "i",
        "ï": "i",
        "ó": "o",
        "ò": "o",
        "õ": "o",
        "ô": "o",
        "ö": "o",
        "ú": "u",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ç": "c",
    }

    for antigo, novo in substituicoes.items():
        texto = texto.replace(
            antigo,
            novo,
        )

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def produto_fitness_feminino(titulo):
    """
    Verifica se o título pertence ao nicho de roupas fitness
    femininas.

    A filtragem é propositalmente conservadora para evitar
    que produtos masculinos, infantis ou suplementos apareçam.
    """

    texto = texto_normalizado(
        titulo
    )

    if not texto:
        return False

    # Rejeita produtos claramente fora do nicho.
    for palavra in PALAVRAS_EXCLUIDAS:

        palavra_normalizada = texto_normalizado(
            palavra
        )

        if palavra_normalizada in texto:
            return False

    palavras_roupa = [
        "legging",
        "top fitness",
        "top academia",
        "conjunto fitness",
        "conjunto academia",
        "short fitness",
        "short academia",
        "shorts fitness",
        "bermuda fitness",
        "camiseta fitness",
        "camiseta academia",
        "regata fitness",
        "regata academia",
        "blusa fitness",
        "blusa academia",
        "roupa fitness",
        "roupa academia",
        "calca legging",
        "calca fitness",
    ]

    encontrou_roupa = any(
        termo in texto
        for termo in palavras_roupa
    )

    if not encontrou_roupa:
        return False

    # Termos femininos.
    termos_femininos = [
        "feminina",
        "feminino",
        "mulher",
        "mulheres",
        "lady",
        "woman",
    ]

    # Alguns produtos de fitness são claramente femininos
    # mesmo sem trazer "feminina" no título, principalmente
    # leggings e tops.
    produto_obviamente_feminino = (
        "legging" in texto
        or "top fitness" in texto
        or "top academia" in texto
    )

    feminino = any(
        termo in texto
        for termo in termos_femininos
    )

    return bool(
        feminino
        or produto_obviamente_feminino
    )


def montar_url_produto(item):
    """
    Obtém o link do produto retornado pelo Mercado Livre.
    """

    link = (
        item.get("permalink")
        or item.get("url")
        or ""
    )

    if link:
        return link

    item_id = (
        item.get("id")
        or ""
    )

    if item_id:
        return (
            "https://produto.mercadolivre.com.br/"
            + str(item_id)
        )

    return ""


def formatar_produto_ml(item):
    """
    Converte o resultado do Mercado Livre para um formato
    simples usado pelo frontend.
    """

    titulo = (
        item.get("title")
        or ""
    )

    preco = item.get(
        "price",
        0,
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

    preco_original = item.get(
        "original_price"
    )

    try:
        if preco_original is not None:
            preco_original = float(
                preco_original
            )

    except (
        ValueError,
        TypeError,
    ):
        preco_original = None

    desconto = 0

    if (
        preco_original
        and preco_original > preco
    ):
        desconto = round(
            (
                1
                -
                (
                    preco
                    /
                    preco_original
                )
            )
            * 100
        )

    return {
        "id": item.get("id"),
        "titulo": titulo,
        "title": titulo,
        "preco": preco,
        "price": preco,
        "preco_original": preco_original,
        "desconto": desconto,
        "link": montar_url_produto(item),
        "permalink": item.get(
            "permalink"
        ),
        "thumbnail": item.get(
            "thumbnail"
        ),
        "imagem": item.get(
            "thumbnail"
        ),
        "categoria": NICHO,
        "nicho": "Roupas Fitness Femininas",
        "vendedor": item.get(
            "seller",
            {},
        ),
        "condicao": item.get(
            "condition"
        ),
        "disponibilidade": item.get(
            "available_quantity"
        ),
    }


def buscar_ml(
    termo,
    limite=20,
):
    """
    Busca diretamente na API do Mercado Livre.

    Essa função existe para que /api/buscar funcione
    independentemente das versões anteriores dos services.
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

    url = (
        api_base.rstrip("/")
        + "/sites/"
        + site_id
        + "/search"
    )

    params = {
        "q": termo,
        "limit": max(
            1,
            min(
                int(limite),
                50,
            ),
        ),
    }

    headers = {
        "Accept": "application/json",
        "Authorization": (
            "Bearer "
            + str(token)
        ),
        "User-Agent": getattr(
            Config,
            "ML_USER_AGENT",
            "Robo-Ofertas-ML/10.0.0",
        ),
    }

    connect_timeout = getattr(
        Config,
        "ML_CONNECT_TIMEOUT",
        10,
    )

    read_timeout = getattr(
        Config,
        "ML_READ_TIMEOUT",
        30,
    )

    logger.info(
        "Buscando Mercado Livre: %s",
        termo,
    )

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=(
            connect_timeout,
            read_timeout,
        ),
    )

    if not response.ok:

        try:
            payload = response.json()

        except ValueError:
            payload = response.text

        logger.error(
            "Mercado Livre retornou HTTP %s: %s",
            response.status_code,
            payload,
        )

        raise RuntimeError(
            "Mercado Livre retornou HTTP "
            + str(response.status_code)
            + "."
        )

    try:
        return response.json()

    except ValueError:
        raise RuntimeError(
            "Resposta inválida do Mercado Livre."
        )


# ============================================================
# BUSCA PRINCIPAL
# ============================================================

@routes.route(
    "/api/buscar",
    methods=["GET", "POST"],
)
def buscar():
    """
    Busca SOMENTE roupas fitness femininas.

    Exemplos:

    /api/buscar?produto=Leggings&limite=20

    /api/buscar?produto=top&limite=20

    /api/buscar?produto=conjunto&limite=20

    Mesmo que o frontend envie outro termo, o resultado
    passa pelo filtro do nicho fitness feminino.
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

        termo = (
            dados.get("produto")
            or dados.get("q")
            or dados.get("busca")
            or ""
        )

        limite = inteiro(
            dados.get(
                "limite",
                20,
            ),
            20,
        )

    else:

        termo = (
            request.args.get(
                "produto"
            )
            or
            request.args.get(
                "q"
            )
            or
            request.args.get(
                "busca"
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

    termo = str(
        termo
    ).strip()

    # Se o frontend não mandar termo, usamos uma busca
    # específica do nicho.
    if not termo:

        termo = (
            "legging fitness feminina"
        )

    token = token_mercado_livre()

    if not token:

        return resposta_erro(
            "Mercado Livre não está conectado.",
            401,
            conectado=False,
        )

    resultados = []
    consultas_realizadas = []

    # --------------------------------------------------------
    # Primeiro tenta exatamente o termo enviado.
    # Depois utiliza termos específicos do nicho se necessário.
    # --------------------------------------------------------

    consultas = [
        termo
    ]

    for termo_nicho in TERMOS_FITNESS_FEMININO:

        if len(consultas) >= 5:
            break

        if texto_normalizado(
            termo_nicho
        ) not in [
            texto_normalizado(x)
            for x in consultas
        ]:

            consultas.append(
                termo_nicho
            )

    try:

        for consulta in consultas:

            consultas_realizadas.append(
                consulta
            )

            try:

                payload = buscar_ml(
                    consulta,
                    limite=50,
                )

            except Exception as exc:

                logger.warning(
                    "Busca '%s' falhou: %s",
                    consulta,
                    exc,
                )

                continue

            itens = payload.get(
                "results",
                [],
            )

            for item in itens:

                titulo = (
                    item.get("title")
                    or ""
                )

                if not produto_fitness_feminino(
                    titulo
                ):
                    continue

                produto = formatar_produto_ml(
                    item
                )

                produto_id = produto.get(
                    "id"
                )

                if any(
                    x.get("id")
                    == produto_id
                    for x in resultados
                ):
                    continue

                resultados.append(
                    produto
                )

                if len(resultados) >= limite:
                    break

            if len(resultados) >= limite:
                break

    except Exception as exc:

        logger.exception(
            "Erro geral na busca."
        )

        return resposta_erro(
            "Erro ao buscar produtos.",
            500,
            detalhe=str(exc),
        )

    resultados = resultados[
        :limite
    ]

    logger.info(
        "Busca fitness feminina: %s produtos encontrados.",
        len(resultados),
    )

    return jsonify({

        "sucesso":
            True,

        "total":
            len(resultados),

        "produto":
            termo,

        "nicho":
            "Roupas Fitness Femininas",

        "categoria":
            "fitness_feminino",

        "consultas":
            consultas_realizadas,

        "ofertas":
            resultados,

        "produtos":
            resultados,

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
                "Robo Ofertas PRO",
            ),

        "versao":
            getattr(
                Config,
                "APP_VERSION",
                "10.0.0",
            ),

        "nicho":
            "Roupas Fitness Femininas",

        "mercado_livre":
            bool(
                token_mercado_livre()
            ),

        "mercado_livre_configurado":
            mercado_livre_configurado(),

        "whatsapp":
            whatsapp_service.configurado(),

        "agendamento":
            getattr(
                Config,
                "INTERVALO_OFERTAS",
                0,
            ),

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

    token = (
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

    status_filtro = request.args.get(
        "status"
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
        dados.get("oferta")
        or dados
    )

    try:

        oferta_id = db.salvar_oferta(
            oferta
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
        dados.get("oferta")
        or dados
    )

    try:

        post = post_service.criar_post(
            oferta
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
        dados.get("oferta")
        or dados
    )

    try:

        caminho = image_service.criar_imagem(
            oferta
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
        dados.get("numero")
        or
        dados.get("destinatario")
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
                    "Robo Ofertas PRO",
                ),

            "nicho":
                "fitness_feminino",

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

        valor = dados[
            chave
        ]

        try:

            db.salvar_configuracao(
                chave,
                valor,
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

    ml_token = token_mercado_livre()

    try:

        estatisticas = db.estatisticas()

    except Exception:

        logger.exception(
            "Erro obtendo estatísticas do banco."
        )

        estatisticas = {}

    return jsonify({

        "sucesso":
            True,

        "nicho":
            "Roupas Fitness Femininas",

        "mercado_livre": {

            "configurado":
                mercado_livre_configurado(),

            "token_disponivel":
                bool(ml_token),

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
                "Robo Ofertas PRO",
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
