# """
# Routes API pour les réponses utilisateur.
# Blueprint : /api/responses

# SAINT+ est appelé automatiquement après chaque soumission
# pour mettre à jour la maîtrise et fournir les métriques enrichies.
# """

# from flask import request
# from flask.views import MethodView
# from flask_smorest import Blueprint, abort

# from app.extensions import mongo
# from app.models.exercise import Exercise
# from app.models.user_response import UserResponse
# from app.models.user_progress import UserProgress
# from app.services.saint_service import SAINTService
# from app.schemas.user_response import SubmitResponseSchema
# from app.schemas.user_progress import UserProgressListSchema

# response_bp = Blueprint(
#     "responses", __name__,
#     url_prefix="/api/responses",
#     description="Réponses utilisateur"
# )


# # ──────────────────────────────────────────────
# # Soumettre une réponse (+ SAINT+)
# # ──────────────────────────────────────────────

# @response_bp.route("/submit")
# class SubmitResponse(MethodView):

#     @response_bp.arguments(SubmitResponseSchema, location='json')
#     @response_bp.response(201)
#     def post(self, data):
#         """
#         Soumet une réponse à un exercice.

#         1. Vérifie la réponse
#         2. Sauvegarde en base
#         3. Appelle SAINT+ pour mettre à jour la maîtrise
#         4. Retourne le résultat enrichi

#         Body JSON :
#         {
#             "user_id": "abc123",
#             "exercise_id": "def456",
#             "answer": "float",
#             "time_spent": 45
#         }
#         """
#         user_id = data.get("user_id")
#         exercise_id = data.get("exercise_id")
#         answer = data.get("answer")
#         time_spent = data.get("time_spent", 0)

#         db = mongo.db

#         # ── 1. Récupérer l'exercice ──
#         exercise = Exercise.get_by_id(db, exercise_id)
#         if not exercise:
#             abort(404, message=f"Exercice {exercise_id} introuvable")

#         # ── 2. Vérifier la réponse ──
#         check_result = Exercise.check_answer(exercise, answer)

#         # ── 3. Sauvegarder la réponse en base ──
#         response_doc = UserResponse.create(
#             user_id=user_id,
#             exercise_id=exercise_id,
#             competence_id=exercise["competence_id"],
#             lesson_id=exercise["lesson_id"],
#             answer=answer,
#             is_correct=check_result["is_correct"],
#             time_spent=time_spent,
#         )
#         response_id = UserResponse.insert(db, response_doc)

#         # ── 4. Incrémenter les compteurs de l'exercice ──
#         Exercise.increment_attempts(db, exercise_id, check_result["is_correct"])

#         # ── 5. SAINT+ : prédiction enrichie ──
#         competence_id = str(exercise["competence_id"])
#         saint_result = SAINTService.update_knowledge(
#             db=db,
#             user_id=user_id,
#             competence_id=competence_id,
#             is_correct=check_result["is_correct"]
#         )

#         # ── 6. Stats mises à jour ──
#         stats = UserResponse.get_user_stats(db, user_id, competence_id)

#         return {
#             "response_id": str(response_id),
#             "is_correct": check_result["is_correct"],
#             "correct_answer": check_result["correct_answer"],
#             "explanation": check_result["explanation"],

#             # Stats classiques
#             "stats": stats,

#             # Métriques SAINT+ enrichies
#             "saint_prediction": {
#                 "p_correct": saint_result.get("p_correct"),
#                 "mastery": saint_result.get("mastery"),
#                 "zone": saint_result.get("zone"),
#                 "zone_label": saint_result.get("zone_label"),
#                 "is_mastered": saint_result.get("is_mastered", False),
#                 "estimated_attempts": saint_result.get("estimated_attempts"),
#                 "hint": saint_result.get("hint_probability"),
#                 "engagement": saint_result.get("engagement"),
#                 "anomaly": saint_result.get("anomaly"),
#                 "recommended_difficulty": saint_result.get("recommended_difficulty"),
#                 "recommended_exercises_count": saint_result.get("recommended_exercises_count"),
#                 "confidence": saint_result.get("confidence"),
#             },
#         }


# # ──────────────────────────────────────────────
# # Prédiction SAINT+ sans soumettre de réponse
# # ──────────────────────────────────────────────

# @response_bp.route("/predict/<user_id>")
# class PredictPerformance(MethodView):

#     @response_bp.response(200)
#     def get(self, user_id):
#         """
#         Prédit la performance d'un élève sans soumettre de réponse.

#         Query params :
#             competence_id : ID de la compétence (optionnel)
#         """
#         competence_id = request.args.get("competence_id", None)
#         db = mongo.db

#         result = SAINTService.predict(db, user_id, competence_id)

#         return {
#             "user_id": user_id,
#             "competence_id": competence_id,
#             "prediction": result,
#         }


# # ──────────────────────────────────────────────
# # Progression SAINT+ d'un élève
# # ──────────────────────────────────────────────

# @response_bp.route("/progress/<user_id>")
# class UserProgressRoute(MethodView):

#     @response_bp.response(200, UserProgressListSchema)
#     def get(self, user_id):
#         """
#         Récupère la progression complète d'un utilisateur.

#         Query params :
#             subject_id : filtrer par matière (optionnel)
#         """
#         subject_id = request.args.get("subject_id", None)

#         if subject_id:
#             progresses = UserProgress.find_by_user_and_subject(user_id, subject_id)
#         else:
#             progresses = UserProgress.find_by_user(user_id)

#         return {
#             "user_id": user_id,
#             "competences_count": len(progresses),
#             "progresses": [UserProgress.to_dict(p) for p in progresses],
#         }


# # ──────────────────────────────────────────────
# # Historique (inchangé)
# # ──────────────────────────────────────────────

# @response_bp.route("/user/<user_id>/history")
# class UserHistory(MethodView):

#     @response_bp.response(200)
#     def get(self, user_id):
#         """Historique des réponses d'un utilisateur."""
#         limit = request.args.get("limit", 50, type=int)
#         db = mongo.db
#         responses = UserResponse.get_by_user(db, user_id, limit=limit)

#         for r in responses:
#             r["_id"] = str(r["_id"])
#             r["user_id"] = str(r["user_id"])
#             r["exercise_id"] = str(r["exercise_id"])
#             r["competence_id"] = str(r["competence_id"])
#             r["lesson_id"] = str(r["lesson_id"])

#         return {
#             "user_id": user_id,
#             "count": len(responses),
#             "responses": responses,
#         }


# # ──────────────────────────────────────────────
# # Par compétence (inchangé)
# # ──────────────────────────────────────────────

# @response_bp.route("/user/<user_id>/competence/<competence_id>")
# class UserCompetenceResponses(MethodView):

#     @response_bp.response(200)
#     def get(self, user_id, competence_id):
#         """Réponses d'un utilisateur pour une compétence."""
#         db = mongo.db
#         responses = UserResponse.get_by_user_and_competence(db, user_id, competence_id)

#         for r in responses:
#             r["_id"] = str(r["_id"])
#             r["user_id"] = str(r["user_id"])
#             r["exercise_id"] = str(r["exercise_id"])
#             r["competence_id"] = str(r["competence_id"])
#             r["lesson_id"] = str(r["lesson_id"])

#         correctness = [r["is_correct"] for r in responses]

#         return {
#             "user_id": user_id,
#             "competence_id": competence_id,
#             "count": len(responses),
#             "correctness_history": correctness,
#             "responses": responses,
#         }


# # ──────────────────────────────────────────────
# # Par leçon (inchangé)
# # ──────────────────────────────────────────────

# @response_bp.route("/user/<user_id>/lesson/<lesson_id>")
# class UserLessonResponses(MethodView):

#     @response_bp.response(200)
#     def get(self, user_id, lesson_id):
#         """Réponses d'un utilisateur pour une leçon."""
#         db = mongo.db
#         responses = UserResponse.get_by_user_and_lesson(db, user_id, lesson_id)

#         for r in responses:
#             r["_id"] = str(r["_id"])
#             r["user_id"] = str(r["user_id"])
#             r["exercise_id"] = str(r["exercise_id"])
#             r["competence_id"] = str(r["competence_id"])
#             r["lesson_id"] = str(r["lesson_id"])

#         return {
#             "user_id": user_id,
#             "lesson_id": lesson_id,
#             "count": len(responses),
#             "responses": responses,
#         }


# # ──────────────────────────────────────────────
# # Stats (inchangé)
# # ──────────────────────────────────────────────

# @response_bp.route("/user/<user_id>/stats")
# class UserGlobalStats(MethodView):

#     @response_bp.response(200)
#     def get(self, user_id):
#         """Stats globales d'un utilisateur."""
#         db = mongo.db
#         stats = UserResponse.get_user_stats(db, user_id)
#         stats["user_id"] = user_id
#         return stats


# @response_bp.route("/user/<user_id>/stats/<competence_id>")
# class UserCompetenceStats(MethodView):

#     @response_bp.response(200)
#     def get(self, user_id, competence_id):
#         """Stats d'un utilisateur pour une compétence."""
#         db = mongo.db
#         stats = UserResponse.get_user_stats(db, user_id, competence_id)
#         stats["user_id"] = user_id
#         stats["competence_id"] = competence_id
#         return stats


# # ──────────────────────────────────────────────
# # Résumé (inchangé)
# # ──────────────────────────────────────────────

# @response_bp.route("/user/<user_id>/summary")
# class UserSummary(MethodView):

#     @response_bp.response(200)
#     def get(self, user_id):
#         """Résumé de toutes les compétences travaillées."""
#         subject_id = request.args.get("subject_id", None)
#         db = mongo.db
#         summary = UserResponse.get_user_competence_summary(db, user_id, subject_id)

#         return {
#             "user_id": user_id,
#             "competences_worked": len(summary),
#             "summary": summary,
#         }


# # ──────────────────────────────────────────────
# # Supprimer (inchangé)
# # ──────────────────────────────────────────────

# @response_bp.route("/user/<user_id>")
# class DeleteUserResponses(MethodView):

#     @response_bp.response(200)
#     def delete(self, user_id):
#         """Supprime tout l'historique de réponses d'un utilisateur."""
#         db = mongo.db
#         count = UserResponse.delete_by_user(db, user_id)
#         return {
#             "message": f"{count} réponse(s) supprimée(s)",
#             "user_id": user_id,
#             "deleted_count": count,
#         }