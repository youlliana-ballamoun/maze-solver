from flask import Flask, render_template_string, request, jsonify
import serial
import threading
import time

PORT = "COM15"
BAUD = 9600

app = Flask(__name__)

bt = None
logs = []
lock = threading.Lock()

connected = False

def connect_bluetooth():
    global bt, connected
    try:
        bt = serial.Serial(PORT, BAUD, timeout=1)

        # DEBUG 
        print("===== BLUETOOTH DEBUG =====")
        print("PORT OPENED:", PORT)
        print("SERIAL OBJECT:", bt)
        print("IS OPEN:", bt.is_open)
        print("===========================")

        connected = bt.is_open

    except Exception as e:
        connected = False
        print("Bluetooth NOT connected:", e)

connect_bluetooth()

#  BLUETOOTH READER 
def read_bt():
    global logs

    while True:
        try:
            if bt and bt.is_open:
                if bt.in_waiting:
                    data = bt.readline().decode(errors='ignore').strip()

                    if data:
                        print("CAR:", data)

                        with lock:
                            logs.append(data)
                            if len(logs) > 100:
                                logs.pop(0)

        except Exception as e:
            print("Bluetooth read error:", e)

threading.Thread(target=read_bt, daemon=True).start()

# Website Interface
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Maze Solver Dashboard</title>
<style>
body { font-family: Arial; text-align: center; background: #111; color: white; }
button { padding: 15px 30px; font-size: 20px; margin: 10px; border-radius: 10px; cursor: pointer; }
.explore { background: green; }
.solve { background: blue; }
#log { width: 80%; height: 300px; margin: auto; background: black; overflow-y: scroll; padding: 10px; border: 1px solid #444; text-align: left; }
</style>
</head>

<body>

<h1> Maze Solver Dashboard</h1>

<h3 id="conn">Bluetooth: Checking...</h3>
<h2 id="status">Status: WAITING</h2>

<button class="explore" onclick="sendCommand('E')">Explore</button>
<button class="solve" onclick="sendCommand('S')">Solve</button>

<h2>Live Log</h2>
<div id="log"></div>

<script>

function sendCommand(cmd){
    fetch('/send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({command: cmd})
    });
}

function updateLogs(){
    fetch('/logs')
    .then(res => res.json())
    .then(data => {
        let logDiv = document.getElementById("log");
        logDiv.innerHTML = data.logs.join("<br>");
        logDiv.scrollTop = logDiv.scrollHeight;

        if(data.logs.length > 0){
            document.getElementById("status").innerText =
                "Status: " + data.logs[data.logs.length - 1];
        }
    });
}

function checkConnection(){
    fetch('/status')
    .then(res => res.json())
    .then(data => {
        document.getElementById("conn").innerText =
            data.connected ? "Bluetooth: Connected ✅" : "Bluetooth: Not Connected ❌";
    });
}

setInterval(updateLogs, 1000);
setInterval(checkConnection, 2000);

</script>

</body>
</html>
"""

# ROUTES 
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/send", methods=["POST"])
def send():
    cmd = request.json.get("command")

    try:
        if bt and bt.is_open:
            bt.write((cmd + "\n").encode())
    except Exception as e:
        print("Send error:", e)

    return jsonify({"status": "sent"})

@app.route("/logs")
def get_logs():
    with lock:
        return jsonify({"logs": list(logs)})

@app.route("/status")
def status():
    # 🔥 SIMPLE REAL CONNECTION = PORT OPEN ONLY
    return jsonify({
        "connected": bt is not None and bt.is_open
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
