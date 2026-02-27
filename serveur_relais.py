# -*- coding: latin-1 -*-
from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import hashlib
import json
import time
from datetime import datetime
import logging
import os

app = Flask(__name__)
CORS(app)

# تكوين السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تخزين البيانات في الذاكرة (في الإنتاج استخدم قاعدة بيانات)
pending_sessions = {}
completed_sessions = {}

class SessionManager:
    @staticmethod
    def create_session(user_data):
        """إنشاء جلسة جديدة"""
        session_id = str(uuid.uuid4())
        
        session_data = {
            'session_id': session_id,
            'user_id': user_data.get('user_id'),
            'transaction_id': user_data.get('transaction_id'),
            'user_ip': user_data.get('user_ip'),
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'selfie_data': None,
            'liveness_result': None,
            'payment_ready': False
        }
        
        pending_sessions[session_id] = session_data
        logger.info(f"✅ New session created: {session_id}")
        
        return session_data
    
    @staticmethod
    def update_session(session_id, selfie_data, liveness_result):
        """تحديث الجلسة ببيانات السيلفي"""
        if session_id in pending_sessions:
            pending_sessions[session_id].update({
                'selfie_data': selfie_data,
                'liveness_result': liveness_result,
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'payment_ready': True
            })
            
            completed_sessions[session_id] = pending_sessions.pop(session_id)
            logger.info(f"✅ Session completed: {session_id}")
            return True
        return False
    
    @staticmethod
    def get_session(session_id):
        """الحصول على بيانات الجلسة"""
        return pending_sessions.get(session_id) or completed_sessions.get(session_id)

class LivenessProcessor:
    @staticmethod
    def process_selfie_data(selfie_data):
        """معالجة بيانات السيلفي"""
        try:
            # محاكاة معالجة اللايفنس
            liveness_score = round(0.85 + (0.15 * (hash(selfie_data.get('image_id', '')) % 100) / 100), 2)
            
            return {
                'success': True,
                'liveness_score': liveness_score,
                'is_live': liveness_score > 0.7,
                'processed_at': datetime.now().isoformat(),
                'quality_check': 'passed',
                'face_detected': True,
                'verification_id': f"verif_{int(time.time())}"
            }
            
        except Exception as e:
            logger.error(f"❌ Liveness processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'is_live': False
            }

class PaymentManager:
    @staticmethod
    def prepare_payment(session_data):
        """تحضير بيانات الدفع"""
        if not session_data.get('payment_ready'):
            return None
            
        return {
            'payment_eligible': True,
            'session_id': session_data['session_id'],
            'user_id': session_data['user_id'],
            'amount': 85.00,
            'currency': 'USD',
            'payment_url': f"/payment/checkout?session={session_data['session_id']}",
            'verification_id': session_data.get('liveness_result', {}).get('verification_id', '')
        }

# === Routes ===

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "BLS Liveness Proxy Server",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(pending_sessions),
        "completed_sessions": len(completed_sessions),
        "message": "Server is running successfully on Render!"
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """فحص صحة السيرفر"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv('ENVIRONMENT', 'production')
    })

@app.route('/api/create-session', methods=['POST'])
def create_session():
    """إنشاء جلسة جديدة من قبل المستخدم"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        required_fields = ['user_id', 'transaction_id', 'user_ip']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing field: {field}"}), 400
        
        session_data = SessionManager.create_session(data)
        
        return jsonify({
            "success": True,
            "session_id": session_data['session_id'],
            "status": "pending",
            "message": "Session created successfully. Share with client for selfie.",
            "timestamp": session_data['created_at']
        })
        
    except Exception as e:
        logger.error(f"❌ Session creation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/client/submit-selfie', methods=['POST'])
def submit_selfie():
    """استقبال بيانات السيلفي من جهاز العميل"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        session_id = data.get('session_id')
        selfie_data = data.get('selfie_data', {})
        
        if not session_id:
            return jsonify({"success": False, "error": "Session ID required"}), 400
        
        logger.info(f"📸 Processing selfie for session: {session_id}")
        
        liveness_result = LivenessProcessor.process_selfie_data(selfie_data)
        
        if not liveness_result['success']:
            return jsonify({
                "success": False,
                "error": "Liveness verification failed",
                "details": liveness_result.get('error')
            }), 400
        
        if SessionManager.update_session(session_id, selfie_data, liveness_result):
            session_data = SessionManager.get_session(session_id)
            payment_data = PaymentManager.prepare_payment(session_data)
            
            return jsonify({
                "success": True,
                "session_id": session_id,
                "liveness_result": liveness_result,
                "payment_data": payment_data,
                "message": "Selfie processed successfully. Payment is ready."
            })
        else:
            return jsonify({"success": False, "error": "Session not found"}), 404
            
    except Exception as e:
        logger.error(f"❌ Selfie submission error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/check-session/<session_id>', methods=['GET'])
def check_session(session_id):
    """التحقق من حالة الجلسة"""
    try:
        session_data = SessionManager.get_session(session_id)
        
        if not session_data:
            return jsonify({"success": False, "error": "Session not found"}), 404
        
        response = {
            "success": True,
            "session_id": session_id,
            "status": session_data['status'],
            "user_id": session_data['user_id'],
            "created_at": session_data['created_at']
        }
        
        if session_data['status'] == 'completed':
            response['liveness_result'] = session_data['liveness_result']
            response['payment_data'] = PaymentManager.prepare_payment(session_data)
            response['completed_at'] = session_data['completed_at']
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Session check error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/selfie/<session_id>')
def page_selfie(session_id):
    """Page d'accueil pour le téléphone (GET)"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Selfie BLS</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial; background: #f5f5f5; margin: 0; padding: 20px; }}
            .container {{ max-width: 400px; margin: 0 auto; background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            h2 {{ color: #075E54; text-align: center; }}
            button {{ background: #25D366; color: white; border: none; padding: 15px; width: 100%; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; margin: 20px 0; }}
            .info {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>📱 Selfie BLS</h2>
            <div class="info">
                <p><strong>Session :</strong> {session_id[:8]}...</p>
                <p>👉 Prépare-toi à faire un selfie</p>
                <p>📸 Regarde bien l'écran</p>
            </div>
            <button onclick="window.location.href='https://algeria.blsspainglobal.com/dza/appointment/livenessrequest'">
                📸 COMMENCER
            </button>
            <p style="text-align: center; font-size: 12px; color: #666;">
                ⏱️ Session valable 30 minutes
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/api/selfie-status/<session_id>', methods=['GET'])
def selfie_status(session_id):
    """Vérifier si le selfie est terminé (GET)"""
    session = SessionManager.get_session(session_id)
    if not session:
        return jsonify({'status': 'inconnu'})
    
    return jsonify({
        'status': session['status'],
        'liveness_result': session.get('liveness_result')
    })
