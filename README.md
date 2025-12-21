# Meme I Recalled From A Video - Monorepo

This repository contains two main components for processing videos and searching for memes.

## Projects

- **[image-search-api-server](./image-search-api-server)**: TypeScript API server for LINE and Discord integrations.
- **[video-processor](./video-processor)**: Python-based video processing tool using OCR and scene detection.

## Getting Started

### Prerequisites

- Node.js & npm (for the API server)
- Python 3.12+ and `uv` (for the video processor)

### Running the API Server

```bash
npm install
npm run server:dev
```

### Running the Video Processor

```bash
npm run processor:run
```
