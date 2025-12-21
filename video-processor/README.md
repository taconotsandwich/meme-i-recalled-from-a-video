# Video Processing & Cloudflare Deployment Tool

A unified tool that extracts frames from videos using intelligent scene detection and OCR, and automatically deploys the results to **Cloudflare R2** (Images) and **Cloudflare D1** (Database).

> **Note:** This tool bridges your local video content with your Serverless Cloudflare Worker.

## Features

- **One-Command Workflow:** Process -> SQL Gen -> R2 Upload -> D1 Execute.
- **Intelligent Processing:** Scene detection, deduplication, and multi-engine OCR.
- **Auto-Deployment:** 
  - Uploads extracted images to an R2 Bucket.
  - Updates the remote D1 database with new entries pointing to those R2 URLs.

## Installation

1. Clone this repository.
2. Install [uv](https://github.com/astral-sh/uv) (recommended) or use standard pip.
3. Sync dependencies:
   ```bash
   uv sync
   ```
4. **Prerequisites for Deployment:**
   - Node.js & NPM installed.
   - `wrangler` authenticated (`npx wrangler login`).

## Usage

### 1. Local Processing Only
Just process the video and generate a SQL file locally.

```bash
uv run main.py ./videos/meme.mp4
```

### 2. Deployment to Cloudflare
Deployment is now handled by a dedicated shell script in the root directory for better stability and performance.

**Step 1: Process and generate SQL**
```bash
uv run main.py ./videos/meme.mp4 \
  --r2-public-url https://meme-image-search.taconotsandwich.workers.dev/img
```

**Step 2: Run the deployment script**
From the project root:
```bash
./deploy.sh
```

| Flag              | Description                                                                                                      | 
|:------------------|:-----------------------------------------------------------------------------------------------------------------|
| `--r2-public-url` | The public domain where images are accessible (used to generate the correct SQL links).                          |

### Full Option List

| Category          | Option              | Default         | Description                                          | 
|:------------------|:--------------------|:----------------|:-----------------------------------------------------|
| **Input/Output**  | `<input_path>`      | -               | Video file or directory path.                        |
|                   | `-o, --output`      | `output`        | Folder for extracted images/metadata.                |
|                   | `--sql-file`        | `d1_import.sql` | Name of the generated SQL file.                      |
| **Extraction**    | `-i, --interval`    | `30`            | Extract every Nth frame (if scene detection is off). |
|                   | `--scene-detection` | `False`         | Enable scene-aware extraction.                       |
|                   | `--scene-threshold` | `30.0`          | Threshold for scene change detection.                 |
|                   | `--min-scene-len`   | `15`            | Minimum length of a scene in frames.                 |
|                   | `--keyframes-per-scene`| `3`          | Number of frames to pick from each detected scene.   |
| **OCR**           | `--ocr-engine`      | `tesseract`     | `tesseract` or `easyocr`.                            |
|                   | `--lang`            | `eng`           | Language code (e.g., `chi_tra`, `eng`).              |
|                   | `--text-region`     | `all`           | `all`, `top`, or `bottom`.                           |
| **Performance**   | `--workers`         | `4`             | Number of OCR worker processes.                      |
|                   | `--batch-size`      | `8`             | Number of frames processed in one batch.             |
| **Deduplication** | `--dedup-mode`      | `both`          | `ssim`, `text`, or `both`.                           |
|                   | `--ssim-threshold`  | `0.9`           | 0.0-1.0 similarity threshold.                        |

## How Deployment Works

1.  **Process:** Video is analyzed via `main.py`. Frames with no subtitles are trimmed.
2.  **Generate SQL:** `d1_import.sql` is created with the public URLs pre-calculated.
3.  **Deploy (Shell):** The `./deploy.sh` script uploads the images to R2 and executes the SQL on D1 sequentially for maximum stability.
