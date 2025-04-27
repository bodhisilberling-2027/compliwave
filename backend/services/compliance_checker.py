from typing import List, Dict, Any
import re
from datetime import datetime
import json
from .document_processor import DocumentProcessor
import asyncio

class ComplianceChecker:
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.rules = {
            "past_performance": {
                "name": "Past Performance Disclosure",
                "description": "Documents must include a disclaimer about past performance not being indicative of future results.",
                "pattern": r"(?i)past performance.*not indicative.*future results",
                "required": True
            },
            "aum_disclosure": {
                "name": "AUM Disclosure",
                "description": "AUM figures must be current (within 30 days) and include a date.",
                "pattern": r"(?i)(?:AUM|Assets Under Management).*(\d{1,2}/\d{1,2}/\d{2,4})",
                "required": True
            },
            "forward_looking": {
                "name": "Forward-Looking Statements",
                "description": "Forward-looking statements must include appropriate disclaimers.",
                "pattern": r"(?i)(?:forward-looking|future|projected|expected).*(?:statement|disclaimer)",
                "required": True
            },
            "third_party_data": {
                "name": "Third-Party Data Attribution",
                "description": "Third-party data must be properly attributed.",
                "pattern": r"(?i)(?:source|attribution|provided by).*[A-Za-z]",
                "required": True
            },
            "risk_disclosure": {
                "name": "Risk Disclosure",
                "description": "Documents must include appropriate risk disclosures.",
                "pattern": r"(?i)(?:risk|disclosure).*(?:investment|market|liquidity)",
                "required": True
            }
        }

    async def check_compliance(self, document_id: str, text: str) -> Dict[str, Any]:
        """Check document text against compliance rules."""
        violations = []
        
        # Check each rule
        for rule_id, rule in self.rules.items():
            if not re.search(rule["pattern"], text):
                if rule["required"]:
                    violations.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "description": rule["description"],
                        "text": "Missing required disclosure",
                        "suggestion": self._get_suggestion(rule_id)
                    })

        # Use Azure OpenAI for additional context-aware checks
        ai_violations = await self._check_with_ai(text)
        violations.extend(ai_violations)

        return {
            "document_id": document_id,
            "timestamp": datetime.utcnow().isoformat(),
            "violations": violations,
            "status": "completed"
        }

    def _get_suggestion(self, rule_id: str) -> str:
        """Get a suggested fix for a rule violation."""
        suggestions = {
            "past_performance": "Add the following disclaimer: 'Past performance is not indicative of future results.'",
            "aum_disclosure": "Include current AUM figures with the date of measurement.",
            "forward_looking": "Add a forward-looking statement disclaimer.",
            "third_party_data": "Properly attribute all third-party data sources.",
            "risk_disclosure": "Include appropriate risk disclosures for the investment strategy."
        }
        return suggestions.get(rule_id, "Please review the document for compliance with regulatory requirements.")

    async def _check_with_ai(self, text: str) -> List[Dict[str, Any]]:
        """Use Azure OpenAI for additional context-aware compliance checks."""
        prompt = f"""
        Analyze the following document text for potential compliance issues beyond basic rule checking.
        Focus on:
        1. Misleading statements
        2. Incomplete disclosures
        3. Regulatory requirements
        4. Industry best practices

        Document text:
        {text}

        Format the response as a JSON object with the following structure:
        {{
            "violations": [
                {{
                    "rule_id": "ai_detected",
                    "rule_name": "AI Detected Issue",
                    "description": "description of the issue",
                    "text": "relevant text from document",
                    "suggestion": "suggested fix"
                }}
            ]
        }}
        """

        try:
            response = await self.document_processor.check_compliance(text, [prompt])
            result = json.loads(response)
            return result.get("violations", [])
        except Exception as e:
            print(f"Error in AI compliance check: {str(e)}")
            return [] 