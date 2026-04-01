"""
Modèle Lesson - Leçon/Contenu pédagogique.
"""

from app.extensions import mongo
from bson import ObjectId
from datetime import datetime


class Lesson:
    """Gestion des leçons (contenu pédagogique)."""
    
    COLLECTION = 'lessons'
    
    @staticmethod
    def create(competence_id, title, content, order_index, estimated_time=None):
        """
        Créer une nouvelle leçon.
        
        Args:
            competence_id (str|ObjectId): ID de la compétence
            title (str): Titre de la leçon
            content (str): Contenu (Markdown)
            order_index (int): Ordre d'affichage
            estimated_time (int, optional): Temps estimé en minutes
            
        Returns:
            dict: Document créé
        """
        lesson = {
            'competence_id': ObjectId(competence_id),
            'title': title,
            'content': content,
            'order_index': order_index,
            'estimated_time': estimated_time,
            'created_at': datetime.utcnow()
        }
        
        result = mongo.db[Lesson.COLLECTION].insert_one(lesson)
        lesson['_id'] = result.inserted_id
        
        return lesson
    
    @staticmethod
    def bulk_create(lessons_list):
        """
        Créer plusieurs leçons en une fois.
        
        Args:
            lessons_list (list): Liste de dicts de leçons
            
        Returns:
            list: IDs des leçons créées
        """
        for lesson in lessons_list:
            lesson['created_at'] = datetime.utcnow()
            if 'competence_id' in lesson and not isinstance(lesson['competence_id'], ObjectId):
                lesson['competence_id'] = ObjectId(lesson['competence_id'])
        
        result = mongo.db[Lesson.COLLECTION].insert_many(lessons_list)
        return result.inserted_ids
    
    @staticmethod
    def find_by_competence(competence_id):
        """
        Trouver toutes les leçons d'une compétence (triées par ordre).
        
        Args:
            competence_id (str|ObjectId): ID de la compétence
            
        Returns:
            list: Liste des leçons triées
        """
        return list(mongo.db[Lesson.COLLECTION].find(
            {'competence_id': ObjectId(competence_id)}
        ).sort('order_index', 1))
    
    @staticmethod
    def find_by_id(lesson_id):
        """Trouver une leçon par ID."""
        try:
            return mongo.db[Lesson.COLLECTION].find_one({'_id': ObjectId(lesson_id)})
        except Exception:
            return None
    
    @staticmethod
    def update(lesson_id, updates):
        """Mettre à jour une leçon."""
        result = mongo.db[Lesson.COLLECTION].update_one(
            {'_id': ObjectId(lesson_id)},
            {'$set': updates}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete(lesson_id):
        """Supprimer une leçon."""
        result = mongo.db[Lesson.COLLECTION].delete_one({'_id': ObjectId(lesson_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def delete_by_competence(competence_id):
        """Supprimer toutes les leçons d'une compétence."""
        result = mongo.db[Lesson.COLLECTION].delete_many(
            {'competence_id': ObjectId(competence_id)}
        )
        return result.deleted_count
    
    @staticmethod
    def to_dict(lesson):
        """
        Convertir un document MongoDB en dict JSON-friendly.
        
        Args:
            lesson (dict): Document MongoDB
            
        Returns:
            dict|None: Dictionnaire formaté ou None
        """
        if not lesson:
            return None
        
        return {
            'id': str(lesson['_id']),
            'competence_id': str(lesson['competence_id']),
            'title': lesson['title'],
            'content': lesson['content'],
            'order': lesson['order_index'],
            'estimated_time': lesson.get('estimated_time'),
            'created_at': lesson['created_at'].isoformat()
        }