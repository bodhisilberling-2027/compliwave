#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration(command, message=None):
    """Run an Alembic migration command"""
    try:
        if command == "revision" and message:
            cmd = ["alembic", command, "--autogenerate", "-m", message]
        else:
            cmd = ["alembic", command]
            
        subprocess.run(cmd, check=True)
        logger.info(f"Migration command '{command}' completed successfully")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

def create_migration(message):
    """Create a new migration"""
    if not message:
        message = f"Migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_migration("revision", message)

def upgrade_database(revision="head"):
    """Upgrade database to specified revision"""
    run_migration(f"upgrade {revision}")

def downgrade_database(revision):
    """Downgrade database to specified revision"""
    run_migration(f"downgrade {revision}")

def show_migration_history():
    """Show migration history"""
    run_migration("history")

def show_current_revision():
    """Show current database revision"""
    run_migration("current")

def main():
    parser = argparse.ArgumentParser(description="Database migration utility")
    parser.add_argument("--action", choices=["create", "upgrade", "downgrade", "history", "current"], required=True)
    parser.add_argument("--message", help="Migration message (required for create action)")
    parser.add_argument("--revision", help="Target revision for upgrade/downgrade")
    
    args = parser.parse_args()
    
    if args.action == "create":
        if not args.message:
            logger.error("--message is required for create action")
            sys.exit(1)
        create_migration(args.message)
        
    elif args.action == "upgrade":
        upgrade_database(args.revision or "head")
        
    elif args.action == "downgrade":
        if not args.revision:
            logger.error("--revision is required for downgrade action")
            sys.exit(1)
        downgrade_database(args.revision)
        
    elif args.action == "history":
        show_migration_history()
        
    elif args.action == "current":
        show_current_revision()

if __name__ == "__main__":
    main() 