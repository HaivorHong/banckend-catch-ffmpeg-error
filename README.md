# banckend-catch-ffmpeg-error
# FFmpeg Video Parser API

A lightweight service based on FastAPI that parses video files or URLs by invoking ffmpeg. When parsing fails, detailed error messages are automatically written to a local log file (format: `<video_name>_timestamp.log`).

## Functional Features

- Single-process invocation of ffmpeg to avoid resource contention
- Supports local file paths and network addresses (URLs)
- Generate detailed log files when errors occur to facilitate troubleshooting
Provide a clear JSON API interface

## Environmental Requirements

- Python 3.8+
- ffmpeg (requires installation and addition to the system PATH)

Installation and Operation

1. Clone the project or create the three files mentioned above.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
