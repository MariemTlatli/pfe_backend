"""
Service Gemini - Interface avec l'API Google Generative AI via REST.
"""

import requests
import json
from app.config import Config

class GeminiService:
    """Interface pour communiquer avec Gemini API (REST)."""
    
    API_KEY = Config.GEMINI_API_KEY
    MODEL = Config.GEMINI_MODEL

    @staticmethod
    def generate_hints(exercise_data):
        """
        Génère 4 indices spécifiques pour aider à résoudre l'exercice donné.
        """
        if not GeminiService.API_KEY:
            return ["Désolé, l'API Gemini n'est pas configurée.", "Veuillez ajouter GEMINI_API_KEY.", "", ""]

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GeminiService.MODEL}:generateContent?key={GeminiService.API_KEY}"
        
        question = exercise_data.get("question", "")
        context = exercise_data.get("context", "")
        correct_answer = exercise_data.get("correct_answer", "")
        
        prompt = f"""
        Tu es un tuteur pédagogique expert. Ta mission est de générer EXACTEMENT 4 indices progressifs pour aider un élève à résoudre l'exercice suivant sans donner directement la réponse.

        EXERCICE:
        Question: {question}
        Réponse correcte (pour ton information): {correct_answer}

        CONSIGNES:
        1. Les indices doivent être de plus en plus révélateurs.
        2. Le premier doit être subtil, le dernier doit être une aide majeure.
        3. Ne donne PAS la réponse finale.
        4. Réponds UNIQUEMENT par un tableau JSON de 4 chaînes de caractères.

        FORMAT ATTENDU:
        ["Indice 1", "Indice 2", "Indice 3", "Indice 4"]
        """

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 1024,
                "stopSequences": []
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Extraction du texte de la réponse
            candidates = data.get("candidates", [])
            if not candidates:
                return ["Erreur: Aucun candidat reçu de Gemini."]
                
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            # Nettoyage et parsing JSON
            text = text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            elif text.startswith("```"):
                text = text.replace("```", "").strip()
                
            hints = json.loads(text)
            if isinstance(hints, list) and len(hints) >= 4:
                return hints[:4]
            return ["Erreur de formatage des indices."]
            
        except Exception as e:
            print(f"Erreur GeminiService: {str(e)}")
            return [f"Erreur lors de la génération: {str(e)}"]
