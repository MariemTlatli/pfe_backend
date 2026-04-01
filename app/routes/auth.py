from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import ValidationError, Schema, fields
from app.models.user import UserSchema
from app.services.auth_service import AuthService

# ── Blueprint Smorest ──
auth_blp = Blueprint(
    "auth",
    __name__,
    url_prefix="/api/auth",
    description="Authentification des utilisateurs"
)


# ── Schémas de réponse ──
class LoginSchema(Schema):
    """Schéma pour la connexion."""
    email = fields.Email(required=True, metadata={"example": "ahmed@example.com"})
    password = fields.String(
        required=True,
        load_only=True,
        metadata={"example": "secret123"}
    )


class UserResponseSchema(Schema):
    """Schéma de réponse après login/register."""
    user_id = fields.String(metadata={"description": "ID de l'utilisateur"})
    username = fields.String(metadata={"description": "Nom d'utilisateur"})
    email = fields.Email(metadata={"description": "Email"})
    access_token = fields.String(metadata={"description": "Token JWT"})


class MessageSchema(Schema):
    """Schéma de message générique."""
    success = fields.Boolean()
    message = fields.String()
    data = fields.Nested(UserResponseSchema, allow_none=True)


# ──────────────────────────────────────
#  POST /api/auth/register
# ──────────────────────────────────────
@auth_blp.route("/register")
class RegisterView(MethodView):
    
    @auth_blp.arguments(UserSchema, location="json")
    @auth_blp.response(201, MessageSchema)
    @auth_blp.alt_response(400, description="Données invalides")
    @auth_blp.alt_response(409, description="Email ou username déjà utilisé")
    def post(self, data):
        """Inscrit un nouvel utilisateur"""
        
        try:
            result = AuthService.register(
                username=data["username"],
                email=data["email"],
                password=data["password"]
            )

            return {
                "success": True,
                "message": "Inscription réussie.",
                "data": result
            }

        except ValueError as e:
            abort(409, message=str(e))

        except Exception as e:
            abort(500, message=f"Erreur serveur: {str(e)}")


# ──────────────────────────────────────
#  POST /api/auth/login
# ──────────────────────────────────────
@auth_blp.route("/login")
class LoginView(MethodView):
    
    @auth_blp.arguments(LoginSchema, location="json")
    @auth_blp.response(200, MessageSchema)
    @auth_blp.alt_response(401, description="Identifiants invalides")
    def post(self, data):
        """Connecte un utilisateur existant"""
        
        try:
            result = AuthService.login(
                email=data["email"],
                password=data["password"]
            )

            return {
                "success": True,
                "message": "Connexion réussie.",
                "data": result
            }

        except ValueError as e:
            abort(401, message=str(e))

        except Exception as e:
            abort(500, message=f"Erreur serveur: {str(e)}")