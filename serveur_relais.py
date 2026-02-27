# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, redirect, make_response
from flask_cors import CORS
import uuid
import time
import os
import base64
import json

app = Flask(__name__)
CORS(app)

sessions = {}

@app.route('/')
def home():
    return "✅ Serveur de partage de session BLS"

@app.route('/api/create-session', methods=['POST'])
def create_session():
    """Reçoit les données de session du PC"""
    data = request.json
    session_id = str(uuid.uuid4())[:8]
    
    # Stocker TOUTES les données de session
    sessions[session_id] = {
        'url': data.get('url'),  # L'URL BLS
        'cookies': data.get('cookies', []),  # Les cookies
        'local_storage': data.get('local_storage', {}),  # Le localStorage
        'status': 'en_attente',
        'created_at': time.time()
    }
    
    return jsonify({'success': True, 'session_id': session_id})

@app.route('/selfie/<session_id>')
def selfie_page(session_id):
    """Page pour le téléphone"""
    if session_id not in sessions:
        return "Session invalide", 404
    
    session = sessions[session_id]
    
    # Créer une page qui va restaurer la session
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Session BLS</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial; background: #f0f0f0; padding: 20px; }}
            .container {{ max-width: 400px; margin: 0 auto; background: white; padding: 25px; border-radius: 15px; }}
            .btn {{ background: #25D366; color: white; border: none; padding: 15px; width: 100%; border-radius: 8px; font-size: 16px; cursor: pointer; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📱 Transfert de session</h2>
            <p>Clique sur le bouton pour reprendre la session BLS sur ton téléphone.</p>
            <button class="btn" onclick="restaurerSession()">
                🔄 REPRENDRE LA SESSION
            </button>
            <div id="status"></div>
        </div>

        <script>
            function restaurerSession() {{
                document.getElementById('status').innerHTML = '⏳ Restauration...';
                
                // Rediriger vers la page de restauration
                window.location.href = '/restaurer/{session_id}';
            }}
        </script>
    </body>
    </html>
    """
    return html

@app.route('/restaurer/<session_id>')
def restaurer_session(session_id):
    """Restaure la session et redirige vers BLS"""
    if session_id not in sessions:
        return "Session invalide", 404
    
    session = sessions[session_id]
    
    # Créer une réponse qui va rediriger vers BLS
    response = make_response(redirect(session['url']))
    
    # Ajouter tous les cookies
    for cookie in session.get('cookies', []):
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            # Nettoyer le nom et la valeur
            name = name.strip()
            value = value.strip().rstrip(';')
            response.set_cookie(name, value, domain='.blsspainglobal.com', path='/')
    
    # Marquer la session comme restaurée
    session['restored_at'] = time.time()
    
    return response

@app.route('/api/statut/<session_id>')
def statut(session_id):
    if session_id not in sessions:
        return jsonify({'status': 'inconnu'})
    
    session = sessions[session_id]
    return jsonify({
        'status': session.get('status', 'en_attente'),
        'restored': 'restored_at' in session
    })

@app.route('/api/termine/<session_id>', methods=['POST'])
def termine(session_id):
    if session_id in sessions:
        sessions[session_id]['status'] = 'termine'
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
