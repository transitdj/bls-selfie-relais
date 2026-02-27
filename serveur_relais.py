# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app)

sessions = {}

@app.route('/')
def home():
    return "✅ Serveur actif"

@app.route('/api/create-session', methods=['POST'])
def create_session():
    data = request.json
    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        'status': 'en_attente',
        'phone': data.get('phone', ''),
        'created_at': time.time()
    }
    return jsonify({'success': True, 'session_id': session_id})

@app.route('/selfie/<session_id>')
def selfie_page(session_id):
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Selfie BLS</title></head>
    <body style="font-family:Arial; text-align:center; padding:50px;">
        <h2>📱 Selfie BLS</h2>
        <p>Session: {session_id}</p>
        <p>👉 Fais ton selfie sur BLS, puis clique ci-dessous</p>
        <button onclick="fetch('/api/termine/{session_id}',{{method:'POST'}}).then(()=>alert('✅ Merci !'))">
            J'AI TERMINÉ
        </button>
    </body>
    </html>
    """

@app.route('/api/termine/<session_id>', methods=['POST'])
def termine(session_id):
    if session_id in sessions:
        sessions[session_id]['status'] = 'termine'
    return jsonify({'success': True})

@app.route('/api/statut/<session_id>')
def statut(session_id):
    if session_id not in sessions:
        return jsonify({'status': 'inconnu'})
    return jsonify({'status': sessions[session_id]['status']})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
