#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import subprocess
from datetime import datetime
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alembic_cmd = ["alembic"]
        
        # Set up Alembic environment variables
        os.environ["DATABASE_URL"] = self.config["DATABASE_URL"]
    
    def create_migration(self, message: str) -> None:
        """Create a new migration"""
        try:
            logger.info(f"Creating new migration: {message}")
            
            # Generate migration
            result = subprocess.run(
                self.alembic_cmd + ["revision", "--autogenerate", "-m", message],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to create migration: {result.stderr}")
                sys.exit(1)
            
            logger.info("Migration created successfully")
            
        except Exception as e:
            logger.error(f"Error creating migration: {str(e)}")
            sys.exit(1)
    
    def upgrade_database(self, revision: str = "head") -> None:
        """Upgrade database to specified revision"""
        try:
            logger.info(f"Upgrading database to revision: {revision}")
            
            # Run upgrade
            result = subprocess.run(
                self.alembic_cmd + ["upgrade", revision],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to upgrade database: {result.stderr}")
                sys.exit(1)
            
            logger.info("Database upgraded successfully")
            
        except Exception as e:
            logger.error(f"Error upgrading database: {str(e)}")
            sys.exit(1)
    
    def downgrade_database(self, revision: str) -> None:
        """Downgrade database to specified revision"""
        try:
            logger.info(f"Downgrading database to revision: {revision}")
            
            # Run downgrade
            result = subprocess.run(
                self.alembic_cmd + ["downgrade", revision],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to downgrade database: {result.stderr}")
                sys.exit(1)
            
            logger.info("Database downgraded successfully")
            
        except Exception as e:
            logger.error(f"Error downgrading database: {str(e)}")
            sys.exit(1)
    
    def show_migrations(self) -> None:
        """Show migration history"""
        try:
            logger.info("Showing migration history")
            
            # Get current revision
            current = subprocess.run(
                self.alembic_cmd + ["current"],
                capture_output=True,
                text=True
            )
            
            # Get migration history
            history = subprocess.run(
                self.alembic_cmd + ["history"],
                capture_output=True,
                text=True
            )
            
            if current.returncode != 0 or history.returncode != 0:
                logger.error("Failed to get migration history")
                sys.exit(1)
            
            print("\nCurrent Revision:")
            print(current.stdout.strip())
            print("\nMigration History:")
            print(history.stdout.strip())
            
        except Exception as e:
            logger.error(f"Error showing migrations: {str(e)}")
            sys.exit(1)
    
    def check_migrations(self) -> None:
        """Check for pending migrations"""
        try:
            logger.info("Checking for pending migrations")
            
            # Get current revision
            current = subprocess.run(
                self.alembic_cmd + ["current"],
                capture_output=True,
                text=True
            )
            
            # Get head revision
            head = subprocess.run(
                self.alembic_cmd + ["heads"],
                capture_output=True,
                text=True
            )
            
            if current.returncode != 0 or head.returncode != 0:
                logger.error("Failed to check migrations")
                sys.exit(1)
            
            current_rev = current.stdout.strip().split()[0]
            head_rev = head.stdout.strip().split()[0]
            
            if current_rev != head_rev:
                logger.warning(f"Database is not at the latest revision")
                logger.warning(f"Current: {current_rev}")
                logger.warning(f"Head: {head_rev}")
                sys.exit(1)
            
            logger.info("Database is up to date")
            
        except Exception as e:
            logger.error(f"Error checking migrations: {str(e)}")
            sys.exit(1)
    
    def backup_database(self) -> None:
        """Create a backup of the database"""
        try:
            logger.info("Creating database backup")
            
            # Parse database URL
            db_url = self.config["DATABASE_URL"]
            if db_url.startswith("postgresql://"):
                db_url = db_url[13:]
            
            # Extract connection details
            auth, rest = db_url.split("@")
            user, password = auth.split(":")
            host, port_db = rest.split(":")
            port, db = port_db.split("/")
            
            # Create backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_{db}_{timestamp}.sql"
            
            # Run pg_dump
            result = subprocess.run(
                [
                    "pg_dump",
                    "-h", host,
                    "-p", port,
                    "-U", user,
                    "-F", "c",
                    "-b",
                    "-v",
                    "-f", backup_file,
                    db
                ],
                capture_output=True,
                text=True,
                env={"PGPASSWORD": password}
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to create backup: {result.stderr}")
                sys.exit(1)
            
            logger.info(f"Backup created successfully: {backup_file}")
            
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            sys.exit(1)
    
    def restore_database(self, backup_file: str) -> None:
        """Restore database from backup"""
        try:
            logger.info(f"Restoring database from backup: {backup_file}")
            
            # Parse database URL
            db_url = self.config["DATABASE_URL"]
            if db_url.startswith("postgresql://"):
                db_url = db_url[13:]
            
            # Extract connection details
            auth, rest = db_url.split("@")
            user, password = auth.split(":")
            host, port_db = rest.split(":")
            port, db = port_db.split("/")
            
            # Run pg_restore
            result = subprocess.run(
                [
                    "pg_restore",
                    "-h", host,
                    "-p", port,
                    "-U", user,
                    "-d", db,
                    "-v",
                    "-c",
                    backup_file
                ],
                capture_output=True,
                text=True,
                env={"PGPASSWORD": password}
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to restore backup: {result.stderr}")
                sys.exit(1)
            
            logger.info("Database restored successfully")
            
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Database Migration Tool")
    parser.add_argument("--action", required=True,
                       choices=["create", "upgrade", "downgrade", "show", "check", "backup", "restore"],
                       help="Action to perform")
    parser.add_argument("--message", help="Migration message for create action")
    parser.add_argument("--revision", help="Target revision for upgrade/downgrade actions")
    parser.add_argument("--backup-file", help="Backup file for restore action")
    parser.add_argument("--database-url", required=True,
                       help="Database URL (e.g., postgresql://user:pass@host:port/db)")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        "DATABASE_URL": args.database_url
    }
    
    # Create migrator
    migrator = DatabaseMigrator(config)
    
    # Perform requested action
    if args.action == "create":
        if not args.message:
            logger.error("--message is required for create action")
            sys.exit(1)
        migrator.create_migration(args.message)
        
    elif args.action == "upgrade":
        migrator.upgrade_database(args.revision or "head")
        
    elif args.action == "downgrade":
        if not args.revision:
            logger.error("--revision is required for downgrade action")
            sys.exit(1)
        migrator.downgrade_database(args.revision)
        
    elif args.action == "show":
        migrator.show_migrations()
        
    elif args.action == "check":
        migrator.check_migrations()
        
    elif args.action == "backup":
        migrator.backup_database()
        
    elif args.action == "restore":
        if not args.backup_file:
            logger.error("--backup-file is required for restore action")
            sys.exit(1)
        migrator.restore_database(args.backup_file)

if __name__ == "__main__":
    main() 