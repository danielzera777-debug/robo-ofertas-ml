"""
Exceções personalizadas do Robo de Ofertas ML.

As exceções deste arquivo permitem que os serviços e rotas
identifiquem claramente o tipo de falha ocorrido sem depender
de mensagens específicas de bibliotecas externas.
"""

from __future__ import annotations

from typing import Any, Optional


# ============================================================
# EXCEÇÃO BASE
# ============================================================

class RoboOfertasError(Exception):
    """
    Exceção base do projeto.
    """

    default_message = (
        "Ocorreu um erro no Robo de Ofertas."
    )

    default_code = "robo_ofertas_error"

    default_status_code = 500

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Any = None,
    ):

        self.message = (
            str(message)
            if message
            else self.default_message
        )

        self.code = (
            str(code)
            if code
            else self.default_code
        )

        self.status_code = (
            int(status_code)
            if status_code is not None
            else self.default_status_code
        )

        self.details = details

        super().__init__(
            self.message
        )

    def to_dict(self) -> dict:
        """
        Converte a exceção para estrutura adequada
        para respostas da API.
        """

        payload = {
            "ok": False,
            "erro": self.code,
            "mensagem": self.message,
        }

        if self.details is not None:

            payload["detalhes"] = (
                self.details
            )

        return payload


# ============================================================
# CONFIGURAÇÃO
# ============================================================

class ConfigurationError(
    RoboOfertasError
):
    """
    Erro de configuração da aplicação.
    """

    default_message = (
        "A configuração da aplicação está incompleta."
    )

    default_code = "configuration_error"

    default_status_code = 500


# ============================================================
# AUTENTICAÇÃO
# ============================================================

class AuthenticationError(
    RoboOfertasError
):
    """
    Erro relacionado à autenticação.
    """

    default_message = (
        "Não foi possível autenticar."
    )

    default_code = "authentication_error"

    default_status_code = 401


class AuthorizationError(
    RoboOfertasError
):
    """
    Usuário autenticado, porém sem permissão.
    """

    default_message = (
        "Você não possui permissão para realizar esta ação."
    )

    default_code = "authorization_error"

    default_status_code = 403


# ============================================================
# MERCADO LIVRE
# ============================================================

class MercadoLivreError(
    RoboOfertasError
):
    """
    Erro genérico relacionado à API do Mercado Livre.
    """

    default_message = (
        "Ocorreu um erro ao comunicar com o Mercado Livre."
    )

    default_code = "mercado_livre_error"

    default_status_code = 502


class MercadoLivreAuthenticationError(
    MercadoLivreError
):
    """
    Falha de autenticação OAuth do Mercado Livre.
    """

    default_message = (
        "A autenticação com o Mercado Livre falhou."
    )

    default_code = (
        "mercado_livre_authentication_error"
    )

    default_status_code = 401


class MercadoLivreForbiddenError(
    MercadoLivreError
):
    """
    Mercado Livre recusou a operação por falta de
    autorização ou permissão.
    """

    default_message = (
        "O Mercado Livre recusou esta operação."
    )

    default_code = (
        "mercado_livre_forbidden"
    )

    default_status_code = 403


class MercadoLivreNotFoundError(
    MercadoLivreError
):
    """
    Recurso não encontrado no Mercado Livre.
    """

    default_message = (
        "O recurso solicitado não foi encontrado no Mercado Livre."
    )

    default_code = (
        "mercado_livre_not_found"
    )

    default_status_code = 404


class MercadoLivreRateLimitError(
    MercadoLivreError
):
    """
    Limite de requisições da API atingido.
    """

    default_message = (
        "O limite de requisições do Mercado Livre foi atingido."
    )

    default_code = (
        "mercado_livre_rate_limit"
    )

    default_status_code = 429


class MercadoLivreTimeoutError(
    MercadoLivreError
):
    """
    A API demorou além do limite configurado.
    """

    default_message = (
        "A comunicação com o Mercado Livre excedeu o tempo limite."
    )

    default_code = (
        "mercado_livre_timeout"
    )

    default_status_code = 504


# ============================================================
# PRODUTOS
# ============================================================

class ProductError(
    RoboOfertasError
):
    """
    Erro relacionado a produtos.
    """

    default_message = (
        "Não foi possível processar o produto."
    )

    default_code = "product_error"

    default_status_code = 400


class ProductNotFoundError(
    ProductError
):
    """
    Produto não encontrado.
    """

    default_message = (
        "Produto não encontrado."
    )

    default_code = "product_not_found"

    default_status_code = 404


class InvalidProductError(
    ProductError
):
    """
    Produto com dados inválidos.
    """

    default_message = (
        "Os dados do produto são inválidos."
    )

    default_code = "invalid_product"

    default_status_code = 400


# ============================================================
# OFERTAS
# ============================================================

class OfferError(
    RoboOfertasError
):
    """
    Erro relacionado às ofertas.
    """

    default_message = (
        "Não foi possível processar a oferta."
    )

    default_code = "offer_error"

    default_status_code = 400


class OfferNotFoundError(
    OfferError
):
    """
    Oferta não encontrada.
    """

    default_message = (
        "Oferta não encontrada."
    )

    default_code = "offer_not_found"

    default_status_code = 404


class InvalidOfferError(
    OfferError
):
    """
    Oferta inválida.
    """

    default_message = (
        "Os dados da oferta são inválidos."
    )

    default_code = "invalid_offer"

    default_status_code = 400


# ============================================================
# VALIDAÇÃO
# ============================================================

class ValidationError(
    RoboOfertasError
):
    """
    Dados enviados pelo usuário são inválidos.
    """

    default_message = (
        "Os dados enviados são inválidos."
    )

    default_code = "validation_error"

    default_status_code = 400


# ============================================================
# BANCO DE DADOS
# ============================================================

class DatabaseError(
    RoboOfertasError
):
    """
    Erro de banco de dados.
    """

    default_message = (
        "Ocorreu um erro no banco de dados."
    )

    default_code = "database_error"

    default_status_code = 500


class DatabaseConnectionError(
    DatabaseError
):
    """
    Não foi possível conectar ao banco.
    """

    default_message = (
        "Não foi possível conectar ao banco de dados."
    )

    default_code = (
        "database_connection_error"
    )

    default_status_code = 503


# ============================================================
# WHATSAPP
# ============================================================

class WhatsAppError(
    RoboOfertasError
):
    """
    Erro relacionado ao WhatsApp.
    """

    default_message = (
        "Ocorreu um erro ao processar o WhatsApp."
    )

    default_code = "whatsapp_error"

    default_status_code = 502


class WhatsAppConfigurationError(
    WhatsAppError
):
    """
    Configuração do WhatsApp incompleta.
    """

    default_message = (
        "A integração com o WhatsApp não está configurada."
    )

    default_code = (
        "whatsapp_configuration_error"
    )

    default_status_code = 503


# ============================================================
# RATE LIMIT
# ============================================================

class RateLimitError(
    RoboOfertasError
):
    """
    Limite de requisições interno atingido.
    """

    default_message = (
        "Limite de requisições atingido."
    )

    default_code = "rate_limit"

    default_status_code = 429


# ============================================================
# SERVIÇO INDISPONÍVEL
# ============================================================

class ServiceUnavailableError(
    RoboOfertasError
):
    """
    Serviço temporariamente indisponível.
    """

    default_message = (
        "Serviço temporariamente indisponível."
    )

    default_code = "service_unavailable"

    default_status_code = 503


# ============================================================
# HELPERS
# ============================================================

def is_robo_error(
    error: BaseException,
) -> bool:
    """
    Verifica se uma exceção pertence ao projeto.
    """

    return isinstance(
        error,
        RoboOfertasError,
    )


def exception_to_response(
    error: BaseException,
) -> dict:
    """
    Converte uma exceção em payload JSON.
    """

    if isinstance(
        error,
        RoboOfertasError,
    ):

        return error.to_dict()

    return {
        "ok": False,
        "erro": "internal_server_error",
        "mensagem": (
            "Erro interno do servidor."
        ),
    }


def exception_status_code(
    error: BaseException,
) -> int:
    """
    Retorna o HTTP status associado à exceção.
    """

    if isinstance(
        error,
        RoboOfertasError,
    ):

        return error.status_code

    return 500


# ============================================================
# EXPORTAÇÕES
# ============================================================

__all__ = [
    "RoboOfertasError",
    "ConfigurationError",
    "AuthenticationError",
    "AuthorizationError",
    "MercadoLivreError",
    "MercadoLivreAuthenticationError",
    "MercadoLivreForbiddenError",
    "MercadoLivreNotFoundError",
    "MercadoLivreRateLimitError",
    "MercadoLivreTimeoutError",
    "ProductError",
    "ProductNotFoundError",
    "InvalidProductError",
    "OfferError",
    "OfferNotFoundError",
    "InvalidOfferError",
    "ValidationError",
    "DatabaseError",
    "DatabaseConnectionError",
    "WhatsAppError",
    "WhatsAppConfigurationError",
    "RateLimitError",
    "ServiceUnavailableError",
    "is_robo_error",
    "exception_to_response",
    "exception_status_code",
]
