#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import psycopg2
from datetime import datetime
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrganizationManager:
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
    
    def create_organization(self, name: str, domain: str = None,
                          subscription_tier: str = "basic") -> Dict[str, Any]:
        """Create a new organization"""
        try:
            with self.conn.cursor() as cur:
                # Check if organization already exists
                cur.execute(
                    "SELECT id FROM organizations WHERE name = %s",
                    (name,)
                )
                if cur.fetchone():
                    logger.error(f"Organization with name {name} already exists")
                    return None
                
                # Create organization
                cur.execute(
                    """
                    INSERT INTO organizations (name, domain, subscription_tier, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, name, domain, subscription_tier, created_at
                    """,
                    (name, domain, subscription_tier, datetime.now(), datetime.now())
                )
                
                org = cur.fetchone()
                self.conn.commit()
                
                return {
                    "id": org[0],
                    "name": org[1],
                    "domain": org[2],
                    "subscription_tier": org[3],
                    "created_at": org[4]
                }
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating organization: {str(e)}")
            return None
    
    def update_organization(self, org_id: int, **kwargs) -> Dict[str, Any]:
        """Update organization details"""
        try:
            with self.conn.cursor() as cur:
                # Check if organization exists
                cur.execute(
                    "SELECT id FROM organizations WHERE id = %s",
                    (org_id,)
                )
                if not cur.fetchone():
                    logger.error(f"Organization with ID {org_id} not found")
                    return None
                
                # Build update query
                update_fields = []
                values = []
                
                if "name" in kwargs:
                    update_fields.append("name = %s")
                    values.append(kwargs["name"])
                
                if "domain" in kwargs:
                    update_fields.append("domain = %s")
                    values.append(kwargs["domain"])
                
                if "subscription_tier" in kwargs:
                    update_fields.append("subscription_tier = %s")
                    values.append(kwargs["subscription_tier"])
                
                update_fields.append("updated_at = %s")
                values.append(datetime.now())
                
                # Add org_id to values
                values.append(org_id)
                
                # Execute update
                cur.execute(
                    f"""
                    UPDATE organizations
                    SET {", ".join(update_fields)}
                    WHERE id = %s
                    RETURNING id, name, domain, subscription_tier, created_at, updated_at
                    """,
                    values
                )
                
                org = cur.fetchone()
                self.conn.commit()
                
                return {
                    "id": org[0],
                    "name": org[1],
                    "domain": org[2],
                    "subscription_tier": org[3],
                    "created_at": org[4],
                    "updated_at": org[5]
                }
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error updating organization: {str(e)}")
            return None
    
    def delete_organization(self, org_id: int) -> bool:
        """Delete an organization"""
        try:
            with self.conn.cursor() as cur:
                # Check if organization exists
                cur.execute(
                    "SELECT id FROM organizations WHERE id = %s",
                    (org_id,)
                )
                if not cur.fetchone():
                    logger.error(f"Organization with ID {org_id} not found")
                    return False
                
                # Delete organization
                cur.execute(
                    "DELETE FROM organizations WHERE id = %s",
                    (org_id,)
                )
                
                self.conn.commit()
                return True
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error deleting organization: {str(e)}")
            return False
    
    def get_organization(self, org_id: int) -> Dict[str, Any]:
        """Get organization details"""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, domain, subscription_tier, created_at, updated_at
                    FROM organizations
                    WHERE id = %s
                    """,
                    (org_id,)
                )
                
                org = cur.fetchone()
                if not org:
                    logger.error(f"Organization with ID {org_id} not found")
                    return None
                
                return {
                    "id": org[0],
                    "name": org[1],
                    "domain": org[2],
                    "subscription_tier": org[3],
                    "created_at": org[4],
                    "updated_at": org[5]
                }
                
        except Exception as e:
            logger.error(f"Error getting organization: {str(e)}")
            return None
    
    def list_organizations(self, subscription_tier: str = None,
                          limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List organizations with optional filters"""
        try:
            with self.conn.cursor() as cur:
                # Build query
                query = """
                    SELECT id, name, domain, subscription_tier, created_at, updated_at
                    FROM organizations
                    WHERE 1=1
                """
                values = []
                
                if subscription_tier is not None:
                    query += " AND subscription_tier = %s"
                    values.append(subscription_tier)
                
                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                values.extend([limit, offset])
                
                # Execute query
                cur.execute(query, values)
                
                orgs = []
                for row in cur.fetchall():
                    orgs.append({
                        "id": row[0],
                        "name": row[1],
                        "domain": row[2],
                        "subscription_tier": row[3],
                        "created_at": row[4],
                        "updated_at": row[5]
                    })
                
                return orgs
                
        except Exception as e:
            logger.error(f"Error listing organizations: {str(e)}")
            return []
    
    def get_organization_users(self, org_id: int,
                             limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get users belonging to an organization"""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, role, created_at, updated_at
                    FROM users
                    WHERE organization_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (org_id, limit, offset)
                )
                
                users = []
                for row in cur.fetchall():
                    users.append({
                        "id": row[0],
                        "email": row[1],
                        "role": row[2],
                        "created_at": row[3],
                        "updated_at": row[4]
                    })
                
                return users
                
        except Exception as e:
            logger.error(f"Error getting organization users: {str(e)}")
            return []
    
    def get_organization_stats(self, org_id: int) -> Dict[str, Any]:
        """Get organization statistics"""
        try:
            with self.conn.cursor() as cur:
                # Get user count
                cur.execute(
                    "SELECT COUNT(*) FROM users WHERE organization_id = %s",
                    (org_id,)
                )
                user_count = cur.fetchone()[0]
                
                # Get document count
                cur.execute(
                    "SELECT COUNT(*) FROM documents WHERE organization_id = %s",
                    (org_id,)
                )
                document_count = cur.fetchone()[0]
                
                # Get compliance check count
                cur.execute(
                    "SELECT COUNT(*) FROM compliance_checks WHERE organization_id = %s",
                    (org_id,)
                )
                compliance_check_count = cur.fetchone()[0]
                
                return {
                    "user_count": user_count,
                    "document_count": document_count,
                    "compliance_check_count": compliance_check_count
                }
                
        except Exception as e:
            logger.error(f"Error getting organization stats: {str(e)}")
            return {
                "user_count": 0,
                "document_count": 0,
                "compliance_check_count": 0
            }

def main():
    parser = argparse.ArgumentParser(description="Organization Management Tool")
    parser.add_argument("--action", required=True,
                       choices=["create", "update", "delete", "get", "list", "users", "stats"],
                       help="Action to perform")
    parser.add_argument("--org-id", type=int, help="Organization ID")
    parser.add_argument("--name", help="Organization name")
    parser.add_argument("--domain", help="Organization domain")
    parser.add_argument("--subscription-tier", choices=["basic", "premium", "enterprise"],
                       help="Subscription tier")
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
    
    # Create organization manager
    manager = OrganizationManager(config)
    
    # Perform requested action
    if args.action == "create":
        if not args.name:
            logger.error("--name is required for create action")
            sys.exit(1)
        
        org = manager.create_organization(
            args.name,
            args.domain,
            args.subscription_tier
        )
        
        if org:
            print("\nOrganization created successfully:")
            print(f"ID: {org['id']}")
            print(f"Name: {org['name']}")
            print(f"Domain: {org['domain']}")
            print(f"Subscription Tier: {org['subscription_tier']}")
            print(f"Created at: {org['created_at']}")
        
    elif args.action == "update":
        if not args.org_id:
            logger.error("--org-id is required for update action")
            sys.exit(1)
        
        update_data = {}
        if args.name:
            update_data["name"] = args.name
        if args.domain:
            update_data["domain"] = args.domain
        if args.subscription_tier:
            update_data["subscription_tier"] = args.subscription_tier
        
        org = manager.update_organization(args.org_id, **update_data)
        
        if org:
            print("\nOrganization updated successfully:")
            print(f"ID: {org['id']}")
            print(f"Name: {org['name']}")
            print(f"Domain: {org['domain']}")
            print(f"Subscription Tier: {org['subscription_tier']}")
            print(f"Created at: {org['created_at']}")
            print(f"Updated at: {org['updated_at']}")
        
    elif args.action == "delete":
        if not args.org_id:
            logger.error("--org-id is required for delete action")
            sys.exit(1)
        
        if manager.delete_organization(args.org_id):
            print(f"\nOrganization {args.org_id} deleted successfully")
        
    elif args.action == "get":
        if not args.org_id:
            logger.error("--org-id is required for get action")
            sys.exit(1)
        
        org = manager.get_organization(args.org_id)
        
        if org:
            print("\nOrganization details:")
            print(f"ID: {org['id']}")
            print(f"Name: {org['name']}")
            print(f"Domain: {org['domain']}")
            print(f"Subscription Tier: {org['subscription_tier']}")
            print(f"Created at: {org['created_at']}")
            print(f"Updated at: {org['updated_at']}")
        
    elif args.action == "list":
        orgs = manager.list_organizations(
            args.subscription_tier,
            args.limit,
            args.offset
        )
        
        print(f"\nFound {len(orgs)} organizations:")
        for org in orgs:
            print(f"\nID: {org['id']}")
            print(f"Name: {org['name']}")
            print(f"Domain: {org['domain']}")
            print(f"Subscription Tier: {org['subscription_tier']}")
            print(f"Created at: {org['created_at']}")
            print(f"Updated at: {org['updated_at']}")
        
    elif args.action == "users":
        if not args.org_id:
            logger.error("--org-id is required for users action")
            sys.exit(1)
        
        users = manager.get_organization_users(
            args.org_id,
            args.limit,
            args.offset
        )
        
        print(f"\nFound {len(users)} users in organization {args.org_id}:")
        for user in users:
            print(f"\nID: {user['id']}")
            print(f"Email: {user['email']}")
            print(f"Role: {user['role']}")
            print(f"Created at: {user['created_at']}")
            print(f"Updated at: {user['updated_at']}")
        
    elif args.action == "stats":
        if not args.org_id:
            logger.error("--org-id is required for stats action")
            sys.exit(1)
        
        stats = manager.get_organization_stats(args.org_id)
        
        print(f"\nOrganization {args.org_id} statistics:")
        print(f"User Count: {stats['user_count']}")
        print(f"Document Count: {stats['document_count']}")
        print(f"Compliance Check Count: {stats['compliance_check_count']}")

if __name__ == "__main__":
    main() 