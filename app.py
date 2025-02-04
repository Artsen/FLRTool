import os
import time
import uuid
import threading
import subprocess
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from werkzeug.utils import secure_filename

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'your_secure_secret_key'  # Replace with your own secret

# Folders
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
PREVIEW_FOLDER = os.path.join('static', 'previews')

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, PREVIEW_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

def allowed_video(filename):
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in ALLOWED_VIDEO_EXTENSIONS
    return False

# In-memory progress tracking
progress = {}

def process_video_async(task_id, input_path, output_prefix, options):
    """
    Process the video asynchronously:
      - Extract first frame
      - Extract last frame
      - Create reversed video
    The outputs are saved using output_prefix.
    """
    results = {}
    try:
        if options.get('extract_first'):
            first_output = f"{output_prefix}_first.jpg"
            logging.info(f"Extracting first frame: {first_output}")
            cmd_first = [
                'ffmpeg', '-y', '-i', input_path,
                '-vf', 'select=eq(n\\,0)',
                '-q:v', '3',
                first_output
            ]
            subprocess.run(cmd_first, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            results['first_frame'] = os.path.basename(first_output)
        if options.get('extract_last'):
            last_output = f"{output_prefix}_last.jpg"
            logging.info(f"Extracting last frame: {last_output}")
            cmd_last = [
                'ffmpeg', '-y', '-sseof', '-0.1', '-i', input_path,
                '-update', '1',
                '-q:v', '3',
                last_output
            ]
            subprocess.run(cmd_last, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            results['last_frame'] = os.path.basename(last_output)
        if options.get('reverse_video'):
            reversed_output = f"{output_prefix}_reversed.mp4"
            logging.info(f"Creating reversed video: {reversed_output}")
            cmd_reversed = [
                'ffmpeg', '-y', '-i', input_path,
                '-vf', 'reverse',
                '-af', 'areverse',
                reversed_output
            ]
            subprocess.run(cmd_reversed, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            results['reversed_video'] = os.path.basename(reversed_output)
        progress[task_id]['status'] = 'completed'
        progress[task_id]['result'] = results
    except Exception as e:
        logging.error(f"Error processing video: {e}")
        progress[task_id]['status'] = 'error'
        progress[task_id]['result'] = str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_preview', methods=['POST'])
def upload_preview():
    if 'video_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    file = request.files['video_file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    if file and allowed_video(file.filename):
        original_filename = file.filename
        safe_filename = secure_filename(original_filename)
        name, ext = os.path.splitext(safe_filename)
        
        # Use the original name (without a unique ID) so outputs are named simply.
        input_filename = f"{name}{ext}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        # (Optionally: check if file exists to avoid overwriting.)
        file.save(input_path)
        logging.info(f"Uploaded file saved to {input_path}")
        
        # Create a preview image using the original name.
        preview_filename = f"{name}_preview.jpg"
        preview_path = os.path.join(PREVIEW_FOLDER, preview_filename)
        try:
            cmd_preview = [
                'ffmpeg', '-y', '-i', input_path,
                '-vf', 'select=eq(n\\,0)',
                '-q:v', '3',
                preview_path
            ]
            subprocess.run(cmd_preview, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            logging.error(f"Error extracting preview: {e}")
            return jsonify({'status': 'error', 'message': 'Error extracting preview.'}), 500
        preview_url = url_for('static', filename=f"previews/{preview_filename}")
        # Set the output prefix to the original name.
        output_prefix = f"{name}"
        return jsonify({
            'status': 'success',
            'preview_url': preview_url,
            'input_file': input_filename,
            'output_prefix': output_prefix
        })
    else:
        return jsonify({'status': 'error', 'message': 'Invalid file type.'}), 400

@app.route('/process_video_async', methods=['POST'])
def process_video_async_route():
    data = request.json
    input_file = data.get('input_file')
    output_prefix = data.get('output_prefix')
    extract_first = bool(data.get('extract_first', True))
    extract_last = bool(data.get('extract_last', True))
    reverse_video = bool(data.get('reverse_video', True))
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_file)
    # The outputs will be placed in OUTPUT_FOLDER.
    output_prefix_full = os.path.join(app.config['OUTPUT_FOLDER'], output_prefix)
    task_id = uuid.uuid4().hex
    progress[task_id] = {'status': 'processing', 'result': None}
    options = {
        'extract_first': extract_first,
        'extract_last': extract_last,
        'reverse_video': reverse_video
    }
    thread = threading.Thread(target=process_video_async, args=(task_id, input_path, output_prefix_full, options))
    thread.start()
    return jsonify({'task_id': task_id}), 202

@app.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    if task_id in progress:
        return jsonify(progress[task_id])
    else:
        return jsonify({'status': 'unknown'}), 404

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

@app.route('/video/<filename>')
def serve_video(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
