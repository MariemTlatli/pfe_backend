"""
Routes Gamification - Gestion de l'XP, des niveaux et des badges.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields, validate
from flask import request

from app.services.uno_service import GamificationServiceV2
from app.schemas.common import MessageSchema


blp = Blueprint(
    "Gamification",
    __name__,
    url_prefix="/api/gamification",
    description="Système de gamification : XP, niveaux et badges"
)


# # ==========================================
# # SCHÉMAS (à déplacer idéalement dans app/schemas/gamification.py)
# # ==========================================

# class initialiserSchema(Schema):
#     user_id = fields.String()
#     difficulty = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))
#     nb_cartes = fields.Integer(required=True)




# class BadgeStatsInputSchema(Schema):
#     total = fields.Integer(required=True)
#     streak = fields.Integer(required=True)
#     avg_time = fields.Float(required=True, validate=validate.Range(min=0.0))

# class CheckBadgesInputSchema(Schema):
#     stats = fields.Nested(BadgeStatsInputSchema, required=True)
#     mastery_level = fields.Float(required=True, validate=validate.Range(min=0.0, max=1.0))

# class BadgeOutputSchema(Schema):
#     id = fields.String()
#     name = fields.String()
#     earned_at = fields.DateTime()


# class GamificationInitOutputSchema(Schema):
#     joker_cards = fields.Integer()
#     plus4_cards = fields.Integer()
#     reverse_cards = fields.Integer()
#     plus2_cards = fields.Integer()
#     skip_cards = fields.Integer()
#     nb_exercices_imposes= fields.Integer()    


# # ==========================================
# # ROUTES
# # ==========================================

# @blp.route("/initialiser")
# class attribuer_mes_cartes(MethodView):
#     """Attribuer des points XP après un exercice."""
    
#     @blp.arguments(initialiserSchema)
#     @blp.response(200, CarteSchema(many=True))
#     def post(self, data):
#         """Simuler distibution des cartes"""
#         try:
#             result = GamificationServiceV2.attribuer_les_cartes(
#                 user_id=data['user_id'],
#                 difficulty=data['difficulty'],
#                 nb_cartes=data['nb_cartes']
#             )
#             print(result)
#             return result
#         except Exception as e:
#             abort(500, message=f"Erreur lors de l'attribution des cartes: {str(e)}")


# @blp.route("/special_cards_init/<string:user_id>")
# class GamificationStatusView(MethodView):
#     """nombres des cartes spéciales d'un utilisateur."""
#     @blp.response(200, GamificationInitOutputSchema)
#     def get(self, user_id):
#         """Récupérer nombres les cartes spéciales d'un utilisateur."""
#         try:
#             res = GamificationServiceV2.initialiser_les_cartes_spécial(user_id)
#             return res
#         except Exception as e:
#             abort(500, message=f"Erreur lors de la récupération des infos: {str(e)}")            

# @blp.route("/<string:user_id>/badges")
# class CheckBadgesView(MethodView):
#     """Vérifier et débloquer les badges éligibles."""
    
#     @blp.arguments(CheckBadgesInputSchema)
#     @blp.response(200, BadgeOutputSchema(many=True))
#     def post(self, data, user_id):
#         """Vérifier les critères et attribuer les nouveaux badges."""
#         try:
#             new_badges = GamificationService.check_and_award_badges(
#                 user_id=user_id,
#                 stats=data['stats'],
#                 mastery_level=data['mastery_level']
#             )
#             return new_badges
#         except Exception as e:
#             abort(500, message=f"Erreur lors de la vérification des badges: {str(e)}")

from marshmallow import Schema, fields, validate

# ─────────────────────────────────────────────
# QUERY PARAMS
# ─────────────────────────────────────────────

class DifficultyQuerySchema(Schema):
    difficulty = fields.Float(
        load_default=0.5,
        metadata={"description": "Niveau de difficulté entre 0 et 1", "example": 0.5}
    )

class UnoQuerySchema(Schema):
    difficulty = fields.Float(
        load_default=0.5,
        metadata={"description": "Niveau de difficulté entre 0 et 1", "example": 0.5}
    )
    nb_exercices_restants = fields.Int(
        load_default=0,
        metadata={"description": "Nombre d'exercices restants", "example": 3}
    )

class CiblesQuerySchema(Schema):
    nombre = fields.Int(
        load_default=4,
        metadata={"description": "Nombre de cibles à proposer", "example": 4}
    )

class CarteSchema(Schema):
    user_id = fields.String(required=True)
    valeur = fields.Integer(required=True)
    couleur = fields.String(required=True)
# ─────────────────────────────────────────────
# BODY JSON
# ─────────────────────────────────────────────

class UpdateCartesSchema(Schema):
    difficulty = fields.Float(
        required=True,
        metadata={"description": "Difficulté entre 0 et 1", "example": 0.5}
    )

class UtiliserPlus2Schema(Schema):
    from_user_id = fields.Str(
        required=True,
        metadata={"description": "ID expéditeur", "example": "64a1b2c3d4e5f6a7b8c9d0e1"}
    )
    to_user_id = fields.Str(
        required=True,
        metadata={"description": "ID cible", "example": "64a1b2c3d4e5f6a7b8c9d0e2"}
    )
    nb_exercices = fields.Int(
        load_default=2,
        metadata={"description": "Nombre d'exercices à imposer", "example": 2}
    )

class UtiliserSkipSchema(Schema):
    nb_exercices_a_annuler = fields.Int(
        load_default=2,
        metadata={"description": "Nombre d'exercices à annuler", "example": 2}
    )

class EmotionIncrementSchema(Schema):
    emotion_type = fields.Str(
        required=True,
        metadata={"description": "Type d'émotion", "example": "sad"}
    )

class EmotionInversionSchema(Schema):
    emotion_type = fields.Str(
        required=True,
        metadata={"description": "Type d'émotion", "example": "colere"}
    )
    seuil = fields.Int(
        load_default=12,
        metadata={"description": "Seuil d'occurrences", "example": 12}
    )

class JokerSchema(Schema):
    new_difficulty = fields.Float(
        required=True,
        metadata={"description": "Nouvelle difficulté entre 0 et 1", "example": 0.8}
    )

class JokerEmotionSchema(Schema):
    seuil_sad = fields.Int(
        load_default=5,
        metadata={"description": "Seuil d'émotions sad", "example": 5}
    )

class UtiliserPlus4Schema(Schema):
    exercise_id = fields.Str(
        required=True,
        metadata={"description": "ID de l'exercice en cours", "example": "64a1b2c3d4e5f6a7b8c9d0e4"}
    )

# ─────────────────────────────────────────────
# RESPONSES
# ─────────────────────────────────────────────

class SuccessSchema(Schema):
    success = fields.Bool(metadata={"example": True})
    message = fields.Str(metadata={"example": "Opération réussie."})

class CartesResponseSchema(Schema):
    success          = fields.Bool(metadata={"example": True})
    cartes           = fields.List(fields.Dict())
    couleur_dominante = fields.Str(metadata={"example": "v"})

class SpecialCardsResponseSchema(Schema):
    success = fields.Bool(metadata={"example": True})
    data    = fields.Dict()

class CiblesResponseSchema(Schema):
    success = fields.Bool(metadata={"example": True})
    cibles  = fields.List(fields.Dict())

class UnoResponseSchema(Schema):
    success = fields.Bool(metadata={"example": True})
    data    = fields.Dict()

from flask import Blueprint, request, jsonify
from app.services.uno_service import GamificationServiceV2
class GamificationStatusOutputSchema(Schema):
    joker_cards = fields.Integer()
    plus4_cards = fields.Integer()
    reverse_cards = fields.Integer()
    skip_cards = fields.Integer()
    plus2_cards = fields.Integer()
    
class MaitriseSchema(Schema):
    user_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        metadata={"description": "Identifiant unique de l'utilisateur", "example": 42}
    )
    competence_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        metadata={"description": "Identifiant unique de la compétence", "example": 7}
    )
# ─────────────────────────────────────────────
# CARTES PÉDAGOGIQUES
# ─────────────────────────────────────────────
from flask.views import MethodView
from flask_smorest import Blueprint

from app.services.uno_service import GamificationServiceV2

blp = Blueprint(
    "gamification",
    __name__,
    url_prefix="/api/gamification",
    description="Système de gamification UNO"
)


# ═════════════════════════════════════════════
# CARTES PÉDAGOGIQUES
# ═════════════════════════════════════════════


@blp.route("/special_cards/<string:user_id>")
class GamificationStatusView(MethodView):
    """Statut des cartes spéciales d'un utilisateur."""
    @blp.response(200, GamificationStatusOutputSchema)
    def get(self, user_id):
        """Récupérer les cartes spéciales d'un utilisateur."""
        try:
            status = GamificationServiceV2.get_user_special_cards(user_id)
            return status
        except Exception as e:
            abort(500, message=f"Erreur lors de la récupération des infos: {str(e)}")

@blp.route("/cartes/<string:user_id>")
class Cartes(MethodView):

    @blp.arguments(DifficultyQuerySchema, location="query")  # ← query param
    @blp.response(200, CarteSchema(many=True))
    @blp.doc(description="Retourne les cartes pédagogiques d'un utilisateur")
    def get(self, args, user_id):
        difficulty = args["difficulty"]
        result = GamificationServiceV2.attribuer_les_cartes(
                user_id=user_id,
                difficulty=difficulty,
                nb_cartes=7
            )
        print(result)
        return result


@blp.route("/cartes/<string:user_id>/vider")
class ViderMain(MethodView):

    @blp.response(200, SuccessSchema)
    @blp.doc(description="Supprime toutes les cartes d'un utilisateur")
    def delete(self, user_id):
        return GamificationServiceV2.vider_la_main(user_id)


@blp.route("/cartes/<string:user_id>/mettre-a-jour")
class MettreAJourCartes(MethodView):

    @blp.arguments(UpdateCartesSchema, location="json")  # ← body JSON
    @blp.response(200, SuccessSchema)
    @blp.doc(description="Met à jour les cartes existantes d'un utilisateur")
    def put(self, args, user_id):
        difficulty = args["difficulty"]
        return GamificationServiceV2.mettre_a_jour_cartes_existantes(user_id, difficulty)


# ═════════════════════════════════════════════
# CARTES SPÉCIALES
# ═════════════════════════════════════════════

@blp.route("/special/<string:user_id>")
class SpecialCards(MethodView):

    @blp.response(200, SpecialCardsResponseSchema)
    @blp.doc(description="Retourne les cartes spéciales d'un utilisateur")
    def get(self, user_id):
        result = GamificationServiceV2.get_user_special_cards(user_id)
        return {"success": True, "data": result}


@blp.route("/special/<string:user_id>/initialiser")
class InitialiserSpecial(MethodView):

    @blp.response(200, SuccessSchema)
    @blp.doc(description="Initialise les cartes spéciales d'un utilisateur")
    def post(self, user_id):
        modified = GamificationServiceV2.initialiser_les_cartes_special(user_id)
        return {
            "success": True,
            "modified_count": modified,
            "message": "Cartes spéciales initialisées."
        }


# ═════════════════════════════════════════════
# CARTE +2
# ═════════════════════════════════════════════

@blp.route("/plus2/<string:user_id>/attribuer")
class AttribuerPlus2(MethodView):

    @blp.response(200, SuccessSchema)
    @blp.doc(description="Attribue une carte +2 à un utilisateur")
    def post(self, user_id):
        return GamificationServiceV2.attribuer_carte_plus2(user_id)


@blp.route("/plus2/utiliser")
class UtiliserPlus2(MethodView):

    @blp.arguments(UtiliserPlus2Schema, location="json")  # ← body JSON
    @blp.response(200, SuccessSchema)
    @blp.doc(description="Utilise une carte +2 contre un utilisateur cible")
    def post(self, args):
        from_user_id = args["from_user_id"]
        to_user_id   = args["to_user_id"]
        nb_exercices = args["nb_exercices"]
        return GamificationServiceV2.utiliser_carte_plus2(
            from_user_id, to_user_id, nb_exercices
        )


@blp.route("/plus2/cibles/<string:user_id>")
class ProposerCibles(MethodView):

    @blp.arguments(CiblesQuerySchema, location="query")  # ← query param
    @blp.response(200, CiblesResponseSchema)
    @blp.doc(description="Propose des utilisateurs cibles pour une attaque +2")
    def get(self, args, user_id):
        nombre = args["nombre"]
        cibles = GamificationServiceV2.proposer_utilisateurs_cibles(user_id, nombre)
        return {"success": True, "cibles": cibles}


# ═════════════════════════════════════════════
# CARTE SKIP
# ═════════════════════════════════════════════

@blp.route("/skip/<string:user_id>/attribuer")
class AttribuerSkip(MethodView):

    @blp.response(200, SuccessSchema)
    @blp.doc(description="Attribue une carte Skip à un utilisateur")
    def post(self, user_id):
        return GamificationServiceV2.attribuer_carte_skip(user_id)


@blp.route("/skip/<string:user_id>/utiliser")
class UtiliserSkip(MethodView):

    @blp.arguments(UtiliserSkipSchema, location="json")  # ← body JSON
    @blp.response(200, SuccessSchema)
    @blp.doc(description="Utilise une carte Skip pour annuler des exercices imposés")
    def post(self, args, user_id):
        nb = args["nb_exercices_a_annuler"]
        return GamificationServiceV2.utiliser_carte_skip(user_id, nb)


# ═════════════════════════════════════════════
# CARTE INVERSION
# ═════════════════════════════════════════════

@blp.route("/reverse/<string:user_id>/utiliser")
class ActiverInversion(MethodView):

    @blp.response(200, SuccessSchema)
    @blp.doc(description="Active le bouclier d'inversion d'un utilisateur")
    def post(self, user_id):
        return GamificationServiceV2.activer_carte_inversion(user_id)


@blp.route("/inversion/<string:user_id>/attribuer-par-emotion")
class AttribuerInversionEmotion(MethodView):

    @blp.arguments(EmotionInversionSchema, location="json")  # ← body JSON
    @blp.response(200, SuccessSchema)
    @blp.doc(description="Attribue une carte Inversion si l'émotion dominante atteint le seuil")
    def post(self, args, user_id):
        emotion_type = args["emotion_type"]
        seuil        = args["seuil"]
        return GamificationServiceV2.attribuer_carte_inversion_par_emotion(
            user_id, emotion_type, seuil
        )


@blp.route("/emotion/<string:user_id>/increment")
class IncrementEmotion(MethodView):

    @blp.arguments(EmotionIncrementSchema, location="json")  # ← body JSON
    @blp.response(200, SuccessSchema)
    @blp.doc(description="Incrémente un compteur émotionnel pour un utilisateur")
    def post(self, args, user_id):
        emotion_type = args["emotion_type"]
        GamificationServiceV2.increment_emotion(user_id, emotion_type)
        return {"success": True, "message": f"Émotion '{emotion_type}' incrémentée."}


# ═════════════════════════════════════════════
# CARTE +4 / MAÎTRISE
# ═════════════════════════════════════════════

@blp.route("/plus4/<string:user_id>/utiliser")
class UtiliserPlus4(MethodView):

    @blp.arguments(UtiliserPlus4Schema, location="json")
    @blp.response(200, SuccessSchema)
    @blp.doc(description="Utilise une carte +4 pour obtenir 4 indices")
    def post(self, args, user_id):
        exercise_id = args["exercise_id"]
        return GamificationServiceV2.utiliser_carte_plus4(user_id, exercise_id)

@blp.route("/maitrise/attribuer")
class AttribuerMaitrise(MethodView):

    @blp.arguments(MaitriseSchema, location="json")  # ← body JSON
    @blp.response(200, SuccessSchema)
    @blp.doc(description="Attribue une carte +4 suite à la maîtrise d'une compétence")
    def post(self, args):
        user_id       = args["user_id"]
        competence_id = args["competence_id"]
        return GamificationServiceV2.attribuer_carte_plus4(user_id, competence_id)


# ═════════════════════════════════════════════
# CARTE JOKER
# ═════════════════════════════════════════════

@blp.route("/joker/<string:user_id>/utiliser")
class UtiliserJoker(MethodView):

    @blp.arguments(JokerSchema, location="json")  # ← body JSON
    @blp.response(200, SuccessSchema)
    @blp.doc(description="Utilise une carte Joker pour changer la difficulté")
    def post(self, args, user_id):
        new_difficulty = args["new_difficulty"]
        return GamificationServiceV2.utiliser_carte_joker(user_id, new_difficulty)


@blp.route("/joker/<string:user_id>/attribuer-par-emotion")
class AttribuerJokerEmotion(MethodView):

    @blp.arguments(JokerEmotionSchema, location="json")  # ← body JSON
    @blp.response(200, SuccessSchema)
    @blp.doc(description="Attribue un Joker si >= seuil émotions sad")
    def post(self, args, user_id):
        seuil_sad = args["seuil_sad"]
        return GamificationServiceV2.attribuer_joker_par_emotion(user_id, seuil_sad)


# ═════════════════════════════════════════════
# UNO
# ═════════════════════════════════════════════

@blp.route("/uno/<string:user_id>")
class UnoState(MethodView):

    @blp.arguments(UnoQuerySchema, location="query")  # ← query params
    @blp.response(200, UnoResponseSchema)
    @blp.doc(description="Retourne l'état UNO d'un utilisateur")
    def get(self, args, user_id):
        difficulty            = args["difficulty"]
        nb_exercices_restants = args["nb_exercices_restants"]
        result = GamificationServiceV2.get_uno_state(
            user_id, difficulty, nb_exercices_restants
        )
        return {"success": True, "data": result}