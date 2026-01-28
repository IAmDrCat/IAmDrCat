from flask import Flask, send_from_directory, request, send_file, jsonify, session, redirect, url_for
import os
import threading
import time

app = Flask(__name__, static_folder='.')
app.secret_key = 'super_secret_key_change_in_production'  # Needed for sessions

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

# --- Verification Routes ---

@app.route('/checkpoint/1')
def checkpoint_1():
    # Start the verification flow
    session['step'] = 1
    # Only set start_time if it's not already set, or if we want to reset it on visit
    if 'start_time' not in session:
        session['start_time'] = time.time()
    return send_from_directory('checkpoints', 'checkpoint1.html')

@app.route('/checkpoint/2')
def checkpoint_2():
    # Ensure user has completed step 1
    if session.get('step') is None or session.get('step') < 1:
        return redirect(url_for('checkpoint_1'))
    
    # Check if 2 minutes (120 seconds) have passed
    start_time = session.get('start_time', 0)
    elapsed = time.time() - start_time
    if elapsed < 120:
        remaining = int(120 - elapsed)
        return f"<h1>Too fast!</h1><p>Please wait {remaining} more seconds before proceeding to Step 2.</p><a href='/checkpoint/1'>Go Back</a>", 403
    
    # Update step to 2
    session['step'] = 2
    return send_from_directory('checkpoints', 'checkpoint2.html')

@app.route('/key')
def get_key():
    # Ensure user has completed step 2
    if session.get('step') is None or session.get('step') < 2:
        return redirect(url_for('checkpoint_1'))
    
    return send_from_directory('checkpoints', 'key.html')

# --- Static File Handler ---

@app.route('/<path:path>')
def serve_static(path):
    # SECURITY: Prevent direct access to checkpoints folder to enforce the flow
    if 'checkpoints/' in path or 'checkpoints\\' in path:
        return "Access denied. Please start verification at /checkpoint/1", 403

    # Try creating a clean URL support
    if os.path.exists(os.path.join('.', path)):
         return send_from_directory('.', path)
    elif os.path.exists(os.path.join('.', path + '.html')):
         return send_from_directory('.', path + '.html')
    return "File not found", 404

if __name__ == '__main__':
    print("Starting IAmDrCat Server on http://localhost:8000")
    print("Press Ctrl+C to stop")
    app.run(port=8000, debug=True, threaded=True)
