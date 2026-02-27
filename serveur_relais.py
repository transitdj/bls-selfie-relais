# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app)

# Stockage simple
sessions = {}

@app.route('/')
def home():
    return "✅ Serveur relais BLS actif"

@app.route('/api/create-session', methods=['POST'])
def create_session():
    """Crée une nouvelle session"""
    data = request.json
    session_id = str(uuid.uuid4())[:8]
    
    sessions[session_id] = {
        'status': 'en_attente',
        'created_at': time.time(),
        'phone': data.get('phone', '')
    }
    
    return jsonify({'success': True, 'session_id': session_id})

@app.route('/selfie/<session_id>')
def page_selfie(session_id):
    """UNIQUEMENT GET - Page pour le téléphone"""
    if session_id not in sessions:
        return "Session invalide", 404
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Selfie BLS</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial; background: #f0f0f0; padding: 20px; }}
            .container {{ max-width: 400px; margin: 0 auto; background: white; padding: 25px; border-radius: 15px; }}
            button {{ background: #25D366; color: white; border: none; padding: 15px; width: 100%; border-radius: 8px; font-size: 16px; cursor: pointer; margin: 20px 0; }}
            .info {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📱 Selfie BLS</h2>
            <div class="info">
                <p><strong>Session :</strong> {session_id}</p>
                <p>👉 Clique sur le bouton pour faire le selfie</p>
            </div>
            <button onclick="window.location.href='https://algeria.blsspainglobal.com/dza/appointment/livenessrequest'">
                📸 FAIRE LE SELFIE
            </button>
            <p style="text-align: center; margin-top: 20px;">
                <a href="#" onclick="terminerSelfie('{session_id}')">✅ J'ai terminé</a>
            </p>
        </div>
        <script>
            function terminerSelfie(id) {{
                fetch('/api/termine/' + id, {{method: 'POST'}})
                    .then(() => alert('Merci ! Tu peux fermer cette page.'));
            }}
        </script>
    </body>
    </html>
    """

@app.route('/api/termine/<session_id>', methods=['POST'])
def termine_selfie(session_id):
    """Marque la session comme terminée"""
    if session_id in sessions:
        sessions[session_id]['status'] = 'termine'
    return jsonify({'success': True})

@app.route('/api/statut/<session_id>')
def statut_session(session_id):
    """Vérifie le statut"""
    if session_id not in sessions:
        return jsonify({'status': 'inconnu'})
    return jsonify({'status': sessions[session_id].get('status', 'en_attente')})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
