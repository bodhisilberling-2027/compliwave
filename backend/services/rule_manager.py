from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..models import ComplianceRule, User, Organization
import re
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

class RuleManager:
    def __init__(self):
        self.severity_levels = ["low", "medium", "high"]

    async def create_rule(
        self,
        name: str,
        description: str,
        pattern: str,
        severity: str,
        organization_id: str,
        user: User,
        db: Session
    ) -> ComplianceRule:
        """Create a new compliance rule."""
        try:
            if severity not in self.severity_levels:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid severity level. Must be one of {self.severity_levels}"
                )
            
            # Validate pattern is a valid regex
            try:
                re.compile(pattern)
            except re.error:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid regex pattern"
                )
            
            rule = ComplianceRule(
                name=name,
                description=description,
                pattern=pattern,
                severity=severity,
                organization_id=organization_id,
                created_by=user.id
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return rule
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create rule: {str(e)}"
            )

    async def update_rule(
        self,
        rule_id: str,
        updates: Dict[str, Any],
        user: User,
        db: Session
    ) -> ComplianceRule:
        """Update an existing compliance rule."""
        try:
            rule = db.query(ComplianceRule).filter(ComplianceRule.id == rule_id).first()
            if not rule:
                raise HTTPException(
                    status_code=404,
                    detail="Rule not found"
                )
            
            # Check if user has permission to update
            if rule.organization_id != user.organization_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied"
                )
            
            # Update fields
            if "name" in updates:
                rule.name = updates["name"]
            if "description" in updates:
                rule.description = updates["description"]
            if "pattern" in updates:
                try:
                    re.compile(updates["pattern"])
                    rule.pattern = updates["pattern"]
                except re.error:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid regex pattern"
                    )
            if "severity" in updates:
                if updates["severity"] not in self.severity_levels:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid severity level. Must be one of {self.severity_levels}"
                    )
                rule.severity = updates["severity"]
            if "is_active" in updates:
                rule.is_active = updates["is_active"]
            
            rule.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(rule)
            return rule
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update rule: {str(e)}"
            )

    async def delete_rule(
        self,
        rule_id: str,
        user: User,
        db: Session
    ) -> None:
        """Delete a compliance rule."""
        rule = db.query(ComplianceRule).filter(ComplianceRule.id == rule_id).first()
        if not rule:
            raise ValueError("Rule not found")
        
        # Check if user has permission to delete
        if rule.organization_id != user.organization_id:
            raise ValueError("Access denied")
        
        db.delete(rule)
        db.commit()

    async def get_rules(
        self,
        organization_id: str,
        user: User,
        db: Session,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all compliance rules for an organization."""
        query = db.query(ComplianceRule).filter(
            ComplianceRule.organization_id == organization_id
        )
        
        if active_only:
            query = query.filter(ComplianceRule.is_active == True)
        
        rules = query.all()
        
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "pattern": rule.pattern,
                "severity": rule.severity,
                "is_active": rule.is_active,
                "created_at": rule.created_at,
                "updated_at": rule.updated_at,
                "created_by": rule.creator.email
            }
            for rule in rules
        ]

    async def test_rule(
        self,
        rule_id: str,
        text: str,
        user: User,
        db: Session
    ) -> Dict[str, Any]:
        """Test a compliance rule against sample text."""
        rule = db.query(ComplianceRule).filter(ComplianceRule.id == rule_id).first()
        if not rule:
            raise ValueError("Rule not found")
        
        # Check if user has permission to test
        if rule.organization_id != user.organization_id:
            raise ValueError("Access denied")
        
        try:
            pattern = re.compile(rule.pattern)
            matches = list(pattern.finditer(text))
            
            return {
                "rule_id": rule.id,
                "rule_name": rule.name,
                "matches": [
                    {
                        "text": match.group(),
                        "start": match.start(),
                        "end": match.end()
                    }
                    for match in matches
                ],
                "match_count": len(matches)
            }
        except re.error:
            raise ValueError("Invalid regex pattern") 