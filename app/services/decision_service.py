"""
Service de Décision Finale — Combine ZPD + SAINT+ + Émotion.

Décide :
- continue    : Exercice suivant (même compétence)
- next        : Passer à la compétence suivante
- adapt       : Adapter la difficulté
- pause       : Pause recommandée (frustration)
- review      : Réviser les bases
- stop        : Compétence maîtrisée, arrêter
"""

from app.services.ollama_service import OllamaService


class DecisionService:

    """Service de décision basé sur des règles simples"""
    
    # Seuils de configuration
    MASTERY_THRESHOLD = 0.9        # Seuil de maîtrise
    FAST_RESPONSE_TIME = 30        # Réponse rapide (secondes)
    SLOW_RESPONSE_TIME = 120       # Réponse lente (secondes)
    MAX_HINTS_BEFORE_ADAPT = 2     # Indices avant adaptation
    
    @staticmethod
    def make_simple_decision(
        is_correct: bool,
        saint_result: dict,
        zpd_result: dict,
        time_spent: int = 0,
        hints_used: int = 0,
        emotion_data: dict = None
    ) -> dict:
        """
        Décision basée sur 4 actions possibles :
        - continue : Exercice similaire
        - next : Compétence suivante
        - adapt : Adapter la difficulté
        - pause : Recommander une pause
        """
        
        # ═══════════════════════════════════════════════════════
        # ── EXTRAIRE LES MÉTRIQUES ──
        # ═══════════════════════════════════════════════════════
        mastery = float(saint_result.get("mastery", 0))
        is_mastered = saint_result.get("is_mastered", False) or mastery >= 0.9
        p_correct = float(saint_result.get("p_correct", 0.5))
        
        # Zone et difficulté
        zone = zpd_result.get("effective_zone", "unknown")
        recommended_diff = saint_result.get("recommended_difficulty", {})
        current_difficulty = float(recommended_diff.get("value", 0.5))
        exercise_types = zpd_result.get("recommended_exercise_types", ["qcm_simple"])
        
        # Émotions (si disponibles)
        emotion = None
        if emotion_data:
            emotion = emotion_data.get("dominant_emotion", None)
        
        # ═══════════════════════════════════════════════════════
        # ── DÉTECTION DES CONDITIONS ──
        # ═══════════════════════════════════════════════════════
        
        # Conditions de performance
        is_fast = time_spent < 30
        is_slow = time_spent > 120
        used_many_hints = hints_used >= 2
        
        # Conditions émotionnelles (frustration/fatigue)
        is_frustrated = emotion in ["frustrated", "angry", "confused"]
        is_tired = emotion in ["tired", "bored", "disengaged"]
        needs_pause = is_frustrated or is_tired
        
        # Conditions de progression
        is_struggling = not is_correct and (used_many_hints or is_slow)
        is_excelling = is_correct and is_fast and hints_used == 0
        
        # ═══════════════════════════════════════════════════════
        # ── DÉCISION PAR PRIORITÉ ──
        # ═══════════════════════════════════════════════════════
        
        # ─────────────────────────────────────────────────────────
        # PRIORITÉ 1: PAUSE (Frustration/Fatigue détectée)
        # ─────────────────────────────────────────────────────────
        if needs_pause:

            return {
            "status": "success",
            "action": "continue",
            "response_type": "next_competence",
            "message": "Prends une grande respiration, tu vas y arriver !",
            "encouragement": "Prends une grande respiration, tu vas y arriver !",
            "next_step": {
                "action": "generate_exercise",
                "difficulty": 0.8,
                "exercise_types": ["qcm_simple"],
                "same_competence": True
            },
            "ui": {
                "show_encouragement": True,
                "auto_proceed": True,
                "delay_seconds": 2
            },
            "is_correct": True,
            "metadata": {
                "reason": "standard_progression",
                "mastery": 0.9
            }
            }

            # return DecisionService._build_pause_decision(
            #     emotion=emotion,
            #     is_correct=is_correct,
            #     current_difficulty=current_difficulty,
            #     exercise_types=exercise_types
            # )
        
        # ─────────────────────────────────────────────────────────
        # PRIORITÉ 2: NEXT (Compétence maîtrisée)
        # ─────────────────────────────────────────────────────────
        if is_mastered:
            # return DecisionService._build_next_decision(
            #     mastery=mastery,
            #     exercise_types=exercise_types,
            #     is_correct=is_correct
            # )
            return {
            "status": "success",
            "action": "continue",
            "response_type": "next_competence",
            "message": "Prends une grande respiration, tu vas y arriver !",
            "encouragement": "Prends une grande respiration, tu vas y arriver !",
            "next_step": {
                "action": "generate_exercise",
                "difficulty": 0.8,
                "exercise_types": ["qcm_simple"],
                "same_competence": True
            },
            "ui": {
                "show_encouragement": True,
                "auto_proceed": True,
                "delay_seconds": 2
            },
            "is_correct": True,
            "metadata": {
                "reason": "standard_progression",
                "mastery": 0.9
            }
            }
        
        # ─────────────────────────────────────────────────────────
        # PRIORITÉ 3: ADAPT (Adapter la difficulté)
        # ─────────────────────────────────────────────────────────
        # Cas 3a: Trop difficile → Réduire
        if is_struggling:
            # return DecisionService._build_adapt_decision(
            #     direction="easier",
            #     current_difficulty=current_difficulty,
            #     reason="struggling",
            #     exercise_types=exercise_types,
            #     is_correct=is_correct
            # )
            return {
            "status": "success",
            "action": "continue",
            "response_type": "next_competence",
            "message": "Prends une grande respiration, tu vas y arriver !",
            "encouragement": "Prends une grande respiration, tu vas y arriver !",
            "next_step": {
                "action": "generate_exercise",
                "difficulty": 0.8,
                "exercise_types": ["qcm_simple"],
                "same_competence": True
            },
            "ui": {
                "show_encouragement": True,
                "auto_proceed": True,
                "delay_seconds": 2
            },
            "is_correct": True,
            "metadata": {
                "reason": "standard_progression",
                "mastery": 0.9
            }
            }
        
        # Cas 3b: Trop facile → Augmenter
        if is_excelling and mastery > 0.6:
            # return DecisionService._build_adapt_decision(
            #     direction="harder",
            #     current_difficulty=current_difficulty,
            #     reason="excelling",
            #     exercise_types=exercise_types,
            #     is_correct=is_correct
            # )
            return {
            "status": "success",
            "action": "continue",
            "response_type": "next_competence",
            "message": "Prends une grande respiration, tu vas y arriver !",
            "encouragement": "Prends une grande respiration, tu vas y arriver !",
            "next_step": {
                "action": "generate_exercise",
                "difficulty": 0.8,
                "exercise_types": ["qcm_simple"],
                "same_competence": True
            },
            "ui": {
                "show_encouragement": True,
                "auto_proceed": True,
                "delay_seconds": 2
            },
            "is_correct": True,
            "metadata": {
                "reason": "standard_progression",
                "mastery": 0.9
            }
            }
        
        # ─────────────────────────────────────────────────────────
        # PRIORITÉ 4: CONTINUE (Par défaut)
        # ─────────────────────────────────────────────────────────
        # return DecisionService._build_continue_decision(
        #     is_correct=is_correct,
        #     current_difficulty=current_difficulty,
        #     exercise_types=exercise_types,
        #     mastery=mastery
        # )
        return {
            "status": "success",
            "action": "continue",
            "response_type": "next_competence",
            "message": "Prends une grande respiration, tu vas y arriver !",
            "encouragement": "Prends une grande respiration, tu vas y arriver !",
            "next_step": {
                "action": "generate_exercise",
                "difficulty": 0.8,
                "exercise_types": ["qcm_simple"],
                "same_competence": True
            },
            "ui": {
                "show_encouragement": True,
                "auto_proceed": True,
                "delay_seconds": 2
            },
            "is_correct": True,
            "metadata": {
                "reason": "standard_progression",
                "mastery": 0.9
            }
            }
    
    # ═══════════════════════════════════════════════════════════════
    # ── BUILDERS DE DÉCISION ──
    # ═══════════════════════════════════════════════════════════════
    
    @staticmethod
    def _build_continue_decision(
        is_correct: bool,
        current_difficulty: float,
        exercise_types: list,
        mastery: float
    ) -> dict:
        """Action CONTINUE : Exercice similaire"""
        
        if is_correct:
            message = "Bien joué ! Continuons avec un exercice similaire."
            encouragement = "Tu progresses bien ! 👍"
        else:
            message = "Pas grave ! Réessayons avec un exercice du même type."
            encouragement = "La persévérance paie toujours ! 💪"
        
        return {
            "status": "success",
            "action": "continue",
            "response_type": "next_exercise",
            "message": message,
            "encouragement": encouragement,
            "next_step": {
                "action": "generate_exercise",
                "difficulty": current_difficulty,
                "exercise_types": exercise_types,
                "same_competence": True
            },
            "ui": {
                "show_encouragement": True,
                "auto_proceed": True,
                "delay_seconds": 2
            },
            "is_correct": is_correct,
            "metadata": {
                "reason": "standard_progression",
                "mastery": mastery
            }
        }
    
    @staticmethod
    def _build_next_decision(mastery: float, exercise_types: list, is_correct: bool) -> dict:
        """Action NEXT : Passer à la compétence suivante"""
        
        return {
            "status": "success",
            "action": "next",
            "response_type": "competence_mastered",
            "message": "🎉 Félicitations ! Tu as maîtrisé cette compétence !",
            "encouragement": "Excellent travail ! Passons à la suite !",
            "next_step": {
                "action": "next_competence",
                "difficulty": 0.3,  # Recommencer facile
                "exercise_types": ["qcm_simple", "code_completion"],
                "same_competence": False
            },
            "ui": {
                "show_encouragement": True,
                "auto_proceed": False,
                "delay_seconds": 3,
                "show_celebration": True
            },
            "is_correct": is_correct,
            "metadata": {
                "reason": "mastery_achieved",
                "mastery": mastery
            }
        }
    
    @staticmethod
    def _build_adapt_decision(
        direction: str,
        current_difficulty: float,
        reason: str,
        exercise_types: list, 
        is_correct: bool
    ) -> dict:
        """Action ADAPT : Adapter la difficulté"""
        
        if direction == "easier":
            # Réduire la difficulté
            new_difficulty = max(current_difficulty - 0.15, 0.1)
            message = "Prenons un exercice plus accessible."
            encouragement = "Chaque pas compte, même les petits ! 📚"
            new_types = ["qcm_simple", "exercice_guide"]
        else:
            # Augmenter la difficulté
            new_difficulty = min(current_difficulty + 0.15, 1.0)
            message = "Tu gères bien ! Essayons quelque chose de plus challengeant."
            encouragement = "Tu es prêt pour le niveau supérieur ! 🚀"
            new_types = ["code_completion", "code_writing"]
        
        return {
            "status": "success",
            "action": "adapt",
            "response_type": "difficulty_adjusted",
            "message": message,
            "encouragement": encouragement,
            "adaptation": {
                "direction": direction,
                "previous_difficulty": current_difficulty,
                "new_difficulty": new_difficulty
            },
            "next_step": {
                "action": "generate_exercise",
                "difficulty": new_difficulty,
                "exercise_types": new_types,
                "same_competence": True
            },
            "is_correct": is_correct,
            "ui": {
                "show_encouragement": True,
                "auto_proceed": True,
                "delay_seconds": 2
            },
            "metadata": {
                "reason": reason,
                "direction": direction
            }
        }
    
    @staticmethod
    def _build_pause_decision(
        emotion: str,
        is_correct: bool,
        current_difficulty: float,
        exercise_types: list
    ) -> dict:
        """Action PAUSE : Recommander une pause"""
        
        # Messages selon l'émotion
        if emotion in ["frustrated", "angry"]:
            message = "Je sens que c'est un peu difficile. Une petite pause ?"
            encouragement = "Respire un coup, tu reviendras plus fort ! 🧘"
            suggestion = "Prends 5 minutes, bois de l'eau, et on reprend !"
        elif emotion in ["tired", "bored"]:
            message = "Tu sembles fatigué. Et si on faisait une pause ?"
            encouragement = "Le repos fait partie de l'apprentissage ! 😴"
            suggestion = "Une pause de 10 minutes te fera du bien !"
        else:
            message = "C'est peut-être le moment de souffler un peu."
            encouragement = "Prends soin de toi ! 💚"
            suggestion = "Reviens quand tu te sens prêt !"
        
        return {
            "status": "success",
            "action": "pause",
            "response_type": "break_recommended",
            "message": message,
            "encouragement": encouragement,
            "pause_info": {
                "reason": emotion or "general",
                "suggested_duration_minutes": 5 if emotion in ["frustrated", "angry"] else 10,
                "suggestion": suggestion
            },
            "next_step": {
                "action": "resume_later",
                "difficulty": max(current_difficulty - 0.1, 0.1),  # Légèrement plus facile au retour
                "exercise_types": ["qcm_simple", "exercice_guide"],
                "same_competence": True
            },
            "ui": {
                "show_encouragement": True,
                "auto_proceed": False,
                "delay_seconds": 0,
                "show_pause_modal": True
            },
            "is_correct": is_correct,
            "metadata": {
                "reason": "emotional_state",
                "detected_emotion": emotion
            }
        }




    
    # # ══════════════════════════════════════════════════════════
    # # SEUILS DE DÉCISION
    # # ══════════════════════════════════════════════════════════
    
    # MASTERY_THRESHOLD = 0.90          # Seuil de maîtrise
    # FRUSTRATION_THRESHOLD = 0.40      # Seuil de frustration
    # HIGH_ENGAGEMENT = 0.70            # Engagement élevé
    # LOW_ENGAGEMENT = 0.30             # Engagement faible
    # ANOMALY_SEVERITY_HIGH = "high"    # Anomalie grave

    # # ══════════════════════════════════════════════════════════
    # # MÉTHODE AVEC LLM (OLLAMA)
    # # ══════════════════════════════════════════════════════════
    
    # @classmethod
    # def make_decision_with_llm(
    #     cls,
    #     user_id: str,
    #     competence_id: str,
    #     saint_result: dict,
    #     zpd_result: dict,
    #     emotion_data: dict = None,
    #     is_correct: bool = True,
    #     time_spent: int = 0,
    #     hints_used: int = 0,
    # ) -> dict:
    #     """
    #     Décision enrichie avec LLM (Ollama).
    #     Utilise les règles comme fallback si LLM échoue.
    #     """
    #     try:
    #         # Construire le prompt
    #         prompt = cls._build_decision_prompt(
    #             saint_result=saint_result,
    #             zpd_result=zpd_result,
    #             emotion_data=emotion_data,
    #             is_correct=is_correct,
    #             time_spent=time_spent,
    #             hints_used=hints_used
    #         )
            
    #         # Appeler Ollama
    #         response_data = OllamaService.generate_json(prompt, temperature=0.3)
            
    #         action = cls.process_decision(response_data)
                
    #     except Exception as e:
    #         print(f"[WARN] LLM decision failed, using rules: {e}")
        
    #     # Fallback aux règles
    #     return action
    
    # def process_decision(decision: dict) -> dict:
    #         """
    #         Traite la décision et retourne la réponse appropriée
    #         selon l'action recommandée.
    #         """
    #         action = decision.get('action')
    #         reason = decision.get('reason', '')
    #         message = decision.get('message', '')
    #         difficulty = decision.get('recommended_difficulty', 0.5)
    #         encouragement = decision.get('encouragement', '')
    #         exercise_types = decision.get('suggested_exercise_types', [])
    #         difficulty_adjustment = decision.get('difficulty_adjustment', 0)

    #         # ─────────────────────────────────────────────
    #         # 1️⃣ CONTINUE - Exercice similaire
    #         # ─────────────────────────────────────────────
    #         if action == 'continue':
    #             return {
    #                 "status": "success",
    #                 "response_type": "next_exercise",
    #                 "message": message,
    #                 "encouragement": encouragement,
    #                 "next_step": {
    #                     "action": "generate_exercise",
    #                     "difficulty": difficulty,
    #                     "exercise_types": exercise_types,
    #                     "same_competence": True,  # Rester sur la même compétence
    #                 },
    #                 "ui": {
    #                     "show_encouragement": True,
    #                     "auto_proceed": True,
    #                     "delay_seconds": 2,  # Petit délai avant le prochain exercice
    #                 }
    #             }

    #         # ─────────────────────────────────────────────
    #         # 2️⃣ NEXT - Passer à la compétence suivante
    #         # ─────────────────────────────────────────────
    #         elif action == 'next':
    #             return {
    #                 "status": "success",
    #                 "response_type": "next_competence",
    #                 "message": message,
    #                 "encouragement": encouragement,
    #                 "next_step": {
    #                     "action": "load_next_competence",
    #                     "difficulty": difficulty,
    #                     "exercise_types": exercise_types,
    #                     "same_competence": False,  # Nouvelle compétence
    #                     "mark_current_as": "mastered",  # Marquer comme maîtrisé
    #                 },
    #                 "ui": {
    #                     "show_celebration": True,  # 🎉 Animation de succès
    #                     "show_progress_bar": True,
    #                     "auto_proceed": False,  # Laisser l'élève voir sa réussite
    #                 }
    #             }

    #         # ─────────────────────────────────────────────
    #         # 3️⃣ ADAPT - Adapter la difficulté
    #         # ─────────────────────────────────────────────
    #         elif action == 'adapt':
    #             direction = "easier" if difficulty_adjustment < 0 else "harder"
    #             return {
    #                 "status": "success",
    #                 "response_type": "adapt_difficulty",
    #                 "message": message,
    #                 "encouragement": encouragement,
    #                 "next_step": {
    #                     "action": "generate_exercise",
    #                     "difficulty": difficulty,
    #                     "difficulty_direction": direction,
    #                     "difficulty_adjustment": difficulty_adjustment,
    #                     "exercise_types": exercise_types,
    #                     "same_competence": True,
    #                 },
    #                 "ui": {
    #                     "show_encouragement": True,
    #                     "show_hint": direction == "easier",  # Indice si plus facile
    #                     "auto_proceed": True,
    #                     "delay_seconds": 3,
    #                 }
    #             }

    #         # ─────────────────────────────────────────────
    #         # 4️⃣ PAUSE - Recommander une pause
    #         # ─────────────────────────────────────────────
    #         elif action == 'pause':
    #             return {
    #                 "status": "success",
    #                 "response_type": "take_break",
    #                 "message": message,
    #                 "encouragement": encouragement,
    #                 "next_step": {
    #                     "action": "pause_session",
    #                     "resume_difficulty": difficulty,
    #                     "save_progress": True,
    #                 },
    #                 "ui": {
    #                     "show_break_screen": True,
    #                     "suggested_break_duration": 5,  # 5 minutes
    #                     "show_motivational_quote": True,
    #                     "auto_proceed": False,
    #                     "show_resume_button": True,
    #                 }
    #             }

    #         # ─────────────────────────────────────────────
    #         # ❌ ACTION INCONNUE
    #         # ─────────────────────────────────────────────
    #         else:
    #             return {
    #                 "status": "error",
    #                 "response_type": "unknown_action",
    #                 "message": f"Action inconnue : {action}",
    #                 "next_step": {
    #                     "action": "generate_exercise",
    #                     "difficulty": 0.5,  # Difficulté par défaut
    #                 }
    #             }
#     # ══════════════════════════════════════════════════════════
#     # PROMPT BUILDER
#     # ══════════════════════════════════════════════════════════
    
#     @classmethod
#     def _build_decision_prompt(
#         cls,
#         saint_result: dict,
#         zpd_result: dict,
#         emotion_data: dict,
#         is_correct: bool,
#         time_spent: int,
#         hints_used: int
#     ) -> str:
#         """Construit le prompt pour la décision LLM."""
        
#         # Extraire les infos clés
#         mastery = cls._safe_float(saint_result.get("mastery", 0))
#         p_correct = cls._safe_float(saint_result.get("p_correct", 0.5))
#         zone = saint_result.get("zone", "unknown")
#         engagement = saint_result.get("engagement", {})
#         engagement_score = cls._safe_float(engagement.get("score", 0.5))
#         engagement_level = engagement.get("level", "moyen")
        
#         hint_prob = saint_result.get("hint_probability", {})
#         hint_level = hint_prob.get("level", "moyen")
        
#         anomaly = saint_result.get("anomaly", {})
#         has_anomaly = anomaly.get("has_anomaly", False)
        
#         competence_name = ""
#         zpd_zone = "unknown"
#         if zpd_result:
#             competence_name = zpd_result.get("name", "")
#             zpd_zone = zpd_result.get("effective_zone", "unknown")
        
#         frustration = False
#         emotion = "neutral"
#         if emotion_data:
#             frustration = emotion_data.get("frustration_detected", False)
#             emotion = emotion_data.get("dominant_emotion", "neutral")
        
#         prompt = f"""Tu es un tuteur pédagogique intelligent. Analyse les données de l'élève et décide de la prochaine action.

# **DONNÉES DE L'ÉLÈVE** :

# 📊 **Performance SAINT+** :
# - Maîtrise actuelle : {mastery:.1%}
# - Probabilité de succès : {p_correct:.1%}
# - Zone : {zone}
# - Engagement : {engagement_level} ({engagement_score:.0%})
# - Besoin d'indice : {hint_level}
# - Anomalie détectée : {"Oui" if has_anomaly else "Non"}

# 📚 **Compétence** :
# - Nom : {competence_name}
# - Zone ZPD : {zpd_zone}

# 🎯 **Dernière interaction** :
# - Réponse correcte : {"Oui" if is_correct else "Non"}
# - Temps passé : {time_spent} secondes
# - Indices utilisés : {hints_used}

# 😊 **État émotionnel** :
# - Émotion dominante : {emotion}
# - Frustration détectée : {"Oui" if frustration else "Non"}

# **ACTIONS POSSIBLES** :
# 1. `continue` : Continuer avec un exercice similaire
# 2. `next` : Passer à la compétence suivante (si maîtrisé)
# 3. `adapt` : Adapter la difficulté (plus facile/difficile)
# 4. `pause` : Recommander une pause (frustration/fatigue)

# **FORMAT DE RÉPONSE (JSON strict)** :

# {{
#   "action": "continue",
#   "reason": "L'élève progresse bien",
#   "message": "Continuons avec le prochain exercice !",
#   "difficulty_adjustment": 0.05,
#   "recommended_difficulty": 0.6,
#   "suggested_exercise_types": ["qcm_multiple", "code_completion"],
#   "encouragement": "Tu fais du bon travail !"
# }}

# **IMPORTANT** : Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire.
# """
#         return prompt
    
    # ══════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════
    
    @staticmethod
    def _safe_float(value) -> float:
        """Convertit une valeur en float de manière sécurisée."""
        try:
            import numpy as np
            if isinstance(value, (np.floating, np.float64, np.float32)):
                return float(value)
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0