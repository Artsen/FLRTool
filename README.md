# FLR Tool

FLR Tool is a lightweight Flask-based web application that lets you upload a video and automatically extract the first frame, last frame, and a reversed version of the video. With an inline preview and a polished, card-based results area, it’s perfect for creative workflows.

## Features

- Upload a video file and preview its first frame.
- Asynchronously process and extract:
  - The first frame
  - The last frame
  - A reversed version of the video
- Clean, descriptive file names (e.g. `filename_first.jpg`)
- Inline, responsive results display using Bootstrap 5.
- Simple, modern UI with a dark theme.

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Artsen/FLRTool.git
   cd FLRTool
   ```
2. **Install the requirements:**

   ```bash
   pip install -r requirements.txt
   ```
3. **Run the application:**
   ```bash
   python app.py
   ```
4. **Open your browser at:** 
   `http://127.0.0.1:5000/`

## Requirements
* Python 3.x
* Flask
* APScheduler
* FFmpeg (must be installed and available in your system PATH)

## License
MIT License
