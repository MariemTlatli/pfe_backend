"""
Routes API pour les réponses utilisateur.
Blueprint : /api/responses

Workflow :
1. Vérifier la réponse
2. ZPD (analyser la zone)
3. SAINT+ (mettre à jour la maîtrise)
4. Sauvegarder la réponse
5. Décision service (simulation LLM)
"""

from flask import request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.extensions import mongo
from app.models.exercise import Exercise
from app.models.user_response import UserResponse
from app.models.user_progress import UserProgress
from app.schemas.submission_schema import SubmitResponseWithEmotionSchema
from app.services.decision_service import DecisionService
from app.services.saint_service import SAINTService
from app.schemas.user_response import SubmitResponseSchema
from app.schemas.user_progress import UserProgressListSchema
from app.services.zpd_service import ZPDService
from bson import ObjectId
import numpy as np

response_bp = Blueprint(
    "responses_final", __name__,
    url_prefix="/api/responses",
    description="Réponses utilisateur"
)
import numpy as np
from bson import ObjectId

def to_jsonable(data):
    if isinstance(data, dict):
        return {k: to_jsonable(v) for k, v in data.items()}
    
    elif isinstance(data, list):
        return [to_jsonable(v) for v in data]
    
    elif isinstance(data, ObjectId):
        return str(data)
    
    elif isinstance(data, (np.floating,)):
        return float(data)
    
    elif isinstance(data, (np.integer,)):
        return int(data)
    
    elif isinstance(data, (np.bool_,)):
        return bool(data)
    
    else:
        return data

@response_bp.route("/submit")
class SubmitResponseWithEmotion(MethodView):

    @response_bp.arguments(SubmitResponseWithEmotionSchema, location='json')
    @response_bp.response(201)
    def post(self, data):
        """
        Workflow :
        1. Vérifier la réponse
        2. ZPD (analyser la zone avec mastery du front)
        3. SAINT+ (mettre à jour la maîtrise)
        4. Sauvegarder la réponse
        5. Décision service (simulation LLM)
        """
        db = mongo.db
        
        # ══════════════════════════════════════════════════════════
        # ── 1. DONNÉES DE BASE ──
        # ══════════════════════════════════════════════════════════
        user_id = data.get("user_id")
        exercise_id = data.get("exercise_id")
        competence_id = data.get("competence_id")
        answer = data.get("answer")
        time_spent = data.get("time_spent_seconds", 0)
        hints_used = data.get("hints_used", 0)
        emotion_data = data.get("emotion_data", {})
        
        current_mastery = data.get("currentMasteryLevel", 0.0)
        
        # ══════════════════════════════════════════════════════════
        # ── 2. VÉRIFIER LA RÉPONSE ──
        # ══════════════════════════════════════════════════════════
        exercise = Exercise.get_by_id(db, exercise_id)
        if not exercise:
            abort(404, message="Exercice non trouvé")
            
        check_result = Exercise.check_answer(exercise, answer)
        is_correct = check_result["is_correct"]
         
        # ══════════════════════════════════════════════════════════
        # ── 3. ZPD (ANALYSE ZONE AVEC MASTERY DU FRONT) ──
        # ══════════════════════════════════════════════════════════
        zpd_result = ZPDService(db).analyze_competence(
            competence_id=str(competence_id),
            mastery_level=current_mastery,
            user_id=user_id,
        )
        
        # ══════════════════════════════════════════════════════════
        # ── 4. SAINT+ (MISE À JOUR MAÎTRISE) ──
        # ══════════════════════════════════════════════════════════
        saint_result = SAINTService.update_knowledge(
            db=db,
            user_id=user_id,
            competence_id=str(competence_id),
            is_correct=is_correct,
        )

        print("zpd_result", zpd_result)
        print("mastery_level", current_mastery)
        print("saint_result", saint_result)
        
        # ══════════════════════════════════════════════════════════
        # ── 5. SAUVEGARDE DE LA RÉPONSE ──
        # ══════════════════════════════════════════════════════════
        # Créer le document de base
        response_doc = UserResponse.create(
            user_id=user_id,
            exercise_id=exercise_id,
            competence_id=competence_id,
            lesson_id=exercise.get("lesson_id"),
            answer=answer,
            is_correct=is_correct,
            time_spent=time_spent
        )
        
        # Ajouter les champs enrichis
        response_doc["hints_used"] = hints_used
        response_doc["emotion_data"] = emotion_data
        response_doc["saint_result"] = saint_result
        response_doc["zpd_result"] = zpd_result
        response_doc["mastery_before"] = current_mastery
        response_doc["user_id"] = str(user_id)
        response_doc["exercise_id"] = str(exercise_id)
        response_doc["competence_id"] = str(competence_id)
        
        # Insérer en base
        response_id = UserResponse.insert(db, response_doc)
        response_doc["_id"] = str(response_id)  # Ajouter l'ID de la rresponse_id
        
        # ══════════════════════════════════════════════════════════
        # ── 6. DÉCISION SERVICE (SIMULATION LLM) ──
        # ══════════════════════════════════════════════════════════
        # decision = DecisionService.make_decision_with_llm(
        #     user_id=user_id,
        #     competence_id=competence_id,
        #     saint_result=saint_result,
        #     zpd_result=zpd_result,
        #     emotion_data=emotion_data,
        #     is_correct=is_correct,
        #     time_spent=time_spent,
        #     hints_used=hints_used,
        # )
        
        decision = DecisionService.make_simple_decision(
            saint_result=saint_result,
            zpd_result=zpd_result,
            emotion_data=emotion_data,
            is_correct=is_correct,
            time_spent=time_spent,
            hints_used=hints_used,
        )
        
        # # Mettre à jour le document avec la décision
        db[UserResponse.collection_name].update_one(
            {"_id": response_id},
            {"$set": {"decision": decision}}
        )
        print("+++++++++++++++" *20)
        print("decision ", decision)
        print("+++++++++++++++" *20)

        # ══════════════════════════════════════════════════════════
        # ── 7. RÉPONSE FINALE ──
        # ══════════════════════════════════════════════════════════
        return to_jsonable(decision), 201

@response_bp.route("/history/<user_id>")
class UserResponseHistory(MethodView):
    """Récupérer l'historique des réponses d'un utilisateur"""
    
    @response_bp.response(200)
    def get(self, user_id):
        db = mongo.db
        
        responses = UserResponse.get_by_user(db, user_id, limit=50)
        
        # Convertir ObjectId en string
        for response in responses:
            response["_id"] = str(response["_id"])
            response["user_id"] = str(response.get("user_id", ""))
            response["exercise_id"] = str(response.get("exercise_id", ""))
            response["competence_id"] = str(response.get("competence_id", ""))
            response["lesson_id"] = str(response.get("lesson_id", ""))
            
        return {
            "user_id": user_id,
            "total_responses": len(responses),
            "responses": responses
        }


@response_bp.route("/stats/<user_id>/<competence_id>")
class CompetenceStats(MethodView):
    """Statistiques pour une compétence donnée"""
    
    @response_bp.response(200)
    def get(self, user_id, competence_id):
        db = mongo.db
        
        # Stats utilisateur pour cette compétence
        stats = UserResponse.get_user_stats(db, user_id, competence_id)
        
        if stats["total"] == 0:
            return {
                "user_id": user_id,
                "competence_id": competence_id,
                "total_attempts": 0,
                "message": "Aucune donnée disponible"
            }
        
        # Récupérer la progression actuelle
        progress = UserProgress.get_or_create(user_id, competence_id)
        
        # Récupérer la dernière prédiction SAINT+
        last_prediction = UserProgress.get_last_prediction(user_id, competence_id)
        
        return {
            "user_id": user_id,
            "competence_id": competence_id,
            "total_attempts": stats["total"],
            "correct_answers": stats["correct"],
            "incorrect_answers": stats["incorrect"],
            "success_rate": stats["success_rate"],
            "current_mastery": progress.get("mastery", 0.0),
            "exercises_completed": progress.get("exercises_completed", 0),
            "current_streak": stats["streak"],
            "best_streak": stats["best_streak"],
            "average_time": stats["avg_time"],
            "last_prediction": last_prediction,
            "source": progress.get("source", "saint+")
        }


@response_bp.route("/competence-summary/<user_id>")
class UserCompetenceSummary(MethodView):
    """Résumé de toutes les compétences d'un utilisateur"""
    
    @response_bp.response(200)
    def get(self, user_id):
        db = mongo.db
        
        # Optionnel : filtrer par matière
        subject_id = request.args.get("subject_id")
        
        summary = UserResponse.get_user_competence_summary(db, user_id, subject_id)
        
        # Enrichir avec les données de progression
        for item in summary:
            comp_id = item["competence_id"]
            progress = UserProgress.get_or_create(user_id, comp_id)
            
            item["mastery"] = progress.get("mastery", 0.0)
            item["is_mastered"] = UserProgress.is_mastered(user_id, comp_id)
            item["exercises_completed"] = progress.get("exercises_completed", 0)
            item["source"] = progress.get("source", "saint+")
        
        return {
            "user_id": user_id,
            "subject_id": subject_id,
            "total_competences": len(summary),
            "competences": summary
        }