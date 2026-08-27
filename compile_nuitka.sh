#!/usr/bin/env bash
# Prepared with love by YakomoDev - https://ko-fi.com/yakomodev
# Nuitka compilation automation script for Mission Ui.

set -e

echo "=========================================================="
echo "🌟 Starting Nuitka Compilation Process for Mission Ui"
echo "=========================================================="

# 1. Paths configuration
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$ROOT_DIR/data"
BACKUP_DIR="$ROOT_DIR/data_backup"

# Ensure we are in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
        echo "[*] Activating virtual environment..."
        source "$ROOT_DIR/.venv/bin/activate"
    else
        echo "[-] Warning: No active virtual environment found. Compiling with system Python."
    fi
fi

# 2. Creating blank project environment (Backup existing user data)
echo "[*] Backing up local developer data (database & preferences)..."
mkdir -p "$BACKUP_DIR"

FILES_TO_BACKUP=("missions.db" "prefs.json" "shaping_diagnostics.txt" "arabic_font_test.png")
DIRS_TO_BACKUP=("blueprints_migrated_backup" "days_migrated_backup")

for file in "${FILES_TO_BACKUP[@]}"; do
    if [ -f "$DATA_DIR/$file" ]; then
        mv "$DATA_DIR/$file" "$BACKUP_DIR/"
        echo "    -> Backed up $file"
    fi
done

for dir in "${DIRS_TO_BACKUP[@]}"; do
    if [ -d "$DATA_DIR/$dir" ]; then
        mv "$DATA_DIR/$dir" "$BACKUP_DIR/"
        echo "    -> Backed up directory $dir/"
    fi
done

echo "[+] Workspace is now a clean 'Blank Project' (Ready for standalone export)."

# 3. Compile using Nuitka
echo "[*] Running Nuitka Compiler..."
echo "[*] Target name: 'Mission Ui'"

python3 -m nuitka --standalone --show-progress \
  --enable-plugin=tk-inter \
  --include-data-dir="$DATA_DIR=data" \
  --output-filename="Mission Ui" \
  --remove-output \
  "$ROOT_DIR/app.py"

# 4. Rename the distribution directory if needed
DIST_DIR="$ROOT_DIR/app.dist"
NEW_DIST_DIR="$ROOT_DIR/Mission Ui"

if [ -d "$DIST_DIR" ]; then
    echo "[*] Customizing distribution folder name..."
    if [ -d "$NEW_DIST_DIR" ]; then
        rm -rf "$NEW_DIST_DIR"
    fi
    mv "$DIST_DIR" "$NEW_DIST_DIR"
    echo "[+] Standalone app is packaged inside: $NEW_DIST_DIR"
fi

# Copy agent folder containing the GGUF model
if [ -d "$ROOT_DIR/agent" ]; then
    echo "[*] Copying local AI agent folder into standalone package..."
    cp -r "$ROOT_DIR/agent" "$NEW_DIST_DIR/"
    echo "[+] AI model copied successfully!"
fi

# 5. Restore developer workspace
echo "[*] Restoring developer workspace data..."
for file in "${FILES_TO_BACKUP[@]}"; do
    if [ -f "$BACKUP_DIR/$file" ]; then
        mv "$BACKUP_DIR/$file" "$DATA_DIR/"
    fi
done

for dir in "${DIRS_TO_BACKUP[@]}"; do
    if [ -d "$BACKUP_DIR/$dir" ]; then
        mv "$BACKUP_DIR/$dir" "$DATA_DIR/"
    fi
done

if [ -d "$BACKUP_DIR" ]; then
    rmdir "$BACKUP_DIR" || rm -rf "$BACKUP_DIR"
fi

echo "=========================================================="
echo "🎉 SUCCESS: Compiled standalone bundle created!"
echo "📍 Location: $NEW_DIST_DIR"
echo "🚀 Run with: './Mission Ui/Mission Ui'"
echo "📂 User data is stocked inside 'Mission Ui/data/' and persists safely."
echo "=========================================================="
