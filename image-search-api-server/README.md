# Meme Search API Server

A TypeScript-based Cloudflare Worker using the Hono framework to power the Discord bot interactions and serve meme images from R2.

## Cloudflare Setup Guide

### 1. Authentication
Ensure you are logged into your Cloudflare account via the CLI:
```bash
npx wrangler login
```

### 2. Database Setup (D1)
Create the D1 database that will store the searchable meme metadata:
```bash
npx wrangler d1 create meme
```
*Note: Copy the `database_id` from the output and update your `wrangler.toml` file under the `[[d1_databases]]` section.*

### 3. Storage Setup (R2)
Create the R2 bucket where the actual image files will be stored:
```bash
npx wrangler r2 bucket create meme
```
*Note: Ensure the `bucket_name` in `wrangler.toml` matches the name used here.*

### 4. Environment Secrets
The following secrets are required for the application to function. Use the command below to set each one securely on Cloudflare's servers:

```bash
npx wrangler secret put <SECRET_NAME>
```

| Secret Name          | Description                                                                 |
|:---------------------|:----------------------------------------------------------------------------|
| `DISCORD_PUBLIC_KEY` | Found in Discord Developer Portal -> General Information.                   |
| `DISCORD_APP_ID`     | Your Bot's Application ID.                                                  |
| `DISCORD_BOT_TOKEN`  | Found in Discord Developer Portal -> Bot -> Token.                          |
| `ADMIN_SECRET`       | A private password you choose to protect the `/register-commands` endpoint. |

### 5. Deployment
Deploy the worker to your Cloudflare account:
```bash
npx wrangler deploy
```

## API Endpoints

- **`POST /api/discord/webhook`**: The main interaction endpoint for Discord. This URL should be pasted into the "Interactions Endpoint URL" field in the Discord Developer Portal.
- **`GET /img/*`**: A proxy endpoint that fetches and serves private images from the R2 bucket.
- **`GET /register-commands?secret=...`**: An admin-only endpoint used to register/update the slash commands with Discord.

## Development

To run the worker locally for testing:
```bash
npm install
npm run dev
```
For local development, secrets can be stored in a `.dev.vars` file (which is ignored by Git).