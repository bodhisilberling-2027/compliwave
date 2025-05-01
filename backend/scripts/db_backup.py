#!/usr/bin/env python3
import os
import sys
import subprocess
from datetime import datetime
import boto3
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_backup(db_name, db_user, db_password, db_host, backup_dir):
    """Create a PostgreSQL database backup"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.sql")
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    try:
        # Set PostgreSQL environment variables
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        # Create backup
        cmd = [
            "pg_dump",
            "-h", db_host,
            "-U", db_user,
            "-d", db_name,
            "-f", backup_file
        ]
        
        subprocess.run(cmd, env=env, check=True)
        logger.info(f"Backup created successfully: {backup_file}")
        return backup_file
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup failed: {str(e)}")
        sys.exit(1)

def upload_to_s3(backup_file, bucket_name, aws_access_key=None, aws_secret_key=None):
    """Upload backup file to S3"""
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        backup_key = f"backups/{os.path.basename(backup_file)}"
        s3.upload_file(backup_file, bucket_name, backup_key)
        logger.info(f"Backup uploaded to S3: s3://{bucket_name}/{backup_key}")
        
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        sys.exit(1)

def restore_backup(backup_file, db_name, db_user, db_password, db_host):
    """Restore PostgreSQL database from backup"""
    try:
        # Set PostgreSQL environment variables
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        # Drop existing database
        drop_cmd = [
            "dropdb",
            "-h", db_host,
            "-U", db_user,
            "--if-exists",
            db_name
        ]
        subprocess.run(drop_cmd, env=env, check=True)
        
        # Create new database
        create_cmd = [
            "createdb",
            "-h", db_host,
            "-U", db_user,
            db_name
        ]
        subprocess.run(create_cmd, env=env, check=True)
        
        # Restore from backup
        restore_cmd = [
            "psql",
            "-h", db_host,
            "-U", db_user,
            "-d", db_name,
            "-f", backup_file
        ]
        subprocess.run(restore_cmd, env=env, check=True)
        logger.info(f"Database restored successfully from {backup_file}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Restore failed: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Database backup and restore utility")
    parser.add_argument("--action", choices=["backup", "restore"], required=True)
    parser.add_argument("--db-name", required=True)
    parser.add_argument("--db-user", required=True)
    parser.add_argument("--db-password", required=True)
    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--backup-dir", default="./backups")
    parser.add_argument("--s3-bucket")
    parser.add_argument("--aws-access-key")
    parser.add_argument("--aws-secret-key")
    parser.add_argument("--backup-file")
    
    args = parser.parse_args()
    
    if args.action == "backup":
        backup_file = create_backup(
            args.db_name,
            args.db_user,
            args.db_password,
            args.db_host,
            args.backup_dir
        )
        
        if args.s3_bucket:
            upload_to_s3(
                backup_file,
                args.s3_bucket,
                args.aws_access_key,
                args.aws_secret_key
            )
    
    elif args.action == "restore":
        if not args.backup_file:
            logger.error("--backup-file is required for restore action")
            sys.exit(1)
            
        restore_backup(
            args.backup_file,
            args.db_name,
            args.db_user,
            args.db_password,
            args.db_host
        )

if __name__ == "__main__":
    main() 