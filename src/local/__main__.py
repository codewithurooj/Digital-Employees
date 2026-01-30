"""Local orchestrator entry point.

Usage:
    python -m src.local --vault ./AI_Employee_Vault
    python -m src.local --vault ./AI_Employee_Vault --live
"""

import argparse
import logging
import signal
import sys

from .local_orchestrator import LocalOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Local Agent Orchestrator")
    parser.add_argument("--vault", default="./AI_Employee_Vault", help="Vault path")
    parser.add_argument("--agent-id", default="local", help="Agent ID")
    parser.add_argument("--sync-interval", type=int, default=60, help="Sync interval (s)")
    parser.add_argument("--live", action="store_true", help="Live mode (not dry run)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    orchestrator = LocalOrchestrator(
        vault_path=args.vault,
        agent_id=args.agent_id,
        sync_interval=args.sync_interval,
        dry_run=not args.live,
    )

    def signal_handler(signum, frame):
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(f"\nLocal Agent: {args.agent_id}")
    print(f"Vault: {args.vault}")
    print(f"Mode: {'LIVE' if args.live else 'DRY RUN'}")
    print("Press Ctrl+C to stop\n")

    orchestrator.run()


if __name__ == "__main__":
    main()
