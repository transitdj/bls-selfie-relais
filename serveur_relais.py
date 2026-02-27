# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, redirect, make_response
from flask_cors import CORS
import requests
import uuid
import time
import os
import json
import threading

app = Flask(__name__)
CORS(app)

# Stockage des sessions
sessions = {}

# Configuration BLS
BLS_BASE_URL = "https://algeria.blsspainglobal.com"
BLS_LOGIN_URL = f"{BLS_BASE_URL}/dza/account/login"
BLS_LOGIN_CAPTCHA_URL = f"{BLS_BASE_URL}/dza/newcaptcha/logincaptcha"
BLS_SELFIE_URL = f"{BLS_BASE_URL}/dza/appointment/livenessrequest"

def login_to_bls(email, password):
    """Fonction pour se connecter à BLS et récupérer les cookies"""
    session = requests.Session()
    
    # Étape 1: Page de login (pour avoir les cookies initiaux)
    session.get(BLS_LOGIN_URL)
    
    # Étape 2: Envoyer l'email
    login_data = {
        "Email": email,
        "__RequestVerificationToken": extract_token(session)
    }
    session.post(BLS_LOGIN_URL, data=login_data)
    
    # Étape 3: Envoyer le mot de passe (on ignore le captcha pour simplifier)
    password_data = {
        "Password": password,
        "__RequestVerificationToken": extract_token(session)
    }
    session.post(BLS_LOGIN_CAPTCHA_URL, data=password_data)
    
    return session.cookies.get_dict()

def extract_token(session):
    """Extrait le token CSRF d'une page"""
    # Version simplifiée - dans la vraie vie il faudrait parser le HTML
    return "faketoken"

@app.route('/')
def home():
    return "✅ Serveur passerelle BLS actif"

@app.route('/api/create-session', methods=['POST'])
def create_session():
    """Reçoit les identifiants du PC et prépare une session pour le téléphone"""
    data = request.json
    session_id = str(uuid.uuid4())[:8]
    
    # Stocker les identifiants temporairement
    sessions[session_id] = {
        'email': data.get('email'),
        'password': data.get('password'),
        'status': 'en_attente',
        'cookies': None,
        'created_at': time.time()
    }
    
    print(f"✅ Session {session_id} créée pour {data.get('email')}")
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'lien': f"{request.host_url}connecter/{session_id}"
    })

@app.route('/connecter/<session_id>')
def connecter_session(session_id):
    """Page pour le téléphone - se connecte automatiquement à BLS"""
    if session_id not in sessions:
        return "Session invalide", 404
    
    session_data = sessions[session_id]
    
    # Afficher une page de chargement
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Connexion BLS</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial; background: #f0f0f0; padding: 20px; }}
            .container {{ max-width: 400px; margin: 0 auto; background: white; padding: 25px; border-radius: 15px; text-align: center; }}
            .spinner {{ border: 4px solid #f3f3f3; border-top: 4px solid #25D366; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 20px auto; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📱 Connexion à BLS</h2>
            <div class="spinner"></div>
            <p>Connexion en cours pour <strong>{session_data['email']}</strong>...</p>
            <p id="status">Préparation de la session...</p>
        </div>
        
        <script>
            // Appeler le serveur pour obtenir la redirection
            fetch('/api/rediriger/{session_id}')
                .then(r => r.json())
                .then(data => {{
                    if (data.success) {{
                        document.getElementById('status').innerHTML = '✅ Connecté ! Redirection...';
                        window.location.href = data.url;
                    }} else {{
                        document.getElementById('status').innerHTML = '❌ Erreur: ' + data.error;
                    }}
                }});
        </script>
    </body>
    </html>
    """

@app.route('/api/rediriger/<session_id>')
def rediriger_vers_bls(session_id):
    """API appelée par le téléphone pour obtenir la redirection vers BLS"""
    if session_id not in sessions:
        return jsonify({'success': False, 'error': 'Session invalide'}), 404
    
    session_data = sessions[session_id]
    
    try:
        # Se connecter à BLS
        cookies = login_to_bls(session_data['email'], session_data['password'])
        
        # Créer une réponse de redirection
        response = make_response(redirect(BLS_SELFIE_URL))
        
        # Ajouter tous les cookies BLS
        for name, value in cookies.items():
            response.set_cookie(name, value, domain='.blsspainglobal.com', path='/')
        
        # Marquer la session comme utilisée
        session_data['status'] = 'utilise'
        session_data['cookies'] = cookies
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/statut/<session_id>')
def statut_session(session_id):
    """Vérifie si la session a été utilisée"""
    if session_id not in sessions:
        return jsonify({'status': 'inconnu'})
    
    return jsonify({
        'status': sessions[session_id]['status']
    })

@app.route('/api/termine/<session_id>', methods=['POST'])
def termine_session(session_id):
    """Marque la session comme terminée (selfie fait)"""
    if session_id in sessions:
        sessions[session_id]['status'] = 'termine'
    return jsonify({'success': True})

# Nettoyage automatique des sessions expirées
def nettoyer_sessions():
    while True:
        time.sleep(300)  # Toutes les 5 minutes
        maintenant = time.time()
        a_supprimer = []
        for sid, data in sessions.items():
            if maintenant - data['created_at'] > 3600:  # 1 heure
                a_supprimer.append(sid)
        for sid in a_supprimer:
            del sessions[sid]
            print(f"🧹 Session {sid} supprimée")

threading.Thread(target=nettoyer_sessions, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
