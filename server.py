from flask import Flask, send_from_directory, request, send_file, jsonify
import os
import threading
import time

app = Flask(__name__, static_folder='.')

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
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
