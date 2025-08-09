from flask import Flask, request, jsonify, send_from_directory
import socket
import threading
import os
import time

app = Flask(__name__)
PORT = 5001

# Folder to save received files
RECEIVE_FOLDER = "received_files"
os.makedirs(RECEIVE_FOLDER, exist_ok=True)

# Global to store received filename (simplified for demo)
received_file_info = {
    'filename': None,
    'received': False
}

def receive_file_server():
    s = socket.socket()
    s.bind(('0.0.0.0', PORT))
    s.listen(1)
    print(f"Receiver listening on port {PORT}...")
    conn, addr = s.accept()
    print(f"Connected by sender: {addr}")

    received = conn.recv(1024).decode()
    filename, filesize = received.split('|')
    filesize = int(filesize)

    filepath = os.path.join(RECEIVE_FOLDER, filename)
    with open(filepath, 'wb') as f:
        bytes_read = 0
        while bytes_read < filesize:
            data = conn.recv(4096)
            if not data:
                break
            f.write(data)
            bytes_read += len(data)

    conn.close()
    s.close()
    print(f"Received file saved as {filepath}")

    # Update global status
    received_file_info['filename'] = filename
    received_file_info['received'] = True

def send_file_to_ip(ip, filepath):
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    s = socket.socket()
    s.settimeout(10)
    s.connect((ip, PORT))

    s.send(f"{filename}|{filesize}".encode())

    with open(filepath, 'rb') as f:
        while True:
            bytes_read = f.read(4096)
            if not bytes_read:
                break
            s.sendall(bytes_read)
    s.close()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/send', methods=['POST'])
def send_route():
    if 'ip' not in request.form or 'file' not in request.files:
        return jsonify({"success": False, "message": "IP and file are required"}), 400
    ip = request.form['ip']
    file = request.files['file']
    filename = file.filename
    save_path = filename
    file.save(save_path)

    try:
        send_file_to_ip(ip, save_path)
        os.remove(save_path)
        return jsonify({"success": True})
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/receive', methods=['POST'])
def receive_route():
    # Reset status
    received_file_info['received'] = False
    received_file_info['filename'] = None

    # Run receiver in thread so request returns immediately
    thread = threading.Thread(target=receive_file_server, daemon=True)
    thread.start()

    # Wait up to 30 seconds for file to be received (simplified)
    timeout = 30
    waited = 0
    while not received_file_info['received'] and waited < timeout:
        time.sleep(1)
        waited += 1

    if received_file_info['received']:
        return jsonify({"success": True, "filename": received_file_info['filename']})
    else:
        return jsonify({"success": False, "message": "Timeout waiting for file"}), 504

@app.route('/received_files/<filename>')
def download_file(filename):
    return send_from_directory(RECEIVE_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
