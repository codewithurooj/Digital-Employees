"""Cloud orchestrator entry point.

Usage:
    python -m src.cloud --vault ./AI_Employee_Vault
    python -m src.cloud --vault ./AI_Employee_Vault --live
"""

import argparse
import logging
import signal
import sys

from .cloud_orchestrator import CloudOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Cloud Agent Orchestrator")
    parser.add_argument("--vault", default="./AI_Employee_Vault", help="Vault path")
    parser.add_argument("--agent-id", default="cloud", help="Agent ID")
    parser.add_argument("--sync-interval", type=int, default=60, help="Sync interval (s)")
    parser.add_argument("--health-interval", type=int, default=60, help="Health check interval (s)")
    parser.add_argument("--live", action="store_true", help="Live mode (not dry run)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    orchestrator = CloudOrchestrator(
        vault_path=args.vault,
        agent_id=args.agent_id,
        sync_interval=args.sync_interval,
        health_interval=args.health_interval,
        dry_run=not args.live,
    )

    def signal_handler(signum, frame):
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"\nCloud Agent: {args.agent_id}")
    print(f"Vault: {args.vault}")
    print(f"Mode: {'LIVE' if args.live else 'DRY RUN'}")
    print("Press Ctrl+C to stop\n")

    orchestrator.run()


if __name__ == "__main__":
    main()
