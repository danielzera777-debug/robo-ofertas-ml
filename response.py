"""
Respostas padronizadas da API do Robo de Ofertas ML.
"""

from typing import Any, Dict, Optional

from flask import jsonify


# ============================================================
# RESPOSTA DE SUCESSO
# ============================================================

def success_response(
    data: Any = None,
    message: str = "Operação realizada com sucesso.",
    status_code: int = 200,
    **extra: Any,
):
    """
    Cria uma resposta JSON padronizada para operações
    realizadas com sucesso.
    """

    payload: Dict[str, Any] = {
        "ok": True,
        "sucesso": True,
        "mensagem": message,
    }

    if data is not None:

        payload["dados"] = data

    if extra:

        payload.update(
            extra
        )

    return jsonify(
        payload
    ), status_code


# ============================================================
# RESPOSTA DE ERRO
# ============================================================

def error_response(
    message: str = "Ocorreu um erro.",
    status_code: int = 400,
    error_code: str = "error",
    details: Optional[Any] = None,
    **extra: Any,
):
    """
    Cria uma resposta JSON padronizada para erros.
    """

    payload: Dict[str, Any] = {
        "ok": False,
        "sucesso": False,
        "erro": error_code,
        "mensagem": str(
            message
        ),
    }

    if details is not None:

        payload["detalhes"] = details

    if extra:

        payload.update(
            extra
        )

    return jsonify(
        payload
    ), status_code


# ============================================================
# RESPOSTA DE PAGINAÇÃO
# ============================================================

def paginated_response(
    items,
    page: int = 1,
    per_page: int = 20,
    total: Optional[int] = None,
    message: str = "Dados encontrados.",
    **extra: Any,
):
    """
    Resposta padronizada para listas paginadas.
    """

    items = list(
        items or []
    )

    page = max(
        1,
        int(page or 1),
    )

    per_page = max(
        1,
        int(per_page or 20),
    )

    if total is None:

        total = len(
            items
        )

    total = max(
        0,
        int(total),
    )

    pages = (
        (total + per_page - 1)
        // per_page
        if total
        else 0
    )

    payload = {
        "ok": True,
        "sucesso": True,
        "mensagem": message,
        "dados": items,
        "paginacao": {
            "pagina": page,
            "por_pagina": per_page,
            "total": total,
            "paginas": pages,
            "tem_proxima": (
                page < pages
            ),
            "tem_anterior": (
                page > 1
                and pages > 0
            ),
        },
    }

    if extra:

        payload.update(
            extra
        )

    return jsonify(
        payload
    ), 200


# ============================================================
# RESPOSTA DE STATUS
# ============================================================

def status_response(
    status: str = "online",
    service: str = "robo-ofertas",
    **extra: Any,
):
    """
    Resposta simples para health/status.
    """

    payload = {
        "ok": True,
        "status": status,
        "service": service,
    }

    if extra:

        payload.update(
            extra
        )

    return jsonify(
        payload
    ), 200


# ============================================================
# RESPOSTA VAZIA
# ============================================================

def empty_response(
    message: str = "Nenhum resultado encontrado.",
):
    """
    Retorna uma resposta válida sem resultados.
    """

    return jsonify(
        {
            "ok": True,
            "sucesso": True,
            "mensagem": message,
            "dados": [],
        }
    ), 200


# ============================================================
# RESPOSTA NÃO AUTORIZADA
# ============================================================

def unauthorized_response(
    message: str = "Autenticação necessária.",
):
    """
    Retorna erro HTTP 401.
    """

    return error_response(
        message=message,
        status_code=401,
        error_code="unauthorized",
    )


# ============================================================
# RESPOSTA PROIBIDA
# ============================================================

def forbidden_response(
    message: str = "Acesso não autorizado.",
):
    """
    Retorna erro HTTP 403.
    """

    return error_response(
        message=message,
        status_code=403,
        error_code="forbidden",
    )


# ============================================================
# RESPOSTA NÃO ENCONTRADA
# ============================================================

def not_found_response(
    message: str = "Recurso não encontrado.",
):
    """
    Retorna erro HTTP 404.
    """

    return error_response(
        message=message,
        status_code=404,
        error_code="not_found",
    )


# ============================================================
# RESPOSTA DE LIMITE
# ============================================================

def rate_limit_response(
    message: str = (
        "Muitas requisições. "
        "Tente novamente em instantes."
    ),
):
    """
    Retorna erro HTTP 429.
    """

    return error_response(
        message=message,
        status_code=429,
        error_code="rate_limit",
    )
