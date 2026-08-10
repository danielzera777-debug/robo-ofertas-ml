"""
Rotas de autenticação e integração do Mercado Livre.

Este módulo é compatível com o app.py e com o Config atual.

Responsabilidades:
- iniciar OAuth do Mercado Livre;
- receber callback;
- trocar authorization code por access token;
- armazenar token na sessão;
- informar status da conexão;
- desconectar a sessão;
"""

from __future__ import annotations

import hashlib
import base64
import logging
import secrets
from urllib.parse import urlencode

import requests

from flask import (
    Blueprint,
    jsonify,
    redirect,
    request,
    session,
)

from config import get_config


LOGGER_NAME = "robo-ofertas.auth"

logger = logging.getLogger(
    LOGGER_NAME
)

routes = Blueprint(
    "auth",
    __name__,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

Config = get_config()


# ============================================================
# PKCE
# ============================================================

def generate_code_verifier() -> str:
    """
    Gera um code_verifier seguro para OAuth PKCE.
    """

    return secrets.token_urlsafe(
        64
    )[:128]


def generate_code_challenge(
    verifier: str,
) -> str:
    """
    Gera o code_challenge S256.
    """

    digest = hashlib.sha256(
        verifier.encode(
            "utf-8"
        )
    ).digest()

    return (
        base64.urlsafe_b64encode(
            digest
        )
        .decode(
            "utf-8"
        )
        .rstrip("=")
    )


# ============================================================
# STATUS
# ============================================================

@routes.route(
    "/api/auth/status",
    methods=["GET"],
)
def auth_status():
    """
    Retorna o estado atual da conexão.
    """

    access_token = session.get(
        "access_token"
    )

    return jsonify(
        sucesso=True,
        conectado=bool(
            access_token
        ),
        mercado_livre={
            "configurado": (
                Config.mercado_livre_configured()
            ),
            "conectado": bool(
                access_token
            ),
            "site_id": Config.ML_SITE_ID,
        },
    )


# ============================================================
# INICIAR OAUTH
# ============================================================

@routes.route(
    "/auth/mercadolivre",
    methods=["GET"],
)
@routes.route(
    "/auth/mercadolivre/connect",
    methods=["GET"],
)
def conectar_mercado_livre():
    """
    Inicia o fluxo OAuth do Mercado Livre.
    """

    if not Config.mercado_livre_configured():

        logger.error(
            "Mercado Livre não configurado."
        )

        return jsonify(
            sucesso=False,
            erro="mercado_livre_nao_configurado",
            mensagem=(
                "Configure ML_CLIENT_ID, "
                "ML_CLIENT_SECRET e "
                "ML_REDIRECT_URI no Render."
            ),
        ), 503

    state = secrets.token_urlsafe(
        32
    )

    verifier = generate_code_verifier()

    challenge = generate_code_challenge(
        verifier
    )

    session[
        "oauth_state"
    ] = state

    session[
        "oauth_code_verifier"
    ] = verifier

    session.modified = True

    params = {
        "response_type": "code",
        "client_id": Config.ML_CLIENT_ID,
        "redirect_uri": Config.ML_REDIRECT_URI,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    authorization_url = (
        Config.ML_AUTH_URL
        + "?"
        + urlencode(
            params
        )
    )

    return redirect(
        authorization_url
    )


# ============================================================
# CALLBACK
# ============================================================

@routes.route(
    "/auth/callback",
    methods=["GET"],
)
@routes.route(
    "/auth/mercadolivre/callback",
    methods=["GET"],
)
def mercado_livre_callback():
    """
    Recebe o retorno do Mercado Livre.
    """

    error = request.args.get(
        "error"
    )

    if error:

        description = request.args.get(
            "error_description",
            "",
        )

        session.pop(
            "oauth_state",
            None,
        )

        session.pop(
            "oauth_code_verifier",
            None,
        )

        return jsonify(
            sucesso=False,
            erro=error,
            mensagem=description
            or "Autorização cancelada.",
        ), 400

    code = request.args.get(
        "code"
    )

    state = request.args.get(
        "state"
    )

    if not code:

        return jsonify(
            sucesso=False,
            erro="authorization_code_ausente",
            mensagem=(
                "O Mercado Livre não enviou "
                "o código de autorização."
            ),
        ), 400

    saved_state = session.get(
        "oauth_state"
    )

    if (
        not saved_state
        or not state
        or not secrets.compare_digest(
            str(saved_state),
            str(state),
        )
    ):

        logger.warning(
            "State OAuth inválido."
        )

        return jsonify(
            sucesso=False,
            erro="state_invalido",
            mensagem=(
                "A validação de segurança "
                "da autorização falhou."
            ),
        ), 400

    verifier = session.get(
        "oauth_code_verifier"
    )

    if not verifier:

        return jsonify(
            sucesso=False,
            erro="code_verifier_ausente",
            mensagem=(
                "O code_verifier OAuth "
                "não foi encontrado."
            ),
        ), 400

    token_data = {
        "grant_type": "authorization_code",
        "client_id": Config.ML_CLIENT_ID,
        "client_secret": Config.ML_CLIENT_SECRET,
        "code": code,
        "redirect_uri": Config.ML_REDIRECT_URI,
        "code_verifier": verifier,
    }

    try:

        response = requests.post(
            Config.ML_OAUTH_TOKEN_URL,
            data=token_data,
            headers={
                "Accept": "application/json",
                "User-Agent": Config.ML_USER_AGENT,
            },
            timeout=(
                Config.ML_CONNECT_TIMEOUT,
                Config.ML_READ_TIMEOUT,
            ),
        )

    except requests.RequestException as exc:

        logger.exception(
            "Erro comunicando com Mercado Livre."
        )

        return jsonify(
            sucesso=False,
            erro="mercado_livre_indisponivel",
            mensagem=(
                "Não foi possível comunicar "
                "com o Mercado Livre."
            ),
            detalhe=str(exc),
        ), 502

    if not response.ok:

        try:

            payload = response.json()

        except ValueError:

            payload = {
                "resposta": response.text
            }

        logger.error(
            "Falha no OAuth Mercado Livre: %s",
            payload,
        )

        return jsonify(
            sucesso=False,
            erro="oauth_token_error",
            status=response.status_code,
            resposta=payload,
        ), 400

    try:

        token = response.json()

    except ValueError:

        return jsonify(
            sucesso=False,
            erro="resposta_token_invalida",
            mensagem=(
                "O Mercado Livre retornou "
                "uma resposta inválida."
            ),
        ), 502

    access_token = token.get(
        "access_token"
    )

    if not access_token:

        return jsonify(
            sucesso=False,
            erro="access_token_ausente",
            mensagem=(
                "O Mercado Livre não retornou "
                "um access_token."
            ),
        ), 502

    # --------------------------------------------------------
    # SESSÃO
    # --------------------------------------------------------

    session[
        "access_token"
    ] = access_token

    if token.get(
        "refresh_token"
    ):

        session[
            "refresh_token"
        ] = token.get(
            "refresh_token"
        )

    if token.get(
        "user_id"
    ) is not None:

        session[
            "user_id"
        ] = token.get(
            "user_id"
        )

    if token.get(
        "expires_in"
    ) is not None:

        session[
            "expires_in"
        ] = token.get(
            "expires_in"
        )

    session[
        "mercado_livre_connected"
    ] = True

    session.pop(
        "oauth_state",
        None,
    )

    session.pop(
        "oauth_code_verifier",
        None,
    )

    session.modified = True

    logger.info(
        "Mercado Livre conectado com sucesso."
    )

    return redirect(
        "/?mercado_livre=conectado"
    )


# ============================================================
# DESCONECTAR
# ============================================================

@routes.route(
    "/auth/mercadolivre/logout",
    methods=["GET"],
)
@routes.route(
    "/api/auth/logout",
    methods=["POST", "GET"],
)
def desconectar_mercado_livre():
    """
    Remove os dados OAuth da sessão.
    """

    session.pop(
        "access_token",
        None,
    )

    session.pop(
        "refresh_token",
        None,
    )

    session.pop(
        "user_id",
        None,
    )

    session.pop(
        "expires_in",
        None,
    )

    session.pop(
        "mercado_livre_connected",
        None,
    )

    session.pop(
        "oauth_state",
        None,
    )

    session.pop(
        "oauth_code_verifier",
        None,
    )

    session.modified = True

    return jsonify(
        sucesso=True,
        conectado=False,
        mensagem=(
            "Mercado Livre desconectado."
        ),
    )


# ============================================================
# REGISTRO DO BLUEPRINT
# ============================================================

def register_auth_routes(
    app,
):
    """
    Registra as rotas de autenticação na aplicação.

    O app.py procura exatamente esta função.
    """

    app.register_blueprint(
        routes
    )

    logger.info(
        "Rotas de autenticação carregadas."
    )

    return app


__all__ = [
    "routes",
    "register_auth_routes",
]
