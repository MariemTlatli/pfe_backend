# app/models/competence.py
from bson import ObjectId
from datetime import datetime
from app.extensions import mongo

class Competence:
    """
    Modèle Competence étendu avec attributs ZPD.
    
    Nouveaux champs :
    - zpd_thresholds : seuils définissant les zones d'apprentissage
    - difficulty_params : paramètres de difficulté pour la génération d'exercices
    
    Zones ZPD :
    - MASTERED (maîtrisé)     : mastery >= seuil_mastered (0.85)
    - ZPD (zone optimale)     : seuil_learning <= mastery < seuil_mastered
    - FRUSTRATION (trop dur)  : mastery < seuil_learning (0.40)
    """

    COLLECTION = 'competences'
    collection_name = "competences"

    # ──────────────────────────────────────────────
    # Constantes ZPD
    # ──────────────────────────────────────────────
    ZONE_MASTERED = "mastered"
    ZONE_ZPD = "zpd"
    ZONE_FRUSTRATION = "frustration"

    DEFAULT_ZPD_THRESHOLDS = {
        "mastered": 0.85,   # Au-dessus → compétence acquise
        "learning": 0.40,   # Entre learning et mastered → ZPD (zone optimale)
        # En-dessous de learning → zone de frustration
    }

    DEFAULT_DIFFICULTY_PARAMS = {
        "base_difficulty": 0.5,   # Difficulté intrinsèque (0.0 - 1.0)
        "weight": 1.0,            # Poids/importance dans le curriculum
        "min_exercises": 3,       # Exercices minimum avant validation
        "mastery_exercises": 5,   # Exercices pour maîtrise complète
    }

    # ──────────────────────────────────────────────
    # Mapping difficulté → types d'exercices
    # ──────────────────────────────────────────────
    EXERCISE_TYPES_BY_ZONE = {
        ZONE_FRUSTRATION: ["qcm", "vrai_faux", "texte_a_trous"],
        ZONE_ZPD: ["qcm_multiple", "code_completion", "exercice_guide"],
        ZONE_MASTERED: ["code_libre", "debugging", "projet_mini"],
    }

    # ──────────────────────────────────────────────
    # CRUD
    # ──────────────────────────────────────────────

    @staticmethod
    def create(subject_id, code, name, description, level=0,
               graph_data=None, prerequisites=None,
               zpd_thresholds=None, difficulty_params=None):
        """
        Crée un document competence avec attributs ZPD.
        
        Args:
            subject_id: ID de la matière
            code: Code unique (ex: "VAR001")
            name: Nom de la compétence
            description: Description
            level: Profondeur dans le graphe (calculé automatiquement)
            graph_data: Position visuelle {"x": int, "y": int}
            prerequisites: Liste de prérequis [{"competence_id": ObjectId, "strength": float}]
            zpd_thresholds: Seuils ZPD personnalisés (optionnel)
            difficulty_params: Paramètres de difficulté personnalisés (optionnel)
            
        Returns:
            dict: Document prêt pour insertion MongoDB
        """
        doc = {
        "subject_id": ObjectId(subject_id) if isinstance(subject_id, str) else subject_id,
        "code": code,
        "name": name,
        "description": description,
        "level": level,
        "graph_data": graph_data or {"x": 0, "y": 0},
        "prerequisites": prerequisites or [],
        "zpd_thresholds": zpd_thresholds or Competence.DEFAULT_ZPD_THRESHOLDS.copy(),
        "difficulty_params": difficulty_params or Competence.DEFAULT_DIFFICULTY_PARAMS.copy(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

        # ✅ INSERTION MongoDB
        result = mongo.db[Competence.COLLECTION].insert_one(doc)

        # ✅ Ajouter _id au document retourné
        doc["_id"] = result.inserted_id

        return doc
    @staticmethod
    def count_lessons(competence_id):
        """
        Compte le nombre de leçons pour une compétence.
        
        Args:
            competence_id: ID de la compétence
            
        Returns:
            int: Nombre de leçons
        """
        from app.models.lesson import Lesson  # Import local pour éviter circular import
        
        lessons = Lesson.find_by_competence(competence_id)
        return len(lessons)

    @staticmethod
    def has_lessons(competence_id):
        """
        Vérifie si une compétence a des leçons.
        
        Args:
            competence_id: ID de la compétence
            
        Returns:
            bool: True si au moins une leçon existe
        """
        return Competence.count_lessons(competence_id) > 0
    @staticmethod
    def get_by_id(competence_id):
        """Récupère une compétence par ID"""
        return mongo.db[Competence.COLLECTION].find_one({
            "_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        })

    @staticmethod
    def get_by_subject(subject_id):
        """Récupère toutes les compétences d'une matière"""
        return list(mongo.db[Competence.COLLECTION].find({
            "subject_id": ObjectId(subject_id) if isinstance(subject_id, str) else subject_id
        }))

    @staticmethod
    def get_by_code(subject_id, code):
        """Récupère une compétence par son code dans une matière"""
        return mongo.db[Competence.COLLECTION].find_one({
            "subject_id": ObjectId(subject_id) if isinstance(subject_id, str) else subject_id,
            "code": code
        })

    @staticmethod
    def insert(competence_doc):
        """Insère une compétence en base"""
        result = mongo.db[Competence.COLLECTION].insert_one(competence_doc)
        return result.inserted_id

    @staticmethod
    def update_level(competence_id, level):
        """Met à jour le niveau d'une compétence"""
        return mongo.db[Competence.COLLECTION].update_one(
            {"_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id},
            {"$set": {"level": level, "updated_at": datetime.utcnow()}}
        )

    @staticmethod
    def update_graph_data(competence_id, graph_data):
        """Met à jour les données graphiques d'une compétence"""
        return mongo.db[Competence.COLLECTION].update_one(
            {"_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id},
            {"$set": {"graph_data": graph_data, "updated_at": datetime.utcnow()}}
        )

    @staticmethod
    def update(competence_id, update_fields):
        """Met à jour des champs d'une compétence (wrapper utilisant mongo.db)"""
        update_fields["updated_at"] = datetime.utcnow()
        result = mongo.db[Competence.COLLECTION].update_one(
            {"_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id},
            {"$set": update_fields}
        )
        return result.modified_count > 0

    @staticmethod
    def delete(competence_id):
        """Supprime une seule compétence"""
        result = mongo.db[Competence.COLLECTION].delete_one({
            "_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        })
        return result.deleted_count > 0

    @staticmethod
    def delete_by_subject(subject_id):
        """Supprime toutes les compétences d'une matière"""
        result = mongo.db[Competence.COLLECTION].delete_many({
            "subject_id": ObjectId(subject_id) if isinstance(subject_id, str) else subject_id
        })
        return result.deleted_count

    # ──────────────────────────────────────────────
    # Wrapper methods for simpler usage (using mongo.db)
    # ──────────────────────────────────────────────

    @staticmethod
    def find_by_id(competence_id):
        """Trouver une compétence par ID (wrapper utilisant mongo.db)"""
        try:
            return mongo.db[Competence.COLLECTION].find_one({
                "_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
            })
        except Exception:
            return None

    @staticmethod
    def find_by_subject(subject_id):
        """Trouver toutes les compétences d'une matière (wrapper utilisant mongo.db)"""
        try:
            return list(mongo.db[Competence.COLLECTION].find({
                "subject_id": ObjectId(subject_id) if isinstance(subject_id, str) else subject_id
            }).sort("level", 1))
        except Exception:
            return []

    @staticmethod
    def find_by_code(subject_id, code):
        """Trouver une compétence par son code (wrapper utilisant mongo.db)"""
        try:
            return mongo.db[Competence.COLLECTION].find_one({
                "subject_id": ObjectId(subject_id) if isinstance(subject_id, str) else subject_id,
                "code": code
            })
        except Exception:
            return None

    @staticmethod
    def find_all():
        """Trouver toutes les compétences (wrapper utilisant mongo.db)"""
        try:
            return list(mongo.db[Competence.COLLECTION].find())
        except Exception:
            return []

    @staticmethod
    def to_dict(competence, include_prerequisites=False):
        """
        Convertir un document MongoDB en dict JSON-friendly.
        
        Args:
            competence (dict): Document MongoDB
            include_prerequisites (bool): Inclure les prérequis détaillés
            
        Returns:
            dict|None: Dictionnaire formaté ou None
        """
        if not competence:
            return None
        # ✅ NOUVEAU : Compter les leçons
        lessons_count = Competence.count_lessons(competence['_id'])
        data = {
            'id': str(competence['_id']),
            'subject_id': str(competence['subject_id']),
            'code': competence['code'],
            'name': competence['name'],
            'description': competence['description'],
            'level': competence.get('level', 0),
            'graph_data': competence.get('graph_data', {"x": 0, "y": 0}),
            'zpd_thresholds': competence.get('zpd_thresholds', Competence.DEFAULT_ZPD_THRESHOLDS.copy()),
            'difficulty_params': competence.get('difficulty_params', Competence.DEFAULT_DIFFICULTY_PARAMS.copy()),
            'created_at': competence['created_at'],
            'has_lessons': lessons_count > 0,
            'lessons_count': lessons_count,
        }
        
        if include_prerequisites:
            prerequisites = competence.get('prerequisites', [])
            data['prerequisites'] = []
            for prereq in prerequisites:
                prereq_comp = Competence.find_by_id(prereq['competence_id'])
                if prereq_comp:
                    data['prerequisites'].append({
                        'competence_id': str(prereq['competence_id']),
                        'competence_code': prereq_comp.get('code'),
                        'competence_name': prereq_comp.get('name'),
                        'strength': prereq.get('strength', 1.0)
                    })
        else:
            data['prerequisites'] = [
                {
                    'competence_id': str(p['competence_id']),
                    'strength': p.get('strength', 1.0)
                }
                for p in competence.get('prerequisites', [])
            ]
        
        return data

    # ──────────────────────────────────────────────
    # Prérequis
    # ──────────────────────────────────────────────

    @staticmethod
    def add_prerequisite(competence_id, prerequisite_id, strength=1.0):
        """Ajoute un prérequis à une compétence (wrapper utilisant mongo.db)"""
        result = mongo.db[Competence.COLLECTION].update_one(
            {"_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id},
            {
                "$push": {
                    "prerequisites": {
                        "competence_id": ObjectId(prerequisite_id) if isinstance(prerequisite_id, str) else prerequisite_id,
                        "strength": min(max(strength, 0.0), 1.0)
                    }
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    @staticmethod
    def remove_prerequisite(competence_id, prerequisite_id):
        """Supprime un prérequis spécifique"""
        result = mongo.db[Competence.COLLECTION].update_one(
            {"_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id},
            {
                "$pull": {
                    "prerequisites": {
                        "competence_id": ObjectId(prerequisite_id) if isinstance(prerequisite_id, str) else prerequisite_id
                    }
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    @staticmethod
    def clear_prerequisites(competence_id):
        """Supprime tous les prérequis d'une compétence"""
        result = mongo.db[Competence.COLLECTION].update_one(
            {"_id": ObjectId(competence_id) if isinstance(competence_id, str) else competence_id},
            {
                "$set": {
                    "prerequisites": [],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    @staticmethod
    def get_prerequisites_competences(competence_id):
        """Récupère les documents complets des prérequis"""
        competence = Competence.find_by_id(competence_id)
        if not competence or not competence.get("prerequisites"):
            return []

        prereq_ids = [p["competence_id"] for p in competence["prerequisites"]]
        return list(mongo.db[Competence.COLLECTION].find({"_id": {"$in": prereq_ids}}))

    @staticmethod
    def get_dependents(competence_id):
        """Récupère les compétences qui dépendent de celle-ci"""
        comp_id = ObjectId(competence_id) if isinstance(competence_id, str) else competence_id
        return list(mongo.db[Competence.COLLECTION].find({
            "prerequisites.competence_id": comp_id
        }))

    # ──────────────────────────────────────────────
    # ZPD — Classification et difficulté
    # ──────────────────────────────────────────────

    @staticmethod
    def classify_zone(mastery_level, zpd_thresholds=None):
        """
        Classifie un niveau de maîtrise dans une zone ZPD.
        
        Args:
            mastery_level: float [0.0, 1.0] — probabilité de maîtrise (depuis BKT)
            zpd_thresholds: dict avec 'mastered' et 'learning' (optionnel)
            
        Returns:
            str: ZONE_MASTERED, ZONE_ZPD, ou ZONE_FRUSTRATION
            
        Exemple:
            >>> Competence.classify_zone(0.90)
            'mastered'
            >>> Competence.classify_zone(0.55)
            'zpd'
            >>> Competence.classify_zone(0.20)
            'frustration'
        """
        thresholds = zpd_thresholds or Competence.DEFAULT_ZPD_THRESHOLDS

        if mastery_level >= thresholds["mastered"]:
            return Competence.ZONE_MASTERED
        elif mastery_level >= thresholds["learning"]:
            return Competence.ZONE_ZPD
        else:
            return Competence.ZONE_FRUSTRATION

    @staticmethod
    def get_optimal_difficulty(mastery_level, difficulty_params=None):
        """
        Calcule la difficulté optimale d'exercice selon la maîtrise actuelle.
        Principe ZPD : cibler légèrement au-dessus du niveau actuel.
        
        Args:
            mastery_level: float [0.0, 1.0]
            difficulty_params: dict avec 'base_difficulty' (optionnel)
            
        Returns:
            float: difficulté optimale [0.1, 1.0]
            
        Logique :
            - Zone frustration : difficulté = mastery + 0.10 (petit stretch)
            - Zone ZPD         : difficulté = mastery + 0.15 (stretch optimal)
            - Zone maîtrisée   : difficulté = mastery + 0.05 (maintien/challenge)
        """
        params = difficulty_params or Competence.DEFAULT_DIFFICULTY_PARAMS
        base = params["base_difficulty"]
        zone = Competence.classify_zone(mastery_level)

        stretch_map = {
            Competence.ZONE_FRUSTRATION: 0.10,
            Competence.ZONE_ZPD: 0.15,
            Competence.ZONE_MASTERED: 0.05,
        }
        stretch = stretch_map[zone]

        optimal = mastery_level + stretch

        # Borner par la difficulté de base
        optimal = max(optimal, base * 0.5)
        optimal = min(optimal, base * 1.5)

        # Borner globalement
        optimal = max(0.1, min(1.0, optimal))

        return round(optimal, 3)

    @staticmethod
    def get_exercise_types(mastery_level, zpd_thresholds=None):
        """
        Retourne les types d'exercices adaptés à la zone de l'élève.
        
        Args:
            mastery_level: float [0.0, 1.0]
            zpd_thresholds: dict (optionnel)
            
        Returns:
            list[str]: types d'exercices recommandés
            
        Exemple:
            >>> Competence.get_exercise_types(0.20)
            ['qcm', 'vrai_faux', 'texte_a_trous']
            >>> Competence.get_exercise_types(0.60)
            ['qcm_multiple', 'code_completion', 'exercice_guide']
            >>> Competence.get_exercise_types(0.90)
            ['code_libre', 'debugging', 'projet_mini']
        """
        zone = Competence.classify_zone(mastery_level, zpd_thresholds)
        return Competence.EXERCISE_TYPES_BY_ZONE[zone]

    @staticmethod
    def get_zpd_analysis(competence_id, mastery_level):
        """
        Analyse ZPD complète pour une compétence et un niveau de maîtrise donné.
        """
        competence = Competence.find_by_id(competence_id)
        if not competence:
            return None

        thresholds = competence.get("zpd_thresholds", Competence.DEFAULT_ZPD_THRESHOLDS)
        diff_params = competence.get("difficulty_params", Competence.DEFAULT_DIFFICULTY_PARAMS)

        zone = Competence.classify_zone(mastery_level, thresholds)
        optimal_diff = Competence.get_optimal_difficulty(mastery_level, diff_params)
        exercise_types = Competence.get_exercise_types(mastery_level, thresholds)

        # Analyse des prérequis
        prereqs = competence.get("prerequisites", [])
        prereq_info = []
        for p in prereqs:
            prereq_comp = Competence.find_by_id(p["competence_id"])
            if prereq_comp:
                prereq_info.append({
                    "competence_id": str(p["competence_id"]),
                    "code": prereq_comp["code"],
                    "name": prereq_comp["name"],
                    "strength": p["strength"],
                })

        return {
            "competence_id": str(competence["_id"]),
            "code": competence["code"],
            "name": competence["name"],
            "level": competence.get("level", 0),
            "mastery_level": mastery_level,
            "zone": zone,
            "zone_label": {
                Competence.ZONE_MASTERED: "Maîtrisé — Prêt pour la suite",
                Competence.ZONE_ZPD: "Zone Proximale — Apprentissage optimal",
                Competence.ZONE_FRUSTRATION: "Trop difficile — Renforcer les bases",
            }[zone],
            "optimal_difficulty": optimal_diff,
            "recommended_exercise_types": exercise_types,
            "thresholds": thresholds,
            "difficulty_params": diff_params,
            "prerequisites": prereq_info,
            "is_ready_to_learn": zone != Competence.ZONE_FRUSTRATION,
        }

    # ──────────────────────────────────────────────
    # ZPD — Mise à jour des seuils
    # ──────────────────────────────────────────────

    @staticmethod
    def update_zpd_thresholds(competence_id, mastered=None, learning=None):
        """
        Met à jour les seuils ZPD d'une compétence.
        """
        competence = Competence.find_by_id(competence_id)
        if not competence:
            return False

        thresholds = competence.get("zpd_thresholds", Competence.DEFAULT_ZPD_THRESHOLDS.copy())

        if mastered is not None:
            thresholds["mastered"] = min(max(mastered, 0.0), 1.0)
        if learning is not None:
            thresholds["learning"] = min(max(learning, 0.0), 1.0)

        # Validation : learning < mastered
        if thresholds["learning"] >= thresholds["mastered"]:
            thresholds["learning"] = thresholds["mastered"] - 0.1

        return Competence.update(competence_id, {"zpd_thresholds": thresholds})

    @staticmethod
    def update_difficulty_params(competence_id, **kwargs):
        """
        Met à jour les paramètres de difficulté.
        
        Args:
            db: connexion MongoDB
            competence_id: ID
            **kwargs: base_difficulty, weight, min_exercises, mastery_exercises
            
        Returns:
            bool: True si mis à jour
        """
        competence = Competence.find_by_id(competence_id)
        if not competence:
            return False

        params = competence.get("difficulty_params", Competence.DEFAULT_DIFFICULTY_PARAMS.copy())

        allowed_keys = {"base_difficulty", "weight", "min_exercises", "mastery_exercises"}
        for key, value in kwargs.items():
            if key in allowed_keys:
                params[key] = value

        # Validation
        params["base_difficulty"] = min(max(params["base_difficulty"], 0.0), 1.0)
        params["weight"] = max(params["weight"], 0.1)
        params["min_exercises"] = max(int(params["min_exercises"]), 1)
        params["mastery_exercises"] = max(int(params["mastery_exercises"]), params["min_exercises"])

        return Competence.update(db, competence_id, {"difficulty_params": params})