/**
 * PM2 Ecosystem Configuration
 * AI Employee Platinum Tier - Cloud Agent
 *
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 save
 *   pm2 startup
 */

module.exports = {
  apps: [
    {
      name: 'cloud-orchestrator',
      script: 'python',
      args: '-m src.cloud.cloud_orchestrator',
      cwd: '/home/ubuntu/Digital-Employees',
      interpreter: 'none',
      env: {
        PYTHONPATH: '/home/ubuntu/Digital-Employees',
        AGENT_ID: 'cloud',
        WORK_ZONE: 'cloud',
        DRY_RUN: 'false',
        VAULT_PATH: '/home/ubuntu/AI_Employee_Vault'
      },
      // Restart configuration
      max_restarts: 10,
      min_uptime: '10s',
      max_memory_restart: '500M',
      restart_delay: 5000,
      autorestart: true,

      // Logging
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      error_file: '/home/ubuntu/Digital-Employees/logs/cloud-orchestrator-error.log',
      out_file: '/home/ubuntu/Digital-Employees/logs/cloud-orchestrator-out.log',
      merge_logs: true,

      // Process management
      kill_timeout: 10000,
      wait_ready: true,
      listen_timeout: 10000,

      // Watch disabled for production
      watch: false,
      ignore_watch: ['node_modules', 'logs', '.git', '__pycache__']
    },
    {
      name: 'health-monitor',
      script: 'python',
      args: '-m src.cloud.health_monitor',
      cwd: '/home/ubuntu/Digital-Employees',
      interpreter: 'none',
      env: {
        PYTHONPATH: '/home/ubuntu/Digital-Employees',
        AGENT_ID: 'cloud',
        VAULT_PATH: '/home/ubuntu/AI_Employee_Vault',
        CHECK_INTERVAL: '60'
      },
      // Restart every 6 hours for memory cleanup
      cron_restart: '0 */6 * * *',
      max_restarts: 5,
      autorestart: true,

      // Logging
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      error_file: '/home/ubuntu/Digital-Employees/logs/health-monitor-error.log',
      out_file: '/home/ubuntu/Digital-Employees/logs/health-monitor-out.log',
      merge_logs: true
    },
    {
      name: 'sync-daemon',
      script: 'python',
      args: '-m src.cloud.sync_daemon',
      cwd: '/home/ubuntu/Digital-Employees',
      interpreter: 'none',
      env: {
        PYTHONPATH: '/home/ubuntu/Digital-Employees',
        AGENT_ID: 'cloud',
        VAULT_PATH: '/home/ubuntu/AI_Employee_Vault',
        SYNC_INTERVAL: '30'
      },
      max_restarts: 10,
      autorestart: true,

      // Logging
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      error_file: '/home/ubuntu/Digital-Employees/logs/sync-daemon-error.log',
      out_file: '/home/ubuntu/Digital-Employees/logs/sync-daemon-out.log',
      merge_logs: true
    }
  ],

  // Deployment configuration (optional)
  deploy: {
    production: {
      user: 'ubuntu',
      host: ['your-cloud-vm-ip'],
      ref: 'origin/main',
      repo: 'git@github.com:yourusername/Digital-Employees.git',
      path: '/home/ubuntu/Digital-Employees',
      'pre-deploy-local': '',
      'post-deploy': 'pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
};
