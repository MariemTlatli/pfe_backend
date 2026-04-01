from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


def auth_required(fn):
    """
    Décorateur qui protège une route.
    Vérifie la présence et la validité du token JWT.
    Injecte `current_user_id` comme premier argument.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            current_user_id = get_jwt_identity()
            return fn(current_user_id, *args, **kwargs)

        except Exception as e:
            return jsonify({
                "success": False,
                "message": "Authentification requise.",
                "error": str(e)
            }), 401

    return wrapper