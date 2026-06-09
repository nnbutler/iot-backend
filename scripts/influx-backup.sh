#!/bin/sh
set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d)
KEEP_DAYS=${BACKUP_KEEP_DAYS:-7}

# Run backup
influx backup "$BACKUP_DIR/$DATE" \
  --host http://influxdb:8086 \
  --token "$INFLUXDB_TOKEN"

# Remove backups older than retention window
find "$BACKUP_DIR" -maxdepth 1 -mindepth 1 -type d -mtime "+$KEEP_DAYS" -exec rm -rf {} +
