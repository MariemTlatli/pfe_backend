"""
Service Lesson - Génération de leçons avec Ollama.
"""

from app.services.ollama_service import OllamaService
from app.models.competence import Competence
from app.models.lesson import Lesson
from app.config import Config


class LessonService:
    """Génération de leçons pédagogiques avec GenAI."""
    
    @staticmethod
    def generate_for_competence(competence_id):
        print("\n========== GENERATE LESSONS ==========")
        print(f"[DEBUG] competence_id: {competence_id}")

        # Vérifier que la compétence existe
        competence = Competence.find_by_id(competence_id)
        print(f"[DEBUG] competence found: {competence}")

        if not competence:
            print("[ERROR] Competence not found")
            raise ValueError(f"Compétence {competence_id} introuvable")
        
        # Vérifier si leçons déjà générées
        existing = Lesson.find_by_competence(competence_id)
        print(f"[DEBUG] existing lessons count: {len(existing)}")

        if existing:
            print("[ERROR] Lessons already exist")
            raise ValueError(f"Leçons déjà générées pour cette compétence ({len(existing)} leçons)")
        
        # Construire le prompt
        print("[DEBUG] Building prompt...")
        prompt = LessonService._build_lessons_prompt(competence)
        print(f"[DEBUG] Prompt preview (first 300 chars):\n{prompt[:300]}")

        # Appeler Ollama
        try:
            print("[DEBUG] Calling Ollama...")
            response_data = OllamaService.generate_json(prompt, temperature=0.5)
            print(f"[DEBUG] Ollama response: {response_data}")
        except Exception as e:
            print(f"[ERROR] Ollama failed: {e}")
            raise Exception(f"Erreur lors de la génération avec Ollama: {str(e)}")
        
        # Valider la structure
        print("[DEBUG] Validating response structure...")
        if 'lessons' not in response_data:
            print("[ERROR] 'lessons' key missing in response")
            raise ValueError("Format de réponse invalide (manque 'lessons')")
        
        lessons_data = response_data['lessons']
        print(f"[DEBUG] lessons_data count: {len(lessons_data)}")
        
        # Limiter le nombre de leçons
        max_lessons = Config.MAX_LESSONS_PER_COMPETENCE
        print(f"[DEBUG] max_lessons: {max_lessons}")

        if len(lessons_data) > max_lessons:
            print("[DEBUG] Truncating lessons_data")
            lessons_data = lessons_data[:max_lessons]
        
        # Créer les leçons
        created_lessons = []
        print("[DEBUG] Creating lessons in DB...")

        for i, lesson_data in enumerate(lessons_data, start=1):
            print(f"[DEBUG] Lesson {i}: {lesson_data}")

            lesson = Lesson.create(
                competence_id=competence_id,
                title=lesson_data['title'],
                content=lesson_data['content'],
                order_index=i,
                estimated_time=lesson_data.get('estimated_time', 15)
            )
            print(f"[DEBUG] Lesson created with ID: {lesson.get('_id')}")

            created_lessons.append(lesson)
        
        print("[DEBUG] All lessons created successfully")

        return [Lesson.to_dict(l) for l in created_lessons]
    
    @staticmethod
    def _build_lessons_prompt(competence):
        """
        Construire le prompt pour générer les leçons.
        
        Args:
            competence (dict): Document de la compétence
            
        Returns:
            str: Prompt formaté
        """
        max_lessons = Config.MAX_LESSONS_PER_COMPETENCE
        
        # Récupérer les prérequis
        prerequisites = Competence.get_prerequisites_competences(competence['_id'])
        prereq_text = ""
        if prerequisites:
            prereq_text = "\n**Prérequis supposés maîtrisés** :\n"
            for prereq in prerequisites:
                prereq_text += f"- {prereq['name']}\n"
        
        prompt = f"""Tu es un expert pédagogique. Crée un cours progressif pour la compétence suivante :

**Compétence** : {competence['name']}
**Description** : {competence.get('description', '')}
**Niveau** : {competence.get('level', 1)} (1=débutant, 2=intermédiaire, 3=avancé)
{prereq_text}

**CONSIGNES** :
1. Génère entre 3 et {max_lessons} leçons progressives
2. Chaque leçon doit :
   - Avoir un titre clair et engageant
   - Contenu en Markdown (avec # pour titres, ** pour gras, etc.)
   - Inclure : théorie, exemples concrets, analogies
   - Durée estimée en minutes (5 à 30 min)

3. Progression pédagogique :
   - Leçon 1 : Introduction et concepts de base
   - Leçons intermédiaires : Approfondissement avec exemples
   - Dernière leçon : Synthèse et cas pratiques

4. Ton pédagogique : clair, accessible, motivant

**FORMAT DE RÉPONSE (JSON strict)** :

{{
  "lessons": [
    {{
      "title": "Introduction aux variables",
      "content": "# Les variables en Python\\n\\nUne variable est...",
      "estimated_time": 15
    }},
    {{
      "title": "Types de données",
      "content": "# Les différents types\\n\\n...",
      "estimated_time": 20
    }}
  ]
}}

**IMPORTANT** : 
- Le contenu doit être en Markdown valide
- Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire
"""
        return prompt
    
    @staticmethod
    def regenerate_for_competence(competence_id):
        """
        Régénérer les leçons (supprime les anciennes).
        
        Args:
            competence_id (str): ID de la compétence
            
        Returns:
            list: Nouvelles leçons
        """
        # Supprimer les anciennes leçons
        Lesson.delete_by_competence(competence_id)
        
        # Générer les nouvelles
        return LessonService.generate_for_competence(competence_id)