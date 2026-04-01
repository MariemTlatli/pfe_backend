"""
Modèle UserSubject - Inscription d'un utilisateur à une matière.
"""

from app.extensions import mongo
from bson import ObjectId
from datetime import datetime


class UserSubject:
    """Gestion des inscriptions utilisateur-matière."""
    
    COLLECTION = 'user_subjects'
    
    @staticmethod
    def enroll(user_id, subject_id):
        """
        Inscrire un utilisateur à une matière.
        
        Args:
            user_id (str|ObjectId): ID de l'utilisateur
            subject_id (str|ObjectId): ID de la matière
            
        Returns:
            dict: Document d'inscription créé
            
        Raises:
            ValueError: Si déjà inscrit
        """
        # Vérifier si déjà inscrit
        existing = mongo.db[UserSubject.COLLECTION].find_one({
            'user_id': ObjectId(user_id),
            'subject_id': ObjectId(subject_id)
        })
        
        if existing:
            raise ValueError("Utilisateur déjà inscrit à cette matière")
        
        enrollment = {
            'user_id': ObjectId(user_id),
            'subject_id': ObjectId(subject_id),
            'enrolled_at': datetime.utcnow(),
            'status': 'active',  # active, paused, completed
            'progress': 0.0,  # Pourcentage de compétences maîtrisées
            'current_competence_id': None,  # Compétence en cours
            'completed_competences': [],  # IDs des compétences maîtrisées
            'stats': {
                'total_lessons_completed': 0,
                'total_exercises_completed': 0,
                'total_time_spent': 0,  # en secondes
                'average_mastery': 0.0
            }
        }
        
        result = mongo.db[UserSubject.COLLECTION].insert_one(enrollment)
        enrollment['_id'] = result.inserted_id
        
        return enrollment
    
    @staticmethod
    def bulk_enroll(user_id, subject_ids):
        """
        Inscrire un utilisateur à plusieurs matières.
        
        Args:
            user_id (str|ObjectId): ID de l'utilisateur
            subject_ids (list): Liste d'IDs de matières
            
        Returns:
            dict: {
                'enrolled': [...],
                'already_enrolled': [...],
                'total': int
            }
        """
        enrolled = []
        already_enrolled = []
        
        for subject_id in subject_ids:
            try:
                enrollment = UserSubject.enroll(user_id, subject_id)
                enrolled.append({
                    'subject_id': str(subject_id),
                    'enrollment_id': str(enrollment['_id'])
                })
            except ValueError:
                already_enrolled.append(str(subject_id))
        
        return {
            'enrolled': enrolled,
            'already_enrolled': already_enrolled,
            'total': len(enrolled)
        }
    
    @staticmethod
    def unenroll(user_id, subject_id):
        """
        Désinscrire un utilisateur d'une matière.
        
        Args:
            user_id (str|ObjectId): ID de l'utilisateur
            subject_id (str|ObjectId): ID de la matière
            
        Returns:
            bool: True si désinscrit
        """
        result = mongo.db[UserSubject.COLLECTION].delete_one({
            'user_id': ObjectId(user_id),
            'subject_id': ObjectId(subject_id)
        })
        
        return result.deleted_count > 0
    
    @staticmethod
    def find_by_user(user_id):
        """
        Récupérer toutes les inscriptions d'un utilisateur.
        
        Args:
            user_id (str|ObjectId): ID de l'utilisateur
            
        Returns:
            list: Liste des inscriptions
        """
        return list(mongo.db[UserSubject.COLLECTION].find(
            {'user_id': ObjectId(user_id)}
        ).sort('enrolled_at', -1))
    
    @staticmethod
    def find_by_user_and_subject(user_id, subject_id):
        """
        Trouver une inscription spécifique.
        
        Args:
            user_id (str|ObjectId): ID de l'utilisateur
            subject_id (str|ObjectId): ID de la matière
            
        Returns:
            dict|None: Document d'inscription ou None
        """
        return mongo.db[UserSubject.COLLECTION].find_one({
            'user_id': ObjectId(user_id),
            'subject_id': ObjectId(subject_id)
        })
    
    @staticmethod
    def is_enrolled(user_id, subject_id):
        """
        Vérifier si un utilisateur est inscrit à une matière.
        
        Args:
            user_id (str|ObjectId): ID de l'utilisateur
            subject_id (str|ObjectId): ID de la matière
            
        Returns:
            bool: True si inscrit
        """
        return UserSubject.find_by_user_and_subject(user_id, subject_id) is not None
    
    @staticmethod
    def update_progress(user_id, subject_id, progress_data):
        """
        Mettre à jour la progression d'un utilisateur.
        
        Args:
            user_id (str|ObjectId): ID de l'utilisateur
            subject_id (str|ObjectId): ID de la matière
            progress_data (dict): Données de progression
            
        Returns:
            bool: True si mis à jour
        """
        result = mongo.db[UserSubject.COLLECTION].update_one(
            {
                'user_id': ObjectId(user_id),
                'subject_id': ObjectId(subject_id)
            },
            {
                '$set': {
                    **progress_data,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def get_user_subjects_with_details(user_id):
        """
        Récupérer les matières d'un utilisateur avec tous les détails.
        
        Args:
            user_id (str|ObjectId): ID de l'utilisateur
            
        Returns:
            list: Liste des matières avec progression
        """
        from app.models.subject import Subject
        from app.models.competence import Competence
        
        enrollments = UserSubject.find_by_user(user_id)

        result = []
        for enrollment in enrollments:
            subject = Subject.find_by_id(enrollment['subject_id'])
            if not subject:
                continue
            
            # Récupérer les compétences
            competences = Competence.find_by_subject(enrollment['subject_id'])
            total_competences = len(competences)
            completed_competences = len(enrollment.get('completed_competences', []))
            
            result.append({
                'enrollment_id': str(enrollment['_id']),
                'subject': Subject.to_dict(subject),
                'enrolled_at': enrollment['enrolled_at'],
                'status': enrollment.get('status', 'active'),
                'progress': {
                    'percentage': enrollment.get('progress', 0.0),
                    'completed_competences': completed_competences,
                    'total_competences': total_competences
                },
                'current_competence_id': str(enrollment['current_competence_id']) if enrollment.get('current_competence_id') else None,
                'stats': enrollment.get('stats', {})
            })
        
        return result
    
    @staticmethod
    def to_dict(enrollment):
        """
        Convertir un document MongoDB en dict JSON-friendly.
        
        Args:
            enrollment (dict): Document MongoDB
            
        Returns:
            dict|None: Dictionnaire formaté ou None
        """
        if not enrollment:
            return None
        
        return {
            'id': str(enrollment['_id']),
            'user_id': str(enrollment['user_id']),
            'subject_id': str(enrollment['subject_id']),
            'enrolled_at': enrollment['enrolled_at'].isoformat(),
            'status': enrollment.get('status', 'active'),
            'progress': enrollment.get('progress', 0.0),
            'current_competence_id': str(enrollment['current_competence_id']) if enrollment.get('current_competence_id') else None,
            'completed_competences': [str(c) for c in enrollment.get('completed_competences', [])],
            'stats': enrollment.get('stats', {})
        }