#!/bin/bash
PROJECT_DIR="/home/mynamemyway/projects/antoshkin-pwa-card"
BACKUP_DIR="$PROJECT_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp "$PROJECT_DIR/data/loyalty.db" "$BACKUP_DIR/loyalty_$DATE.db"
ls -t $BACKUP_DIR/*.db | tail -n +8 | xargs -r rm