"""
Service de génération d'exercices adaptatifs via Ollama.

Flux :
  1. Récupère le contenu de la leçon (Lesson)
  2. Récupère les infos de la compétence (Competence)
  3. Construit un prompt adapté au type + difficulté
  4. Appelle Ollama → JSON
  5. Valide et stocke l'exercice en DB

Supporte tous les types :
  qcm, qcm_multiple, vrai_faux, texte_a_trous,
  code_completion, code_libre, debugging, projet_mini
"""

import time
import traceback
from bson import ObjectId
from app.models.exercise import Exercise
from app.models.competence import Competence
from app.services.ollama_service import OllamaService


class ExerciseGeneratorService:

    def __init__(self, db):
        self.db = db
        self.ollama = OllamaService()

        # ──────────────────────────────────────────────
    # Génération ADAPTATIVE avec SAINT+
    # ──────────────────────────────────────────────

    def generate_adaptive_exercises(self, competence_id, competence, lessons,
                                    lesson_titles, count=3, saint_context=None,
                                    regenerate=False):
        """
        Génère des exercices adaptatifs personnalisés avec contexte SAINT+.

        Args:
            competence_id: str — ID de la compétence
            competence: dict — Document de la compétence
            lessons: list — Liste de TOUTES les leçons de la compétence
            lesson_titles: list — Titres des leçons
            count: int — Nombre d'exercices à générer (1-10)
            saint_context: dict — Contexte SAINT+ :
                - mastery: float (0.0-1.0)
                - zone: str (frustration, zpd, mastered)
                - optimal_difficulty: float (0.0-1.0)
                - hint_level: str (faible, moyen, fort)
                - recommended_exercise_types: list[str]
                - engagement: str (faible, moyen, élevé, inconnu)
                - p_correct: float (0.0-1.0)
            regenerate: bool — Supprimer les exercices existants

        Returns:
            dict: {
                "generated": int,
                "errors": int,
                "exercises": [...],
                "details": [...]
            }
        """
        # Contexte SAINT+ par défaut
        if not saint_context:
            saint_context = {
                "mastery": 0.5,
                "zone": "zpd",
                "optimal_difficulty": 0.5,
                "hint_level": "moyen",
                "recommended_exercise_types": [],
                "engagement": "moyen",
                "p_correct": 0.5,
            }

        # Extraire les paramètres SAINT+
        zone = saint_context.get("zone", "zpd")
        optimal_difficulty = saint_context.get("optimal_difficulty", 0.5)
        recommended_types = saint_context.get("recommended_exercise_types", [])
        hint_level = saint_context.get("hint_level", "moyen")
        engagement = saint_context.get("engagement", "moyen")
        mastery = saint_context.get("mastery", 0.5)
        p_correct = saint_context.get("p_correct", 0.5)

        print(f"[ADAPTIVE] Génération adaptative:")
        print(f"  Zone: {zone}, Mastery: {mastery:.2f}, Difficulty: {optimal_difficulty:.2f}")
        print(f"  Hints: {hint_level}, Engagement: {engagement}, P(correct): {p_correct:.2f}")
        print(f"  Leçons: {lesson_titles}")

        # Déterminer les types d'exercices
        if recommended_types and len(recommended_types) > 0:
            exercise_types = []
            for i in range(count):
                exercise_types.append(recommended_types[i % len(recommended_types)])
        else:
            exercise_types = self._choose_adaptive_types(count, zone, optimal_difficulty)

        print(f"  Types choisis: {exercise_types}")

        # Supprimer les exercices existants si regenerate
        if regenerate:
            deleted_count = Exercise.delete_by_competence(self.db, competence_id)
            print(f"  🗑️ {deleted_count} exercice(s) existant(s) supprimé(s)")

        # Préparer les résultats
        results = {
            "competence_id": str(competence_id),
            "lessons_count": len(lessons),
            "requested": count,
            "generated": 0,
            "errors": 0,
            "exercises": [],
            "details": [],
        }

        # Générer chaque exercice
        for i, ex_type in enumerate(exercise_types):
            print(f"  📝 Génération exercice adaptatif {i+1}/{count} (type={ex_type})...")

            try:
                exercise_id = self._generate_adaptive_single_exercise(
                    competence=competence,
                    lessons=lessons,
                    lesson_titles=lesson_titles,
                    exercise_type=ex_type,
                    difficulty=optimal_difficulty,
                    saint_context=saint_context,
                    index=i
                )

                if exercise_id:
                    # Récupérer l'exercice créé
                    exercise = Exercise.get_by_id(self.db, exercise_id)
                    exercise_data = {
                        "id": str(exercise_id),
                        "type": ex_type,
                        "difficulty": optimal_difficulty,
                        "question": exercise.get("question", ""),
                        "options": exercise.get("options", []),
                        "hints": exercise.get("hints", []),
                        "estimated_time": exercise.get("estimated_time", 60),
                    }
                    
                    results["generated"] += 1
                    results["exercises"].append(exercise_data)
                    results["details"].append({
                        "id": str(exercise_id),
                        "type": ex_type,
                        "status": "generated",
                    })
                    print(f"  ✅ Exercice adaptatif {i+1} généré")
                else:
                    results["errors"] += 1
                    results["details"].append({
                        "id": None,
                        "type": ex_type,
                        "status": "error",
                    })
                    print(f"  ❌ Exercice adaptatif {i+1} échoué")

            except Exception as e:
                results["errors"] += 1
                results["details"].append({
                    "id": None,
                    "type": ex_type,
                    "status": "error",
                    "error": str(e),
                })
                print(f"  ❌ Exception: {e}")
                traceback.print_exc()

            # Pause entre les générations
            if i < count - 1:
                time.sleep(1)

        return results

    # ──────────────────────────────────────────────
    # Génération d'un seul exercice adaptatif
    # ──────────────────────────────────────────────

    def _generate_adaptive_single_exercise(self, competence, lessons, lesson_titles,
                                          exercise_type, difficulty, saint_context, index=0):
        """
        Génère UN exercice adaptatif via Ollama avec prompt enrichi SAINT+.

        Returns:
            ObjectId ou None
        """
        comp_id = competence["_id"]
        # Utiliser la première leçon comme référence
        lesson_id = lessons[0]["_id"] if lessons else None

        if not lesson_id:
            print("  ⚠️ Aucune leçon disponible")
            return None

        # Créer le document planned
        exercise_doc = Exercise.create(
            competence_id=comp_id,
            lesson_id=lesson_id,
            exercise_type=exercise_type,
            difficulty=difficulty,
            status=Exercise.STATUS_PLANNED,
        )
        exercise_id = Exercise.insert(self.db, exercise_doc)

        # Passer en generating
        Exercise.update_status(self.db, exercise_id, Exercise.STATUS_GENERATING)

        try:
            # Construire le prompt ADAPTATIF enrichi avec SAINT+
            prompt = self._build_adaptive_prompt(
                competence=competence,
                lessons=lessons,
                lesson_titles=lesson_titles,
                exercise_type=exercise_type,
                difficulty=difficulty,
                saint_context=saint_context,
                index=index
            )

            # Température adaptée à l'engagement
            temperature = self._get_temperature_for_engagement(
                saint_context.get("engagement", "moyen")
            )

            result = self.ollama.generate_json(prompt, temperature=temperature)

            if not result:
                Exercise.update_status(self.db, exercise_id, Exercise.STATUS_ERROR)
                return None

            # Valider et extraire
            validated = self._validate_exercise_response(result, exercise_type)
            if not validated:
                Exercise.update_status(self.db, exercise_id, Exercise.STATUS_ERROR)
                return None

            # Mettre à jour le contenu
            Exercise.update_content(
                self.db,
                exercise_id,
                question=validated["question"],
                options=validated.get("options", []),
                correct_answer=validated["correct_answer"],
                explanation=validated.get("explanation", ""),
                hints=validated.get("hints", []),
                code_template=validated.get("code_template", ""),
                expected_output=validated.get("expected_output", ""),
            )

            # Mettre à jour le temps estimé
            if "estimated_time" in validated:
                Exercise.update(self.db, exercise_id, {
                    "estimated_time": int(validated["estimated_time"])
                })

            return exercise_id

        except Exception as e:
            Exercise.update_status(self.db, exercise_id, Exercise.STATUS_ERROR)
            print(f"  Erreur génération adaptative: {e}")
            traceback.print_exc()
            return None

    # ──────────────────────────────────────────────
    # Construction du prompt adaptatif avec SAINT+
    # ──────────────────────────────────────────────

    def _build_adaptive_prompt(self, competence, lessons, lesson_titles,
                              exercise_type, difficulty, saint_context, index=0):
        """
        Construit un prompt ENRICHI avec le contexte SAINT+.
        Utilise les titres et contenus de TOUTES les leçons.
        """
        comp_name = competence.get("name", "")
        comp_desc = competence.get("description", "")

        # Extraire le contexte SAINT+
        mastery = saint_context.get("mastery", 0.5)
        zone = saint_context.get("zone", "zpd")
        hint_level = saint_context.get("hint_level", "moyen")
        engagement = saint_context.get("engagement", "moyen")
        p_correct = saint_context.get("p_correct", 0.5)

        learning_context = self._generate_learning_context(competence, lesson_titles)

        # ──────────────────────────────────────────────
        # Combiner le contenu de toutes les leçons
        # ──────────────────────────────────────────────
        lessons_summary = ""
        for i, lesson in enumerate(lessons):
            title = lesson.get("title", f"Leçon {i+1}")
            content = lesson.get("content", "")

            # Tronquer si trop long
            if len(content) > 1000:
                content = content[:1000] + "\n[... suite tronquée ...]"

            lessons_summary += f"\n**LEÇON {i+1}: {title}**\n{content}\n"

        # Tronquer le total si nécessaire
        if len(lessons_summary) > 4000:
            lessons_summary = lessons_summary[:4000] + "\n[... contenu tronqué ...]"

        # ──────────────────────────────────────────────
        # Instructions selon la zone ZPD
        # ──────────────────────────────────────────────
        zone_config = {
            "frustration": {
                "tone": "très encourageant, simple et accessible",
                "focus": "Concentre-toi sur les concepts de BASE des premières leçons.",
                "difficulty_desc": "TRÈS FACILE",
                "hints_instruction": "Fournis 3 à 4 indices TRÈS détaillés qui guident pas à pas.",
            },
            "zpd": {
                "tone": "pédagogique, stimulant et progressif",
                "focus": "Combine les concepts de plusieurs leçons de manière progressive.",
                "difficulty_desc": "MOYEN",
                "hints_instruction": "Fournis 2 à 3 indices progressifs sans tout révéler.",
            },
            "mastered": {
                "tone": "challengeant, créatif et avancé",
                "focus": "Crée un exercice qui COMBINE et APPROFONDIT tous les concepts.",
                "difficulty_desc": "DIFFICILE",
                "hints_instruction": "Fournis 1 à 2 indices minimalistes.",
            }
        }

        config = zone_config.get(zone, zone_config["zpd"])

        # ──────────────────────────────────────────────
        # Note sur l'engagement
        # ──────────────────────────────────────────────
        engagement_notes = {
            "faible": "\n⚠️ ATTENTION : L'élève montre des signes de DÉSENGAGEMENT. "
                     "Rends l'exercice TRÈS interactif, ludique et motivant !",
            "moyen": "",
            "élevé": "\n✨ L'élève est très engagé. Tu peux proposer des défis ambitieux.",
            "inconnu": ""
        }
        engagement_note = engagement_notes.get(engagement, "")

        # ──────────────────────────────────────────────
        # Instructions spécifiques au type d'exercice
        # ──────────────────────────────────────────────
        type_instructions = self._get_type_json_format(exercise_type)

        # ──────────────────────────────────────────────
        # Construire le prompt final
        # ──────────────────────────────────────────────
        prompt = f"""Tu es un professeur expert en pédagogie adaptative assistée par IA.

══════════════════════════════════════════════════════
CONTEXTE PÉDAGOGIQUE
══════════════════════════════════════════════════════

**COMPÉTENCE** : {comp_name}
**Description** : {comp_desc}
**Exercice numéro** : {index + 1}

══════════════════════════════════════════════════════
CONTEXTE PÉDAGOGIQUE
══════════════════════════════════════════════════════
{learning_context}

══════════════════════════════════════════════════════
PROFIL DE L'ÉLÈVE (Analyse SAINT+ IA)
══════════════════════════════════════════════════════

- Niveau de maîtrise actuel : {mastery * 100:.0f}%
- Zone d'apprentissage : {zone.upper()}
- Probabilité de réussite : {p_correct * 100:.0f}%
- Besoin d'indices : {hint_level.upper()}
- Engagement : {engagement.upper()}
{engagement_note}

══════════════════════════════════════════════════════
CONSIGNES DE GÉNÉRATION
══════════════════════════════════════════════════════

1. **Ton** : {config['tone']}

2. **Focus** : {config['focus']}

3. **Difficulté** : {config['difficulty_desc']} (niveau {difficulty:.0%})

4. **Indices** : {config['hints_instruction']}

5. **Type d'exercice** : {exercise_type.upper()}

══════════════════════════════════════════════════════
FORMAT DE RÉPONSE (JSON STRICT)
══════════════════════════════════════════════════════

{type_instructions}

**IMPORTANT** :
- Base l'exercice sur le CONTENU DES LEÇONS ci-dessus
- Adapte la difficulté au niveau de l'élève ({zone})
- Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire
"""

        return prompt

    # ──────────────────────────────────────────────
    # Format JSON selon le type d'exercice
    # ──────────────────────────────────────────────

    def _get_type_json_format(self, exercise_type):
        """Retourne le format JSON attendu selon le type d'exercice."""

        formats = {
            "qcm": """{{
    "question": "Question claire avec UNE seule bonne réponse",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option B",
    "explanation": "Explication pédagogique de la bonne réponse",
    "hints": ["Indice 1", "Indice 2"],
    "estimated_time": 30
}}""",

            "qcm_multiple": """{{
    "question": "Question avec PLUSIEURS bonnes réponses (le préciser)",
    "options": ["Option A", "Option B", "Option C", "Option D", "Option E"],
    "correct_answer": ["Option A", "Option C"],
    "explanation": "Explication de chaque bonne réponse",
    "hints": ["Indice 1", "Indice 2"],
    "estimated_time": 45
}}""",

            "vrai_faux": """{{
    "question": "Affirmation à évaluer comme Vrai ou Faux",
    "options": ["Vrai", "Faux"],
    "correct_answer": "Vrai",
    "explanation": "Explication détaillée",
    "hints": ["Indice"],
    "estimated_time": 20
}}""",

            "texte_a_trous": """{{
    "question": "Phrase avec des ___ à compléter",
    "options": [],
    "correct_answer": "mot1, mot2",
    "explanation": "Explication des mots manquants",
    "hints": ["Indice pour le premier trou", "Indice pour le second"],
    "estimated_time": 40
}}""",

            "code_completion": """{{
    "question": "Complète le code suivant",
    "options": [],
    "correct_answer": "le code complet corrigé",
    "code_template": "def fonction():\\n    # TODO: compléter\\n    pass",
    "expected_output": "Résultat attendu",
    "explanation": "Explication de la solution",
    "hints": ["Indice 1", "Indice 2"],
    "estimated_time": 90
}}""",

            "code_libre": """{{
    "question": "Écris un programme qui fait X",
    "options": [],
    "correct_answer": "def solution():\\n    return resultat",
    "expected_output": "Entrée: X → Sortie: Y",
    "explanation": "Explication étape par étape",
    "hints": ["Indice sur l'approche", "Indice sur la syntaxe"],
    "estimated_time": 120
}}""",

            "debugging": """{{
    "question": "Trouve et corrige l'erreur dans ce code",
    "options": [],
    "correct_answer": "le code corrigé",
    "code_template": "def buggy():\\n    return 1 - 1  # Bug ici",
    "expected_output": "Ce que le code devrait retourner",
    "explanation": "Explication du bug et de la correction",
    "hints": ["Regarde la ligne X", "L'opérateur est incorrect"],
    "estimated_time": 90
}}""",

            "projet_mini": """{{
    "question": "Mini-projet en 3 étapes:\\n1. Étape 1\\n2. Étape 2\\n3. Étape 3",
    "options": [],
    "correct_answer": "Code solution complet",
    "expected_output": "Description du résultat final",
    "explanation": "Explication de chaque étape",
    "hints": ["Indice étape 1", "Indice étape 2"],
    "estimated_time": 300
}}"""
        }

        return formats.get(exercise_type, formats["qcm"])

    # ──────────────────────────────────────────────
    # Choix des types selon la zone ZPD
    # ──────────────────────────────────────────────

    def _choose_adaptive_types(self, count, zone, difficulty):
        """
        Choisit les types d'exercices selon la zone ZPD.

        - FRUSTRATION : Types simples (qcm, vrai_faux)
        - ZPD : Types variés (qcm, code_completion, texte_a_trous)
        - MASTERED : Types avancés (code_libre, debugging)
        """
        zone_pools = {
            "frustration": ["qcm", "vrai_faux", "texte_a_trous", "qcm"],
            "zpd": ["qcm", "code_completion", "texte_a_trous", "qcm_multiple", "debugging"],
            "mastered": ["code_libre", "debugging", "projet_mini", "code_completion"],
        }

        pool = zone_pools.get(zone, zone_pools["zpd"])

        types = []
        for i in range(count):
            types.append(pool[i % len(pool)])

        return types

    # ──────────────────────────────────────────────
    # Température selon l'engagement
    # ──────────────────────────────────────────────

    def _get_temperature_for_engagement(self, engagement):
        """
        Adapte la température de génération selon l'engagement.

        - Faible engagement → Température haute (plus créatif)
        - Élevé engagement → Température basse (plus précis)
        """
        temperatures = {
            "faible": 0.7,
            "moyen": 0.5,
            "élevé": 0.3,
            "inconnu": 0.5,
        }

        return temperatures.get(engagement, 0.5)
    
    
        # ──────────────────────────────────────────────
    # Génération de contexte pédagogique
    # ──────────────────────────────────────────────

    def _generate_learning_context(self, competence, lesson_titles):
        """
        Génère un contexte pédagogique détaillé à partir de :
        - Nom de la compétence
        - Description de la compétence  
        - Titres des leçons

        Le LLM déduit les concepts à évaluer sans avoir le contenu.

        Args:
            competence: dict — Document de la compétence
            lesson_titles: list — Titres des leçons

        Returns:
            str: Contexte pédagogique pour la génération d'exercices
        """
        comp_name = competence.get("name", "")
        comp_desc = competence.get("description", "")

        prompt = f"""Tu es un expert pédagogique. À partir du nom de la compétence et des titres des leçons, génère un CONTEXTE PÉDAGOGIQUE détaillé.

**COMPÉTENCE** : {comp_name}
**Description** : {comp_desc}
**Titres des leçons** :
{chr(10).join([f"  {i+1}. {title}" for i, title in enumerate(lesson_titles)])}

**CONSIGNES** :
À partir de ces informations, déduis :
1. Les CONCEPTS CLÉS enseignés
2. Les NOTIONS TECHNIQUES à maîtriser
3. Les COMPÉTENCES PRATIQUES attendues
4. Les ERREURS COURANTES à éviter
5. Les CAS D'USAGE concrets

**FORMAT JSON** :
{{
    "concepts_cles": ["concept1", "concept2", "concept3"],
    "notions_techniques": ["notion1", "notion2"],
    "competences_pratiques": ["savoir faire X", "être capable de Y"],
    "erreurs_courantes": ["erreur1", "erreur2"],
    "cas_usage": ["cas1", "cas2"]
}}

Réponds UNIQUEMENT avec le JSON.
"""

        try:
            print("[CONTEXT] Génération du contexte pédagogique...")
            result = self.ollama.generate_json(prompt, temperature=0.3)

            if result:
                context = self._format_learning_context(result, comp_name, lesson_titles)
                print("[CONTEXT] Contexte généré avec succès")
                return context

        except Exception as e:
            print(f"[CONTEXT] Erreur: {e}")

        # Fallback simple
        return self._fallback_context(comp_name, comp_desc, lesson_titles)

    def _format_learning_context(self, context_json, comp_name, lesson_titles):
        """
        Formate le contexte JSON en texte structuré pour le prompt.
        """
        concepts = context_json.get("concepts_cles", [])
        notions = context_json.get("notions_techniques", [])
        competences = context_json.get("competences_pratiques", [])
        erreurs = context_json.get("erreurs_courantes", [])
        cas_usage = context_json.get("cas_usage", [])

        formatted = f"""
**COMPÉTENCE** : {comp_name}
**LEÇONS** : {', '.join(lesson_titles)}

**CONCEPTS CLÉS À ÉVALUER** :
{chr(10).join([f'  • {c}' for c in concepts])}

**NOTIONS TECHNIQUES** :
{chr(10).join([f'  • {n}' for n in notions])}

**COMPÉTENCES PRATIQUES ATTENDUES** :
{chr(10).join([f'  ✓ {c}' for c in competences])}

**ERREURS COURANTES À TESTER** :
{chr(10).join([f'  ⚠ {e}' for e in erreurs])}

**CAS D'USAGE** :
{chr(10).join([f'  → {c}' for c in cas_usage])}
"""
        return formatted

    def _fallback_context(self, comp_name, comp_desc, lesson_titles):
        """
        Contexte de secours si le LLM échoue.
        """
        return f"""
**COMPÉTENCE** : {comp_name}
**DESCRIPTION** : {comp_desc}
**LEÇONS À COUVRIR** : {', '.join(lesson_titles)}

Génère un exercice basé sur ces leçons.
"""
    
     # ──────────────────────────────────────────────
    # Validation de la réponse Ollama
    # ──────────────────────────────────────────────

    def _validate_exercise_response(self, response, exercise_type):
        """
        Valide la réponse JSON d'Ollama.

        Args:
            response: dict — JSON parsé depuis Ollama
            exercise_type: str — type attendu

        Returns:
            dict validé ou None si invalide
        """
        if not isinstance(response, dict):
            print(f"  ⚠️ Réponse n'est pas un dict: {type(response)}")
            return None

        # Champs obligatoires
        question = response.get("question", "").strip()
        correct_answer = response.get("correct_answer", "")

        if not question:
            print("  ⚠️ Question vide")
            return None

        if not correct_answer and correct_answer != False:
            print("  ⚠️ Réponse correcte vide")
            return None

        # Validation spécifique au type
        if exercise_type == "qcm":
            options = response.get("options", [])
            if len(options) < 3:
                print(f"  ⚠️ QCM avec {len(options)} options (min 3)")
                return None
            if correct_answer not in options:
                # Essayer de trouver une correspondance approximative
                for opt in options:
                    if str(correct_answer).strip().lower() == opt.strip().lower():
                        correct_answer = opt
                        break
                else:
                    print(f"  ⚠️ Réponse correcte \'\'{correct_answer}\'\'  pas dans les options")
                    return None

        elif exercise_type == "qcm_multiple":
            options = response.get("options", [])
            if len(options) < 4:
                print(f"  ⚠️ QCM multiple avec {len(options)} options (min 4)")
                return None
            if not isinstance(correct_answer, list):
                correct_answer = [correct_answer]

        elif exercise_type == "vrai_faux":
            options = ["Vrai", "Faux"]
            normalized = str(correct_answer).strip().lower()
            if normalized in ("vrai", "true", "1"):
                correct_answer = "Vrai"
            elif normalized in ("faux", "false", "0"):
                correct_answer = "Faux"
            else:
                print(f"  ⚠️ Réponse vrai/faux invalide: {correct_answer}")
                return None

        elif exercise_type in ("code_completion", "debugging"):
            if not response.get("code_template", "").strip():
                print(f"  ⚠️ Pas de code_template pour {exercise_type}")
                return None

        # Construire le résultat validé
        validated = {
            "question": question,
            "options": response.get("options", []),
            "correct_answer": correct_answer,
            "explanation": response.get("explanation", ""),
            "hints": response.get("hints", []),
            "code_template": response.get("code_template", ""),
            "expected_output": response.get("expected_output", ""),
            "estimated_time": response.get("estimated_time", 60),
        }

        return validated


    
   