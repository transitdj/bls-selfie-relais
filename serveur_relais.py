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
    
    # Stocker l'URL BLS reçue du PC
    bls_url = data.get('bls_url', '')
    
    sessions[session_id] = {
        'status': 'en_attente',
        'phone': data.get('phone', ''),
        'bls_url': bls_url,  # Sauvegarde l'URL BLS
        'created_at': time.time()
    }
    
    print(f"✅ Session {session_id} créée avec URL: {bls_url[:50]}...")
    return jsonify({'success': True, 'session_id': session_id})

@app.route('/selfie/<session_id>')
def selfie_page(session_id):
    if session_id not in sessions:
        return "Session invalide", 404
    
    session = sessions[session_id]
    bls_url = session.get('bls_url', '')
    
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
            .btn {{ background: #25D366; color: white; border: none; padding: 15px; width: 100%; border-radius: 8px; font-size: 16px; cursor: pointer; margin: 10px 0; }}
            .bls-link {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0; word-break: break-all; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2 style="text-align:center;">📱 Selfie BLS</h2>
            <p><strong>Session :</strong> {session_id}</p>
            
            <div class="bls-link">
                <p>🔗 <strong>Lien BLS à ouvrir :</strong></p>
                <p style="font-size:12px;">{bls_url}</p>
            </div>

            <button class="btn" onclick="window.location.href='{bls_url}'">
                📸 OUVRIR LA PAGE SELFIE BLS
            </button>

            <p style="text-align:center; margin:20px 0;">⬇️ APRÈS AVOIR FINI ⬇️</p>

            <button class="btn" style="background:#28a745;" onclick="terminer()">
                ✅ J'AI TERMINÉ LE SELFIE
            </button>
        </div>

        <script>
            function terminer() {{
                fetch('/api/termine/{session_id}', {{method: 'POST'}})
                    .then(() => {{
                        alert('✅ Merci ! Tu peux fermer cette page.');
                        document.body.innerHTML = '<div style="text-align:center; padding:50px;"><h2>✅ Selfie terminé</h2><p>Tu peux fermer cette page.</p></div>';
                    }});
            }}
        </script>
    </body>
    </html>
    """

@app.route('/api/termine/<session_id>', methods=['POST'])
def termine(session_id):
    if session_id in sessions:
        sessions[session_id]['status'] = 'termine'
        print(f"🎉 Session {session_id} terminée")
    return jsonify({'success': True})

@app.route('/api/statut/<session_id>')
def statut(session_id):
    if session_id not in sessions:
        return jsonify({'status': 'inconnu'})
    return jsonify({'status': sessions[session_id]['status']})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    app.run(host='0.0.0.0', port=port)
