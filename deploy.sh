#!/bin/bash

# Deployment script for Meme Search Bot
# Handles R2 image uploads and D1 database updates with optimized logging

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
TARGET_DIR="$OUTPUT_DIR"
DB_ONLY=false
IMAGE_ONLY=false

for arg in "$@"; do
    if [ "$arg" == "--db-only" ]; then
        DB_ONLY=true
    elif [ "$arg" == "--image-only" ]; then
        IMAGE_ONLY=true
    else
        if [ -d "$OUTPUT_DIR/$arg" ]; then
            TARGET_DIR="$OUTPUT_DIR/$arg"
            echo -e "${BLUE}Targeting specific movie: $arg${NC}"
        else
            echo -e "${RED}Error: Movie folder '$arg' not found in $OUTPUT_DIR${NC}"
            exit 1
        fi
    fi
done

# 2. Find Wrangler Path (Avoid npx overhead)
WRANGLER_BIN=$(which wrangler)
if [ -z "$WRANGLER_BIN" ]; then
    WRANGLER_BIN=$(npm bin)/wrangler
fi
if [ ! -f "$WRANGLER_BIN" ]; then
    WRANGLER_BIN="npx wrangler"
fi

# 3. Upload to R2 (Skip if --db-only is passed)
if [ "$DB_ONLY" = false ]; then
    echo -e "${GREEN}Step 1: Uploading images to R2 bucket '$BUCKET_NAME'...${NC}"

    # Verify wrangler is logged in
    $WRANGLER_BIN whoami || { echo -e "${RED}Error: Wrangler not authenticated. Run 'npx wrangler login'.${NC}"; exit 1; }

    # Count files
    total_files=$(find "$TARGET_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) | wc -l | xargs)
    current=0
    skipped=0
    added=0

    echo -e "${BLUE}Found $total_files total images. Starting deployment...${NC}\n"

    find "$TARGET_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" \) | while read -r img; do
        rel_path=${img#"$OUTPUT_DIR/"}
        current=$((current + 1))
        
        # SMART SKIP: Check if file already exists in R2 (without downloading to disk)
        if $WRANGLER r2 object get "$BUCKET_NAME/$rel_path" --remote --file - > /dev/null 2>&1; then
            echo -e "[$current/$total_files] ${YELLOW}SKIPPED${NC}: $rel_path (Already in R2)"
            skipped=$((skipped + 1))
            continue
        fi

        # Actual upload
        echo -ne "[$current/$total_files] ${GREEN}ADDING${NC}: $rel_path... "
        
        success=false
        for attempt in {1..3}; do
            # Use a timeout of 15 seconds for the upload
            if $WRANGLER_BIN r2 object put "$BUCKET_NAME/$rel_path" --file "$img" --remote > /dev/null 2>&1; then
                success=true
                echo -e "${GREEN}DONE${NC}"
                added=$((added + 1))
                break
            else
                if [ $attempt -lt 3 ]; then
                    echo -ne "${RED}Retry $attempt...${NC} "
                    sleep 2
                fi
            fi
        done

        if [ "$success" = false ]; then
            echo -e "\n${RED}FAILED to upload $rel_path after 3 attempts.${NC}"
            exit 1 
        fi
    done
    echo -e "\n${GREEN}R2 Summary: $added added, $skipped skipped, $total_files total.${NC}"
else
    echo -e "${BLUE}Skipping R2 upload (--db-only mode)${NC}"
fi

# 4. Deploy to D1
if [ "$IMAGE_ONLY" = false ]; then
    echo -e "\n${GREEN}Step 2: Updating D1 Database '$D1_DATABASE'...${NC}"
    cd "$API_SERVER_DIR" || exit
    find "../$TARGET_DIR" -name "d1_import.sql" | while read -r sql_file; do
        echo -e "  Executing: $sql_file"
        $WRANGLER_BIN d1 execute "$D1_DATABASE" --remote --file="$sql_file" > /dev/null 2>&1
    done
    cd ..
else
    echo -e "\n${BLUE}Skipping D1 update (--image-only mode)${NC}"
fi

echo -e "\n${BLUE}==================================================${NC}"
echo -e "${BLUE}           DEPLOYMENT COMPLETE!                 ${NC}"
echo -e "${BLUE}==================================================${NC}"