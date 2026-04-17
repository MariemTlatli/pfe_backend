"""
Service Ollama - Interface avec le modèle GenAI local.
"""

import requests
import json
import re
from app.config import Config


class OllamaService:
    """Interface pour communiquer avec Ollama (LLM local)."""
    
    BASE_URL = Config.OLLAMA_BASE_URL
    MODEL = Config.OLLAMA_MODEL
    TIMEOUT = Config.OLLAMA_TIMEOUT
    
    @staticmethod
    def generate(prompt, temperature=None, max_tokens=4000, system_prompt=None):
        """
        Générer du contenu avec Ollama.
        
        Args:
            prompt (str): Le prompt utilisateur
            temperature (float, optional): Créativité (0-1)
            max_tokens (int): Nombre max de tokens
            system_prompt (str, optional): Instructions système
            
        Returns:
            str: Réponse du modèle
            
        Raises:
            Exception: Si erreur de communication
        """
        url = f"{OllamaService.BASE_URL}/api/generate"
        
        if temperature is None:
            temperature = Config.OLLAMA_TEMPERATURE
        
        payload = {
            "model": OllamaService.MODEL,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }, 
            "format": "json",
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=OllamaService.TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('response', '').strip()
        
        except requests.exceptions.Timeout:
            raise Exception(f"Timeout: Ollama n'a pas répondu en {OllamaService.TIMEOUT}s")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Impossible de se connecter à Ollama sur {OllamaService.BASE_URL}")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Erreur HTTP Ollama: {e}")
        except Exception as e:
            raise Exception(f"Erreur Ollama: {str(e)}")
    
    @staticmethod
    def generate_json(prompt, system_prompt=None, temperature=0.3, max_tokens=2048):
        """
        Générer une réponse JSON structurée et auto-réparée.
        """
        if system_prompt is None:
            system_prompt = (
                "Tu es un assistant qui répond UNIQUEMENT en JSON valide. "
                "Ne pas ajouter de texte avant ou après le JSON. "
                "Pas de markdown, juste du JSON brut."
            )
        
        # ✅ Passer max_tokens explicitement pour éviter la troncature Ollama
        response_text = OllamaService.generate(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
        )
        
        # 1️⃣ Nettoyage initial
        response_text = response_text.strip()
        
        # 2️⃣ Extraction robuste du bloc JSON (ignore texte/markdown parasite)
        start = response_text.find('{')
        end = response_text.rfind('}')
        
        if start != -1 and end != -1:
            response_text = response_text[start : end + 1]
        else:
            # Fallback regex pour les cas où find/rfind échoue
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text, flags=re.IGNORECASE)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            
        # 3️⃣ Normalisation des caractères de contrôle
        response_text = OllamaService._normalize_json_string(response_text)
        
        # 4️⃣ Parsing avec réparation automatique
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            repaired = OllamaService._repair_json(response_text)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"JSON invalide même après réparation: {e}\n"
                    f"Brut: {response_text[:300]}...\n"
                    f"Réparé: {repaired[:300]}..."
                )

    @staticmethod
    def _repair_json(text):
        """
        Répare automatiquement les JSON tronqués ou mal formatés par les LLM :
        - Virgules superflues
        - Accolades/crochets non fermés
        """
        if not text:
            return text
            
        # Supprime les virgules traînantes avant } ou ]
        text = re.sub(r',\s*([}\]])', r'\1', text)
        # Ajoute les virgules manquantes entre }{ ou ][
        text = re.sub(r'(?<=[\}\]])\s*(?=[\{\[])', ', ', text)
        
        # ✅ Fermeture automatique des structures ouvertes (stack-based)
        stack = []
        in_string = False
        escape_next = False
        
        for char in text:
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
                
            if not in_string:
                if char in '{[':
                    stack.append(char)
                elif char == '}' and stack and stack[-1] == '{':
                    stack.pop()
                elif char == ']' and stack and stack[-1] == '[':
                    stack.pop()
                    
        # Ajoute les fermetures manquantes dans l'ordre inverse
        closings = ['}' if c == '{' else ']' for c in reversed(stack)]
        text += ''.join(closings)
        
        return text
    @staticmethod
    def _normalize_json_string(text):
        """
        Normaliser une chaîne brute JSON en échappant correctement les caractères de contrôle.
        
        Cela corrige les cas où Ollama retourne du JSON avec des vraies ruptures de ligne
        au lieu de \n échappé dans les chaînes de caractères.
        
        Args:
            text (str): Texte JSON brut potentiellement mal formé
            
        Returns:
            str: Texte JSON normalisé et valide
        """
        result = []
        in_string = False
        escape_next = False
        i = 0
        
        while i < len(text):
            char = text[i]
            
            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue
            
            if char == '\\' and in_string:
                result.append(char)
                escape_next = True
                i += 1
                continue
            
            if char == '"':
                in_string = not in_string
                result.append(char)
                i += 1
                continue
            
            # Si on est dans une string et qu'on rencontre un caractère de contrôle
            if in_string:
                if char == '\n':
                    result.append('\\n')
                    i += 1
                    continue
                elif char == '\r':
                    result.append('\\r')
                    i += 1
                    continue
                elif char == '\t':
                    result.append('\\t')
                    i += 1
                    continue
                elif ord(char) < 32:  # Autres caractères de contrôle
                    result.append(f'\\u{ord(char):04x}')
                    i += 1
                    continue
            
            result.append(char)
            i += 1
        
        return ''.join(result)
    
    @staticmethod
    def _repair_json(text):
        """
        Appliquer des heuristiques légères pour tenter de réparer du JSON
        généré par le modèle lorsqu'il manque une virgule ou présente une
        syntaxe légèrement incorrecte.
        """
        # insérer une virgule entre deux objets/tableaux adjacents (}{, ][) sans
        # virgule
        repaired = re.sub(r'(?<=[\}\]])\s*(?=[\{\[])', ', ', text)
        # supprimer les virgules superflues avant ] ou }
        repaired = re.sub(r',\s*(?=[\}\]])', '', repaired)
        return repaired
    
    @staticmethod
    def is_available():
        """
        Vérifier si Ollama est accessible.
        
        Returns:
            bool: True si disponible
        """
        try:
            response = requests.get(
                f"{OllamaService.BASE_URL}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def get_models():
        """
        Lister les modèles disponibles.
        
        Returns:
            list: Liste des modèles
        """
        try:
            response = requests.get(
                f"{OllamaService.BASE_URL}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except:
            return []