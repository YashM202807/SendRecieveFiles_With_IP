from flask import Flask, request, render_template_string, redirect, url_for, flash
import socket
import threading
import os

app = Flask(__name__)
app.secret_key = 'secret'

PORT = 5001

HTML = """
<!doctype html>
<title>File Transfer</title>
<h2>Choose an option:</h2>
<form method="POST" enctype="multipart/form-data" action="/send">
    <h3>Send File</h3>
    Receiver IP: <input type="text" name="ip" required><br><br>
    Select file: <input type="file" name="file" required><br><br>
    <input type="submit" value="Send">
</form>

<hr>

<form method="POST" action="/receive">
    <h3>Receive File</h3>
    <input type="submit" value="Wait to Receive">
</form>

{% with messages = get_flashed_messages() %}
  {% if messages %}
    <ul>
    {% for msg in messages %}
      <li>{{ msg }}</li>
    {% endfor %}
    </ul>
  {% endif %}
{% endwith %}
"""

def receive_file_server():
    s = socket.socket()
    s.bind(('0.0.0.0', PORT))
    s.listen(1)
    conn, addr = s.accept()

    # Receive file info
    received = conn.recv(1024).decode()
    filename, filesize = received.split('|')
    filesize = int(filesize)

    with open(filename, 'wb') as f:
        bytes_read = 0
        while bytes_read < filesize:
            data = conn.recv(4096)
            if not data:
                break
            f.write(data)
            bytes_read += len(data)

    conn.close()
    s.close()
    return filename

def send_file_to_ip(ip, filepath):
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    s = socket.socket()
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
    return render_template_string(HTML)

@app.route('/send', methods=['POST'])
def send():
    ip = request.form['ip']
    file = request.files['file']
    filename = file.filename
    file.save(filename)

    try:
        send_file_to_ip(ip, filename)
        flash(f"File '{filename}' sent successfully to {ip}!")
    except Exception as e:
        flash(f"Error sending file: {e}")
    finally:
        os.remove(filename)

    return redirect(url_for('index'))

@app.route('/receive', methods=['POST'])
def receive():
    def threaded_receive():
        filename = receive_file_server()
        print(f"File received: {filename}")

    thread = threading.Thread(target=threaded_receive)
    thread.start()
    flash("Waiting to receive file... Keep this page open.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
