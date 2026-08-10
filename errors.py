"""
Tratamento centralizado de erros do Robo de Ofertas ML.
"""

import logging

from flask import (
    jsonify,
    request,
)


logger = logging.getLogger(
    "robo-ofertas"
)


# ============================================================
# EXCEÇÕES PERSONALIZADAS
# ============================================================

class RoboOfertasError(Exception):
    """
    Erro base da aplicação.
    """

    status_code = 400

    error_code = (
        "robo_ofertas_error"
    )

    def __init__(
        self,
        message="Ocorreu um erro.",
        status_code=None,
        error_code=None,
    ):

        super().__init__(
            message
        )

        self.message = message

        if status_code is not None:

            self.status_code = (
                status_code
            )

        if error_code is not None:

            self.error_code = (
                error_code
            )


class ValidationError(
    RoboOfertasError
):

    status_code = 400

    error_code = (
        "validation_error"
    )


class AuthenticationError(
    RoboOfertasError
):

    status_code = 401

    error_code = (
        "authentication_error"
    )


class AuthorizationError(
    RoboOfertasError
):

    status_code = 403

    error_code = (
        "authorization_error"
    )


class NotFoundError(
    RoboOfertasError
):

    status_code = 404

    error_code = (
        "not_found"
    )


class MercadoLivreError(
    RoboOfertasError
):

    status_code = 502

    error_code = (
        "mercado_livre_error"
    )


class WhatsAppError(
    RoboOfertasError
):

    status_code = 502

    error_code = (
        "whatsapp_error"
    )


# ============================================================
# RESPOSTA DE ERRO
# ============================================================

def error_response(
    message,
    status_code=400,
    error_code="error",
    details=None,
):

    response = {

        "ok": False,

        "sucesso": False,

        "erro": error_code,

        "mensagem": str(
            message
        ),

    }

    if details is not None:

        response[
            "detalhes"
        ] = details

    return jsonify(
        response
    ), status_code


# ============================================================
# REGISTRO DOS HANDLERS
# ============================================================

def register_error_handlers(
    app,
):

    @app.errorhandler(
        RoboOfertasError
    )
    def handle_robo_error(
        error
    ):

        logger.warning(
            "%s: %s",
            error.error_code,
            error.message,
        )

        return error_response(
            error.message,
            error.status_code,
            error.error_code,
        )


    @app.errorhandler(
        400
    )
    def handle_bad_request(
        error
    ):

        return error_response(
            "Requisição inválida.",
            400,
            "bad_request",
        )


    @app.errorhandler(
        401
    )
    def handle_unauthorized(
        error
    ):

        return error_response(
            "Autenticação necessária.",
            401,
            "unauthorized",
        )


    @app.errorhandler(
        403
    )
    def handle_forbidden(
        error
    ):

        return error_response(
            "Acesso não autorizado.",
            403,
            "forbidden",
        )


    @app.errorhandler(
        404
    )
    def handle_not_found(
        error
    ):

        if request.path.startswith(
            "/api/"
        ):

            return error_response(
                "Rota não encontrada.",
                404,
                "not_found",
            )

        return (
            "<!doctype html>"
            "<html lang='pt-BR'>"
            "<head>"
            "<meta charset='utf-8'>"
            "<title>404</title>"
            "</head>"
            "<body>"
            "<h1>404</h1>"
            "<p>Rota não encontrada.</p>"
            "<a href='/'>Voltar</a>"
            "</body>"
            "</html>",
            404,
        )


    @app.errorhandler(
        405
    )
    def handle_method_not_allowed(
        error
    ):

        return error_response(
            "Método HTTP não permitido.",
            405,
            "method_not_allowed",
        )


    @app.errorhandler(
        429
    )
    def handle_rate_limit(
        error
    ):

        return error_response(
            "Muitas requisições. Tente novamente em instantes.",
            429,
            "rate_limit",
        )


    @app.errorhandler(
        500
    )
    def handle_internal_error(
        error
    ):

        logger.exception(
            "Erro interno do servidor."
        )

        return error_response(
            "Erro interno do servidor.",
            500,
            "internal_server_error",
        )


    @app.errorhandler(
        Exception
    )
    def handle_unexpected_error(
        error
    ):

        logger.exception(
            "Erro inesperado: %s",
            error,
        )

        return error_response(
            "Ocorreu um erro inesperado.",
            500,
            "unexpected_error",
        )


# ============================================================
# FUNÇÃO AUXILIAR
# ============================================================

def register_handlers(
    app,
):

    register_error_handlers(
        app
    )
