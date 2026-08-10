"""
Rotas principais do Robo Ofertas PRO.

Este arquivo concentra:
- status da aplicação;
- autenticação Mercado Livre;
- busca de produtos;
- ofertas;
- posts;
- imagens;
- WhatsApp;
- publicações;
- configurações;
- diagnóstico.

Compatível com o app.py e com o config.py atual.
"""

from __future__ import annotations

import logging

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

affiliate_service = (
    AffiliateService()
)

offer_service = (
    OfferService()
)

post_service = (
    PostService()
)

image_service = (
    ImageService()
)

whatsapp_service = (
    WhatsAppService()
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

    resposta.update(
        extra
    )

    return jsonify(
        resposta
    ), status


def numero(
    valor,
    padrao=0,
):

    try:

        return float(
            valor
        )

    except (
        ValueError,
        TypeError,
    ):

        return float(
            padrao
        )


def inteiro(
    valor,
    padrao=0,
):

    try:

        return int(
            valor
        )

    except (
        ValueError,
        TypeError,
    ):

        return int(
            padrao
        )


def mercado_livre_configurado():
    """
    Compatibilidade com diferentes versões do config.py.

    Primeiro tenta o método em inglês.
    Depois tenta o método em português.
    Por último verifica as variáveis diretamente.
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
        or getattr(
            Config,
            "ML_ACCESS_TOKEN",
            "",
        )
    )


# ============================================================
# PÁGINA INICIAL / STATUS
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
# STATUS DA AUTENTICAÇÃO
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
        or getattr(
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

            mensagem = (
                dados.get(
                    "mensagem"
                )
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

    ml_token = (
        token_mercado_livre()
    )

    try:

        estatisticas = (
            db.estatisticas()
        )

    except Exception:

        logger.exception(
            "Erro obtendo estatísticas do banco."
        )

        estatisticas = {}

    return jsonify({

        "sucesso":
            True,

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
# ROTA DE SAÚDE
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

    })


# ============================================================
# EXPORTAÇÃO
# ============================================================

__all__ = [
    "routes",
]
