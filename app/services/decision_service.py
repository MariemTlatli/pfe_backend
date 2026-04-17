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

    # """Service de décision basé sur des règles simples"""
    
    # # Seuils de configuration
    # MASTERY_THRESHOLD = 0.9        # Seuil de maîtrise
    # FAST_RESPONSE_TIME = 30        # Réponse rapide (secondes)
    # SLOW_RESPONSE_TIME = 120       # Réponse lente (secondes)
    # MAX_HINTS_BEFORE_ADAPT = 2     # Indices avant adaptation
    
    # @staticmethod
    # def make_simple_decision(
    #     is_correct: bool,
    #     zpd_result: dict,
    #     time_spent: int = 0,
    #     hints_used: int = 0,
    #     emotion_data: dict = None
    # ) -> dict:
    #     """
    #     Décision basée sur 4 actions possibles :
    #     - continue : Exercice similaire
    #     - next : Compétence suivante
    #     - adapt : Adapter la difficulté
    #     - pause : Recommander une pause
    #     """
        
    #     # ═══════════════════════════════════════════════════════
    #     # ── EXTRAIRE LES MÉTRIQUES ──
    #     # ═══════════════════════════════════════════════════════
    #     mastery = float(zpd_result.get("mastery_level", 0))
    #     is_mastered = zpd_result.get("is_mastered", False) or mastery >= 0.9
    #     p_correct = float(zpd_result.get("saint_metrics", {}).get("p_correct", 0.5))
    #     print("p_correct", p_correct)
    #     # Zone et difficulté
    #     zone = zpd_result.get("effective_zone", "unknown")
    #     recommended_diff = zpd_result.get("saint_plus", {}).get("recommended_difficulty", {})
    #     current_difficulty = float(recommended_diff.get("value", 0.5))
    #     exercise_types = zpd_result.get("recommended_exercise_types", ["qcm_simple"])
        
    #     # Émotions (si disponibles)
    #     emotion = None
    #     if emotion_data:
    #         emotion = emotion_data.get("dominant_emotion", None)
        
    #     # ═══════════════════════════════════════════════════════
    #     # ── DÉTECTION DES CONDITIONS ──
    #     # ═══════════════════════════════════════════════════════
        
    #     # Conditions de performance
    #     is_fast = time_spent < 30
    #     is_slow = time_spent > 120
    #     used_many_hints = hints_used >= 2
        
    #     # Conditions émotionnelles (frustration/fatigue)
    #     is_frustrated = emotion in ["frustrated", "angry", "confused"]
    #     is_tired = emotion in ["tired", "bored", "disengaged"]
    #     needs_pause = is_frustrated or is_tired
        
    #     # Conditions de progression
    #     is_struggling = not is_correct and (used_many_hints or is_slow)
    #     is_excelling = is_correct and is_fast and hints_used == 0
        
    #     # ═══════════════════════════════════════════════════════
    #     # ── DÉCISION PAR PRIORITÉ ──
    #     # ═══════════════════════════════════════════════════════
        
    #     # ─────────────────────────────────────────────────────────
    #     # PRIORITÉ 1: PAUSE (Frustration/Fatigue détectée)
    #     # ─────────────────────────────────────────────────────────
    #     if needs_pause:

    #         return {
    #         "status": "success",
    #         "action": "continue",
    #         "response_type": "next_competence",
    #         "message": "Prends une grande respiration, tu vas y arriver !",
    #         "encouragement": "Prends une grande respiration, tu vas y arriver !",
    #         "next_step": {
    #             "action": "generate_exercise",
    #             "difficulty": 0.8,
    #             "exercise_types": ["qcm_simple"],
    #             "same_competence": True
    #         },
    #         "ui": {
    #             "show_encouragement": True,
    #             "auto_proceed": True,
    #             "delay_seconds": 2
    #         },
    #         "is_correct": True,
    #         "metadata": {
    #             "reason": "standard_progression",
    #             "mastery": 0.9
    #         }
    #         }

    #         # return DecisionService._build_pause_decision(
    #         #     emotion=emotion,
    #         #     is_correct=is_correct,
    #         #     current_difficulty=current_difficulty,
    #         #     exercise_types=exercise_types
    #         # )
        
    #     # ─────────────────────────────────────────────────────────
    #     # PRIORITÉ 2: NEXT (Compétence maîtrisée)
    #     # ─────────────────────────────────────────────────────────
    #     if is_mastered:
    #         # return DecisionService._build_next_decision(
    #         #     mastery=mastery,
    #         #     exercise_types=exercise_types,
    #         #     is_correct=is_correct
    #         # )
    #         return {
    #         "status": "success",
    #         "action": "continue",
    #         "response_type": "next_competence",
    #         "message": "Prends une grande respiration, tu vas y arriver !",
    #         "encouragement": "Prends une grande respiration, tu vas y arriver !",
    #         "next_step": {
    #             "action": "generate_exercise",
    #             "difficulty": 0.8,
    #             "exercise_types": ["qcm_simple"],
    #             "same_competence": True
    #         },
    #         "ui": {
    #             "show_encouragement": True,
    #             "auto_proceed": True,
    #             "delay_seconds": 2
    #         },
    #         "is_correct": True,
    #         "metadata": {
    #             "reason": "standard_progression",
    #             "mastery": 0.9
    #         }
    #         }
        
    #     # ─────────────────────────────────────────────────────────
    #     # PRIORITÉ 3: ADAPT (Adapter la difficulté)
    #     # ─────────────────────────────────────────────────────────
    #     # Cas 3a: Trop difficile → Réduire
    #     if is_struggling:
    #         # return DecisionService._build_adapt_decision(
    #         #     direction="easier",
    #         #     current_difficulty=current_difficulty,
    #         #     reason="struggling",
    #         #     exercise_types=exercise_types,
    #         #     is_correct=is_correct
    #         # )
    #         return {
    #         "status": "success",
    #         "action": "continue",
    #         "response_type": "next_competence",
    #         "message": "Prends une grande respiration, tu vas y arriver !",
    #         "encouragement": "Prends une grande respiration, tu vas y arriver !",
    #         "next_step": {
    #             "action": "generate_exercise",
    #             "difficulty": 0.8,
    #             "exercise_types": ["qcm_simple"],
    #             "same_competence": True
    #         },
    #         "ui": {
    #             "show_encouragement": True,
    #             "auto_proceed": True,
    #             "delay_seconds": 2
    #         },
    #         "is_correct": True,
    #         "metadata": {
    #             "reason": "standard_progression",
    #             "mastery": 0.9
    #         }
    #         }
        
    #     # Cas 3b: Trop facile → Augmenter
    #     if is_excelling and mastery > 0.6:
    #         # return DecisionService._build_adapt_decision(
    #         #     direction="harder",
    #         #     current_difficulty=current_difficulty,
    #         #     reason="excelling",
    #         #     exercise_types=exercise_types,
    #         #     is_correct=is_correct
    #         # )
    #         return {
    #         "status": "success",
    #         "action": "continue",
    #         "response_type": "next_competence",
    #         "message": "Prends une grande respiration, tu vas y arriver !",
    #         "encouragement": "Prends une grande respiration, tu vas y arriver !",
    #         "next_step": {
    #             "action": "generate_exercise",
    #             "difficulty": 0.8,
    #             "exercise_types": ["qcm_simple"],
    #             "same_competence": True
    #         },
    #         "ui": {
    #             "show_encouragement": True,
    #             "auto_proceed": True,
    #             "delay_seconds": 2
    #         },
    #         "is_correct": True,
    #         "metadata": {
    #             "reason": "standard_progression",
    #             "mastery": 0.9
    #         }
    #         }
        
    #     # ─────────────────────────────────────────────────────────
    #     # PRIORITÉ 4: CONTINUE (Par défaut)
    #     # ─────────────────────────────────────────────────────────
    #     # return DecisionService._build_continue_decision(
    #     #     is_correct=is_correct,
    #     #     current_difficulty=current_difficulty,
    #     #     exercise_types=exercise_types,
    #     #     mastery=mastery
    #     # )
    #     return {
    #         "status": "success",
    #         "action": "continue",
    #         "response_type": "next_competence",
    #         "message": "Prends une grande respiration, tu vas y arriver !",
    #         "encouragement": "Prends une grande respiration, tu vas y arriver !",
    #         "next_step": {
    #             "action": "generate_exercise",
    #             "difficulty": 0.8,
    #             "exercise_types": ["qcm_simple"],
    #             "same_competence": True
    #         },
    #         "ui": {
    #             "show_encouragement": True,
    #             "auto_proceed": True,
    #             "delay_seconds": 2
    #         },
    #         "is_correct": True,
    #         "metadata": {
    #             "reason": "standard_progression",
    #             "mastery": 0.9
    #         }
    #         }
    
    # # ═══════════════════════════════════════════════════════════════
    # # ── BUILDERS DE DÉCISION ──
    # # ═══════════════════════════════════════════════════════════════
    
    # @staticmethod
    # def _build_continue_decision(
    #     is_correct: bool,
    #     current_difficulty: float,
    #     exercise_types: list,
    #     mastery: float
    # ) -> dict:
    #     """Action CONTINUE : Exercice similaire"""
        
    #     if is_correct:
    #         message = "Bien joué ! Continuons avec un exercice similaire."
    #         encouragement = "Tu progresses bien ! 👍"
    #     else:
    #         message = "Pas grave ! Réessayons avec un exercice du même type."
    #         encouragement = "La persévérance paie toujours ! 💪"
        
    #     return {
    #         "status": "success",
    #         "action": "continue",
    #         "response_type": "next_exercise",
    #         "message": message,
    #         "encouragement": encouragement,
    #         "next_step": {
    #             "action": "generate_exercise",
    #             "difficulty": current_difficulty,
    #             "exercise_types": exercise_types,
    #             "same_competence": True
    #         },
    #         "ui": {
    #             "show_encouragement": True,
    #             "auto_proceed": True,
    #             "delay_seconds": 2
    #         },
    #         "is_correct": is_correct,
    #         "metadata": {
    #             "reason": "standard_progression",
    #             "mastery": mastery
    #         }
    #     }
    
    # @staticmethod
    # def _build_next_decision(mastery: float, exercise_types: list, is_correct: bool) -> dict:
    #     """Action NEXT : Passer à la compétence suivante"""
        
    #     return {
    #         "status": "success",
    #         "action": "next",
    #         "response_type": "competence_mastered",
    #         "message": "🎉 Félicitations ! Tu as maîtrisé cette compétence !",
    #         "encouragement": "Excellent travail ! Passons à la suite !",
    #         "next_step": {
    #             "action": "next_competence",
    #             "difficulty": 0.3,  # Recommencer facile
    #             "exercise_types": ["qcm_simple", "code_completion"],
    #             "same_competence": False
    #         },
    #         "ui": {
    #             "show_encouragement": True,
    #             "auto_proceed": False,
    #             "delay_seconds": 3,
    #             "show_celebration": True
    #         },
    #         "is_correct": is_correct,
    #         "metadata": {
    #             "reason": "mastery_achieved",
    #             "mastery": mastery
    #         }
    #     }
    
    # @staticmethod
    # def _build_adapt_decision(
    #     direction: str,
    #     current_difficulty: float,
    #     reason: str,
    #     exercise_types: list, 
    #     is_correct: bool
    # ) -> dict:
    #     """Action ADAPT : Adapter la difficulté"""
        
    #     if direction == "easier":
    #         # Réduire la difficulté
    #         new_difficulty = max(current_difficulty - 0.15, 0.1)
    #         message = "Prenons un exercice plus accessible."
    #         encouragement = "Chaque pas compte, même les petits ! 📚"
    #         new_types = ["qcm_simple", "exercice_guide"]
    #     else:
    #         # Augmenter la difficulté
    #         new_difficulty = min(current_difficulty + 0.15, 1.0)
    #         message = "Tu gères bien ! Essayons quelque chose de plus challengeant."
    #         encouragement = "Tu es prêt pour le niveau supérieur ! 🚀"
    #         new_types = ["code_completion", "code_writing"]
        
    #     return {
    #         "status": "success",
    #         "action": "adapt",
    #         "response_type": "difficulty_adjusted",
    #         "message": message,
    #         "encouragement": encouragement,
    #         "adaptation": {
    #             "direction": direction,
    #             "previous_difficulty": current_difficulty,
    #             "new_difficulty": new_difficulty
    #         },
    #         "next_step": {
    #             "action": "generate_exercise",
    #             "difficulty": new_difficulty,
    #             "exercise_types": new_types,
    #             "same_competence": True
    #         },
    #         "is_correct": is_correct,
    #         "ui": {
    #             "show_encouragement": True,
    #             "auto_proceed": True,
    #             "delay_seconds": 2
    #         },
    #         "metadata": {
    #             "reason": reason,
    #             "direction": direction
    #         }
    #     }
    
    # @staticmethod
    # def _build_pause_decision(
    #     emotion: str,
    #     is_correct: bool,
    #     current_difficulty: float,
    #     exercise_types: list
    # ) -> dict:
    #     """Action PAUSE : Recommander une pause"""
        
    #     # Messages selon l'émotion
    #     if emotion in ["frustrated", "angry"]:
    #         message = "Je sens que c'est un peu difficile. Une petite pause ?"
    #         encouragement = "Respire un coup, tu reviendras plus fort ! 🧘"
    #         suggestion = "Prends 5 minutes, bois de l'eau, et on reprend !"
    #     elif emotion in ["tired", "bored"]:
    #         message = "Tu sembles fatigué. Et si on faisait une pause ?"
    #         encouragement = "Le repos fait partie de l'apprentissage ! 😴"
    #         suggestion = "Une pause de 10 minutes te fera du bien !"
    #     else:
    #         message = "C'est peut-être le moment de souffler un peu."
    #         encouragement = "Prends soin de toi ! 💚"
    #         suggestion = "Reviens quand tu te sens prêt !"
        
    #     return {
    #         "status": "success",
    #         "action": "pause",
    #         "response_type": "break_recommended",
    #         "message": message,
    #         "encouragement": encouragement,
    #         "pause_info": {
    #             "reason": emotion or "general",
    #             "suggested_duration_minutes": 5 if emotion in ["frustrated", "angry"] else 10,
    #             "suggestion": suggestion
    #         },
    #         "next_step": {
    #             "action": "resume_later",
    #             "difficulty": max(current_difficulty - 0.1, 0.1),  # Légèrement plus facile au retour
    #             "exercise_types": ["qcm_simple", "exercice_guide"],
    #             "same_competence": True
    #         },
    #         "ui": {
    #             "show_encouragement": True,
    #             "auto_proceed": False,
    #             "delay_seconds": 0,
    #             "show_pause_modal": True
    #         },
    #         "is_correct": is_correct,
    #         "metadata": {
    #             "reason": "emotional_state",
    #             "detected_emotion": emotion
    #         }
    #     }




    
#     # ══════════════════════════════════════════════════════════
#     # SEUILS DE DÉCISION
#     # ══════════════════════════════════════════════════════════
    
#     MASTERY_THRESHOLD = 0.85          # Seuil de maîtrise
#     FRUSTRATION_THRESHOLD = 0.40      # Seuil de frustration
#     HIGH_ENGAGEMENT = 0.70            # Engagement élevé
#     LOW_ENGAGEMENT = 0.30             # Engagement faible
#     ANOMALY_SEVERITY_HIGH = "high"    # Anomalie grave

#     # ══════════════════════════════════════════════════════════
#     # MÉTHODE AVEC LLM (OLLAMA)
#     # ══════════════════════════════════════════════════════════
    
#     @classmethod
#     def make_decision_with_llm(
#         cls,
#         user_id: str,
#         competence_id: str,
#         zpd_result: dict,
#         emotion_data: dict = None,
#         is_correct: bool = True,
#         time_spent: int = 0,
#         hints_used: int = 0,
#     ) -> dict:
#         """
#         Décision enrichie avec LLM (Ollama).
#         Recommande dynamiquement la difficulté et le type d'exercice.
#         Les métriques SAINT+ sont extraites du résultat ZPD.
#         """
#         # Extraire saint_result de zpd_result
#         saint_result = zpd_result.get("saint_metrics", {}) if zpd_result else {}

#         try:
#             # Construire le prompt
#             prompt = cls._build_decision_prompt(
#                 saint_result=saint_result,
#                 zpd_result=zpd_result,
#                 emotion_data=emotion_data,
#                 is_correct=is_correct,
#                 time_spent=time_spent,
#                 hints_used=hints_used
#             )
            
#             # Appeler Ollama
#             response_data = OllamaService.generate_json(prompt, temperature=0.3)
#             print("**********json************")
#             print(response_data)    
#             print("**********************")    
#             response_data = cls._enforce_business_rules(response_data, zpd_result)
#             print("**********forced************")
#             print(response_data)    
#             print("**********************")    
#             cls.process_decision(response_data)
#             print("*********llm*************")
#             print(response_data)    
#             print("**********************")    
#         except Exception as e:
#             print(f"[WARN] LLM decision failed: {e}")
        
#         # Fallback minimaliste qui ne dépend pas de optimal_difficulty de ZPD
#         current_mastery = cls._safe_float(zpd_result.get("mastery_level", 0.5))
#         fallback_diff = min(max(current_mastery + (0.05 if is_correct else -0.1), 0.1), 1.0)
        
#         return {
#             "status": "success",
#             "action": "continue",
#             "response_type": "next_exercise",
#             "message": "Continuons l'entraînement !",
#             "encouragement": "Tu es sur la bonne voie !",
#             "next_step": {
#                 "action": "generate_exercise",
#                 "difficulty": fallback_diff,
#                 "exercise_types": ["qcm_simple", "code_completion"],
#                 "same_competence": True
#             },
#             "ui": {
#                 "show_encouragement": True,
#                 "auto_proceed": True,
#                 "delay_seconds": 2
#             }
#         }
#     @classmethod
#     def _enforce_business_rules(cls, decision: dict, zpd_result: dict) -> dict:
#         """
#         Force le respect des règles métier CRITIQUES, indépendamment de la réponse LLM.
#         """
#         mastery = cls._safe_float(zpd_result.get("mastery_level", 0))
#         zone = zpd_result.get("effective_zone", "unknown")
        
#         # 🚨 RÈGLE ABSOLUE : Si mastery >= 0.85 ET zone = mastered → FORCER 'next'
#         if mastery >= cls.MASTERY_THRESHOLD and zone == "mastered":
#             print(f"[INFO] 🎯 Mastery {mastery:.2f} >= {cls.MASTERY_THRESHOLD} + zone='mastered' → Force action='next'")
#             decision["action"] = "next"
#             decision["reason"] = f"Compétence maîtrisée ({mastery:.0%}). Passage à la compétence suivante."
#             decision["recommended_difficulty"] = 0.3  # Recommencer facile sur la nouvelle compétence
        
#         # 🚨 Valider et corriger exercise_types
#         valid_types = ["qcm", "vrai_faux", "texte_a_trous", "qcm_multiple", "code_completion", 
#                       "exercice_guide", "code_libre", "debugging", "projet_mini", "logic_puzzle"]
        
#         requested = decision.get("suggested_exercise_types", [])
#         filtered = [t for t in requested if t in valid_types]
        
#         # Si aucun type valide, fallback intelligent selon la difficulté
#         if not filtered:
#             diff = decision.get("recommended_difficulty", 0.5)
#             if diff < 0.4:
#                 filtered = ["qcm", "vrai_faux"]
#             elif diff < 0.7:
#                 filtered = ["qcm_multiple", "code_completion"]
#             else:
#                 filtered = ["code_libre", "debugging"]
        
#         decision["suggested_exercise_types"] = filtered
        
#         return decision    
#     @staticmethod
#     def process_decision(decision: dict) -> dict:
#             """
#             Traite la décision et retourne la réponse appropriée
#             selon l'action recommandée.
#             """
#             print("////////////////////////////////////////////////////")
#             action = decision.get('action')
#             reason = decision.get('reason', '')
#             message = decision.get('message', '')
#             difficulty = decision.get('recommended_difficulty', 0.5)
#             encouragement = decision.get('encouragement', '')
#             exercise_types = decision.get('suggested_exercise_types', [])
#             difficulty_adjustment = decision.get('difficulty_adjustment', 0)
#             print("action", action)
#             print("reason", reason)
#             print("message", message)
#             print("difficulty", difficulty)
#             print("encouragement", encouragement)
#             print("exercise_types", exercise_types)
#             print("difficulty_adjustment", difficulty_adjustment)
#             print("////////////////////////////////////////////////////")
#             # ─────────────────────────────────────────────
#             # 1️⃣ CONTINUE - Exercice similaire
#             # ─────────────────────────────────────────────
#             if action == 'continue':
#                 return {
#                     "status": "success",
#                     "response_type": "next_exercise",
#                     "message": message,
#                     "encouragement": encouragement,
#                     "next_step": {
#                         "action": "generate_exercise",
#                         "difficulty": difficulty,
#                         "exercise_types": exercise_types,
#                         "same_competence": True,  # Rester sur la même compétence
#                     },
#                     "ui": {
#                         "show_encouragement": True,
#                         "auto_proceed": True,
#                         "delay_seconds": 2,  # Petit délai avant le prochain exercice
#                     }
#                 }

#             # ─────────────────────────────────────────────
#             # 2️⃣ NEXT - Passer à la compétence suivante
#             # ─────────────────────────────────────────────
#             elif action == 'next':
#                 return {
#                     "status": "success",
#                     "response_type": "next_competence",
#                     "message": message,
#                     "encouragement": encouragement,
#                     "next_step": {
#                         "action": "load_next_competence",
#                         "difficulty": difficulty,
#                         "exercise_types": exercise_types,
#                         "same_competence": False,  # Nouvelle compétence
#                         "mark_current_as": "mastered",  # Marquer comme maîtrisé
#                     },
#                     "ui": {
#                         "show_celebration": True,  # 🎉 Animation de succès
#                         "show_progress_bar": True,
#                         "auto_proceed": False,  # Laisser l'élève voir sa réussite
#                     }
#                 }

#             # ─────────────────────────────────────────────
#             # 3️⃣ ADAPT - Adapter la difficulté
#             # ─────────────────────────────────────────────
#             elif action == 'adapt':
#                 direction = "easier" if difficulty_adjustment < 0 else "harder"
#                 return {
#                     "status": "success",
#                     "response_type": "adapt_difficulty",
#                     "message": message,
#                     "encouragement": encouragement,
#                     "next_step": {
#                         "action": "generate_exercise",
#                         "difficulty": difficulty,
#                         "difficulty_direction": direction,
#                         "difficulty_adjustment": difficulty_adjustment,
#                         "exercise_types": exercise_types,
#                         "same_competence": True,
#                     },
#                     "ui": {
#                         "show_encouragement": True,
#                         "show_hint": direction == "easier",  # Indice si plus facile
#                         "auto_proceed": True,
#                         "delay_seconds": 3,
#                     }
#                 }

#             # ─────────────────────────────────────────────
#             # 4️⃣ PAUSE - Recommander une pause
#             # ─────────────────────────────────────────────
#             elif action == 'pause':
#                 return {
#                     "status": "success",
#                     "response_type": "take_break",
#                     "message": message,
#                     "encouragement": encouragement,
#                     "next_step": {
#                         "action": "pause_session",
#                         "resume_difficulty": difficulty,
#                         "save_progress": True,
#                     },
#                     "ui": {
#                         "show_break_screen": True,
#                         "suggested_break_duration": 5,  # 5 minutes
#                         "show_motivational_quote": True,
#                         "auto_proceed": False,
#                         "show_resume_button": True,
#                     }
#                 }

#             # ─────────────────────────────────────────────
#             # ❌ ACTION INCONNUE
#             # ─────────────────────────────────────────────
#             else:
#                 return {
#                     "status": "error",
#                     "response_type": "unknown_action",
#                     "message": f"Action inconnue : {action}",
#                     "next_step": {
#                         "action": "generate_exercise",
#                         "difficulty": 0.5,  # Difficulté par défaut
#                     }
#                 }
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
#         """Construit le prompt pour la décision LLM avec hiérarchie multi-métriques."""
        
#         # Extraction sécurisée
#         mastery = cls._safe_float(saint_result.get("mastery", zpd_result.get("mastery_level", 0)))
#         p_correct = cls._safe_float(saint_result.get("p_correct", 0.5))
#         zone = saint_result.get("zone", zpd_result.get("effective_zone", "unknown"))
        
#         engagement = saint_result.get("engagement", {})
#         engagement_score = cls._safe_float(engagement.get("score", 0.5))
#         engagement_level = engagement.get("level", "moyen")
        
#         hint_prob = saint_result.get("hint_probability", {})
#         hint_level = hint_prob.get("level", "moyen")
        
#         anomaly = saint_result.get("anomaly", {})
#         has_anomaly = anomaly.get("has_anomaly", False)
        
#         competence_name = zpd_result.get("name", "Inconnue")
#         competence_desc = zpd_result.get("description", "")
#         zpd_zone = zpd_result.get("effective_zone", "unknown")
        
#         frustration = False
#         emotion = "neutral"
#         if emotion_data:
#             frustration = emotion_data.get("frustration_detected", False)
#             emotion = emotion_data.get("dominant_emotion", "neutral")
            
#         # Mapping pédagogique des 7 émotions
#         emotion_context = {
#             "happiness": "État positif. Maintenir ou augmenter le challenge si la performance le permet.",
#             "neutral": "État stable. Décision basée à 100% sur les indicateurs cognitifs et de performance.",
#             "sadness": "Manque de confiance ou découragement. Privilégier l'encouragement et des exercices progressifs.",
#             "anger": "Frustration active. Risque d'abandon. Réduire la difficulté ou proposer une pause si engagement faible.",
#             "surprise": "Curiosité/Intérêt. Moment idéal pour introduire un concept légèrement plus complexe.",
#             "disgust": "Rejet de la tâche ou du format. Changer de type d'exercice ou proposer une pause courte.",
#             "fear": "Anxiété face à l'échec. Sécuriser avec des exercices très guidés et feedback immédiat."
#         }
#         emotion_instruction = emotion_context.get(emotion, "État neutre par défaut.")

#         prompt = f"""Tu es un tuteur pédagogique expert en sciences cognitives et apprentissage adaptatif.
# Ta mission est d'analyser **l'ensemble des métriques** pour prendre la décision pédagogique optimale.

# ⚠️ RÈGLE D'OR ABSOLUE : 
# L'état émotionnel n'est qu'un **FACTEUR MODULATEUR**. Il influence le ton et le rythme, mais NE DICTE JAMAIS seul la décision. 
# La **Maîtrise (Mastery)** et la **Zone ZPD** restent les pilotes principaux.

# 📊 DONNÉES ACTUELLES :
# 1. COGNITIF (PRIORITÉ 1)
#    - Maîtrise estimée : {mastery:.1%}
#    - Zone ZPD : {zpd_zone}
#    - Probabilité de succès (SAINT+) : {p_correct:.1%}
   
# 2. PERFORMANCE (PRIORITÉ 2)
#    - Dernière réponse : {"RÉUSSIE" if is_correct else "ÉCHOUÉE"}
#    - Temps : {time_spent}s | Indices utilisés : {hints_used}
#    - Engagement global : {engagement_level} ({engagement_score:.0%})
#    - Besoin d'aide prédit : {hint_level}
#    - Anomalie comportementale : {"Oui" if has_anomaly else "Non"}

# 3. ÉMOTIONNEL (PRIORITÉ 3 - MODULATEUR)
#    - Émotion dominante : {emotion}
#    - Frustration détectée : {"OUI" if frustration else "Non"}
#    - Interprétation pédagogique : {emotion_instruction}

# 🧠 CADRE DE DÉCISION MULTI-CRITÈRES (À SUIVRE STRICTEMENT) :
# 1. Évalue d'abord la Maîtrise & ZPD :
#    - Si Maîtrise estimée ≥ 0.85 ET zone = "mastered" → Action : `next`
#    - Si zone = "frustration" OU mastery < 0.40 → Action : `adapt` (plus facile) ou `pause`
# 2. Croise avec la Performance :
#    - Succès rapide + mastery élevée → `adapt` (plus difficile) ou `continue` avec défi
#    - Échec + temps long + indices élevés → `adapt` (plus facile/guidé)
# 3. Module avec l'Émotion & Engagement :
#    - `anger`/`fear`/`disgust` + engagement faible → Forte probabilité de `pause` ou `adapt` très guidé
#    - `sadness` → `continue` avec encouragement fort, ou `adapt` léger (+0.05)
#    - `happiness`/`surprise` + réussite → Maintenir ou augmenter la trajectoire
#    - `neutral` → Décision 100% cognitive. Ignore l'émotion pour le calcul.

# 📚 TYPES D'EXERCICES DISPONIBLES :
# - Faciles/Guidés : qcm, vrai_faux, texte_a_trous, exercice_guide
# - Intermédiaires : qcm_multiple, code_completion
# - Avancés : code_libre, debugging, projet_mini, logic_puzzle

# ⚙️ ACTIONS POSSIBLES :
# - `continue` : Progression standard (ajustement ±0.05)
# - `next` : Compétence suivante (uniquement si mastery ≥ 0.85 ET zone = mastered)
# - `adapt` : Changement significatif de difficulté (>0.1) ou changement de type
# - `pause` : Arrêt temporaire (uniquement si frustration élevée + engagement < 30% + émotion négative)

# 📦 FORMAT DE RÉPONSE (JSON STRICT) :
# {{
#   "action": "continue",
#   "reason": "Synthèse en 1 phrase croisant Maîtrise, Performance et Émotion",
#   "message": "Message pédagogique direct pour l'élève",
#   "difficulty_adjustment": 0.0,
#   "recommended_difficulty": 0.5,
#   "suggested_exercise_types": ["type1", "type2"],
#   "encouragement": "Message de soutien contextuel"
# }}

# ⚠️ CONSIGNES CRITIQUES :
# - `recommended_difficulty` ∈ [0.1, 1.0]. Calcule-le en fonction de mastery et p_correct.
# - Si mastery < 0.4, NE PROPOSE JAMAIS d'exercices avancés.
# - Si engagement < 30% ET émotion négative → privilégie `pause` ou `adapt` très guidé.
# - Réponds UNIQUEMENT avec le JSON valide. Aucune balise markdown, aucun texte avant ou après.
# - Si tu ne peux pas respecter le format, retourne {{}}.
# """
        # return prompt
    # ══════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════
    




    """
    Moteur de décision pédagogique adaptative.
    Prend en entrée les métriques cognitives, émotionnelles et de performance,
    et retourne une recommandation structurée pour l'expérience apprenant.
    """
    
    # ══════════════════════════════════════════════════════════
    # SEUILS DE DÉCISION
    # ══════════════════════════════════════════════════════════
    
    MASTERY_THRESHOLD = 0.85          # Seuil de maîtrise
    FRUSTRATION_THRESHOLD = 0.40      # Seuil de frustration
    HIGH_ENGAGEMENT = 0.70            # Engagement élevé
    LOW_ENGAGEMENT = 0.30             # Engagement faible
    ANOMALY_SEVERITY_HIGH = "high"    # Anomalie grave

    # ══════════════════════════════════════════════════════════
    # MÉTHODE AVEC LLM (OLLAMA) - VERSION CORRIGÉE
    # ══════════════════════════════════════════════════════════
    
    @classmethod
    def make_decision_with_llm(
        cls,
        user_id: str,
        competence_id: str,
        zpd_result: dict,
        emotion_data: dict = None,
        is_correct: bool = True,
        time_spent: int = 0,
        hints_used: int = 0,
    ) -> dict:
        """
        Décision enrichie avec LLM (Ollama).
        Recommande dynamiquement la difficulté et le type d'exercice.
        Les métriques SAINT+ sont extraites du résultat ZPD.
        """
        # Extraire saint_result de zpd_result
        saint_result = zpd_result.get("saint_metrics", {}) if zpd_result else {}

        try:
            # Construire le prompt
            prompt = cls._build_decision_prompt(
                saint_result=saint_result,
                zpd_result=zpd_result,
                emotion_data=emotion_data,
                is_correct=is_correct,
                time_spent=time_spent,
                hints_used=hints_used
            )
            
            # Appeler Ollama
            response_data = OllamaService.generate_json(prompt, temperature=0.3)
            print("**********json************")
            print(response_data)    
            print("**********************")    
            
            # ✅ VALIDATION CRITIQUE : vérifier que l'LLM a bien répondu
            if not response_data or not isinstance(response_data, dict):
                raise ValueError("LLM returned invalid or empty response")
            if "action" not in response_data:
                raise ValueError("LLM response missing required 'action' field")
            
            # Appliquer les règles métier
            response_data = cls._enforce_business_rules(response_data, zpd_result)
            print("**********forced************")
            print(response_data)    
            print("**********************")    
            
            # ✅ RETOURNER la décision traitée (CORRECTION PRINCIPALE)
            result = cls.process_decision(response_data)
            print("*********llm*************")
            print(result)    
            print("**********************")
            return result  # ←←← LE FIX : on retourne VRAIMENT le résultat
            
        except Exception as e:
            print(f"[WARN] LLM decision failed: {e}")
            # Fallback uniquement en cas d'erreur réelle
        
        # 🛡️ FALLBACK : exécuté SEULEMENT si LLM échoue
        current_mastery = cls._safe_float(zpd_result.get("mastery_level", 0.5))
        fallback_diff = min(max(current_mastery + (0.05 if is_correct else -0.1), 0.1), 1.0)
        
        # Sélection dynamique des exercices selon la difficulté
        if fallback_diff < 0.4:
            exercise_types = ["qcm", "vrai_faux"]
        elif fallback_diff < 0.7:
            exercise_types = ["qcm_multiple", "code_completion"]
        else:
            exercise_types = ["code_libre", "debugging"]
        
        return {
            "status": "success",
            "action": "continue",
            "response_type": "next_exercise",
            "message": "Continuons l'entraînement !",
            "encouragement": "Tu es sur la bonne voie !",
            "next_step": {
                "action": "generate_exercise",
                "difficulty": fallback_diff,
                "exercise_types": exercise_types,
                "same_competence": True
            },
            "ui": {
                "show_encouragement": True,
                "auto_proceed": True,
                "delay_seconds": 2
            },
            "meta": {
                "decision_source": "fallback",
                "mastery": current_mastery,
                "is_correct": is_correct
            }
        }

    @classmethod
    def _enforce_business_rules(cls, decision: dict, zpd_result: dict) -> dict:
        """
        Force le respect des règles métier CRITIQUES, indépendamment de la réponse LLM.
        """
        mastery = cls._safe_float(zpd_result.get("mastery_level", 0))
        zone = zpd_result.get("effective_zone", "unknown")
        
        # 🚨 RÈGLE ABSOLUE : Si mastery >= 0.85 ET zone = mastered → FORCER 'next'
        if mastery >= cls.MASTERY_THRESHOLD and zone == "mastered":
            print(f"[INFO] 🎯 Mastery {mastery:.2f} >= {cls.MASTERY_THRESHOLD} + zone='mastered' → Force action='next'")
            decision["action"] = "next"
            decision["reason"] = f"Compétence maîtrisée ({mastery:.0%}). Passage à la compétence suivante."
            decision["recommended_difficulty"] = 0.3  # Recommencer facile sur la nouvelle compétence
        
        # 🚨 Valider et corriger exercise_types
        valid_types = ["qcm", "vrai_faux", "texte_a_trous", "qcm_multiple", "code_completion", 
                      "exercice_guide", "code_libre", "debugging", "projet_mini", "logic_puzzle"]
        
        requested = decision.get("suggested_exercise_types", [])
        filtered = [t for t in requested if t in valid_types]
        
        # Si aucun type valide, fallback intelligent selon la difficulté
        if not filtered:
            diff = decision.get("recommended_difficulty", 0.5)
            if diff < 0.4:
                filtered = ["qcm", "vrai_faux"]
            elif diff < 0.7:
                filtered = ["qcm_multiple", "code_completion"]
            else:
                filtered = ["code_libre", "debugging"]
        
        decision["suggested_exercise_types"] = filtered
        
        # 🆕 Valider l'action (sécurité supplémentaire)
        valid_actions = ["continue", "next", "adapt", "pause"]
        if decision.get("action") not in valid_actions:
            decision["action"] = "continue"
            decision["reason"] = "Action LLM invalide corrigée par règles métier."
        
        # 🆕 Clamp de la difficulté recommandée [0.1, 1.0]
        if "recommended_difficulty" in decision:
            decision["recommended_difficulty"] = min(
                max(decision["recommended_difficulty"], 0.1), 1.0
            )
        
        return decision    
    
    @staticmethod
    def process_decision(decision: dict) -> dict:
        """
        Traite la décision et retourne la réponse appropriée
        selon l'action recommandée.
        """
        print("////////////////////////////////////////////////////")
        action = decision.get('action')
        reason = decision.get('reason', '')
        message = decision.get('message', '')
        difficulty = decision.get('recommended_difficulty', 0.5)
        encouragement = decision.get('encouragement', '')
        exercise_types = decision.get('suggested_exercise_types', [])
        difficulty_adjustment = decision.get('difficulty_adjustment', 0)
        print("action", action)
        print("reason", reason)
        print("message", message)
        print("difficulty", difficulty)
        print("encouragement", encouragement)
        print("exercise_types", exercise_types)
        print("difficulty_adjustment", difficulty_adjustment)
        print("////////////////////////////////////////////////////")
        
        # ─────────────────────────────────────────────
        # 1️⃣ CONTINUE - Exercice similaire
        # ─────────────────────────────────────────────
        if action == 'continue':
            return {
                "status": "success",
                "action": "continue",
                "response_type": "next_exercise",
                "message": message,
                "encouragement": encouragement,
                "next_step": {
                    "action": "generate_exercise",
                    "difficulty": difficulty,
                    "exercise_types": exercise_types,
                    "same_competence": True,
                },
                "ui": {
                    "show_encouragement": True,
                    "auto_proceed": True,
                    "delay_seconds": 2,
                }
            }

        # ─────────────────────────────────────────────
        # 2️⃣ NEXT - Passer à la compétence suivante
        # ─────────────────────────────────────────────
        elif action == 'next':
            return {
                "status": "success",
                "action": "next",
                "response_type": "next_competence",
                "message": message,
                "encouragement": encouragement,
                "next_step": {
                    "action": "load_next_competence",
                    "difficulty": difficulty,
                    "exercise_types": exercise_types,
                    "same_competence": False,
                    "mark_current_as": "mastered",
                },
                "ui": {
                    "show_celebration": True,
                    "show_progress_bar": True,
                    "auto_proceed": False,
                }
            }

        # ─────────────────────────────────────────────
        # 3️⃣ ADAPT - Adapter la difficulté
        # ─────────────────────────────────────────────
        elif action == 'adapt':
            direction = "easier" if difficulty_adjustment < 0 else "harder"
            return {
                "status": "success",
                "action": "adapt",
                "response_type": "adapt_difficulty",
                "message": message,
                "encouragement": encouragement,
                "next_step": {
                    "action": "generate_exercise",
                    "difficulty": difficulty,
                    "difficulty_direction": direction,
                    "difficulty_adjustment": difficulty_adjustment,
                    "exercise_types": exercise_types,
                    "same_competence": True,
                },
                "ui": {
                    "show_encouragement": True,
                    "show_hint": direction == "easier",
                    "auto_proceed": True,
                    "delay_seconds": 3,
                }
            }

        # ─────────────────────────────────────────────
        # 4️⃣ PAUSE - Recommander une pause
        # ─────────────────────────────────────────────
        elif action == 'pause':
            return {
                "status": "success",
                "action": "pause",
                "response_type": "take_break",
                "message": message,
                "encouragement": encouragement,
                "next_step": {
                    "action": "pause_session",
                    "resume_difficulty": difficulty,
                    "save_progress": True,
                },
                "ui": {
                    "show_break_screen": True,
                    "suggested_break_duration": 5,
                    "show_motivational_quote": True,
                    "auto_proceed": False,
                    "show_resume_button": True,
                }
            }

        # ─────────────────────────────────────────────
        # ❌ ACTION INCONNUE
        # ─────────────────────────────────────────────
        else:
            return {
                "status": "error",
                "action": "unknown",
                "response_type": "unknown_action",
                "message": f"Action inconnue : {action}",
                "next_step": {
                    "action": "generate_exercise",
                    "difficulty": 0.5,
                }
            }

    # ══════════════════════════════════════════════════════════
    # PROMPT BUILDER
    # ══════════════════════════════════════════════════════════
    
    @classmethod
    def _build_decision_prompt(
        cls,
        saint_result: dict,
        zpd_result: dict,
        emotion_data: dict,
        is_correct: bool,
        time_spent: int,
        hints_used: int
    ) -> str:
        """Construit le prompt pour la décision LLM avec hiérarchie multi-métriques."""
        
        # Extraction sécurisée
        mastery = cls._safe_float(saint_result.get("mastery", zpd_result.get("mastery_level", 0)))
        p_correct = cls._safe_float(saint_result.get("p_correct", 0.5))
        zone = saint_result.get("zone", zpd_result.get("effective_zone", "unknown"))
        
        engagement = saint_result.get("engagement", {})
        engagement_score = cls._safe_float(engagement.get("score", 0.5))
        engagement_level = engagement.get("level", "moyen")
        
        hint_prob = saint_result.get("hint_probability", {})
        hint_level = hint_prob.get("level", "moyen")
        
        anomaly = saint_result.get("anomaly", {})
        has_anomaly = anomaly.get("has_anomaly", False)
        
        competence_name = zpd_result.get("name", "Inconnue")
        competence_desc = zpd_result.get("description", "")
        zpd_zone = zpd_result.get("effective_zone", "unknown")
        
        frustration = False
        emotion = "neutral"
        if emotion_data:
            frustration = emotion_data.get("frustration_detected", False)
            emotion = emotion_data.get("dominant_emotion", "neutral")
            
        # Mapping pédagogique des 7 émotions
        emotion_context = {
            "happiness": "État positif. Maintenir ou augmenter le challenge si la performance le permet.",
            "neutral": "État stable. Décision basée à 100% sur les indicateurs cognitifs et de performance.",
            "sadness": "Manque de confiance ou découragement. Privilégier l'encouragement et des exercices progressifs.",
            "anger": "Frustration active. Risque d'abandon. Réduire la difficulté ou proposer une pause si engagement faible.",
            "surprise": "Curiosité/Intérêt. Moment idéal pour introduire un concept légèrement plus complexe.",
            "disgust": "Rejet de la tâche ou du format. Changer de type d'exercice ou proposer une pause courte.",
            "fear": "Anxiété face à l'échec. Sécuriser avec des exercices très guidés et feedback immédiat."
        }
        emotion_instruction = emotion_context.get(emotion, "État neutre par défaut.")

        prompt = f"""Tu es un tuteur pédagogique expert en sciences cognitives et apprentissage adaptatif.
Ta mission est d'analyser **l'ensemble des métriques** pour prendre la décision pédagogique optimale.

⚠️ RÈGLE D'OR ABSOLUE : 
L'état émotionnel n'est qu'un **FACTEUR MODULATEUR**. Il influence le ton et le rythme, mais NE DICTE JAMAIS seul la décision. 
La **Maîtrise (Mastery)** et la **Zone ZPD** restent les pilotes principaux.

📊 DONNÉES ACTUELLES :
1. COGNITIF (PRIORITÉ 1)
   - Maîtrise estimée : {mastery:.1%}
   - Zone ZPD : {zpd_zone}
   - Probabilité de succès (SAINT+) : {p_correct:.1%}
   
2. PERFORMANCE (PRIORITÉ 2)
   - Dernière réponse : {"RÉUSSIE" if is_correct else "ÉCHOUÉE"}
   - Temps : {time_spent}s | Indices utilisés : {hints_used}
   - Engagement global : {engagement_level} ({engagement_score:.0%})
   - Besoin d'aide prédit : {hint_level}
   - Anomalie comportementale : {"Oui" if has_anomaly else "Non"}

3. ÉMOTIONNEL (PRIORITÉ 3 - MODULATEUR)
   - Émotion dominante : {emotion}
   - Frustration détectée : {"OUI" if frustration else "Non"}
   - Interprétation pédagogique : {emotion_instruction}

🧠 CADRE DE DÉCISION MULTI-CRITÈRES (À SUIVRE STRICTEMENT) :
1. Évalue d'abord la Maîtrise & ZPD :
   - Si Maîtrise estimée ≥ 0.85 ET zone = "mastered" → Action : `next`
   - Si zone = "frustration" OU mastery < 0.40 → Action : `adapt` (plus facile) ou `pause`
2. Croise avec la Performance :
   - Succès rapide + mastery élevée → `adapt` (plus difficile) ou `continue` avec défi
   - Échec + temps long + indices élevés → `adapt` (plus facile/guidé)
3. Module avec l'Émotion & Engagement :
   - `anger`/`fear`/`disgust` + engagement faible → Forte probabilité de `pause` ou `adapt` très guidé
   - `sadness` → `continue` avec encouragement fort, ou `adapt` léger (+0.05)
   - `happiness`/`surprise` + réussite → Maintenir ou augmenter la trajectoire
   - `neutral` → Décision 100% cognitive. Ignore l'émotion pour le calcul.

📚 TYPES D'EXERCICES DISPONIBLES :
- Faciles/Guidés : qcm, vrai_faux, texte_a_trous, exercice_guide
- Intermédiaires : qcm_multiple, code_completion
- Avancés : code_libre, debugging, projet_mini, logic_puzzle

⚙️ ACTIONS POSSIBLES :
- `continue` : Progression standard (ajustement ±0.05)
- `next` : Compétence suivante (uniquement si mastery ≥ 0.85 ET zone = mastered)
- `adapt` : Changement significatif de difficulté (>0.1) ou changement de type
- `pause` : Arrêt temporaire (uniquement si frustration élevée + engagement < 30% + émotion négative)

📦 FORMAT DE RÉPONSE (JSON STRICT) :
{{
  "action": "continue",
  "reason": "Synthèse en 1 phrase croisant Maîtrise, Performance et Émotion",
  "message": "Message pédagogique direct pour l'élève",
  "difficulty_adjustment": 0.0,
  "recommended_difficulty": 0.5,
  "suggested_exercise_types": ["type1", "type2"],
  "encouragement": "Message de soutien contextuel"
}}

⚠️ CONSIGNES CRITIQUES :
- `recommended_difficulty` ∈ [0.1, 1.0]. Calcule-le en fonction de mastery et p_correct.
- Si mastery < 0.4, NE PROPOSE JAMAIS d'exercices avancés.
- Si engagement < 30% ET émotion négative → privilégie `pause` ou `adapt` très guidé.
- Réponds UNIQUEMENT avec le JSON valide. Aucune balise markdown, aucun texte avant ou après.
- Si tu ne peux pas respecter le format, retourne {{}}.
"""
        return prompt

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



