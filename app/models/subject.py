"""
Modèle Subject - Matière/Sujet d'étude (ex: Python pour débutants).
"""

from app.extensions import mongo
from bson import ObjectId
from datetime import datetime


class Subject:
    """Gestion des matières/sujets d'étude."""
    
    COLLECTION = 'subjects'
    
    @staticmethod
    def create(domain_id, name, description=None):
        """
        Créer une nouvelle matière.
        
        Args:
            domain_id (str|ObjectId): ID du domaine parent
            name (str): Nom de la matière
            description (str, optional): Description
            
        Returns:
            dict: Document créé avec _id
            
        Raises:
            ValueError: Si le domaine n'existe pas
        """
        from app.models.domain import Domain
        
        # Vérifier que le domaine existe
        if not Domain.find_by_id(domain_id):
            raise ValueError(f"Le domaine {domain_id} n'existe pas")
        
        subject = {
            'domain_id': ObjectId(domain_id),
            'name': name,
            'description': description,
            'created_at': datetime.utcnow()
        }
        
        result = mongo.db[Subject.COLLECTION].insert_one(subject)
        subject['_id'] = result.inserted_id
        
        return subject
    
    @staticmethod
    def find_all():
        """Récupérer toutes les matières."""
        return list(mongo.db[Subject.COLLECTION].find().sort('name', 1))
    
    @staticmethod
    def find_by_domain(domain_id):
        """
        Trouver toutes les matières d'un domaine.
        
        Args:
            domain_id (str|ObjectId): ID du domaine
            
        Returns:
            list: Liste des matières
        """
        return list(mongo.db[Subject.COLLECTION].find(
            {'domain_id': ObjectId(domain_id)}
        ).sort('name', 1))
    
    @staticmethod
    def find_by_id(subject_id):
        """Trouver une matière par ID."""
        try:
            return mongo.db[Subject.COLLECTION].find_one({'_id': ObjectId(subject_id)})
        except Exception:
            return None
    
    @staticmethod
    def update(subject_id, updates):
        """Mettre à jour une matière."""
        result = mongo.db[Subject.COLLECTION].update_one(
            {'_id': ObjectId(subject_id)},
            {'$set': updates}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete(subject_id):
        """
        Supprimer une matière et ses compétences associées.
        
        Args:
            subject_id (str|ObjectId): ID de la matière
            
        Returns:
            bool: True si supprimé
        """
        from app.models.competence import Competence
        
        # Supprimer toutes les compétences de la matière
        competences = Competence.find_by_subject(subject_id)
        for comp in competences:
            Competence.delete(comp['_id'])
        
        # Supprimer la matière
        result = mongo.db[Subject.COLLECTION].delete_one({'_id': ObjectId(subject_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def has_curriculum(subject_id):
        """
        Vérifier si la matière a un curriculum généré.
        
        Args:
            subject_id (str|ObjectId): ID de la matière
            
        Returns:
            bool: True si des compétences existent
        """
        from app.models.competence import Competence
        return mongo.db[Competence.COLLECTION].count_documents(
            {'subject_id': ObjectId(subject_id)}
        ) > 0
    
    @staticmethod
    def count_competences(subject_id):
        """Compter le nombre de compétences dans une matière."""
        from app.models.competence import Competence
        return mongo.db[Competence.COLLECTION].count_documents(
            {'subject_id': ObjectId(subject_id)}
        )
    
    @staticmethod
    def to_dict(subject, include_domain=True, include_stats=True):
        """
        Convertir un document MongoDB en dict JSON-friendly.
        
        Args:
            subject (dict): Document MongoDB
            include_domain (bool): Inclure les infos du domaine
            include_stats (bool): Inclure les statistiques
            
        Returns:
            dict|None: Dictionnaire formaté ou None
        """
        if not subject:
            return None
        
        data = {
            'id': str(subject['_id']),
            'domain_id': str(subject['domain_id']),
            'name': subject['name'],
            'description': subject.get('description'),
            'created_at': subject['created_at'].isoformat()
        }
        
        if include_domain:
            from app.models.domain import Domain
            domain = Domain.find_by_id(subject['domain_id'])
            data['domain_name'] = domain['name'] if domain else None
        
        if include_stats:
            data['competences_count'] = Subject.count_competences(subject['_id'])
            data['has_curriculum'] = Subject.has_curriculum(subject['_id'])
        
        return data