#!/bin/bash
# Automated Backup Script for AI Employee Cloud
# Runs daily via cron - backs up Odoo database and filestore
#
# Cron entry (installed by setup-cloud-vm.sh):
#   0 3 * * * /home/ubuntu/Digital-Employees/deploy/cloud/backup-cron.sh

set -e

# Configuration
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/odoo"
RETENTION_DAYS=7
CONTAINER_DB="ai-employee-postgres"
DB_USER="odoo"
DB_NAME="postgres"
LOG_FILE="/var/log/ai-employee-backup.log"

log() {
    echo "[$(date -Iseconds)] $1" | tee -a "$LOG_FILE"
}

log "Starting backup..."

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL database
log "Backing up PostgreSQL database..."
docker exec "$CONTAINER_DB" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/db_${DATE}.sql.gz"

if [ $? -eq 0 ]; then
    DB_SIZE=$(du -h "$BACKUP_DIR/db_${DATE}.sql.gz" | cut -f1)
    log "Database backup complete: db_${DATE}.sql.gz ($DB_SIZE)"
else
    log "ERROR: Database backup failed!"
    exit 1
fi

# Backup Odoo filestore
log "Backing up Odoo filestore..."
docker run --rm \
    -v ai-employee-odoo-data:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf "/backup/filestore_${DATE}.tar.gz" -C /data .

if [ $? -eq 0 ]; then
    FS_SIZE=$(du -h "$BACKUP_DIR/filestore_${DATE}.tar.gz" | cut -f1)
    log "Filestore backup complete: filestore_${DATE}.tar.gz ($FS_SIZE)"
else
    log "ERROR: Filestore backup failed!"
    exit 1
fi

# Cleanup old backups
log "Cleaning up backups older than ${RETENTION_DAYS} days..."
DELETED=$(find "$BACKUP_DIR" -name "*.gz" -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)
log "Deleted $DELETED old backup files"

# List current backups
log "Current backups:"
ls -lh "$BACKUP_DIR"/*.gz 2>/dev/null | while read line; do
    log "  $line"
done

TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Total backup size: $TOTAL_SIZE"
log "Backup completed successfully"
