"""
Création des fichiers pour l'étape 6 (UserResponse + Routes).
Usage : python scripts/setup_step6.py
"""

import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def create_file(relative_path, content):
    full_path = os.path.join(ROOT, relative_path)
    directory = os.path.dirname(full_path)

    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        print(f"  📁 Dossier créé : {directory}")

    if os.path.exists(full_path):
        print(f"  ⚠️  EXISTE DÉJÀ : {relative_path}")
        return False

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✅ Créé : {relative_path}")
    return True


# ══════════════════════════════════════════════
# user_response.py (model)
# ══════════════════════════════════════════════

USER_RESPONSE_MODEL = '''"""
Modèle UserResponse — Réponse d\'un utilisateur à un exercice.

Chaque fois qu\'un utilisateur soumet une réponse, on stocke :
- Ce qu\'il a répondu
- Si c\'était correct
- Le temps passé
- Les métadonnées (exercice, compétence, leçon)

Ces données alimentent ensuite le BKT (étape 7).
"""

from bson import ObjectId
from datetime import datetime


class UserResponse:

    collection_name = "user_responses"

    # ──────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────

    @staticmethod
    def create(user_id, exercise_id, competence_id, lesson_id,
               answer, is_correct, time_spent=0):
        """
        Crée un document réponse utilisateur.

        Args:
            user_id: ID de l\'utilisateur
            exercise_id: ID de l\'exercice
            competence_id: ID de la compétence
            lesson_id: ID de la leçon
            answer: réponse de l\'utilisateur (str, list, bool)
            is_correct: bool — réponse correcte ou non
            time_spent: int — temps en secondes

        Returns:
            dict: document prêt pour insertion MongoDB
        """
        return {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
            "exercise_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id,
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id,
            "lesson_id": ObjectId(lesson_id) if isinstance(lesson_id, str) else lesson_id,
            "answer": answer,
            "is_correct": bool(is_correct),
            "time_spent": max(int(time_spent), 0),
            "created_at": datetime.utcnow(),
        }

    @staticmethod
    def insert(db, response_doc):
        """Insère une réponse en base."""
        collection = db[UserResponse.collection_name]
        result = collection.insert_one(response_doc)
        return result.inserted_id

    @staticmethod
    def get_by_id(db, response_id):
        """Récupère une réponse par ID."""
        collection = db[UserResponse.collection_name]
        return collection.find_one({
            "_id": ObjectId(response_id) if isinstance(response_id, str) else response_id
        })

    # ──────────────────────────────────────────────
    # Requêtes par utilisateur
    # ──────────────────────────────────────────────

    @staticmethod
    def get_by_user(db, user_id, limit=50):
        """Récupère les dernières réponses d\'un utilisateur."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id
            })
            .sort("created_at", -1)
            .limit(limit)
        )

    @staticmethod
    def get_by_user_and_competence(db, user_id, competence_id):
        """Récupère toutes les réponses d\'un utilisateur pour une compétence."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
                "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id,
            })
            .sort("created_at", 1)
        )

    @staticmethod
    def get_by_user_and_exercise(db, user_id, exercise_id):
        """Récupère toutes les tentatives d\'un utilisateur sur un exercice."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
                "exercise_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id,
            })
            .sort("created_at", 1)
        )

    @staticmethod
    def get_by_user_and_lesson(db, user_id, lesson_id):
        """Récupère les réponses d\'un utilisateur pour une leçon."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
                "lesson_id": ObjectId(lesson_id) if isinstance(lesson_id, str) else lesson_id,
            })
            .sort("created_at", 1)
        )

    # ──────────────────────────────────────────────
    # Historique pour BKT
    # ──────────────────────────────────────────────

    @staticmethod
    def get_correctness_history(db, user_id, competence_id):
        """
        Retourne l\'historique de correct/faux pour BKT.

        Returns:
            list[bool]: [True, False, True, True, ...]
            Ordonné du plus ancien au plus récent.
        """
        responses = UserResponse.get_by_user_and_competence(db, user_id, competence_id)
        return [r["is_correct"] for r in responses]

    @staticmethod
    def get_last_n_responses(db, user_id, competence_id, n=10):
        """Récupère les N dernières réponses pour une compétence."""
        collection = db[UserResponse.collection_name]
        return list(
            collection.find({
                "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id,
                "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id,
            })
            .sort("created_at", -1)
            .limit(n)
        )

    # ──────────────────────────────────────────────
    # Stats par utilisateur
    # ──────────────────────────────────────────────

    @staticmethod
    def get_user_stats(db, user_id, competence_id=None):
        """
        Statistiques d\'un utilisateur.

        Args:
            db: connexion MongoDB
            user_id: ID utilisateur
            competence_id: filtrer par compétence (optionnel)

        Returns:
            dict: {total, correct, incorrect, success_rate, avg_time, streak}
        """
        collection = db[UserResponse.collection_name]
        query = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id
        }
        if competence_id:
            query["competence_id"] = ObjectId(competence_id) if isinstance(competence_id, str) else competence_id

        responses = list(collection.find(query).sort("created_at", 1))

        if not responses:
            return {
                "total": 0,
                "correct": 0,
                "incorrect": 0,
                "success_rate": 0.0,
                "avg_time": 0,
                "streak": 0,
                "best_streak": 0,
            }

        total = len(responses)
        correct = sum(1 for r in responses if r["is_correct"])
        incorrect = total - correct
        success_rate = round(correct / total, 3) if total > 0 else 0.0

        times = [r.get("time_spent", 0) for r in responses if r.get("time_spent", 0) > 0]
        avg_time = round(sum(times) / len(times)) if times else 0

        # Streak actuelle (série de bonnes réponses depuis la fin)
        streak = 0
        for r in reversed(responses):
            if r["is_correct"]:
                streak += 1
            else:
                break

        # Meilleure streak
        best_streak = 0
        current = 0
        for r in responses:
            if r["is_correct"]:
                current += 1
                best_streak = max(best_streak, current)
            else:
                current = 0

        return {
            "total": total,
            "correct": correct,
            "incorrect": incorrect,
            "success_rate": success_rate,
            "avg_time": avg_time,
            "streak": streak,
            "best_streak": best_streak,
        }

    @staticmethod
    def get_user_competence_summary(db, user_id, subject_id=None):
        """
        Résumé par compétence pour un utilisateur.

        Returns:
            list[dict]: [{competence_id, total, correct, success_rate}, ...]
        """
        collection = db[UserResponse.collection_name]

        match_stage = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id
        }

        # Si subject_id fourni, filtrer les compétences de cette matière
        competence_ids = None
        if subject_id:
            from app.models.competence import Competence
            comps = Competence.get_by_subject(db, subject_id)
            competence_ids = [c["_id"] for c in comps]
            match_stage["competence_id"] = {"$in": competence_ids}

        pipeline = [
            {"$match": match_stage},
            {"$group": {
                "_id": "$competence_id",
                "total": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
                "avg_time": {"$avg": "$time_spent"},
                "last_response": {"$max": "$created_at"},
            }},
            {"$sort": {"last_response": -1}},
        ]

        results = list(collection.aggregate(pipeline))

        summary = []
        for r in results:
            total = r["total"]
            correct = r["correct"]
            summary.append({
                "competence_id": str(r["_id"]),
                "total": total,
                "correct": correct,
                "incorrect": total - correct,
                "success_rate": round(correct / total, 3) if total > 0 else 0.0,
                "avg_time": round(r["avg_time"]) if r["avg_time"] else 0,
                "last_response": r["last_response"],
            })

        return summary

    # ──────────────────────────────────────────────
    # Suppression
    # ──────────────────────────────────────────────

    @staticmethod
    def delete_by_user(db, user_id):
        """Supprime toutes les réponses d\'un utilisateur."""
        collection = db[UserResponse.collection_name]
        result = collection.delete_many({
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id
        })
        return result.deleted_count

    @staticmethod
    def delete_by_exercise(db, exercise_id):
        """Supprime toutes les réponses liées à un exercice."""
        collection = db[UserResponse.collection_name]
        result = collection.delete_many({
            "exercise_id": ObjectId(exercise_id) if isinstance(exercise_id, str) else exercise_id
        })
        return result.deleted_count

    @staticmethod
    def count_by_user(db, user_id, competence_id=None):
        """Compte les réponses d\'un utilisateur."""
        collection = db[UserResponse.collection_name]
        query = {
            "user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id
        }
        if competence_id:
            query["competence_id"] = ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        return collection.count_documents(query)
'''

# ══════════════════════════════════════════════
# user_response.py (schema)
# ══════════════════════════════════════════════

USER_RESPONSE_SCHEMA = '''"""
Schémas Marshmallow pour UserResponse.
"""

from marshmallow import Schema, fields, validate


class UserResponseSchema(Schema):
    """Schéma complet d\'une réponse utilisateur."""
    id = fields.String(dump_only=True, attribute="_id")
    user_id = fields.String(required=True)
    exercise_id = fields.String(required=True)
    competence_id = fields.String(required=True)
    lesson_id = fields.String(required=True)
    answer = fields.Raw(required=True)
    is_correct = fields.Boolean(dump_only=True)
    time_spent = fields.Integer(load_default=0)
    created_at = fields.DateTime(dump_only=True)


class SubmitResponseSchema(Schema):
    """Schéma pour soumettre une réponse."""
    user_id = fields.String(required=True)
    exercise_id = fields.String(required=True)
    answer = fields.Raw(required=True)
    time_spent = fields.Integer(
        load_default=0,
        validate=validate.Range(min=0),
        metadata={"description": "Temps passé en secondes"}
    )


class UserStatsSchema(Schema):
    """Schéma pour les stats utilisateur."""
    total = fields.Integer()
    correct = fields.Integer()
    incorrect = fields.Integer()
    success_rate = fields.Float()
    avg_time = fields.Integer()
    streak = fields.Integer()
    best_streak = fields.Integer()


class CompetenceSummarySchema(Schema):
    """Schéma pour le résumé par compétence."""
    competence_id = fields.String()
    total = fields.Integer()
    correct = fields.Integer()
    incorrect = fields.Integer()
    success_rate = fields.Float()
    avg_time = fields.Integer()
    last_response = fields.DateTime()
'''

# ══════════════════════════════════════════════
# response_routes.py
# ══════════════════════════════════════════════

RESPONSE_ROUTES = '''"""
Routes API pour les réponses utilisateur.
Blueprint : /api/responses

Endpoints :
  POST   /api/responses/submit                                      → Soumettre une réponse
  GET    /api/responses/user/<user_id>/history                      → Historique
  GET    /api/responses/user/<user_id>/competence/<competence_id>   → Par compétence
  GET    /api/responses/user/<user_id>/lesson/<lesson_id>           → Par leçon
  GET    /api/responses/user/<user_id>/stats                        → Stats globales
  GET    /api/responses/user/<user_id>/stats/<competence_id>        → Stats par compétence
  GET    /api/responses/user/<user_id>/summary                      → Résumé par compétence
  DELETE /api/responses/user/<user_id>                              → Supprimer historique
"""

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.extensions import mongo
from app.models.exercise import Exercise
from app.models.user_response import UserResponse

response_bp = Blueprint(
    "responses", __name__,
    url_prefix="/api/responses",
    description="Réponses utilisateur"
)


# ──────────────────────────────────────────────
# Soumettre une réponse
# ──────────────────────────────────────────────

@response_bp.route("/submit")
class SubmitResponse(MethodView):

    @response_bp.response(201)
    def post(self):
        """
        Soumet une réponse à un exercice.

        Body JSON :
        {
            "user_id": "abc123",
            "exercise_id": "def456",
            "answer": "float",
            "time_spent": 45
        }

        Retourne :
        {
            "response_id": "...",
            "is_correct": true,
            "correct_answer": "float",
            "explanation": "...",
            "stats": { total, correct, streak, ... }
        }
        """
        data = request.get_json() or {}

        user_id = data.get("user_id")
        exercise_id = data.get("exercise_id")
        answer = data.get("answer")
        time_spent = data.get("time_spent", 0)

        if not user_id:
            abort(400, message="user_id requis")
        if not exercise_id:
            abort(400, message="exercise_id requis")
        if answer is None:
            abort(400, message="answer requis")

        db = mongo.db

        # Récupérer l\'exercice
        exercise = Exercise.get_by_id(db, exercise_id)
        if not exercise:
            abort(404, message=f"Exercice {exercise_id} introuvable")

        # Vérifier la réponse
        check_result = Exercise.check_answer(exercise, answer)

        # Créer la réponse en base
        response_doc = UserResponse.create(
            user_id=user_id,
            exercise_id=exercise_id,
            competence_id=exercise["competence_id"],
            lesson_id=exercise["lesson_id"],
            answer=answer,
            is_correct=check_result["is_correct"],
            time_spent=time_spent,
        )
        response_id = UserResponse.insert(db, response_doc)

        # Incrémenter les compteurs de l\'exercice
        Exercise.increment_attempts(db, exercise_id, check_result["is_correct"])

        # Stats mises à jour
        stats = UserResponse.get_user_stats(
            db, user_id, str(exercise["competence_id"])
        )

        return {
            "response_id": str(response_id),
            "is_correct": check_result["is_correct"],
            "correct_answer": check_result["correct_answer"],
            "explanation": check_result["explanation"],
            "stats": stats,
        }


# ──────────────────────────────────────────────
# Historique utilisateur
# ──────────────────────────────────────────────

@response_bp.route("/user/<user_id>/history")
class UserHistory(MethodView):

    @response_bp.response(200)
    def get(self, user_id):
        """
        Historique des réponses d\'un utilisateur.

        Query params :
            limit : nombre max de réponses (défaut 50)
        """
        limit = request.args.get("limit", 50, type=int)

        db = mongo.db
        responses = UserResponse.get_by_user(db, user_id, limit=limit)

        for r in responses:
            r["_id"] = str(r["_id"])
            r["user_id"] = str(r["user_id"])
            r["exercise_id"] = str(r["exercise_id"])
            r["competence_id"] = str(r["competence_id"])
            r["lesson_id"] = str(r["lesson_id"])

        return {
            "user_id": user_id,
            "count": len(responses),
            "responses": responses,
        }


# ──────────────────────────────────────────────
# Par compétence
# ──────────────────────────────────────────────

@response_bp.route("/user/<user_id>/competence/<competence_id>")
class UserCompetenceResponses(MethodView):

    @response_bp.response(200)
    def get(self, user_id, competence_id):
        """Réponses d\'un utilisateur pour une compétence."""
        db = mongo.db
        responses = UserResponse.get_by_user_and_competence(db, user_id, competence_id)

        for r in responses:
            r["_id"] = str(r["_id"])
            r["user_id"] = str(r["user_id"])
            r["exercise_id"] = str(r["exercise_id"])
            r["competence_id"] = str(r["competence_id"])
            r["lesson_id"] = str(r["lesson_id"])

        # Historique correct/faux pour BKT
        correctness = [r["is_correct"] for r in responses]

        return {
            "user_id": user_id,
            "competence_id": competence_id,
            "count": len(responses),
            "correctness_history": correctness,
            "responses": responses,
        }


# ──────────────────────────────────────────────
# Par leçon
# ──────────────────────────────────────────────

@response_bp.route("/user/<user_id>/lesson/<lesson_id>")
class UserLessonResponses(MethodView):

    @response_bp.response(200)
    def get(self, user_id, lesson_id):
        """Réponses d\'un utilisateur pour une leçon."""
        db = mongo.db
        responses = UserResponse.get_by_user_and_lesson(db, user_id, lesson_id)

        for r in responses:
            r["_id"] = str(r["_id"])
            r["user_id"] = str(r["user_id"])
            r["exercise_id"] = str(r["exercise_id"])
            r["competence_id"] = str(r["competence_id"])
            r["lesson_id"] = str(r["lesson_id"])

        return {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "count": len(responses),
            "responses": responses,
        }


# ──────────────────────────────────────────────
# Stats globales
# ──────────────────────────────────────────────

@response_bp.route("/user/<user_id>/stats")
class UserGlobalStats(MethodView):

    @response_bp.response(200)
    def get(self, user_id):
        """Stats globales d\'un utilisateur."""
        db = mongo.db
        stats = UserResponse.get_user_stats(db, user_id)
        stats["user_id"] = user_id
        return stats


# ──────────────────────────────────────────────
# Stats par compétence
# ──────────────────────────────────────────────

@response_bp.route("/user/<user_id>/stats/<competence_id>")
class UserCompetenceStats(MethodView):

    @response_bp.response(200)
    def get(self, user_id, competence_id):
        """Stats d\'un utilisateur pour une compétence."""
        db = mongo.db
        stats = UserResponse.get_user_stats(db, user_id, competence_id)
        stats["user_id"] = user_id
        stats["competence_id"] = competence_id
        return stats


# ──────────────────────────────────────────────
# Résumé par compétence
# ──────────────────────────────────────────────

@response_bp.route("/user/<user_id>/summary")
class UserSummary(MethodView):

    @response_bp.response(200)
    def get(self, user_id):
        """
        Résumé de toutes les compétences travaillées par l\'utilisateur.

        Query params :
            subject_id : filtrer par matière (optionnel)
        """
        subject_id = request.args.get("subject_id", None)

        db = mongo.db
        summary = UserResponse.get_user_competence_summary(db, user_id, subject_id)

        return {
            "user_id": user_id,
            "competences_worked": len(summary),
            "summary": summary,
        }


# ──────────────────────────────────────────────
# Supprimer historique
# ──────────────────────────────────────────────

@response_bp.route("/user/<user_id>")
class DeleteUserResponses(MethodView):

    @response_bp.response(200)
    def delete(self, user_id):
        """Supprime tout l\'historique de réponses d\'un utilisateur."""
        db = mongo.db
        count = UserResponse.delete_by_user(db, user_id)

        return {
            "message": f"{count} réponse(s) supprimée(s)",
            "user_id": user_id,
            "deleted_count": count,
        }
'''

# ══════════════════════════════════════════════
# CRÉATION
# ══════════════════════════════════════════════

FILES = {
    "app/models/user_response.py": USER_RESPONSE_MODEL,
    "app/schemas/user_response.py": USER_RESPONSE_SCHEMA,
    "app/routes/response_routes.py": RESPONSE_ROUTES,
}


def main():
    print("=" * 50)
    print("  SETUP ÉTAPE 6 : UserResponse + Routes")
    print("=" * 50)
    print(f"  Racine : {ROOT}\n")

    created = 0
    skipped = 0

    for path, content in FILES.items():
        if create_file(path, content):
            created += 1
        else:
            skipped += 1

    print(f"\n  Créés  : {created}")
    print(f"  Ignorés: {skipped}")

    print(f"\n  📋 Fichiers créés :")
    print(f"     app/models/user_response.py     — Modèle (CRUD + stats + historique BKT)")
    print(f"     app/schemas/user_response.py    — Schémas Marshmallow")
    print(f"     app/routes/response_routes.py   — Routes API")

    print(f"\n  📋 Endpoints :")
    print(f"     POST   /api/responses/submit")
    print(f"     GET    /api/responses/user/<user_id>/history")
    print(f"     GET    /api/responses/user/<user_id>/competence/<competence_id>")
    print(f"     GET    /api/responses/user/<user_id>/lesson/<lesson_id>")
    print(f"     GET    /api/responses/user/<user_id>/stats")
    print(f"     GET    /api/responses/user/<user_id>/stats/<competence_id>")
    print(f"     GET    /api/responses/user/<user_id>/summary")
    print(f"     DELETE /api/responses/user/<user_id>")

    print(f"\n  ⚠️  ACTION MANUELLE REQUISE :")
    print(f"     Ajouter dans app/__init__.py :\n")
    print(f"       from app.routes.response_routes import response_bp")
    print(f"       api.register_blueprint(response_bp)")


if __name__ == "__main__":
    main()