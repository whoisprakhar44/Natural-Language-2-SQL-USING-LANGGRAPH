"""
NL-to-SQL -- Flask application entry point.

Run with:
    python app.py
"""

import hashlib
import json
import os
import sqlite3

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from nltosql.agent import run_agent
from nltosql.schema_extractor import get_schema_json

app = Flask(__name__)
app.secret_key = os.urandom(24)

# =============================================================================
# Database / Auth Setup
# =============================================================================

def init_auth_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect("data/users.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

init_auth_db()

# =============================================================================
# Routes
# =============================================================================

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        if session.get('logged_in'):
            return redirect(url_for('index'))
        return render_template('login.html')

@app.route('/api/login', methods=['POST'], endpoint='login')
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = sqlite3.connect("data/users.db")
    cur = conn.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    
    if row and row[0] == hash_password(password):
        session['logged_in'] = True
        return redirect(url_for('index'))
    else:
        flash('Invalid username or password', 'error')
        return redirect(url_for('login_page'))

@app.route('/api/signup', methods=['POST'], endpoint='signup')
def signup():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Please fill out all fields', 'error')
        return redirect(url_for('login_page'))
        
    conn = sqlite3.connect("data/users.db")
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        flash('Account created successfully! Please log in.', 'success')
    except sqlite3.IntegrityError:
        flash('Username already exists', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# =============================================================================
# API Routes for the Agent
# =============================================================================

@app.route('/api/schema', methods=['GET'])
def schema():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    schema_str = get_schema_json()
    return app.response_class(
        response=schema_str,
        status=200,
        mimetype='application/json'
    )

@app.route('/api/query', methods=['POST'])
def query():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    question = data.get('question')
    
    if not question:
        return jsonify({"error": "Question is required"}), 400
        
    # Run the agent
    result = run_agent(question)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=8501)
