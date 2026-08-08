from flask import (
    Blueprint,
    jsonify,
    request,
    session
)

from config import config
from database import db
from services.affiliate_service import (
    AffiliateService
)
from services.offer_service import (
    OfferService
)
from services.post_service import (
    PostService
)
from services.image_service import (
    ImageService
)
from services.whatsapp_service import (
    WhatsAppService
)


routes = Blueprint(
    "routes",
    __name__
)


affiliate_service = (
    AffiliateService()
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


def resposta_erro(
    mensagem,
    status=400
):

    return jsonify({
        "sucesso": False,
        "erro": mensagem
    }), status


def numero(
    valor,
    padrao=0
):

    try:

        return float(valor)

    except (
        ValueError,
        TypeError
    ):

        return float(padrao)


# ============================================================
# STATUS
# ============================================================

@routes.route(
    "/api/status",
    methods=["GET"]
)
def status():

    return jsonify({

        "sucesso": True,

        "app":
            config.APP_NAME,

        "mercado_livre":
            bool(
                session.get(
                    "access_token"
                )
                or config.ML_ACCESS_TOKEN
            ),

        "whatsapp":
            whatsapp_service.configurado(),

        "agendamento":
            config.INTERVALO_OFERTAS,

        "database":
            db.estatisticas()

    })


# ============================================================
# OFERTAS SALVAS
# ============================================================

@routes.route(
    "/api/ofertas",
    methods=["GET"]
)
def ofertas():

    try:

        limite = int(
            request.args.get(
                "limite",
                50
            )
        )

    except (
        ValueError,
        TypeError
    ):

        limite = 50

    status_filtro = request.args.get(
        "status"
    )

    dados = db.buscar_ofertas(
        limite=limite,
        status=status_filtro
    )

    return jsonify({
        "sucesso": True,
        "total": len(dados),
        "ofertas": dados
    })


# ============================================================
# SALVAR OFERTA
# ============================================================

@routes.route(
    "/api/ofertas",
    methods=["POST"]
)
def salvar_oferta():

    dados = request.get_json(
        silent=True
    )

    if not isinstance(
        dados,
        dict
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

    oferta_id = db.salvar_oferta(
        oferta
    )

    if not oferta_id:

        return resposta_erro(
            "Não foi possível salvar a oferta."
        )

    return jsonify({
        "sucesso": True,
        "id": oferta_id
    })


# ============================================================
# GERAR POST
# ============================================================

@routes.route(
    "/api/post",
    methods=["POST"]
)
def gerar_post():

    dados = request.get_json(
        silent=True
    )

    if not isinstance(
        dados,
        dict
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

    post = post_service.criar_post(
        oferta
    )

    if not post:

        return resposta_erro(
            "Não foi possível gerar o post."
        )

    return jsonify({
        "sucesso": True,
        "post": post
    })


# ============================================================
# GERAR IMAGEM
# ============================================================

@routes.route(
    "/api/imagem",
    methods=["POST"]
)
def gerar_imagem():

    dados = request.get_json(
        silent=True
    )

    if not isinstance(
        dados,
        dict
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

    caminho = image_service.criar_imagem(
        oferta
    )

    if not caminho:

        return resposta_erro(
            "Não foi possível gerar a imagem."
        )

    return jsonify({
        "sucesso": True,
        "arquivo": caminho
    })


# ============================================================
# PREPARAR OFERTAS
# ============================================================

@routes.route(
    "/api/ofertas/preparar",
    methods=["POST"]
)
def preparar_ofertas():

    dados = request.get_json(
        silent=True
    )

    if not isinstance(
        dados,
        dict
    ):

        return resposta_erro(
            "Dados inválidos."
        )

    produtos = dados.get(
        "produtos",
        []
    )

    margem = numero(
        dados.get(
            "margem",
            config.MARGEM_PADRAO
        ),
        config.MARGEM_PADRAO
    )

    lucro_minimo = numero(
        dados.get(
            "lucro_minimo",
            config.LUCRO_MINIMO_PADRAO
        ),
        config.LUCRO_MINIMO_PADRAO
    )

    desconto_minimo = numero(
        dados.get(
            "desconto_minimo",
            config.DESCONTO_MINIMO_PADRAO
        ),
        config.DESCONTO_MINIMO_PADRAO
    )

    limite = int(
        dados.get(
            "limite",
            config.LIMITE_OFERTAS
        )
    )

    ofertas = (
        affiliate_service.melhores_ofertas(
            produtos=produtos,
            limite=limite,
            margem=margem,
            lucro_minimo=lucro_minimo,
            desconto_minimo=desconto_minimo
        )
    )

    return jsonify({
        "sucesso": True,
        "total": len(ofertas),
        "ofertas": ofertas
    })


# ============================================================
# WHATSAPP
# ============================================================

@routes.route(
    "/api/whatsapp/status",
    methods=["GET"]
)
def whatsapp_status():

    resultado = (
        whatsapp_service.testar_conexao()
    )

    return jsonify(
        resultado
    )


@routes.route(
    "/api/whatsapp/enviar",
    methods=["POST"]
)
def whatsapp_enviar():

    dados = request.get_json(
        silent=True
    )

    if not isinstance(
        dados,
        dict
    ):

        return resposta_erro(
            "Dados inválidos."
        )

    numero_destino = (
        dados.get(
            "numero"
        )
        or dados.get(
            "destinatario"
        )
    )

    oferta = dados.get(
        "oferta"
    )

    if oferta:

        resultado = (
            whatsapp_service.enviar_oferta(
                numero=numero_destino,
                oferta=oferta
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
            whatsapp_service.enviar_texto(
                numero=numero_destino,
                mensagem=mensagem
            )
        )

    return jsonify(
        resultado
    )


# ============================================================
# PUBLICAÇÕES
# ============================================================

@routes.route(
    "/api/publicacoes",
    methods=["GET"]
)
def publicacoes():

    try:

        limite = int(
            request.args.get(
                "limite",
                100
            )
        )

    except (
        ValueError,
        TypeError
    ):

        limite = 100

    dados = db.buscar_publicacoes(
        limite=limite
    )

    return jsonify({
        "sucesso": True,
        "total": len(dados),
        "publicacoes": dados
    })


# ============================================================
# CONFIGURAÇÕES
# ============================================================

@routes.route(
    "/api/config",
    methods=["GET"]
)
def obter_config():

    return jsonify({

        "sucesso": True,

        "config": {

            "app_name":
                config.APP_NAME,

            "site_id":
                config.ML_SITE_ID,

            "margem_padrao":
                config.MARGEM_PADRAO,

            "lucro_minimo":
                config.LUCRO_MINIMO_PADRAO,

            "desconto_minimo":
                config.DESCONTO_MINIMO_PADRAO,

            "limite_ofertas":
                config.LIMITE_OFERTAS,

            "intervalo":
                config.INTERVALO_OFERTAS

        }

    })


@routes.route(
    "/api/config",
    methods=["POST"]
)
def salvar_config():

    dados = request.get_json(
        silent=True
    )

    if not isinstance(
        dados,
        dict
    ):

        return resposta_erro(
            "Dados inválidos."
        )

    permitidos = {

        "margem_padrao",
        "lucro_minimo",
        "desconto_minimo",
        "limite_ofertas",
        "intervalo"

    }

    alterados = []

    for chave in permitidos:

        if chave not in dados:
            continue

        valor = dados[
            chave
        ]

        db.salvar_configuracao(
            chave,
            valor
        )

        alterados.append(
            chave
        )

    return jsonify({

        "sucesso": True,

        "alterados":
            alterados

    })


# ============================================================
# DIAGNÓSTICO
# ============================================================

@routes.route(
    "/api/diagnostico",
    methods=["GET"]
)
def diagnostico():

    ml_token = (
        session.get(
            "access_token"
        )
        or config.ML_ACCESS_TOKEN
    )

    return jsonify({

        "sucesso": True,

        "mercado_livre": {

            "configurado":
                config.mercado_livre_configurado(),

            "token_disponivel":
                bool(ml_token),

            "site_id":
                config.ML_SITE_ID,

            "api":
                config.ML_API_BASE

        },

        "whatsapp": {

            "configurado":
                whatsapp_service.configurado()

        },

        "database":
            db.estatisticas()

    })
