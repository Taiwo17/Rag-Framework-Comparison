
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="$PROJECT_ROOT/evaluation/vector_stores/langchain"
BACKUP_ROOT="$PROJECT_ROOT/production/backup"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/faiss_$TIMESTAMP"

if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: FAISS vector store not found: $SOURCE_DIR"
    exit 1
fi

mkdir -p "$BACKUP_DIR"

cp -a "$SOURCE_DIR/." "$BACKUP_DIR/"

(
    cd "$BACKUP_DIR"
    sha256sum index.faiss index.pkl > SHA256SUMS
)

# Retain only the five most recent backups
cd "$BACKUP_ROOT"

BACKUP_COUNT=$(find . -maxdepth 1 -type d -name 'faiss_*' | wc -l)

if (( BACKUP_COUNT > 5 )); then
    find . -maxdepth 1 -type d -name 'faiss_*' \
        | sort \
        | head -n "$((BACKUP_COUNT - 5))" \
        | while read -r OLD_BACKUP; do
            rm -rf -- "$OLD_BACKUP"
            echo "Removed old backup: $OLD_BACKUP"
        done
fi

echo "Backup completed: $BACKUP_DIR"
echo "Backup checksums:"
cat "$BACKUP_DIR/SHA256SUMS"
