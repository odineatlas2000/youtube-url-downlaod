# Multi-Platform Video Downloader

A Python-based application for downloading videos from various platforms including YouTube, TikTok, Facebook, and Instagram.

## Features

- Download videos in MP4 format
- Convert videos to MP3 audio
- Support for multiple platforms
- Simple and intuitive GUI interface
- Progress tracking
- Customizable output directory

## Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python main.py
```

2. Enter the video URL
3. Select your desired format (MP4 or MP3)
4. Choose the output directory (default is Downloads folder)
5. Click "Download" to start the process

## Supported Platforms

- YouTube
- TikTok
- Facebook
- Instagram
- And many more (supported by yt-dlp)

## Requirements

- Python 3.7+
- yt-dlp
- PyQt6
- moviepy
- requests

## Backend Setup

The application uses a dual backend architecture:
- Node.js server for API handling
- Python script for video downloading

### Node.js Setup

1. Install Node.js dependencies:
```bash
npm install
```

2. Start the server:
```bash
npm start
```

The server will run on port 3000 by default.

### Python Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### API Endpoints

- `POST /api/download`
  - Request body:
    ```json
    {
        "url": "video_url",
        "format": "MP4|MP3",
        "outputPath": "optional_output_path"
    }
    ```
  - Returns a stream of JSON progress updates

- `GET /api/health`
  - Returns server health status

## Note

Some platforms may require authentication or have download restrictions. Please ensure you have the right to download the content and comply with the platform's terms of service.
