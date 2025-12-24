# Video Processing & Cloudflare Deployment Tool (STT-Only Version)

A unified tool that extracts frames from videos using **Whisper STT** (Speech-to-Text), and automatically deploys the results to **Cloudflare R2** (Images) and **Cloudflare D1** (Database).

## Installation

1. Clone this repository.
2. Install [uv](https://github.com/astral-sh/uv).
3. Install **FFmpeg** on your system.
4. Sync dependencies:
   ```bash
   uv sync
   ```
   *Note: Includes `torch` for automatic GPU acceleration (MPS on macOS, CUDA on Windows/Linux).*

4. **Prerequisites for Deployment:**
   - Node.js & NPM installed.
   - `wrangler` authenticated (`npx wrangler login`).

## Usage

### 1. Local Processing
The tool transcribes dialogue and picks the middle frame of each line for extraction. **Automatically uses GPU (MPS/CUDA) if available.**

```bash
uv run main.py ./input/movie.mp4 --stt-lang zh
```

### 2. Deployment to Cloudflare
From the project root:
```bash
./deploy.sh [movie_folder_name] [--db-only] [--image-only]
```

## Full Option List

| Category          | Option         | Default                  | Description                                       | 
|:------------------|:---------------|:-------------------------|:--------------------------------------------------|
| **Input/Output**  | `<input_path>` | -                        | Video file or directory path.                     |
|                   | `-o, --output` | `output`                 | Folder for extracted images/metadata.             |
|                   | `--sql-file`   | `d1_import.sql`          | Name of the SQL file (saved inside movie folder). |
|                   | `--length`     | -                        | Limit processing duration (e.g. `1h`, `1m30s`).   |
| **STT Settings**  | `--stt-lang`   | `en`                     | Language cadd ode for transcription.              |
| **whisper-model** | `large-v3-mlx` | Whisper model size/path. |
| **OCR Settings**  | `--lang`       | `eng`                    | OCR Language code (e.g., `ch_tra`).               |
| **Performance**   | `--workers`    | `4`                      | Number of worker processes.                       |
|                   | `--batch-size` | `8`                      | Number of frames processed in one batch.          |

## How Deployment Works

1.  **Process:** Video is analyzed via `main.py`. Frames are extracted based on detected speech segments.
2.  **Generate SQL:** `d1_import.sql` is created using relative paths for the images.
3.  **Deploy (Shell):** `./deploy.sh` uploads images to R2 and executes SQL on D1.
