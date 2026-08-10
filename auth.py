"""
Autenticação OAuth2 do Mercado Livre
Robo de Ofertas PRO

Este arquivo:
- cria apenas UM Blueprint de autenticação;
- usa nome exclusivo para evitar conflito com outro Blueprint;
- implementa OAuth2 Authorization Code;
- implementa PKCE;
- valida state;
- troca code por access_token;
- guarda access_token e refresh_token na sessão;
- disponibiliza /api/auth/status;
- disponibiliza /auth/mercadolivre;
- disponibiliza /callback;
- disponibiliza /logout.
"""

import base64
import hashlib
import logging
import secrets

import requests

from flask import (
    Blueprint,
    jsonify,
    redirect,
    session,
    url_for,
)


# ============================================================
# LOG
# ============================================================

logger = logging.getLogger("robo-ofertas")


# ============================================================
# BLUEPRINT
# ============================================================
#
# IMPORTANTE:
#
# O nome NÃO é "auth".
#
# Isso evita o erro:
#
# ValueError:
# The name 'auth' is already registered for a different
# blueprint.
#
# ============================================================

auth_routes = Blueprint(
    "mercadolivre_auth",
    __name__,
)


# ============================================================
# FUNÇÕES AUXILIARES DE CONFIGURAÇÃO
# ============================================================

def _config_value(config, *names, default=""):
    """
    Procura uma configuração por diferentes nomes.

    Isso deixa o auth.py compatível com versões diferentes
    do config.py.
    """

    for name in names:

        try:
            value = getattr(
                config,
                name,
                None
            )
        except Exception:
            value = None

        if value is not None:

            value = str(
                value
            ).strip()

            if value:
                return value

    return default


def _get_config():

    try:

        from config import config

        return config

    except Exception:

        try:

            from config import Config

            return Config

        except Exception:

            return None


# ============================================================
# CREDENCIAIS
# ============================================================

def _credentials():

    config = _get_config()

    if config is None:

        return {
            "client_id": "",
            "client_secret": "",
            "redirect_uri": "",
            "auth_url":
                "https://auth.mercadolivre.com.br/authorization",
            "token_url":
                "https://api.mercadolibre.com/oauth/token",
        }

    client_id = _config_value(
        config,
        "ML_CLIENT_ID",
        "CLIENT_ID",
    )

    client_secret = _config_value(
        config,
        "ML_CLIENT_SECRET",
        "CLIENT_SECRET",
    )

    redirect_uri = _config_value(
        config,
        "ML_REDIRECT_URI",
        "REDIRECT_URI",
    )

    auth_url = _config_value(
        config,
        "ML_AUTH_URL",
        "MERCADO_LIVRE_AUTH_URL",
        default=(
            "https://auth.mercadolivre.com.br/"
            "authorization"
        ),
    )

    token_url = _config_value(
        config,
        "ML_OAUTH_TOKEN_URL",
        "ML_TOKEN_URL",
        "MERCADO_LIVRE_TOKEN_URL",
        default=(
            "https://api.mercadolibre.com/"
            "oauth/token"
        ),
    )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "auth_url": auth_url,
        "token_url": token_url,
    }


# ============================================================
# PKCE
# ============================================================

def _gerar_code_verifier():

    """
    Gera um code_verifier seguro para PKCE.
    """

    return secrets.token_urlsafe(
        64
    )


def _gerar_code_challenge(
    code_verifier
):

    """
    Gera code_challenge utilizando S256.
    """

    digest = hashlib.sha256(
        code_verifier.encode(
            "utf-8"
        )
    ).digest()

    return base64.urlsafe_b64encode(
        digest
    ).rstrip(
        b"="
    ).decode(
        "ascii"
    )


# ============================================================
# TOKEN DISPONÍVEL
# ============================================================

def token_disponivel():

    return bool(
        session.get(
            "access_token"
        )
    )


# ============================================================
# STATUS
# ============================================================

@auth_routes.route(
    "/api/auth/status",
    methods=["GET"]
)
def auth_status():

    conectado = bool(
        session.get(
            "access_token"
        )
    )

    return jsonify({

        "sucesso": True,

        "conectado":
            conectado,

        "mercado_livre":
            conectado,

        "usuario_id":
            session.get(
                "user_id"
            ),

        "token_disponivel":
            conectado

    })


# ============================================================
# LOGIN MERCADO LIVRE
# ============================================================

@auth_routes.route(
    "/auth/mercadolivre",
    methods=["GET"]
)
def autenticar_mercado_livre():

    logger.info(
        "Iniciando autenticação Mercado Livre."
    )

    credenciais = _credentials()

    client_id = credenciais[
        "client_id"
    ]

    redirect_uri = credenciais[
        "redirect_uri"
    ]

    auth_url = credenciais[
        "auth_url"
    ]

    if not client_id:

        logger.error(
            "ML_CLIENT_ID não configurado."
        )

        return (
            "Mercado Livre não configurado: "
            "ML_CLIENT_ID ausente.",
            500
        )

    if not redirect_uri:

        logger.error(
            "ML_REDIRECT_URI não configurado."
        )

        return (
            "Mercado Livre não configurado: "
            "ML_REDIRECT_URI ausente.",
            500
        )

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    state = secrets.token_urlsafe(
        32
    )

    session[
        "ml_oauth_state"
    ] = state

    # --------------------------------------------------------
    # PKCE
    # --------------------------------------------------------

    code_verifier = (
        _gerar_code_verifier()
    )

    code_challenge = (
        _gerar_code_challenge(
            code_verifier
        )
    )

    session[
        "ml_code_verifier"
    ] = code_verifier

    session.modified = True

    # --------------------------------------------------------
    # URL DE AUTORIZAÇÃO
    # --------------------------------------------------------

    parametros = {

        "response_type":
            "code",

        "client_id":
            client_id,

        "redirect_uri":
            redirect_uri,

        "state":
            state,

        "code_challenge":
            code_challenge,

        "code_challenge_method":
            "S256",

    }

    from urllib.parse import urlencode

    url = (
        auth_url
        +
        "?"
        +
        urlencode(
            parametros
        )
    )

    return redirect(
        url
    )


# ============================================================
# CALLBACK
# ============================================================

@auth_routes.route(
    "/callback",
    methods=["GET"]
)
def callback():

    logger.info(
        "Callback Mercado Livre recebido."
    )

    # --------------------------------------------------------
    # ERRO DEVOLVIDO PELO MERCADO LIVRE
    # --------------------------------------------------------

    erro = (
        request_arg(
            "error"
        )
    )

    if erro:

        descricao = (
            request_arg(
                "error_description"
            )
        )

        logger.error(
            "Mercado Livre retornou erro: %s",
            erro
        )

        session.pop(
            "ml_oauth_state",
            None
        )

        session.pop(
            "ml_code_verifier",
            None
        )

        return (
            "<h1>Erro na conexão com o Mercado Livre</h1>"
            f"<p>{_html(erro)}</p>"
            f"<p>{_html(descricao)}</p>"
            '<p><a href="/">Voltar</a></p>',
            400
        )

    # --------------------------------------------------------
    # CODE
    # --------------------------------------------------------

    code = (
        request_arg(
            "code"
        )
    )

    if not code:

        return (
            "<h1>Erro</h1>"
            "<p>O Mercado Livre não enviou "
            "o código de autorização.</p>"
            '<p><a href="/">Voltar</a></p>',
            400
        )

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    state_recebido = (
        request_arg(
            "state"
        )
    )

    state_esperado = session.get(
        "ml_oauth_state"
    )

    if not state_recebido:

        logger.error(
            "Callback sem state."
        )

        return (
            "<h1>Erro de segurança</h1>"
            "<p>State ausente.</p>"
            '<p><a href="/">Voltar</a></p>',
            400
        )

    if not state_esperado:

        logger.error(
            "State esperado não encontrado na sessão."
        )

        return (
            "<h1>Erro de sessão</h1>"
            "<p>A sessão de autenticação expirou.</p>"
            '<p><a href="/">Voltar</a></p>',
            400
        )

    if not secrets.compare_digest(
        str(state_recebido),
        str(state_esperado)
    ):

        logger.error(
            "State OAuth inválido."
        )

        session.pop(
            "ml_oauth_state",
            None
        )

        session.pop(
            "ml_code_verifier",
            None
        )

        return (
            "<h1>Erro de segurança</h1>"
            "<p>O state OAuth não confere.</p>"
            '<p><a href="/">Voltar</a></p>',
            400
        )

    # --------------------------------------------------------
    # CONFIGURAÇÃO
    # --------------------------------------------------------

    credenciais = _credentials()

    client_id = credenciais[
        "client_id"
    ]

    client_secret = credenciais[
        "client_secret"
    ]

    redirect_uri = credenciais[
        "redirect_uri"
    ]

    token_url = credenciais[
        "token_url"
    ]

    code_verifier = session.get(
        "ml_code_verifier"
    )

    if not client_id:

        return (
            "<h1>Erro</h1>"
            "<p>ML_CLIENT_ID não configurado.</p>"
            '<p><a href="/">Voltar</a></p>',
            500
        )

    if not client_secret:

        return (
            "<h1>Erro</h1>"
            "<p>ML_CLIENT_SECRET não configurado.</p>"
            '<p><a href="/">Voltar</a></p>',
            500
        )

    if not redirect_uri:

        return (
            "<h1>Erro</h1>"
            "<p>ML_REDIRECT_URI não configurado.</p>"
            '<p><a href="/">Voltar</a></p>',
            500
        )

    # --------------------------------------------------------
    # TROCA CODE POR TOKEN
    # --------------------------------------------------------

    payload = {

        "grant_type":
            "authorization_code",

        "client_id":
            client_id,

        "client_secret":
            client_secret,

        "code":
            code,

        "redirect_uri":
            redirect_uri,

    }

    # Se PKCE foi utilizado no login,
    # envia o mesmo verifier.

    if code_verifier:

        payload[
            "code_verifier"
        ] = code_verifier

    headers = {

        "Accept":
            "application/json",

        "Content-Type":
            "application/x-www-form-urlencoded",

        "User-Agent":
            "Robo-Ofertas-PRO/10.0",

    }

    try:

        resposta = requests.post(

            token_url,

            data=payload,

            headers=headers,

            timeout=30,

        )

    except requests.RequestException as exc:

        logger.exception(
            "Erro de conexão com Mercado Livre: %s",
            exc
        )

        return (
            "<h1>Erro de conexão</h1>"
            "<p>Não foi possível conectar "
            "ao Mercado Livre.</p>"
            '<p><a href="/">Voltar</a></p>',
            502
        )

    # --------------------------------------------------------
    # PROCESSAMENTO DA RESPOSTA
    # --------------------------------------------------------

    try:

        dados = resposta.json()

    except ValueError:

        dados = {}

    if resposta.status_code >= 400:

        logger.error(
            "Mercado Livre recusou OAuth. "
            "HTTP %s.",
            resposta.status_code
        )

        mensagem = (
            dados.get(
                "message"
            )
            or
            dados.get(
                "error_description"
            )
            or
            dados.get(
                "error"
            )
            or
            "Erro desconhecido."
        )

        return (
            "<h1>Falha na conexão</h1>"
            f"<p>{_html(mensagem)}</p>"
            "<p>Verifique o Client ID, "
            "Client Secret e Redirect URI.</p>"
            '<p><a href="/">Voltar</a></p>',
            400
        )

    access_token = dados.get(
        "access_token"
    )

    refresh_token = dados.get(
        "refresh_token"
    )

    if not access_token:

        logger.error(
            "Resposta do Mercado Livre "
            "não contém access_token."
        )

        return (
            "<h1>Erro</h1>"
            "<p>O Mercado Livre não retornou "
            "um access token.</p>"
            '<p><a href="/">Voltar</a></p>',
            502
        )

    # --------------------------------------------------------
    # SALVA NA SESSÃO
    # --------------------------------------------------------

    session[
        "access_token"
    ] = access_token

    if refresh_token:

        session[
            "refresh_token"
        ] = refresh_token

    if dados.get(
        "user_id"
    ) is not None:

        session[
            "user_id"
        ] = dados.get(
            "user_id"
        )

    if dados.get(
        "expires_in"
    ) is not None:

        session[
            "expires_in"
        ] = dados.get(
            "expires_in"
        )

    if dados.get(
        "scope"
    ):

        session[
            "scope"
        ] = dados.get(
            "scope"
        )

    # --------------------------------------------------------
    # LIMPA DADOS TEMPORÁRIOS
    # --------------------------------------------------------

    session.pop(
        "ml_oauth_state",
        None
    )

    session.pop(
        "ml_code_verifier",
        None
    )

    session.modified = True

    logger.info(
        "Mercado Livre conectado com sucesso."
    )

    # --------------------------------------------------------
    # VOLTA PARA A APLICAÇÃO
    # --------------------------------------------------------

    return redirect(
        url_for(
            "index"
        )
    )


# ============================================================
# LOGOUT
# ============================================================

@auth_routes.route(
    "/logout",
    methods=["GET"]
)
def logout():

    logger.info(
        "Desconectando Mercado Livre."
    )

    session.pop(
        "access_token",
        None
    )

    session.pop(
        "refresh_token",
        None
    )

    session.pop(
        "user_id",
        None
    )

    session.pop(
        "expires_in",
        None
    )

    session.pop(
        "scope",
        None
    )

    session.pop(
        "ml_oauth_state",
        None
    )

    session.pop(
        "ml_code_verifier",
        None
    )

    session.modified = True

    return redirect(
        url_for(
            "index"
        )
    )


# ============================================================
# HELPERS
# ============================================================

def request_arg(
    nome,
    default=""
):

    """
    Obtém parâmetro da URL sem depender diretamente
    do objeto request em outras funções.
    """

    try:

        from flask import request

        return request.args.get(
            nome,
            default,
            type=str
        )

    except Exception:

        return default


def _html(valor):

    """
    Escapa texto que será colocado no HTML.
    """

    import html

    return html.escape(
        str(
            valor
            or ""
        )
    )


# ============================================================
# REGISTRO
# ============================================================

def register_auth_routes(
    app,
    *args,
    **kwargs
):

    """
    Registra as rotas de autenticação.

    IMPORTANTE:
    O registro é protegido contra duplicidade.

    Se outro ponto do app já registrou o Blueprint,
    este método não registra novamente.
    """

    # --------------------------------------------------------
    # VERIFICA SE JÁ FOI REGISTRADO
    # --------------------------------------------------------

    if (
        "mercadolivre_auth"
        in app.blueprints
    ):

        logger.info(
            "Blueprint de autenticação "
            "Mercado Livre já registrado."
        )

        return app

    # --------------------------------------------------------
    # REGISTRA
    # --------------------------------------------------------

    app.register_blueprint(
        auth_routes
    )

    logger.info(
        "Blueprint autenticação Mercado Livre registrado."
    )

    return app
