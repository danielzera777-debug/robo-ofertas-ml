"""
Autenticação Mercado Livre
==========================

Rotas OAuth do Mercado Livre.

Fluxo:

1. /auth/mercadolivre
   -> envia o usuário para o Mercado Livre.

2. /callback
   -> recebe o código OAuth.

3. O código é trocado por access_token.

4. O token é salvo na sessão Flask.

5. Usuário retorna para a página inicial.
"""

from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

import requests
from flask import Blueprint, current_app, redirect, request, session


LOGGER = logging.getLogger("robo-ofertas")


auth_routes = Blueprint(
    "auth",
    __name__,
)


# ============================================================
# HELPERS
# ============================================================

def _config(name, default=""):
    """
    Obtém uma configuração da aplicação.
    """
    return current_app.config.get(
        name,
        default,
    )


def _oauth_configurado():
    """
    Verifica se as configurações necessárias
    para o OAuth existem.
    """

    return bool(
        _config("ML_CLIENT_ID")
        and _config("ML_CLIENT_SECRET")
        and _config("ML_REDIRECT_URI")
    )


def _token_url():
    return _config(
        "ML_OAUTH_TOKEN_URL",
        "https://api.mercadolibre.com/oauth/token",
    )


def _authorization_url():
    return _config(
        "ML_AUTH_URL",
        "https://auth.mercadolivre.com.br/authorization",
    )


def _redirect_uri():
    return _config(
        "ML_REDIRECT_URI",
        "",
    )


# ============================================================
# INÍCIO DO LOGIN
# ============================================================

@auth_routes.route(
    "/auth/mercadolivre",
    methods=["GET"],
)
def login_mercadolivre():

    LOGGER.info(
        "Iniciando autenticação Mercado Livre."
    )

    if not _oauth_configurado():

        LOGGER.error(
            "OAuth do Mercado Livre não está configurado."
        )

        return (
            "Mercado Livre não configurado. "
            "Verifique ML_CLIENT_ID, "
            "ML_CLIENT_SECRET e ML_REDIRECT_URI.",
            500,
        )

    # --------------------------------------------------------
    # Estado contra CSRF
    # --------------------------------------------------------

    state = secrets.token_urlsafe(32)

    session["ml_oauth_state"] = state

    # --------------------------------------------------------
    # URL de autorização
    # --------------------------------------------------------

    params = {
        "response_type": "code",
        "client_id": _config(
            "ML_CLIENT_ID"
        ),
        "redirect_uri": _redirect_uri(),
        "state": state,
    }

    url = (
        _authorization_url()
        + "?"
        + urlencode(params)
    )

    return redirect(url)


# ============================================================
# CALLBACK
# ============================================================

@auth_routes.route(
    "/callback",
    methods=["GET"],
)
def callback_mercadolivre():

    LOGGER.info(
        "Callback do Mercado Livre recebido."
    )

    # --------------------------------------------------------
    # Verifica erro retornado pelo Mercado Livre
    # --------------------------------------------------------

    error = request.args.get(
        "error"
    )

    if error:

        descricao = request.args.get(
            "error_description",
            "Autorização recusada.",
        )

        LOGGER.warning(
            "Mercado Livre retornou erro: %s - %s",
            error,
            descricao,
        )

        return redirect(
            "/?erro="
            + str(error)
        )

    # --------------------------------------------------------
    # Código OAuth
    # --------------------------------------------------------

    code = request.args.get(
        "code"
    )

    if not code:

        LOGGER.error(
            "Callback recebido sem código OAuth."
        )

        return (
            "Código de autorização não recebido.",
            400,
        )

    # --------------------------------------------------------
    # Validação do state
    # --------------------------------------------------------

    state_recebido = request.args.get(
        "state"
    )

    state_salvo = session.get(
        "ml_oauth_state"
    )

    if state_salvo:

        if not state_recebido:

            LOGGER.warning(
                "Callback sem state."
            )

            return (
                "Falha de segurança: state ausente.",
                400,
            )

        if state_recebido != state_salvo:

            LOGGER.warning(
                "State OAuth inválido."
            )

            session.pop(
                "ml_oauth_state",
                None,
            )

            return (
                "Falha de segurança: state inválido.",
                400,
            )

    # State não é mais necessário.
    session.pop(
        "ml_oauth_state",
        None,
    )

    # --------------------------------------------------------
    # Troca code por token
    # --------------------------------------------------------

    payload = {
        "grant_type": "authorization_code",
        "client_id": _config(
            "ML_CLIENT_ID"
        ),
        "client_secret": _config(
            "ML_CLIENT_SECRET"
        ),
        "code": code,
        "redirect_uri": _redirect_uri(),
    }

    try:

        response = requests.post(
            _token_url(),
            data=payload,
            headers={
                "Accept": "application/json",
                "User-Agent": _config(
                    "ML_USER_AGENT",
                    "Robo-Ofertas-PRO/10.0",
                ),
            },
            timeout=(
                _config(
                    "ML_CONNECT_TIMEOUT",
                    10,
                ),
                _config(
                    "ML_READ_TIMEOUT",
                    30,
                ),
            ),
        )

    except requests.RequestException:

        LOGGER.exception(
            "Erro de comunicação com Mercado Livre."
        )

        return (
            "Não foi possível conectar ao Mercado Livre.",
            502,
        )

    # --------------------------------------------------------
    # Verifica resposta
    # --------------------------------------------------------

    if response.status_code != 200:

        LOGGER.error(
            "Falha ao trocar código OAuth. "
            "HTTP %s: %s",
            response.status_code,
            response.text[:1000],
        )

        return (
            "Mercado Livre recusou a autenticação. "
            f"HTTP {response.status_code}.",
            400,
        )

    try:

        token_data = response.json()

    except ValueError:

        LOGGER.error(
            "Mercado Livre retornou resposta inválida."
        )

        return (
            "Resposta inválida do Mercado Livre.",
            502,
        )

    access_token = token_data.get(
        "access_token"
    )

    if not access_token:

        LOGGER.error(
            "Resposta OAuth não contém access_token."
        )

        return (
            "Mercado Livre não forneceu o token de acesso.",
            400,
        )

    # --------------------------------------------------------
    # Salva token
    # --------------------------------------------------------

    session["access_token"] = access_token

    refresh_token = token_data.get(
        "refresh_token"
    )

    if refresh_token:

        session["refresh_token"] = (
            refresh_token
        )

    expires_in = token_data.get(
        "expires_in"
    )

    if expires_in:

        session["token_expires_in"] = (
            expires_in
        )

    user_id = token_data.get(
        "user_id"
    )

    if user_id:

        session["ml_user_id"] = user_id

    session["mercado_livre_conectado"] = True

    session.permanent = True

    LOGGER.info(
        "Mercado Livre conectado com sucesso."
    )

    # --------------------------------------------------------
    # Volta para a aplicação
    # --------------------------------------------------------

    return redirect("/")


# ============================================================
# STATUS
# ============================================================

@auth_routes.route(
    "/api/auth/status",
    methods=["GET"],
)
def auth_status():

    conectado = bool(
        session.get(
            "access_token"
        )
    )

    return {
        "sucesso": True,
        "conectado": conectado,
        "mercado_livre": conectado,
    }


# ============================================================
# LOGOUT
# ============================================================

@auth_routes.route(
    "/logout",
    methods=["GET"],
)
def logout():

    session.pop(
        "access_token",
        None,
    )

    session.pop(
        "refresh_token",
        None,
    )

    session.pop(
        "token_expires_in",
        None,
    )

    session.pop(
        "ml_user_id",
        None,
    )

    session.pop(
        "mercado_livre_conectado",
        None,
    )

    session.pop(
        "ml_oauth_state",
        None,
    )

    LOGGER.info(
        "Mercado Livre desconectado."
    )

    return redirect("/")


# ============================================================
# REGISTRO
# ============================================================

def register_auth_routes(app):
    """
    Registra as rotas de autenticação na aplicação Flask.
    """

    app.register_blueprint(
        auth_routes
    )

    LOGGER.info(
        "Rotas de autenticação Mercado Livre registradas."
    )
