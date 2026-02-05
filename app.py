import os
import time
from datetime import datetime
from flask import Flask, render_template, Response, request, redirect, session, jsonify , send_from_directory ,url_for
import cv2

from anpr_engine import run_anpr_on_frame
from ppe_engine import run_ppe_on_frame
from db import init_databases, get_all_anpr_events, get_all_ppe_violations, verify_user
from Videoconverter import process_videos

app = Flask(__name__)
app.secret_key = "anpr_secret_key"

UPLOAD_FOLDER = "static/uploads"
LIVE_FEED_FOLDER = os.path.join("static", "Live Feed")

VIDEO_FOLDER = os.path.join('static', 'Live Feed') #self changed

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LIVE_FEED_FOLDER, exist_ok=True)

# Initialize databases on startup
init_databases()

# ---------------- Stream Control ----------------
stream_running = False

last_processed_frame = None     # latest processed frame
paused_frame = None             # frozen frame for pause
view_mode = "live"              # live | paused | resume

# ---------------- Login ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if verify_user(username, password):
            session['user'] = username
            return redirect('/dashboard')

        return render_template("login.html", error="Invalid username or password")

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template('dashboard.html')



# ---------------- Violations Page ----------------
@app.route('/violations')
def violations():
    if 'user' not in session:
        return redirect('/')

    anpr_data = get_all_anpr_events()
    ppe_data = get_all_ppe_violations()

    return render_template(
        "violations.html",
        anpr_events=anpr_data,
        ppe_events=ppe_data
    )

# ---------------- Camera Stream + Recording ----------------
def gen_frames():
    global stream_running, last_processed_frame, paused_frame, view_mode

    cap = cv2.VideoCapture(0)
    stream_running = True

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fps = 5
    frame_interval = 1.0 / fps
    last_frame_time = time.time()

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    start_time = time.time()

    def new_writer():
        timestamp = datetime.now().strftime('%d.%m.%Y - %H.%M.%S')
        filename = f"live {timestamp}.mp4"
        path = os.path.join(LIVE_FEED_FOLDER, filename)
        return cv2.VideoWriter(path, fourcc, fps, (width, height))

    out = new_writer()

    while stream_running:
        success, frame = cap.read()
        if not success:
            break

        # Rotate recording every 3 minutes
        if time.time() - start_time >= 180:
            out.release()
            out = new_writer()
            start_time = time.time()

        # -------- ALWAYS PROCESS --------
        processed = run_anpr_on_frame(frame, camera_id=1)
        processed = run_ppe_on_frame(processed, camera_id=1)

        # -------- ALWAYS SAVE --------
        out.write(processed)

        last_processed_frame = processed

        # -------- UI STATE MACHINE --------
        if view_mode == "paused":
            if paused_frame is None:
                paused_frame = last_processed_frame.copy()
            display_frame = paused_frame

        elif view_mode == "resume":
            
            paused_frame = None
            display_frame = last_processed_frame
            view_mode = "resume"  

        else:  
            paused_frame = None
            display_frame = last_processed_frame
        # --------------------------------

        ret, buffer = cv2.imencode('.jpg', display_frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        # FPS enforcement
        now = time.time()
        elapsed = now - last_frame_time
        if elapsed < frame_interval:
            time.sleep(frame_interval - elapsed)
        last_frame_time = time.time()

    cap.release()
    out.release()
    stream_running = False




@app.route('/video_feed')

def video_feed():
    if 'user' not in session:
        return redirect('/')
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ---------------- self changed ----------------

@app.route('/videos')


def videos():
    if 'user' not in session:
        return redirect('/')
    
    process_videos(VIDEO_FOLDER)
    
    video_files = []
    if os.path.exists(VIDEO_FOLDER):
        for filename in os.listdir(VIDEO_FOLDER):
            if filename.lower().endswith('c.mp4'):
                video_files.append(filename)    
    return render_template('videos.html', videos=video_files)

@app.route('/static/Live Feed/<path:filename>')
def serve_video(filename):
    return send_from_directory(VIDEO_FOLDER, filename)



# ---------------- Stream Controls ----------------
@app.route('/pause')
def pause_stream():
    global view_mode
    view_mode = "paused"
    return jsonify({"status": "paused"})


@app.route('/play')
def play_stream():
    global view_mode
    view_mode = "resume"
    return jsonify({"status": "resumed"})


@app.route('/live')
def live_stream():
    global view_mode
    view_mode = "live"
    return jsonify({"status": "live"})


@app.route('/stop')
def stop_stream():
    global stream_running
    stream_running = False
    return jsonify({"status": "stopped"})


# ---------------- Image Upload ----------------
@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'user' not in session:
        return redirect('/')

    file = request.files['file']
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    img = cv2.imread(path)

    img = run_anpr_on_frame(img, camera_id=1)
    img = run_ppe_on_frame(img, camera_id=1)

    out_path = os.path.join(UPLOAD_FOLDER, "out_" + file.filename)
    cv2.imwrite(out_path, img)

    return render_template("dashboard.html", image="out_" + file.filename)


# ---------------- Video Upload ----------------
def gen_video(path):
    cap = cv2.VideoCapture(path)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = run_anpr_on_frame(frame, camera_id=1)
        frame = run_ppe_on_frame(frame, camera_id=1)

        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    cap.release()


@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'user' not in session:
        return redirect('/')

    file = request.files['file']
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)
    return render_template("dashboard.html", video=file.filename)


@app.route('/video_stream/<filename>')
def video_stream(filename):
    if 'user' not in session:
        return redirect('/')
    path = os.path.join(UPLOAD_FOLDER, filename)
    return Response(gen_video(path), mimetype='multipart/x-mixed-replace; boundary=frame')


# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(debug=True)

