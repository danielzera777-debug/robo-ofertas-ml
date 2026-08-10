"""
Autenticação e integração OAuth com Mercado Livre.
"""

from __future__ import annotations

import base64
import hashlib
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


logger = logging.getLogger("robo-ofertas.auth")

Config = get_config()


# ============================================================
# BLUEPRINT
# ============================================================

auth_routes = Blueprint(
    "auth",
    __name__,
)


# ============================================================
# PKCE
# ============================================================

def generate_code_verifier():
    return secrets.token_urlsafe(64)[:128]


def generate_code_challenge(verifier):
    digest = hashlib.sha256(
        verifier.encode("utf-8")
    ).digest()

    return (
        base64.urlsafe_b64encode(digest)
        .decode("utf-8")
        .rstrip("=")
    )


# ============================================================
# CONFIGURAÇÃO
# ============================================================

def mercado_livre_configurado():
    """
    Compatibilidade com diferentes versões do Config.
    """

    try:
        metodo = getattr(
            Config,
            "mercado_livre_configurado",
            None
        )

        if callable(metodo):
            return bool(metodo())

    except Exception:
        logger.exception(
            "Erro verificando configuração do Mercado Livre."
        )

    return bool(
        getattr(Config, "ML_CLIENT_ID", None)
        and getattr(Config, "ML_CLIENT_SECRET", None)
        and getattr(Config, "ML_REDIRECT_URI", None)
    )


# ============================================================
# STATUS
# ============================================================

@auth_routes.route(
    "/api/auth/status",
    methods=["GET"]
)
def auth_status():

    access_token = session.get(
        "access_token"
    )

    configurado = mercado_livre_configurado()

    return jsonify({
        "sucesso": True,
        "conectado": bool(access_token),
        "mercado_livre": {
            "configurado": configurado,
            "conectado": bool(access_token),
            "site_id": getattr(
                Config,
                "ML_SITE_ID",
                "MLB"
            )
        }
    })


# ============================================================
# INICIAR AUTENTICAÇÃO
# ============================================================

@auth_routes.route(
    "/auth/mercadolivre",
    methods=["GET"]
)
@auth_routes.route(
    "/auth/mercadolivre/connect",
    methods=["GET"]
)
def conectar_mercado_livre():

    if not mercado_livre_configurado():

        logger.error(
            "Mercado Livre não configurado."
        )

        return jsonify({
            "sucesso": False,
            "erro": "mercado_livre_nao_configurado",
            "mensagem": (
                "Configure ML_CLIENT_ID, "
                "ML_CLIENT_SECRET e "
                "ML_REDIRECT_URI no Render."
            )
        }), 503

    state = secrets.token_urlsafe(32)

    verifier = generate_code_verifier()

    challenge = generate_code_challenge(
        verifier
    )

    session["oauth_state"] = state

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

    auth_url = getattr(
        Config,
        "ML_AUTH_URL",
        "https://auth.mercadolivre.com.br/authorization"
    )

    authorization_url = (
        auth_url
        + "?"
        + urlencode(params)
    )

    logger.info(
        "Iniciando autenticação Mercado Livre."
    )

    return redirect(
        authorization_url
    )


# ============================================================
# CALLBACK
# ============================================================

@auth_routes.route(
    "/callback",
    methods=["GET"]
)
@auth_routes.route(
    "/auth/callback",
    methods=["GET"]
)
@auth_routes.route(
    "/auth/mercadolivre/callback",
    methods=["GET"]
)
def mercado_livre_callback():

    error = request.args.get(
        "error"
    )

    if error:

        description = request.args.get(
            "error_description",
            ""
        )

        session.pop(
            "oauth_state",
            None
        )

        session.pop(
            "oauth_code_verifier",
            None
        )

        return jsonify({
            "sucesso": False,
            "erro": error,
            "mensagem": (
                description
                or "Autorização cancelada."
            )
        }), 400

    code = request.args.get(
        "code"
    )

    state = request.args.get(
        "state"
    )

    if not code:

        return jsonify({
            "sucesso": False,
            "erro": "authorization_code_ausente",
            "mensagem": (
                "O Mercado Livre não enviou "
                "o código de autorização."
            )
        }), 400

    saved_state = session.get(
        "oauth_state"
    )

    if (
        not saved_state
        or not state
        or not secrets.compare_digest(
            str(saved_state),
            str(state)
        )
    ):

        logger.warning(
            "State OAuth inválido."
        )

        return jsonify({
            "sucesso": False,
            "erro": "state_invalido",
            "mensagem": (
                "A validação de segurança "
                "da autorização falhou."
            )
        }), 400

    verifier = session.get(
        "oauth_code_verifier"
    )

    if not verifier:

        return jsonify({
            "sucesso": False,
            "erro": "code_verifier_ausente",
            "mensagem": (
                "O code_verifier OAuth "
                "não foi encontrado."
            )
        }), 400

    token_url = getattr(
        Config,
        "ML_OAUTH_TOKEN_URL",
        "https://api.mercadolibre.com/oauth/token"
    )

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
            token_url,
            data=token_data,
            headers={
                "Accept": "application/json",
                "User-Agent": getattr(
                    Config,
                    "ML_USER_AGENT",
                    "Robo-Ofertas-ML/10.0"
                )
            },
            timeout=(
                getattr(
                    Config,
                    "ML_CONNECT_TIMEOUT",
                    10
                ),
                getattr(
                    Config,
                    "ML_READ_TIMEOUT",
                    30
                )
            )
        )

    except requests.RequestException as exc:

        logger.exception(
            "Erro comunicando com Mercado Livre."
        )

        return jsonify({
            "sucesso": False,
            "erro": "mercado_livre_indisponivel",
            "mensagem": (
                "Não foi possível comunicar "
                "com o Mercado Livre."
            ),
            "detalhe": str(exc)
        }), 502

    try:

        payload = response.json()

    except ValueError:

        payload = {
            "resposta": response.text
        }

    if not response.ok:

        logger.error(
            "Erro OAuth Mercado Livre: %s",
            payload
        )

        return jsonify({
            "sucesso": False,
            "erro": "oauth_token_error",
            "status": response.status_code,
            "resposta": payload
        }), 400

    access_token = payload.get(
        "access_token"
    )

    if not access_token:

        return jsonify({
            "sucesso": False,
            "erro": "access_token_ausente",
            "mensagem": (
                "O Mercado Livre não retornou "
                "um access_token."
            )
        }), 502

    # ========================================================
    # SALVAR SESSÃO
    # ========================================================

    session["access_token"] = access_token

    refresh_token = payload.get(
        "refresh_token"
    )

    if refresh_token:

        session[
            "refresh_token"
        ] = refresh_token

    if payload.get("user_id") is not None:

        session[
            "user_id"
        ] = payload.get("user_id")

    if payload.get("expires_in") is not None:

        session[
            "expires_in"
        ] = payload.get("expires_in")

    session[
        "mercado_livre_connected"
    ] = True

    session.pop(
        "oauth_state",
        None
    )

    session.pop(
        "oauth_code_verifier",
        None
    )

    session.modified = True

    logger.info(
        "Mercado Livre conectado com sucesso."
    )

    return redirect(
        "/?mercado_livre=conectado"
    )


# ============================================================
# LOGOUT
# ============================================================

@auth_routes.route(
    "/auth/mercadolivre/logout",
    methods=["GET"]
)
@auth_routes.route(
    "/api/auth/logout",
    methods=["GET", "POST"]
)
def desconectar_mercado_livre():

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
        "mercado_livre_connected",
        None
    )

    session.pop(
        "oauth_state",
        None
    )

    session.pop(
        "oauth_code_verifier",
        None
    )

    session.modified = True

    return jsonify({
        "sucesso": True,
        "conectado": False,
        "mensagem": (
            "Mercado Livre desconectado."
        )
    })


# ============================================================
# REGISTRO
# ============================================================

def register_auth_routes(app):

    """
    Registra o Blueprint de autenticação somente uma vez.
    """

    if "auth" in app.blueprints:

        logger.warning(
            "Blueprint auth já registrado. "
            "Ignorando novo registro."
        )

        return app

    app.register_blueprint(
        auth_routes
    )

    logger.info(
        "Blueprint autenticação Mercado Livre registrado."
    )

    return app


__all__ = [
    "auth_routes",
    "register_auth_routes",
]
