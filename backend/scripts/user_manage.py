#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import psycopg2
import bcrypt
from datetime import datetime
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.conn = None
        self.setup_connection()
    
    def setup_connection(self) -> None:
        """Set up database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.config["DB_HOST"],
                port=self.config["DB_PORT"],
                database=self.config["DB_NAME"],
                user=self.config["DB_USER"],
                password=self.config["DB_PASSWORD"]
            )
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            sys.exit(1)
    
    def create_user(self, email: str, password: str, role: str = "user",
                   organization_id: int = None) -> Dict[str, Any]:
        """Create a new user"""
        try:
            # Hash password
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode(), salt)
            
            with self.conn.cursor() as cur:
                # Check if user already exists
                cur.execute(
                    "SELECT id FROM users WHERE email = %s",
                    (email,)
                )
                if cur.fetchone():
                    logger.error(f"User with email {email} already exists")
                    return None
                
                # Create user
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, role, organization_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, email, role, organization_id, created_at
                    """,
                    (email, hashed.decode(), role, organization_id,
                     datetime.now(), datetime.now())
                )
                
                user = cur.fetchone()
                self.conn.commit()
                
                return {
                    "id": user[0],
                    "email": user[1],
                    "role": user[2],
                    "organization_id": user[3],
                    "created_at": user[4]
                }
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating user: {str(e)}")
            return None
    
    def update_user(self, user_id: int, **kwargs) -> Dict[str, Any]:
        """Update user details"""
        try:
            with self.conn.cursor() as cur:
                # Check if user exists
                cur.execute(
                    "SELECT id FROM users WHERE id = %s",
                    (user_id,)
                )
                if not cur.fetchone():
                    logger.error(f"User with ID {user_id} not found")
                    return None
                
                # Build update query
                update_fields = []
                values = []
                
                if "email" in kwargs:
                    update_fields.append("email = %s")
                    values.append(kwargs["email"])
                
                if "password" in kwargs:
                    salt = bcrypt.gensalt()
                    hashed = bcrypt.hashpw(kwargs["password"].encode(), salt)
                    update_fields.append("password_hash = %s")
                    values.append(hashed.decode())
                
                if "role" in kwargs:
                    update_fields.append("role = %s")
                    values.append(kwargs["role"])
                
                if "organization_id" in kwargs:
                    update_fields.append("organization_id = %s")
                    values.append(kwargs["organization_id"])
                
                update_fields.append("updated_at = %s")
                values.append(datetime.now())
                
                # Add user_id to values
                values.append(user_id)
                
                # Execute update
                cur.execute(
                    f"""
                    UPDATE users
                    SET {", ".join(update_fields)}
                    WHERE id = %s
                    RETURNING id, email, role, organization_id, created_at, updated_at
                    """,
                    values
                )
                
                user = cur.fetchone()
                self.conn.commit()
                
                return {
                    "id": user[0],
                    "email": user[1],
                    "role": user[2],
                    "organization_id": user[3],
                    "created_at": user[4],
                    "updated_at": user[5]
                }
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating user: {str(e)}")
            return None
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user"""
        try:
            with self.conn.cursor() as cur:
                # Check if user exists
                cur.execute(
                    "SELECT id FROM users WHERE id = %s",
                    (user_id,)
                )
                if not cur.fetchone():
                    logger.error(f"User with ID {user_id} not found")
                    return False
                
                # Delete user
                cur.execute(
                    "DELETE FROM users WHERE id = %s",
                    (user_id,)
                )
                
                self.conn.commit()
                return True
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error deleting user: {str(e)}")
            return False
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Get user details"""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, role, organization_id, created_at, updated_at
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                
                user = cur.fetchone()
                if not user:
                    logger.error(f"User with ID {user_id} not found")
                    return None
                
                return {
                    "id": user[0],
                    "email": user[1],
                    "role": user[2],
                    "organization_id": user[3],
                    "created_at": user[4],
                    "updated_at": user[5]
                }
                
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None
    
    def list_users(self, organization_id: int = None, role: str = None,
                  limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List users with optional filters"""
        try:
            with self.conn.cursor() as cur:
                # Build query
                query = """
                    SELECT id, email, role, organization_id, created_at, updated_at
                    FROM users
                    WHERE 1=1
                """
                values = []
                
                if organization_id is not None:
                    query += " AND organization_id = %s"
                    values.append(organization_id)
                
                if role is not None:
                    query += " AND role = %s"
                    values.append(role)
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                values.extend([limit, offset])
                
                # Execute query
                cur.execute(query, values)
                
                users = []
                for row in cur.fetchall():
                    users.append({
                        "id": row[0],
                        "email": row[1],
                        "role": row[2],
                        "organization_id": row[3],
                        "created_at": row[4],
                        "updated_at": row[5]
                    })
                
                return users
                
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return []
    
    def verify_password(self, email: str, password: str) -> bool:
        """Verify user password"""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT password_hash FROM users WHERE email = %s",
                    (email,)
                )
                
                result = cur.fetchone()
                if not result:
                    return False
                
                stored_hash = result[0].encode()
                return bcrypt.checkpw(password.encode(), stored_hash)
                
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description="User Management Tool")
    parser.add_argument("--action", required=True,
                       choices=["create", "update", "delete", "get", "list", "verify"],
                       help="Action to perform")
    parser.add_argument("--user-id", type=int, help="User ID for get/update/delete actions")
    parser.add_argument("--email", help="User email")
    parser.add_argument("--password", help="User password")
    parser.add_argument("--role", choices=["admin", "user"], help="User role")
    parser.add_argument("--organization-id", type=int, help="Organization ID")
    parser.add_argument("--limit", type=int, default=100, help="Limit for list action")
    parser.add_argument("--offset", type=int, default=0, help="Offset for list action")
    parser.add_argument("--db-host", required=True, help="Database host")
    parser.add_argument("--db-port", required=True, help="Database port")
    parser.add_argument("--db-name", required=True, help="Database name")
    parser.add_argument("--db-user", required=True, help="Database user")
    parser.add_argument("--db-password", required=True, help="Database password")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        "DB_HOST": args.db_host,
        "DB_PORT": args.db_port,
        "DB_NAME": args.db_name,
        "DB_USER": args.db_user,
        "DB_PASSWORD": args.db_password
    }
    
    # Create user manager
    manager = UserManager(config)
    
    # Perform requested action
    if args.action == "create":
        if not all([args.email, args.password]):
            logger.error("--email and --password are required for create action")
            sys.exit(1)
        
        user = manager.create_user(
            args.email,
            args.password,
            args.role,
            args.organization_id
        )
        
        if user:
            print("\nUser created successfully:")
            print(f"ID: {user['id']}")
            print(f"Email: {user['email']}")
            print(f"Role: {user['role']}")
            print(f"Organization ID: {user['organization_id']}")
            print(f"Created at: {user['created_at']}")
        
    elif args.action == "update":
        if not args.user_id:
            logger.error("--user-id is required for update action")
            sys.exit(1)
        
        update_data = {}
        if args.email:
            update_data["email"] = args.email
        if args.password:
            update_data["password"] = args.password
        if args.role:
            update_data["role"] = args.role
        if args.organization_id:
            update_data["organization_id"] = args.organization_id
        
        user = manager.update_user(args.user_id, **update_data)
        
        if user:
            print("\nUser updated successfully:")
            print(f"ID: {user['id']}")
            print(f"Email: {user['email']}")
            print(f"Role: {user['role']}")
            print(f"Organization ID: {user['organization_id']}")
            print(f"Created at: {user['created_at']}")
            print(f"Updated at: {user['updated_at']}")
        
    elif args.action == "delete":
        if not args.user_id:
            logger.error("--user-id is required for delete action")
            sys.exit(1)
        
        if manager.delete_user(args.user_id):
            print(f"\nUser {args.user_id} deleted successfully")
        
    elif args.action == "get":
        if not args.user_id:
            logger.error("--user-id is required for get action")
            sys.exit(1)
        
        user = manager.get_user(args.user_id)
        
        if user:
            print("\nUser details:")
            print(f"ID: {user['id']}")
            print(f"Email: {user['email']}")
            print(f"Role: {user['role']}")
            print(f"Organization ID: {user['organization_id']}")
            print(f"Created at: {user['created_at']}")
            print(f"Updated at: {user['updated_at']}")
        
    elif args.action == "list":
        users = manager.list_users(
            args.organization_id,
            args.role,
            args.limit,
            args.offset
        )
        
        print(f"\nFound {len(users)} users:")
        for user in users:
            print(f"\nID: {user['id']}")
            print(f"Email: {user['email']}")
            print(f"Role: {user['role']}")
            print(f"Organization ID: {user['organization_id']}")
            print(f"Created at: {user['created_at']}")
            print(f"Updated at: {user['updated_at']}")
        
    elif args.action == "verify":
        if not all([args.email, args.password]):
            logger.error("--email and --password are required for verify action")
            sys.exit(1)
        
        if manager.verify_password(args.email, args.password):
            print("\nPassword verification successful")
        else:
            print("\nPassword verification failed")

if __name__ == "__main__":
    main() 