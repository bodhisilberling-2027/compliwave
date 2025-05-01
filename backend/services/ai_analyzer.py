import os
from typing import Dict, List, Optional, Any
import openai
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from ..models import Document, ComplianceRule, ComplianceCheck, AuditLog
import uuid
import spacy
import tensorflow as tf
import numpy as np
from transformers import AutoTokenizer, AutoModel
import pytesseract
from pdf2image import convert_from_path
import cv2
import re
import json
from concurrent.futures import ThreadPoolExecutor
import asyncio
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

class AdvancedDocumentAnalyzer:
    """Advanced AI-powered document analysis service."""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
        
        # Initialize AI models
        self.nlp = spacy.load("en_core_web_lg")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-v3-large")
        self.model = AutoModel.from_pretrained("microsoft/deberta-v3-large")
        
        # Load custom models
        self.risk_model = self._load_risk_model()
        self.compliance_model = self._load_compliance_model()
        self.sentiment_model = self._load_sentiment_model()
        
        # Initialize OpenAI
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Initialize thread pool
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize rule cache
        self.rule_cache = {}
    
    async def analyze_document(
        self,
        document_id: str,
        content: bytes,
        content_type: str,
        rules: Optional[List[str]] = None,
        context: Optional[Dict] = None
    ) -> Dict:
        """Perform comprehensive document analysis."""
        try:
            # Extract text with OCR if needed
            text = await self._extract_text(content, content_type)
            
            # Run parallel analysis
            analysis_tasks = [
                self._analyze_compliance(text, rules),
                self._analyze_risks(text),
                self._analyze_sentiment(text),
                self._analyze_structure(text),
                self._analyze_entities(text),
                self._analyze_relationships(text),
                self._analyze_context(text, context)
            ]
            
            results = await asyncio.gather(*analysis_tasks)
            
            # Combine results
            analysis = {
                'compliance': results[0],
                'risks': results[1],
                'sentiment': results[2],
                'structure': results[3],
                'entities': results[4],
                'relationships': results[5],
                'context': results[6],
                'metadata': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'model_versions': self._get_model_versions()
                }
            }
            
            # Generate recommendations
            analysis['recommendations'] = await self._generate_recommendations(analysis)
            
            # Store results
            await self._store_analysis(document_id, analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            raise
    
    async def _extract_text(self, content: bytes, content_type: str) -> str:
        """Extract text from document with advanced OCR."""
        try:
            if content_type == 'application/pdf':
                # Convert PDF to images
                images = convert_from_path(content)
                text = ""
                
                for image in images:
                    # Preprocess image
                    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                    img = self._preprocess_image(img)
                    
                    # Perform OCR with confidence scores
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    
                    # Filter by confidence
                    confidences = data['conf']
                    texts = data['text']
                    text += ' '.join([t for t, c in zip(texts, confidences) if c > 60])
            else:
                # Handle other document types
                text = content.decode('utf-8')
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            raise
    
    async def _analyze_compliance(self, text: str, rules: Optional[List[str]] = None) -> Dict:
        """Analyze document for compliance with advanced AI."""
        try:
            # Get applicable rules
            if not rules:
                rules = self._get_applicable_rules(text)
            
            compliance_results = []
            for rule in rules:
                # Analyze rule compliance
                result = await self._check_rule_compliance(text, rule)
                compliance_results.append(result)
            
            # Use GPT-4 for advanced analysis
            gpt_analysis = await self._get_gpt_analysis(text, compliance_results)
            
            return {
                'rules': compliance_results,
                'gpt_analysis': gpt_analysis,
                'confidence_scores': self._calculate_confidence_scores(compliance_results)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing compliance: {str(e)}")
            raise
    
    async def _analyze_risks(self, text: str) -> Dict:
        """Analyze document for potential risks."""
        try:
            # Extract risk indicators
            risk_indicators = self._extract_risk_indicators(text)
            
            # Analyze risk patterns
            risk_patterns = self._analyze_risk_patterns(text)
            
            # Calculate risk scores
            risk_scores = self._calculate_risk_scores(risk_indicators, risk_patterns)
            
            return {
                'indicators': risk_indicators,
                'patterns': risk_patterns,
                'scores': risk_scores,
                'recommendations': self._generate_risk_recommendations(risk_scores)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing risks: {str(e)}")
            raise
    
    async def _analyze_sentiment(self, text: str) -> Dict:
        """Analyze document sentiment and tone."""
        try:
            # Analyze overall sentiment
            sentiment = self._analyze_overall_sentiment(text)
            
            # Analyze tone by section
            tone_analysis = self._analyze_tone_by_section(text)
            
            # Detect potential issues
            issues = self._detect_sentiment_issues(sentiment, tone_analysis)
            
            return {
                'overall_sentiment': sentiment,
                'tone_analysis': tone_analysis,
                'issues': issues,
                'recommendations': self._generate_sentiment_recommendations(issues)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            raise
    
    async def _analyze_structure(self, text: str) -> Dict:
        """Analyze document structure and organization."""
        try:
            # Analyze document sections
            sections = self._analyze_sections(text)
            
            # Analyze document flow
            flow = self._analyze_document_flow(text)
            
            # Check structure consistency
            consistency = self._check_structure_consistency(sections)
            
            return {
                'sections': sections,
                'flow': flow,
                'consistency': consistency,
                'recommendations': self._generate_structure_recommendations(consistency)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing structure: {str(e)}")
            raise
    
    async def _analyze_entities(self, text: str) -> Dict:
        """Analyze document entities and relationships."""
        try:
            # Extract named entities
            entities = self._extract_entities(text)
            
            # Analyze entity relationships
            relationships = self._analyze_entity_relationships(entities)
            
            # Detect entity conflicts
            conflicts = self._detect_entity_conflicts(entities, relationships)
            
            return {
                'entities': entities,
                'relationships': relationships,
                'conflicts': conflicts,
                'recommendations': self._generate_entity_recommendations(conflicts)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing entities: {str(e)}")
            raise
    
    async def _analyze_relationships(self, text: str) -> Dict:
        """Analyze document relationships and dependencies."""
        try:
            # Extract relationships
            relationships = self._extract_relationships(text)
            
            # Analyze relationship strength
            strength = self._analyze_relationship_strength(relationships)
            
            # Detect relationship issues
            issues = self._detect_relationship_issues(relationships, strength)
            
            return {
                'relationships': relationships,
                'strength': strength,
                'issues': issues,
                'recommendations': self._generate_relationship_recommendations(issues)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing relationships: {str(e)}")
            raise
    
    async def _analyze_context(self, text: str, context: Optional[Dict] = None) -> Dict:
        """Analyze document context and relevance."""
        try:
            # Analyze document context
            context_analysis = self._analyze_document_context(text, context)
            
            # Check context relevance
            relevance = self._check_context_relevance(context_analysis)
            
            # Generate context insights
            insights = self._generate_context_insights(context_analysis, relevance)
            
            return {
                'context_analysis': context_analysis,
                'relevance': relevance,
                'insights': insights,
                'recommendations': self._generate_context_recommendations(insights)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing context: {str(e)}")
            raise
    
    async def _get_gpt_analysis(self, text: str, compliance_results: List[Dict]) -> Dict:
        """Get advanced analysis from GPT-4."""
        try:
            prompt = self._create_analysis_prompt(text, compliance_results)
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert document compliance analyzer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            return self._parse_gpt_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Error getting GPT analysis: {str(e)}")
            raise
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR results."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh)
            
            # Enhance contrast
            enhanced = cv2.equalizeHist(denoised)
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            raise
    
    def _get_model_versions(self) -> Dict:
        """Get versions of all AI models."""
        return {
            'spacy': spacy.__version__,
            'transformers': self.tokenizer.__version__,
            'tensorflow': tf.__version__,
            'openai': openai.__version__
        }
    
    async def _store_analysis(self, document_id: str, analysis: Dict) -> None:
        """Store analysis results in database."""
        try:
            # Create compliance check record
            check = ComplianceCheck(
                id=str(uuid.uuid4()),
                document_id=document_id,
                status="completed",
                violations=analysis['compliance']['rules'],
                metadata=analysis
            )
            self.db.add(check)
            self.db.commit()
            
            # Create audit log
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                document_id=document_id,
                action="document_analysis",
                details={
                    'analysis_id': check.id,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            self.db.add(audit_log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error storing analysis: {str(e)}")
            raise

    async def add_custom_rule(
        self,
        organization_id: str,
        rule: Dict[str, Any],
        user_id: str
    ) -> Dict:
        """Add a custom compliance rule for an organization."""
        try:
            # Validate rule structure
            self._validate_rule_structure(rule)
            
            # Create rule record
            compliance_rule = ComplianceRule(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                name=rule['name'],
                description=rule['description'],
                pattern=rule['pattern'],
                severity=rule.get('severity', 'medium'),
                category=rule.get('category', 'custom'),
                metadata={
                    'created_by': user_id,
                    'created_at': datetime.utcnow().isoformat(),
                    'version': 1,
                    'custom_fields': rule.get('custom_fields', {}),
                    'conditions': rule.get('conditions', []),
                    'exceptions': rule.get('exceptions', []),
                    'references': rule.get('references', []),
                    'enabled': True
                }
            )
            
            self.db.add(compliance_rule)
            self.db.commit()
            
            # Update cache
            self._update_rule_cache(organization_id, compliance_rule)
            
            # Create audit log
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                user_id=user_id,
                action="add_custom_rule",
                details={
                    'rule_id': compliance_rule.id,
                    'rule_name': rule['name']
                }
            )
            self.db.add(audit_log)
            self.db.commit()
            
            return {
                'id': compliance_rule.id,
                'name': rule['name'],
                'status': 'added',
                'metadata': compliance_rule.metadata
            }
            
        except Exception as e:
            logger.error(f"Error adding custom rule: {str(e)}")
            raise

    async def update_custom_rule(
        self,
        rule_id: str,
        updates: Dict[str, Any],
        user_id: str
    ) -> Dict:
        """Update an existing custom compliance rule."""
        try:
            rule = self.db.query(ComplianceRule).filter(ComplianceRule.id == rule_id).first()
            if not rule:
                raise ValueError("Rule not found")
            
            # Validate updates
            self._validate_rule_updates(updates)
            
            # Update rule fields
            for field, value in updates.items():
                if field in ['name', 'description', 'pattern', 'severity', 'category']:
                    setattr(rule, field, value)
                elif field in ['custom_fields', 'conditions', 'exceptions', 'references']:
                    rule.metadata[field] = value
            
            # Update version
            rule.metadata['version'] += 1
            rule.metadata['last_updated_by'] = user_id
            rule.metadata['last_updated_at'] = datetime.utcnow().isoformat()
            
            self.db.commit()
            
            # Update cache
            self._update_rule_cache(rule.organization_id, rule)
            
            # Create audit log
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                organization_id=rule.organization_id,
                user_id=user_id,
                action="update_custom_rule",
                details={
                    'rule_id': rule_id,
                    'updates': updates
                }
            )
            self.db.add(audit_log)
            self.db.commit()
            
            return {
                'id': rule.id,
                'name': rule.name,
                'status': 'updated',
                'metadata': rule.metadata
            }
            
        except Exception as e:
            logger.error(f"Error updating custom rule: {str(e)}")
            raise

    async def get_custom_rules(
        self,
        organization_id: str,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """Get custom compliance rules for an organization."""
        try:
            query = self.db.query(ComplianceRule).filter(
                ComplianceRule.organization_id == organization_id,
                ComplianceRule.category == 'custom'
            )
            
            if filters:
                if filters.get('enabled') is not None:
                    query = query.filter(ComplianceRule.metadata['enabled'].astext == str(filters['enabled']))
                if filters.get('category'):
                    query = query.filter(ComplianceRule.category == filters['category'])
                if filters.get('severity'):
                    query = query.filter(ComplianceRule.severity == filters['severity'])
            
            rules = query.all()
            
            return [{
                'id': rule.id,
                'name': rule.name,
                'description': rule.description,
                'pattern': rule.pattern,
                'severity': rule.severity,
                'category': rule.category,
                'metadata': rule.metadata
            } for rule in rules]
            
        except Exception as e:
            logger.error(f"Error getting custom rules: {str(e)}")
            raise

    def _validate_rule_structure(self, rule: Dict) -> None:
        """Validate the structure of a custom rule."""
        required_fields = ['name', 'description', 'pattern']
        for field in required_fields:
            if field not in rule:
                raise ValueError(f"Missing required field: {field}")
        
        if not isinstance(rule['pattern'], (str, dict)):
            raise ValueError("Pattern must be a string or dictionary")
        
        if 'severity' in rule and rule['severity'] not in ['low', 'medium', 'high', 'critical']:
            raise ValueError("Invalid severity level")

    def _validate_rule_updates(self, updates: Dict) -> None:
        """Validate rule updates."""
        if 'pattern' in updates and not isinstance(updates['pattern'], (str, dict)):
            raise ValueError("Pattern must be a string or dictionary")
        
        if 'severity' in updates and updates['severity'] not in ['low', 'medium', 'high', 'critical']:
            raise ValueError("Invalid severity level")

    def _update_rule_cache(self, organization_id: str, rule: ComplianceRule) -> None:
        """Update the rule cache for an organization."""
        if organization_id not in self.rule_cache:
            self.rule_cache[organization_id] = {}
        
        self.rule_cache[organization_id][rule.id] = {
            'name': rule.name,
            'pattern': rule.pattern,
            'severity': rule.severity,
            'metadata': rule.metadata
        }

    async def _get_applicable_rules(self, text: str) -> List[Dict]:
        """Get applicable rules for document analysis."""
        try:
            # Get rules from cache or database
            rules = []
            
            # Add custom rules
            custom_rules = self.db.query(ComplianceRule).filter(
                ComplianceRule.category == 'custom',
                ComplianceRule.metadata['enabled'].astext == 'true'
            ).all()
            
            for rule in custom_rules:
                rules.append({
                    'id': rule.id,
                    'name': rule.name,
                    'pattern': rule.pattern,
                    'severity': rule.severity,
                    'category': 'custom',
                    'metadata': rule.metadata
                })
            
            # Add built-in rules
            built_in_rules = self.db.query(ComplianceRule).filter(
                ComplianceRule.category != 'custom',
                ComplianceRule.metadata['enabled'].astext == 'true'
            ).all()
            
            for rule in built_in_rules:
                rules.append({
                    'id': rule.id,
                    'name': rule.name,
                    'pattern': rule.pattern,
                    'severity': rule.severity,
                    'category': rule.category,
                    'metadata': rule.metadata
                })
            
            return rules
            
        except Exception as e:
            logger.error(f"Error getting applicable rules: {str(e)}")
            raise 