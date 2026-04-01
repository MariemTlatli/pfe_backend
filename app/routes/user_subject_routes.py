"""
Routes UserSubject - Gestion des inscriptions utilisateur-matière.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from app.models.user_subject import UserSubject
from app.models.subject import Subject
from app.schemas.user_subject import (
    EnrollmentSchema,
    BulkEnrollSchema,
    EnrollResponseSchema,
    BulkEnrollResponseSchema,
    UserSubjectDetailSchema,
    UpdateProgressSchema
)
from app.models.competence import Competence
from app.services.graph_service import GraphService
        


blp = Blueprint(
    "UserSubjects",
    __name__,
    url_prefix="/api/user-subjects",
    description="Gestion des inscriptions utilisateur-matière"
)

@blp.route("/<string:user_id>/enroll-multiple")
class UserBulkEnroll(MethodView):
    """Inscription multiple pour un utilisateur."""
    
    @blp.arguments(BulkEnrollSchema)
    @blp.response(201, BulkEnrollResponseSchema)
    def post(self, enroll_data, user_id):
        """
        Inscrire un utilisateur à plusieurs matières.
        
        Body:
        {
            "subject_ids": ["subject1", "subject2", "subject3"]
        }
        """
        subject_ids = enroll_data['subject_ids']
        
        # Vérifier que toutes les matières existent
        for subject_id in subject_ids:
            subject = Subject.find_by_id(subject_id)
            if not subject:
                abort(404, message=f"Matière {subject_id} introuvable")
        
        # Inscription multiple
        result = UserSubject.bulk_enroll(user_id, subject_ids)
        
        return {
            **result,
            'message': f"{result['total']} inscription(s) réussie(s)"
        }


@blp.route("/<string:user_id>/subjects")
class UserSubjects(MethodView):
    """Récupérer les matières d'un utilisateur."""
    
    @blp.response(200, UserSubjectDetailSchema(many=True))
    def get(self, user_id):
        """
        Récupérer toutes les matières auxquelles un utilisateur est inscrit.
        
        Retourne les matières avec la progression détaillée.
        """
        subjects = UserSubject.get_user_subjects_with_details(user_id)
        
        return subjects


@blp.route("/<string:user_id>/subjects/<string:subject_id>")
class UserSubjectDetail(MethodView):
    """Détails d'une inscription spécifique."""
    
    @blp.response(200)
    def get(self, user_id, subject_id):
        """
        Récupérer les détails d'une matière spécifique pour un utilisateur.
        """
        
        enrollment = UserSubject.find_by_user_and_subject(user_id, subject_id)
        
        if not enrollment:
            abort(404, message="Inscription introuvable")
        
        # Récupérer la matière
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message="Matière introuvable")
        
        # Récupérer le parcours d'apprentissage
        competences = Competence.find_by_subject(subject_id)
        learning_path = GraphService.get_learning_path(competences)
        
        # Déterminer la prochaine compétence à apprendre
        completed = enrollment.get('completed_competences', [])
        completed_str = [str(c) for c in completed]
        
        next_competence = None
        for comp_id in learning_path:
            if comp_id not in completed_str:
                next_competence = Competence.find_by_id(comp_id)
                break
        
        return {
            'enrollment': UserSubject.to_dict(enrollment),
            'subject': Subject.to_dict(subject),
            'learning_path': {
                'total_steps': len(learning_path),
                'completed_steps': len(completed),
                'current_step': len(completed) + 1 if next_competence else len(learning_path),
                'next_competence': Competence.to_dict(next_competence) if next_competence else None
            },
            'progress': {
                'percentage': (len(completed) / len(learning_path) * 100) if learning_path else 0,
                'completed_competences': len(completed),
                'total_competences': len(learning_path)
            }
        }
    
    @blp.response(204)
    def delete(self, user_id, subject_id):
        """
        Désinscrire un utilisateur d'une matière.
        """
        success = UserSubject.unenroll(user_id, subject_id)
        
        if not success:
            abort(404, message="Inscription introuvable")
        
        return ''


@blp.route("/<string:user_id>/subjects/<string:subject_id>/update-progress")
class UpdateProgress(MethodView):
    """Mettre à jour la progression."""
    
    @blp.arguments(UpdateProgressSchema)
    @blp.response(200)
    def patch(self, progress_data, user_id, subject_id):
        """
        Mettre à jour la progression d'un utilisateur.
        
        Body:
        {
            "current_competence_id": "comp123",
            "progress": 45.5,
            "stats": {
                "total_lessons_completed": 10
            }
        }
        """
        enrollment = UserSubject.find_by_user_and_subject(user_id, subject_id)
        
        if not enrollment:
            abort(404, message="Inscription introuvable")
        
        success = UserSubject.update_progress(user_id, subject_id, progress_data)
        
        if not success:
            abort(500, message="Erreur lors de la mise à jour")
        
        return {
            'message': 'Progression mise à jour',
            'progress': progress_data
        }


@blp.route("/<string:user_id>/available-subjects")
class AvailableSubjects(MethodView):
    """Matières disponibles pour inscription."""
    
    @blp.response(200)
    def get(self, user_id):
        """
        Récupérer les matières auxquelles l'utilisateur n'est PAS encore inscrit.
        """
        # Récupérer toutes les matières
        all_subjects = Subject.find_all()
        
        # Récupérer les inscriptions de l'utilisateur
        enrolled_subjects = UserSubject.find_by_user(user_id)
        enrolled_ids = {str(e['subject_id']) for e in enrolled_subjects}
        
        # Filtrer les matières disponibles
        available = [
            Subject.to_dict(s) 
            for s in all_subjects 
            if str(s['_id']) not in enrolled_ids
        ]
        
        return {
            'available_subjects': available,
            'total': len(available)
        }