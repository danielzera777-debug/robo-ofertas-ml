import time
from datetime import datetime, timezone

from flask import Blueprint, jsonify


health_bp = Blueprint(
    "health",
    __name__,
)


# ============================================================
# HEALTH CHECK
# ============================================================

@health_bp.route(
    "/health",
    methods=["GET"],
)
def health():

    return jsonify(
        ok=True,
        status="online",
        service="robo-ofertas",
        timestamp=int(
            time.time()
        ),
        datetime=datetime.now(
            timezone.utc
        ).isoformat(),
    ), 200


# ============================================================
# PING
# ============================================================

@health_bp.route(
    "/api/ping",
    methods=["GET"],
)
def ping():

    return jsonify(
        ok=True,
        message="pong",
        timestamp=int(
            time.time()
        ),
    ), 200


# ============================================================
# STATUS SIMPLES
# ============================================================

@health_bp.route(
    "/api/health",
    methods=["GET"],
)
def api_health():

    return jsonify(
        ok=True,
        status="online",
        service="robo-ofertas",
    ), 200


# ============================================================
# FUNÇÃO DE REGISTRO
# ============================================================

def register_health_routes(
    app,
):

    app.register_blueprint(
        health_bp
    )
