#!/bin/bash

# Deployment script for Meme Search Bot using wrangler for R2 and D1
# Default behavior: Overwrites existing data and resets the database table.

# --- Configuration ---
BUCKET_NAME="meme"
D1_DATABASE="meme"
OUTPUT_DIR="video-processor/output"
API_SERVER_DIR="image-search-api-server"

# --- Colors ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}        MEME BOT DEPLOYMENT SCRIPT              ${NC}"
echo -e "${BLUE}==================================================${NC}"

# 1. Parse Arguments
MOVIE_NAME=""
SKIP_REPLACE=false

for arg in "$@"; do
    if [ "$arg" == "--skip-replace" ]; then
        SKIP_REPLACE=true
    else
        # If it's not a flag, assume it's the movie name
        if [ -d "$OUTPUT_DIR/$arg" ]; then
            MOVIE_NAME="$arg"
        fi
    fi
done

if [ -z "$MOVIE_NAME" ]; then
    echo -e "${RED}Error: Specify a valid movie folder (e.g., ./deploy.sh let_the_bullet_fly)${NC}"
    exit 1
fi

echo -e "${BLUE}Targeting movie: $MOVIE_NAME${NC}"
[ "$SKIP_REPLACE" = true ] && echo -e "${YELLOW}Mode: Skip Replace (won\'t upload if file exists)${NC}"

TARGET_DIR="$OUTPUT_DIR/$MOVIE_NAME"
WRANGLER_BIN="npx wrangler"

# 2. R2 Upload
echo -e "${GREEN}Step 1: Managing R2 Images...${NC}"

echo -e "${GREEN}Uploading images to $MOVIE_NAME...${NC}"
total_files=$(find "$TARGET_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) | wc -l | xargs)
current=0
skipped=0

find "$TARGET_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) | while read -r img; do
    rel_path=${img#"$OUTPUT_DIR/"}
    current=$((current + 1))
    
    # Check if we should skip
    if [ "$SKIP_REPLACE" = true ]; then
        # Use r2 object get to check existence (returns 0 if found)
        if $WRANGLER_BIN r2 object get "$BUCKET_NAME/$rel_path" --remote --file - > /dev/null 2>&1; then
            echo -e "[$current/$total_files] ${YELLOW}SKIPPED${NC}: $rel_path"
            skipped=$((skipped + 1))
            continue
        fi
    fi

    echo -ne "[$current/$total_files] UPLOADING: $rel_path... "
    $WRANGLER_BIN r2 object put "$BUCKET_NAME/$rel_path" --file "$img" --remote > /dev/null 2>&1 && echo -e "${GREEN}DONE${NC}" || echo -e "${RED}FAIL${NC}"
done

echo -e "\n${GREEN}R2 Summary: Finished. Total: $total_files, Skipped: $skipped${NC}"

# 3. D1 Update
echo -e "\n${GREEN}Step 2: Resetting D1 Database...${NC}"
# Note: d1_import.sql contains 'DROP TABLE IF EXISTS video_frames;'
cd "$API_SERVER_DIR" && $WRANGLER_BIN d1 execute "$D1_DATABASE" --remote --file="../$TARGET_DIR/d1_import.sql"
cd ..

echo -e "\n${BLUE}==================================================${NC}"
echo -e "${BLUE}           DEPLOYMENT COMPLETE!                 ${NC}"
echo -e "${BLUE}==================================================${NC}"