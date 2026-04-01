"""
Routes Lessons - Génération et gestion des leçons.
"""

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from app.models.competence import Competence
from app.models.lesson import Lesson
from app.services.lesson_service import LessonService
from app.services.ollama_service import OllamaService
from app.schemas.lesson import (
    LessonSchema, 
    LessonCreateSchema, 
    LessonGenerateSchema,
    LessonsResponseSchema
)
from app.schemas.common import MessageSchema


blp = Blueprint(
    "Lessons",
    __name__,
    url_prefix="/api/lessons",
    description="Gestion et génération des leçons"
)


@blp.route("/generate/<string:competence_id>")
class LessonGenerate(MethodView):
    """Génération de leçons pour une compétence."""
    
    @blp.arguments(LessonGenerateSchema, location="query")
    @blp.response(201)
    def post(self, args, competence_id):
        """
        Générer les leçons pour une compétence avec Ollama.
        
        Crée automatiquement des leçons progressives :
        - Introduction et concepts de base
        - Approfondissement avec exemples
        - Synthèse et cas pratiques
        """
        # Vérifier que la compétence existe
        competence = Competence.find_by_id(competence_id)
        if not competence:
            abort(404, message=f"Compétence {competence_id} introuvable")
        
        # Vérifier qu'Ollama est disponible
        if not OllamaService.is_available():
            abort(503, message="Service Ollama indisponible. Vérifiez que Ollama est lancé.")
        
        regenerate = args.get('regenerate', False)
        
        try:
            if regenerate:
                lessons = LessonService.regenerate_for_competence(competence_id)
            else:
                lessons = LessonService.generate_for_competence(competence_id)
            
            return {
                "lessons": lessons,
                "competence": Competence.to_dict(competence),
                "count": len(lessons)
            }
        
        except ValueError as e:
            abort(409, message=str(e))
        except Exception as e:
            abort(500, message=f"Erreur de génération: {str(e)}")


@blp.route("/competence/<string:competence_id>")
class LessonsByCompetence(MethodView):
    """Leçons d'une compétence."""
    
    @blp.response(200)
    def get(self, competence_id):
        """Récupérer toutes les leçons d'une compétence."""
        competence = Competence.find_by_id(competence_id)
        if not competence:
            abort(404, message=f"Compétence {competence_id} introuvable")
        
        lessons = Lesson.find_by_competence(competence_id)
        
        return {
            "competence": Competence.to_dict(competence),
            "lessons": [Lesson.to_dict(l) for l in lessons],
            "count": len(lessons),
            "has_lessons": len(lessons) > 0
        }
    
    @blp.arguments(LessonCreateSchema)
    @blp.response(201, LessonSchema)
    def post(self, data, competence_id):
        """Créer manuellement une leçon pour une compétence."""
        competence = Competence.find_by_id(competence_id)
        if not competence:
            abort(404, message=f"Compétence {competence_id} introuvable")
        
        # Déterminer l'ordre
        existing_lessons = Lesson.find_by_competence(competence_id)
        order = data.get('order', len(existing_lessons) + 1)
        
        try:
            lesson = Lesson.create(
                competence_id=competence_id,
                title=data['title'],
                content=data['content'],
                order_index=order,
                estimated_time=data.get('estimated_time')
            )
            return Lesson.to_dict(lesson)
        except Exception as e:
            abort(500, message=f"Erreur création: {str(e)}")


@blp.route("/<string:lesson_id>")
class LessonDetail(MethodView):
    """Opérations sur une leçon spécifique."""
    
    @blp.response(200, LessonSchema)
    def get(self, lesson_id):
        """Récupérer une leçon par ID."""
        lesson = Lesson.find_by_id(lesson_id)
        if not lesson:
            abort(404, message=f"Leçon {lesson_id} introuvable")
        return Lesson.to_dict(lesson)
    
    @blp.arguments(LessonCreateSchema)
    @blp.response(200, LessonSchema)
    def put(self, data, lesson_id):
        """Mettre à jour une leçon."""
        lesson = Lesson.find_by_id(lesson_id)
        if not lesson:
            abort(404, message=f"Leçon {lesson_id} introuvable")
        
        updates = {}
        if 'title' in data:
            updates['title'] = data['title']
        if 'content' in data:
            updates['content'] = data['content']
        if 'order' in data:
            updates['order_index'] = data['order']
        if 'estimated_time' in data:
            updates['estimated_time'] = data['estimated_time']
        
        if updates:
            Lesson.update(lesson_id, updates)
        
        lesson = Lesson.find_by_id(lesson_id)
        return Lesson.to_dict(lesson)
    
    @blp.response(200, MessageSchema)
    def delete(self, lesson_id):
        """Supprimer une leçon."""
        lesson = Lesson.find_by_id(lesson_id)
        if not lesson:
            abort(404, message=f"Leçon {lesson_id} introuvable")
        
        Lesson.delete(lesson_id)
        return {"message": f"Leçon '{lesson['title']}' supprimée avec succès"}