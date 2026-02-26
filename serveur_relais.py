# -*- coding: latin-1 -*-
from flask import Flask, request, jsonify, redirect, make_response, render_template_string
from flask_cors import CORS
import requests
import uuid
import time
import threading
app = Flask(__name__)
CORS(app)

# Stockage temporaire des sessions
sessions = {}

# Page d'instruction pour le selfie
PAGE_INSTRUCTION = """
<!DOCTYPE html>
<html>
<head>
    <title>Selfie BLS</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial; background: #f0f0f0; padding: 20px; }}
        .container {{ max-width: 400px; margin: 0 auto; background: white; 
                     padding: 25px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        button {{ background: #25D366; color: white; border: none; padding: 15px; 
                 width: 100%; border-radius: 8px; font-size: 16px; font-weight: bold; 
                 cursor: pointer; margin: 20px 0; }}
        .info {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        #status {{ margin-top: 20px; padding: 15px; border-radius: 8px; display: none; }}
    </style>
</head>
<body>
    <div class="container">
        <h2 style="text-align: center;">?? Selfie BLS</h2>
        <p>Session : <strong>{{ session_id }}</strong></p>
        
        <div class="info">
            <p>?? Clique sur le bouton pour être redirigé vers la page selfie.</p>
            <p>?? Fais le selfie normalement.</p>
            <p id="instruction">? Une fois terminé, cette page se mettra à jour automatiquement.</p>
        </div>
        
        <button onclick="window.location.href='/rediriger/{{ session_id }}'">
            ?? COMMENCER LE SELFIE
        </button>
        
        <div id="status"></div>
    </div>
    
    <script>
        // Vérifier le statut toutes les 2 secondes
        function checkStatus() {
            fetch('/statut/{{ session_id }}')
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'termine') {
                        document.getElementById('instruction').innerHTML = '? Selfie terminé ! Tu peux fermer cette page.';
                        document.getElementById('status').innerHTML = '? Terminé - La session a été mise à jour.';
                    }
                });
        }
        setInterval(checkStatus, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return "? Serveur relais BLS actif"

@app.route('/api/creer-lien', methods=['POST'])
def creer_lien():
    """Reçoit les données de session du PC et génère un lien public"""
    data = request.json
    session_id = str(uuid.uuid4())[:8]
    
    # Stocker les données de session
    sessions[session_id] = {
        'url': data.get('url'),
        'cookies': data.get('cookies', []),
        'user_agent': data.get('user_agent'),
        'phone': data.get('phone'),
        'created_at': time.time(),
        'status': 'en_attente',
        'pc_notifie': False
    }
    
    # Générer le lien public
    lien_public = f"https://{request.host}/session/{session_id}"
    
    return jsonify({
        'success': True,
        'lien': lien_public,
        'session_id': session_id
    })

@app.route('/session/<session_id>')
def ouvrir_session(session_id):
    """Point d'entrée pour le téléphone"""
    if session_id not in sessions:
        return "Session invalide ou expirée", 404
    
    return render_template_string(PAGE_INSTRUCTION, session_id=session_id)

@app.route('/rediriger/<session_id>')
def rediriger_vers_bls(session_id):
    """Redirige vers BLS avec les bons cookies et headers"""
    if session_id not in sessions:
        return "Session invalide", 404
    
    session = sessions[session_id]
    
    # Créer une réponse de redirection
    response = make_response(redirect(session['url']))
    
    # Ajouter les cookies de la session originale
    for cookie in session.get('cookies', []):
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            response.set_cookie(name.strip(), value.strip())
    
    # Mettre à jour le statut
    session['status'] = 'redirige'
    session['redirected_at'] = time.time()
    
    return response

@app.route('/statut/<session_id>')
def statut_session(session_id):
    """Retourne le statut de la session"""
    if session_id not in sessions:
        return jsonify({'status': 'invalide'})
    
    session = sessions[session_id]
    
    return jsonify({
        'status': session.get('status', 'en_attente'),
        'created_at': session.get('created_at'),
        'redirected_at': session.get('redirected_at')
    })

@app.route('/api/notifier-fin/<session_id>', methods=['POST'])
def notifier_fin(session_id):
    """Appelé par le PC quand le selfie est terminé"""
    if session_id in sessions:
        sessions[session_id]['status'] = 'termine'
        sessions[session_id]['completed_at'] = time.time()
        sessions[session_id]['pc_notifie'] = True
    return jsonify({'success': True})

# ?? NOUVEAU : Détection automatique via webhook
@app.route('/webhook-bls', methods=['POST'])
def webhook_bls():
    """
    Point d'entrée que BLS pourrait appeler après le selfie.
    À configurer si BLS permet les webhooks.
    """
    data = request.json
    print("?? Webhook reçu:", data)
    
    # Chercher la session correspondante
    for session_id, session in sessions.items():
        # Ici il faut un identifiant unique dans la réponse BLS
        # À adapter selon ce que BLS renvoie
        pass
    
    return jsonify({'success': True})

# ?? NOUVEAU : Page de callback (si BLS redirige vers une URL spécifique)
@app.route('/callback-bls')
def callback_bls():
    """
    URL de callback où BLS redirige après le selfie.
    """
    session_id = request.args.get('session')
    if session_id and session_id in sessions:
        sessions[session_id]['status'] = 'termine'
        sessions[session_id]['completed_at'] = time.time()
        return "? Selfie terminé ! Vous pouvez fermer cette page."
    
    return "Session non trouvée", 404

# Nettoyage automatique des vieilles sessions (plus de 30 minutes)
def nettoyer_sessions():
    while True:
        time.sleep(60)  # Vérifier toutes les minutes
        maintenant = time.time()
        a_supprimer = []
        for session_id, session in sessions.items():
            if maintenant - session['created_at'] > 1800:  # 30 minutes
                a_supprimer.append(session_id)
        for session_id in a_supprimer:
            del sessions[session_id]
            print(f"?? Session {session_id} supprimée (expirée)")

# Démarrer le thread de nettoyage
threading.Thread(target=nettoyer_sessions, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
