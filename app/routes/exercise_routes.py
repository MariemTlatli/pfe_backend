"""
Routes API pour les exercices.
Blueprint : /api/exercises

Endpoints :
  POST   /api/exercises/generate/<competence_id>         → Générer des exercices
  GET    /api/exercises/competence/<competence_id>        → Lister par compétence
  GET    /api/exercises/lesson/<lesson_id>                → Lister par leçon
  GET    /api/exercises/<exercise_id>                     → Détail (avec réponse)
  GET    /api/exercises/<exercise_id>/public              → Détail (sans réponse, pour l'élève)
  POST   /api/exercises/<exercise_id>/check               → Vérifier une réponse
  POST   /api/exercises/<exercise_id>/regenerate          → Regénérer un exercice
  DELETE /api/exercises/<exercise_id>                     → Supprimer un exercice
  DELETE /api/exercises/competence/<competence_id>        → Supprimer tous les exercices d'une compétence
  GET    /api/exercises/competence/<competence_id>/stats  → Stats par compétence
"""

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from bson import ObjectId
from app.extensions import mongo
from app.models.exercise import Exercise
from app.models.competence import Competence
from app.services.exercise_generator import ExerciseGeneratorService
from app.schemas.exercise import GenerateExercisesRequestSchema, SubmitAnswerSchema

exercise_bp = Blueprint(
    "exercises", __name__,
    url_prefix="/api/exercises",
    description="Gestion des exercices"
)


# ──────────────────────────────────────────────
# Générer des exercices
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# Générer des exercices avec SAINT+
# ──────────────────────────────────────────────

@exercise_bp.route("/generate/<competence_id>")
class GenerateExercises(MethodView):

    @exercise_bp.arguments(GenerateExercisesRequestSchema, location='json')
    @exercise_bp.response(201)
    def post(self, data, competence_id):
        """
        Génère des exercices adaptatifs avec analyse SAINT+.

        Body JSON :
        {
            "user_id": "507f1f77bcf86cd799439011",  // requis
            "count": 5,                              // optionnel, défaut 3
            "regenerate": false                      // optionnel, défaut false
        }
        """
        from app.services.zpd_service import ZPDService
        from app.services.ollama_service import OllamaService

        user_id = data.get("user_id")
        count = data.get("count", 3)
        regenerate = data.get("regenerate", False)

        db = mongo.db

        # Vérifier que la compétence existe
        competence = Competence.get_by_id( competence_id)
        if not competence:
            abort(404, message=f"Compétence {competence_id} introuvable")

        # Vérifier qu'Ollama est disponible
        if not OllamaService.is_available():
            abort(503, message="Service Ollama indisponible.")

        # Récupérer TOUTES les leçons de la compétence
        lessons = list(db["lessons"].find({
            "competence_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        }).sort("order_index", 1))

        if not lessons:
            abort(404, message=f"Aucune leçon trouvée pour la compétence {competence_id}")

        # Extraire les titres des leçons
        lesson_titles = [lesson.get("title", f"Leçon {i+1}") for i, lesson in enumerate(lessons)]

        print(f"[ADAPTIVE] Compétence: {competence.get('name')}")
        print(f"[ADAPTIVE] {len(lessons)} leçon(s): {lesson_titles}")

        # ═══════════════════════════════════════════════════
        # Analyse SAINT+ de l'utilisateur
        # ═══════════════════════════════════════════════════
        print(f"[ADAPTIVE] Analyse SAINT+ pour user {user_id}...")

        zpd_analysis = ZPDService(db).analyze_competence(
            competence_id=competence_id,
            mastery_level=None,
            all_masteries={},
            user_id=user_id
        )

        if not zpd_analysis:
            abort(500, message="Échec de l'analyse SAINT+")

        # Extraire le contexte SAINT+
        saint_context = {
            "mastery": zpd_analysis.get("mastery_level", 0.0),
            "zone": zpd_analysis.get("effective_zone", "frustration"),
            "optimal_difficulty": zpd_analysis.get("optimal_difficulty", 0.5),
            "hint_level": zpd_analysis.get("saint_metrics", {})
                                     .get("hint_probability", {})
                                     .get("level", "moyen"),
            "recommended_exercise_types": zpd_analysis.get("recommended_exercise_types", []),
            "engagement": zpd_analysis.get("saint_metrics", {})
                                     .get("engagement", {})
                                     .get("level", "inconnu"),
            "p_correct": zpd_analysis.get("saint_metrics", {})
                                    .get("p_correct", 0.5),
        }

        print(f"[ADAPTIVE] Contexte SAINT+: {saint_context}")

        # ═══════════════════════════════════════════════════
        # Générer les exercices adaptatifs
        # ═══════════════════════════════════════════════════
        generator = ExerciseGeneratorService(db)

        result = generator.generate_adaptive_exercises(
            competence_id=competence_id,
            competence=competence,
            lessons=lessons,
            lesson_titles=lesson_titles,
            count=count,
            saint_context=saint_context,
            regenerate=regenerate
        )

        if "error" in result:
            abort(400, message=result["error"])

        # Ajouter infos à la réponse
        result["competence"] = {
            "id": str(competence["_id"]),
            "name": competence.get("name"),
            "description": competence.get("description"),
        }
        result["lesson_titles"] = lesson_titles
        result["saint_context"] = saint_context
        result["message"] = "Exercices adaptatifs générés avec succès"

        return result

# ──────────────────────────────────────────────
# Lister par compétence
# ──────────────────────────────────────────────

@exercise_bp.route("/competence/<competence_id>")
class ExercisesByCompetence(MethodView):

    @exercise_bp.response(200)
    def get(self, competence_id):
        """
        Liste les exercices d'une compétence.

        Query params :
            type   : filtrer par type (optionnel)
            status : filtrer par statut (optionnel)
        """
        exercise_type = request.args.get("type", None)
        status = request.args.get("status", None)

        db = mongo.db
        exercises = Exercise.get_by_competence(db, competence_id, exercise_type, status)

        # Convertir les ObjectId en string
        for ex in exercises:
            ex["_id"] = str(ex["_id"])
            ex["competence_id"] = str(ex["competence_id"])
            ex["lesson_id"] = str(ex["lesson_id"])

        return {
            "competence_id": competence_id,
            "count": len(exercises),
            "exercises": exercises
        }


# ──────────────────────────────────────────────
# Lister par leçon
# ──────────────────────────────────────────────

@exercise_bp.route("/lesson/<lesson_id>")
class ExercisesByLesson(MethodView):

    @exercise_bp.response(200)
    def get(self, lesson_id):
        """
        Liste les exercices d'une leçon.

        Query params :
            type : filtrer par type (optionnel)
        """
        exercise_type = request.args.get("type", None)

        db = mongo.db
        exercises = Exercise.get_by_lesson(db, lesson_id, exercise_type)

        for ex in exercises:
            ex["_id"] = str(ex["_id"])
            ex["competence_id"] = str(ex["competence_id"])
            ex["lesson_id"] = str(ex["lesson_id"])

        return {
            "lesson_id": lesson_id,
            "count": len(exercises),
            "exercises": exercises
        }


# ──────────────────────────────────────────────
# Détail d'un exercice (complet, avec réponse)
# ──────────────────────────────────────────────

@exercise_bp.route("/<exercise_id>")
class ExerciseDetail(MethodView):

    @exercise_bp.response(200)
    def get(self, exercise_id):
        """Détail complet d'un exercice (avec correct_answer)."""
        db = mongo.db
        exercise = Exercise.get_by_id(db, exercise_id)

        if not exercise:
            abort(404, message=f"Exercice {exercise_id} introuvable")

        exercise["_id"] = str(exercise["_id"])
        exercise["competence_id"] = str(exercise["competence_id"])
        exercise["lesson_id"] = str(exercise["lesson_id"])

        return exercise

    @exercise_bp.response(200)
    def delete(self, exercise_id):
        """Supprime un exercice."""
        db = mongo.db
        deleted = Exercise.delete(db, exercise_id)

        if not deleted:
            abort(404, message=f"Exercice {exercise_id} introuvable")

        return {"message": "Exercice supprimé", "exercise_id": exercise_id}


# ──────────────────────────────────────────────
# Détail public (sans réponse, pour l'élève)
# ──────────────────────────────────────────────

@exercise_bp.route("/<exercise_id>/public")
class ExercisePublic(MethodView):

    @exercise_bp.response(200)
    def get(self, exercise_id):
        """
        Détail d'un exercice SANS la réponse correcte.
        C'est cet endpoint que l'élève utilise pour voir l'exercice.
        """
        db = mongo.db
        exercise = Exercise.get_by_id(db, exercise_id)

        if not exercise:
            abort(404, message=f"Exercice {exercise_id} introuvable")

        # Retourner sans correct_answer ni explanation
        return {
            "id": str(exercise["_id"]),
            "competence_id": str(exercise["competence_id"]),
            "lesson_id": str(exercise["lesson_id"]),
            "type": exercise["type"],
            "difficulty": exercise["difficulty"],
            "question": exercise["question"],
            "options": exercise.get("options", []),
            "hints": exercise.get("hints", []),
            "code_template": exercise.get("code_template", ""),
            "estimated_time": exercise.get("estimated_time", 60),
        }


# ──────────────────────────────────────────────
# Vérifier une réponse
# ──────────────────────────────────────────────

@exercise_bp.route("/<exercise_id>/check")
class CheckAnswer(MethodView):

    @exercise_bp.arguments(SubmitAnswerSchema, location='json')
    @exercise_bp.response(200)
    def post(self, data, exercise_id):
        """
        Vérifie la réponse de l'utilisateur.

        Body JSON :
        {
            "answer": "ma réponse",
            "time_spent": 45     // optionnel, en secondes
        }

        Retourne :
        {
            "is_correct": true,
            "correct_answer": "la bonne réponse",
            "explanation": "pourquoi..."
        }
        """
        user_answer = data.get("answer")

        db = mongo.db
        exercise = Exercise.get_by_id(db, exercise_id)

        if not exercise:
            abort(404, message=f"Exercice {exercise_id} introuvable")

        # Vérifier la réponse
        result = Exercise.check_answer(exercise, user_answer)

        # Incrémenter les compteurs de l'exercice
        Exercise.increment_attempts(db, exercise_id, result["is_correct"])

        return result


# ──────────────────────────────────────────────
# Regénérer un exercice
# ──────────────────────────────────────────────

@exercise_bp.route("/<exercise_id>/regenerate")
class RegenerateExercise(MethodView):

    @exercise_bp.response(200)
    def post(self, exercise_id):
        """Regénère un exercice existant (garde type et difficulté)."""
        db = mongo.db
        generator = ExerciseGeneratorService(db)
        result = generator.regenerate_exercise(exercise_id)

        if "error" in result:
            abort(400, message=result["error"])

        return result


# ──────────────────────────────────────────────
# Supprimer tous les exercices d'une compétence
# ──────────────────────────────────────────────

@exercise_bp.route("/competence/<competence_id>/delete-all")
class DeleteAllExercises(MethodView):

    @exercise_bp.response(200)
    def delete(self, competence_id):
        """Supprime tous les exercices d'une compétence."""
        db = mongo.db
        count = Exercise.delete_by_competence(db, competence_id)

        return {
            "message": f"{count} exercice(s) supprimé(s)",
            "competence_id": competence_id,
            "deleted_count": count
        }


# ──────────────────────────────────────────────
# Stats par compétence
# ──────────────────────────────────────────────

@exercise_bp.route("/competence/<competence_id>/stats")
class ExerciseStats(MethodView):

    @exercise_bp.response(200)
    def get(self, competence_id):
        """Statistiques des exercices d'une compétence."""
        db = mongo.db

        competence = Competence.get_by_id(db, competence_id)
        if not competence:
            abort(404, message=f"Compétence {competence_id} introuvable")

        stats = Exercise.get_stats(db, competence_id)

        return stats
