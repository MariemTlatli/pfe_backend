cd backend
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python run.py
=======================================================
- [x] Créer & Activer l'environnement virtuel Python
- [x] Créer le fichier requirements.txt & Installer les dépendances
- [x] Configuration MongoDB
- [x] Créer la structure de dossiers
- [x] Créer Collections MongoDB
  - [x] Collection : users
   {
     _id: ObjectId,
     username: String (unique),
     email: String (unique),
     password: String (hashé),
     created_at: DateTime
   }

  - [x] Collection : interests
   {
     _id: ObjectId,
     name: String (unique),
     description: String,
     icon: String (URL),
     subcategories: [{ name: String }]
   }

  - [x] Collection : user_interests
   {
     _id: ObjectId,
     user_id: String (ref users._id),
     interest_id: String (ref interests._id),
     selected_at: DateTime
   }
   Index unique : (user_id, interest_id)

- [x] Créer app/services/auth_service.py
   - [x] Méthode register(username, email, password)
      - [x] Vérifier unicité email/username
      - [x] Hasher le mot de passe avec bcrypt
      - [x] Insérer dans MongoDB
      - [x] Générer token JWT
   
   - [x] Méthode login(email, password)
      - [x] Chercher l'utilisateur
      - [x] Vérifier le mot de passe
      - [x] Générer token JWT
- [x] Créer app/services/interest_service.py
     - [x] get_all_interests() → Liste tous les intérêts
     - [x] get_interest_by_id(interest_id) → Détails d'un intérêt
     - [x] get_user_interests(user_id) → Intérêts de l'utilisateur
     - [x] select_interests(user_id, interest_ids) → Sélectionner
     - [x] deselect_interest(user_id, interest_id) → Désélectionner
- [x] Créer app/seeds/seed_interests.py
   ☐ Vérifier si la collection est vide
   ☐ Insérer 5 intérêts :
      ☐ Programmation (Python, JavaScript, Java, C++)
      ☐ Mathématiques (Algèbre, Géométrie, Statistiques)
      ☐ Langues (Anglais, Espagnol, Français)
      ☐ Sciences (Physique, Chimie, Biologie)
      ☐ Histoire (Ancienne, Médiévale, Moderne)
   
- [x] Créer les index MongoDB :
      ☐ interests.name (unique)
      ☐ users.email (unique)
      ☐ users.username (unique)
      ☐ user_interests (user_id, interest_id) (unique composite)
- [x] Documentation Swagger (Flask-Smorest) par la configuration OpenAPI

- [ ] Lancer : python run.py
- [ ] Tester : http://localhost:5000/docs
- [ ] Vérifier : http://localhost:5000/openapi.json

=======================================================
Checklist Fonctionnelle :

☐ Un utilisateur peut s'inscrire
☐ Un utilisateur peut se connecter
☐ Un utilisateur reçoit un token JWT
☐ Un utilisateur peut voir tous les intérêts (sans auth)
☐ Un utilisateur peut sélectionner des intérêts (avec auth)
☐ Un utilisateur peut voir ses intérêts (avec auth)
☐ Un utilisateur peut désélectionner un intérêt (avec auth)
☐ Les doublons sont gérés (intérêt déjà sélectionné)
☐ Les erreurs sont claires et cohérentes




{
  "username": "mariem",
  "email": "mariem@example.com",
  "password": "mariem"
}

{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc3Mjg4MTIyOSwianRpIjoiNGNjNDVjNzQtY2VkZS00MWI0LTk2ZjMtNWVmYzc4YTQ0M2UzIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjY5YWMwNTRjMzMxMDA1YWI3ZmExMjQ1MSIsIm5iZiI6MTc3Mjg4MTIyOSwiY3NyZiI6IjYzMmNkYjExLWYyNjQtNDM0ZC05NDJkLTNmNGQ4ZDYyMmRmYyIsImV4cCI6MTc3Mjk2NzYyOX0.i25yEVrMRTIgR7sZvkEwXD7mCkH8kDfJhi1F_ekrdNk",
    "email": "mariem@example.com",
    "user_id": "69ac054c331005ab7fa12451",
    "username": "mariem"
  },
  "message": "Inscription réussie.",
  "success": true
}