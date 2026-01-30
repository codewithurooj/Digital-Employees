#!/bin/bash
# Local Sync Setup Script for AI Employee Platinum Tier
# Configures the local machine to sync with the cloud agent via Git

set -e

echo "============================================"
echo "AI Employee Local Sync Setup - Platinum Tier"
echo "============================================"

# Configuration
VAULT_DIR="${VAULT_PATH:-./AI_Employee_Vault}"
REPO_URL="${VAULT_REPO_URL:-}"

log_info() { echo -e "\033[0;32m[INFO]\033[0m $1"; }
log_warn() { echo -e "\033[1;33m[WARN]\033[0m $1"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

# Check prerequisites
command -v git >/dev/null 2>&1 || { log_error "Git is required but not installed."; exit 1; }
command -v python3 >/dev/null 2>&1 || { log_error "Python 3 is required but not installed."; exit 1; }

# Step 1: Initialize Git in vault if not already
if [ ! -d "$VAULT_DIR/.git" ]; then
    if [ -z "$REPO_URL" ]; then
        log_error "Vault is not a Git repo and no VAULT_REPO_URL provided."
        log_info "Usage: VAULT_REPO_URL=git@github.com:user/vault.git ./setup-local-sync.sh"
        exit 1
    fi

    log_info "Initializing vault Git repository..."
    cd "$VAULT_DIR"
    git init
    git remote add origin "$REPO_URL"
    git fetch origin
    git checkout -b main origin/main || git checkout -b main
    log_info "Vault Git repository initialized."
else
    log_info "Vault already has Git initialized."
    cd "$VAULT_DIR"
fi

# Step 2: Configure Git for local agent
log_info "Configuring Git for local agent..."
git config user.email "local-agent@ai-employee.local"
git config user.name "Local Agent"

# Configure merge strategy
git config pull.rebase false
git config merge.conflictstyle diff3

# Step 3: Create Platinum tier vault folders
log_info "Creating Platinum tier vault folders..."
FOLDERS=(
    "Needs_Action/email"
    "Needs_Action/accounting"
    "Needs_Action/social"
    "Needs_Action/local"
    "Pending_Approval/email"
    "Pending_Approval/accounting"
    "Pending_Approval/social"
    "Pending_Approval/payments"
    "In_Progress/cloud"
    "In_Progress/local"
    "Updates"
    "Signals"
    "Health"
)

for folder in "${FOLDERS[@]}"; do
    mkdir -p "$folder"
    if [ ! -f "$folder/.gitkeep" ]; then
        touch "$folder/.gitkeep"
    fi
done

# Step 4: Verify .gitignore
log_info "Verifying .gitignore..."
REQUIRED_PATTERNS=(
    ".env"
    ".env.*"
    "*.env"
    "config/gmail*.json"
    "config/whatsapp_session/"
    "config/*_token*"
    "*.pem"
    "*.key"
)

GITIGNORE="$VAULT_DIR/.gitignore"
touch "$GITIGNORE"

for pattern in "${REQUIRED_PATTERNS[@]}"; do
    if ! grep -qF "$pattern" "$GITIGNORE"; then
        echo "$pattern" >> "$GITIGNORE"
        log_info "  Added '$pattern' to .gitignore"
    fi
done

# Step 5: Initial sync test
log_info "Testing Git sync..."
git add -A
git diff --cached --quiet && log_info "  No changes to commit." || {
    git commit -m "local: Initialize Platinum tier vault structure"
    log_info "  Committed initial structure."
}

if git remote get-url origin >/dev/null 2>&1; then
    git pull origin main --no-edit 2>/dev/null && log_info "  Pull successful." || log_warn "  Pull failed (remote may not exist yet)."
    git push origin main 2>/dev/null && log_info "  Push successful." || log_warn "  Push failed (check SSH keys)."
else
    log_warn "  No remote configured. Skipping push/pull test."
fi

# Step 6: Update local .env
cd -
log_info ""
log_info "============================================"
log_info "Local Sync Setup Complete!"
log_info "============================================"
log_info ""
log_info "Ensure your .env has these settings:"
log_info "  AGENT_ID=local"
log_info "  WORK_ZONE=local"
log_info "  GIT_AUTO_PULL=true"
log_info "  GIT_PULL_INTERVAL=60"
log_info ""
log_info "Start local agent with:"
log_info "  python -m src.local.local_orchestrator"
