# Meme Search Bot Monorepo

A complete pipeline for turning videos into a searchable meme database accessible via Discord and LINE.

## Architecture

1.  **Video Processor (Python):** Uses **Faster-Whisper (GPU-accelerated)** for STT or **EasyOCR** for OCR to extract keyframes with text.
2.  **Cloudflare R2:** Stores the extracted meme images.
3.  **Cloudflare D1:** Stores the SQLite metadata (OCR text, timestamps, file paths).
4.  **API Server (TypeScript):** A Cloudflare Worker (Hono) that handles search queries and integrates with Discord/LINE.

## Project Structure

- **[`/video-processor`](./video-processor)**: Frame extraction and metadata generation.
- **[`/image-search-api-server`](./image-search-api-server)**: The backend API and bot integration.
- **`deploy.sh`**: Root script to automate R2 uploads and D1 database synchronization.

## Quick Start

### 1. Prerequisites
- **Python 3.12+** with `uv` installed.
- **Node.js 20+** and `npm`.
- **Wrangler CLI** authenticated (`npx wrangler login`).
- **FFmpeg** installed (for audio extraction).

### 2. Setup Cloudflare Resources
Follow the [API Server README](./image-search-api-server/README.md) to create your D1 database, R2 bucket, and set Discord secrets.

### 3. Process a Video
Extract frames and dialogue from a video file:
```bash
# Using STT (Recommended)
npm run processor:run -- ./video-processor/input/movie.mp4 --use-stt --stt-lang zh
```
The processor will automatically use your **GPU (MPS on Mac, CUDA on Linux/Windows)** if available.

### 4. Deploy to Cloudflare
Upload the processed frames to R2 and sync the metadata to D1:
```bash
# Deploy a specific movie
./deploy.sh movie_folder_name

# Or deploy everything in the output folder
./deploy.sh
```

## Development Commands

| Task                 | Command                 |
|:---------------------|:------------------------|
| Run API Locally      | `npm run server:dev`    |
| Build API            | `npm run server:build`  |
| Process Video        | `npm run processor:run -- <args>` |
| Full Deployment      | `./deploy.sh`           |

## License
MIT
