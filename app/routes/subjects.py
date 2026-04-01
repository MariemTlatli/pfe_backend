"""
Routes Subjects - CRUD des matières.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.models.subject import Subject
from app.models.domain import Domain
from app.models.competence import Competence
from app.schemas.subject import SubjectSchema, SubjectCreateSchema, SubjectUpdateSchema
from app.schemas.common import MessageSchema


blp = Blueprint(
    "Subjects",
    __name__,
    url_prefix="/api/subjects",
    description="Gestion des matières et sujets d'étude"
)


@blp.route("")
class SubjectList(MethodView):
    """Liste et création de matières."""
    
    @blp.response(200, SubjectSchema(many=True))
    def get(self):
        """Récupérer toutes les matières."""
        subjects = Subject.find_all()
        return [Subject.to_dict(s) for s in subjects]
    
    @blp.arguments(SubjectCreateSchema)
    @blp.response(201, SubjectSchema)
    def post(self, data):
        """Créer une nouvelle matière."""
        # Vérifier que le domaine existe
        domain = Domain.find_by_id(data['domain_id'])
        if not domain:
            abort(404, message=f"Domaine {data['domain_id']} introuvable")
        
        try:
            subject = Subject.create(
                domain_id=data['domain_id'],
                name=data['name'],
                description=data.get('description')
            )
            return Subject.to_dict(subject)
        except ValueError as e:
            abort(409, message=str(e))
        except Exception as e:
            abort(500, message=f"Erreur serveur: {str(e)}")


@blp.route("/<string:subject_id>")
class SubjectDetail(MethodView):
    """Opérations sur une matière spécifique."""
    
    @blp.response(200, SubjectSchema)
    def get(self, subject_id):
        """Récupérer une matière par ID."""
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        return Subject.to_dict(subject)
    
    @blp.arguments(SubjectUpdateSchema)
    @blp.response(200, SubjectSchema)
    def put(self, data, subject_id):
        """Mettre à jour une matière."""
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        
        updates = {k: v for k, v in data.items() if v is not None}
        if updates:
            Subject.update(subject_id, updates)
        
        subject = Subject.find_by_id(subject_id)
        return Subject.to_dict(subject)
    
    @blp.response(200, MessageSchema)
    def delete(self, subject_id):
        """Supprimer une matière et ses compétences."""
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        
        Subject.delete(subject_id)
        return {"message": f"Matière '{subject['name']}' supprimée avec succès"}


@blp.route("/<string:subject_id>/competences")
class SubjectCompetences(MethodView):
    """Compétences d'une matière."""
    
    @blp.response(200)
    def get(self, subject_id):
        """Récupérer les compétences d'une matière."""
        subject = Subject.find_by_id(subject_id)
        if not subject:
            abort(404, message=f"Matière {subject_id} introuvable")
        
        competences = Competence.find_by_subject(subject_id)
        
        return {
            "subject": Subject.to_dict(subject),
            "competences": [Competence.to_dict(c, include_prerequisites=True) for c in competences],
            "count": len(competences)
        }