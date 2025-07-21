#!/bin/bash
# Generate docker-compose.yml from template with multiple project paths

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/docker-compose.template.yml"
OUTPUT_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"

# Default project paths if not set
DEFAULT_PROJECT_PATHS="/Users/mustafaacar/codemcp"

# Function to generate volume mount lines
generate_volume_mounts() {
    local paths="$1"
    local mounts=""

    # Convert comma-separated paths to array
    IFS=',' read -ra PATHS <<< "$paths"

    for path in "${PATHS[@]}"; do
        # Trim whitespace
        path=$(echo "$path" | xargs)

        if [ -d "$path" ]; then
            # Get basename for the mount point
            basename=$(basename "$path")
            # Add volume mount line with proper indentation
            if [ -z "$mounts" ]; then
                mounts="- ${path}:/opengrok/src/${basename}:ro"
            else
                mounts="${mounts}"$'\n'"      - ${path}:/opengrok/src/${basename}:ro"
            fi
            echo "Adding project: $path -> /opengrok/src/$basename" >&2
        else
            echo "Warning: Directory not found: $path" >&2
        fi
    done

    echo "$mounts"
}

# Read project paths from environment or .env file
if [ -f "$ENV_FILE" ]; then
    # Source the .env file
    set -a
    source "$ENV_FILE"
    set +a
fi

# Use PROJECT_PATHS from environment or default
PROJECT_PATHS="${PROJECT_PATHS:-$DEFAULT_PROJECT_PATHS}"

echo "Generating docker-compose.yml with project paths:"
echo "$PROJECT_PATHS" | tr ',' '\n'

# Generate volume mounts
VOLUME_MOUNTS=$(generate_volume_mounts "$PROJECT_PATHS")

# Read template and replace PROJECT_VOLUMES
if [ -f "$TEMPLATE_FILE" ]; then
    # Use awk to replace the ${PROJECT_VOLUMES} line with actual mounts
    awk -v mounts="$VOLUME_MOUNTS" '
        /\$\{PROJECT_VOLUMES\}/ {
            print mounts
            next
        }
        { print }
    ' "$TEMPLATE_FILE" > "$OUTPUT_FILE"

    echo "Generated docker-compose.yml successfully!"
else
    echo "Error: Template file not found: $TEMPLATE_FILE"
    exit 1
fi
