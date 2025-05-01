from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from ..models import Document, User, Organization, AuditLog
from .notification_service import NotificationService
import uuid
import os

logger = logging.getLogger(__name__)

class WorkflowStage:
    """Represents a stage in the document workflow."""
    def __init__(
        self,
        name: str,
        approvers: List[str],
        required_approvals: int = 1,
        deadline_days: Optional[int] = None,
        auto_reject_on_deadline: bool = False,
        conditions: Optional[Dict] = None,
        parallel_approval: bool = False,
        sla_hours: Optional[int] = None,
        escalation_path: Optional[List[str]] = None
    ):
        self.name = name
        self.approvers = approvers
        self.required_approvals = required_approvals
        self.deadline_days = deadline_days
        self.auto_reject_on_deadline = auto_reject_on_deadline
        self.conditions = conditions  # Conditions for stage activation
        self.parallel_approval = parallel_approval  # Allow parallel approvals
        self.sla_hours = sla_hours  # SLA in hours
        self.escalation_path = escalation_path  # Escalation path for delays

class WorkflowService:
    """Service for managing document workflows and approvals."""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    async def create_workflow(
        self,
        document_id: str,
        stages: List[Dict],
        initiator_id: str,
        priority: str = "normal",  # high, normal, low
        auto_assign: bool = True,
        template_id: Optional[str] = None
    ) -> Dict:
        """Create a new document workflow with enhanced features."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError("Document not found")
            
            # Create workflow stages with enhanced features
            workflow_stages = []
            for stage_data in stages:
                stage = WorkflowStage(
                    name=stage_data['name'],
                    approvers=stage_data['approvers'],
                    required_approvals=stage_data.get('required_approvals', 1),
                    deadline_days=stage_data.get('deadline_days'),
                    auto_reject_on_deadline=stage_data.get('auto_reject_on_deadline', False),
                    conditions=stage_data.get('conditions'),
                    parallel_approval=stage_data.get('parallel_approval', False),
                    sla_hours=stage_data.get('sla_hours'),
                    escalation_path=stage_data.get('escalation_path')
                )
                workflow_stages.append(stage)
            
            # Initialize enhanced workflow state
            workflow_state = {
                'id': str(uuid.uuid4()),
                'document_id': document_id,
                'initiator_id': initiator_id,
                'current_stage': 0,
                'priority': priority,
                'template_id': template_id,
                'stages': [
                    {
                        'name': stage.name,
                        'approvers': stage.approvers,
                        'required_approvals': stage.required_approvals,
                        'deadline_days': stage.deadline_days,
                        'auto_reject_on_deadline': stage.auto_reject_on_deadline,
                        'conditions': stage.conditions,
                        'parallel_approval': stage.parallel_approval,
                        'sla_hours': stage.sla_hours,
                        'escalation_path': stage.escalation_path,
                        'approvals': [],
                        'rejections': [],
                        'comments': [],
                        'start_time': None,
                        'completion_time': None,
                        'sla_status': 'pending'
                    }
                    for stage in workflow_stages
                ],
                'status': 'in_progress',
                'created_at': datetime.utcnow().isoformat(),
                'metrics': {
                    'total_duration': None,
                    'stage_durations': {},
                    'approval_rate': None,
                    'sla_compliance': None
                }
            }
            
            # Auto-assign approvers based on workload and expertise
            if auto_assign:
                await self._auto_assign_approvers(workflow_state)
            
            # Store workflow state in document metadata
            document.metadata = document.metadata or {}
            document.metadata['workflow'] = workflow_state
            self.db.commit()
            
            # Notify first stage approvers
            await self._notify_approvers(document, workflow_stages[0])
            
            # Start SLA tracking
            if workflow_stages[0].sla_hours:
                await self._start_sla_tracking(document, workflow_stages[0])
            
            return workflow_state
            
        except Exception as e:
            logger.error(f"Error creating workflow: {str(e)}")
            raise
    
    async def approve_stage(
        self,
        document_id: str,
        approver_id: str,
        comment: Optional[str] = None
    ) -> Dict:
        """Approve current workflow stage."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError("Document not found")
            
            workflow = document.metadata.get('workflow')
            if not workflow:
                raise ValueError("No active workflow found")
            
            current_stage = workflow['stages'][workflow['current_stage']]
            
            # Validate approver
            if approver_id not in current_stage['approvers']:
                raise ValueError("User not authorized to approve this stage")
            
            # Add approval
            approval = {
                'approver_id': approver_id,
                'timestamp': datetime.utcnow().isoformat(),
                'comment': comment
            }
            current_stage['approvals'].append(approval)
            
            # Check if stage is complete
            if len(current_stage['approvals']) >= current_stage['required_approvals']:
                # Move to next stage or complete workflow
                if workflow['current_stage'] < len(workflow['stages']) - 1:
                    workflow['current_stage'] += 1
                    await self._notify_approvers(
                        document,
                        WorkflowStage(**workflow['stages'][workflow['current_stage']])
                    )
                else:
                    workflow['status'] = 'completed'
                    await self._notify_workflow_completion(document, True)
            
            # Update document
            document.metadata['workflow'] = workflow
            self.db.commit()
            
            # Create audit log
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=approver_id,
                action="workflow_approve",
                details={
                    'stage': current_stage['name'],
                    'comment': comment
                }
            )
            self.db.add(audit_log)
            self.db.commit()
            
            return workflow
            
        except Exception as e:
            logger.error(f"Error approving stage: {str(e)}")
            raise
    
    async def reject_stage(
        self,
        document_id: str,
        approver_id: str,
        reason: str
    ) -> Dict:
        """Reject current workflow stage."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError("Document not found")
            
            workflow = document.metadata.get('workflow')
            if not workflow:
                raise ValueError("No active workflow found")
            
            current_stage = workflow['stages'][workflow['current_stage']]
            
            # Validate approver
            if approver_id not in current_stage['approvers']:
                raise ValueError("User not authorized to reject this stage")
            
            # Add rejection
            rejection = {
                'approver_id': approver_id,
                'timestamp': datetime.utcnow().isoformat(),
                'reason': reason
            }
            current_stage['rejections'].append(rejection)
            
            # Update workflow status
            workflow['status'] = 'rejected'
            document.metadata['workflow'] = workflow
            self.db.commit()
            
            # Notify workflow completion (rejected)
            await self._notify_workflow_completion(document, False)
            
            # Create audit log
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=approver_id,
                action="workflow_reject",
                details={
                    'stage': current_stage['name'],
                    'reason': reason
                }
            )
            self.db.add(audit_log)
            self.db.commit()
            
            return workflow
            
        except Exception as e:
            logger.error(f"Error rejecting stage: {str(e)}")
            raise
    
    async def add_comment(
        self,
        document_id: str,
        user_id: str,
        comment: str
    ) -> Dict:
        """Add comment to current workflow stage."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError("Document not found")
            
            workflow = document.metadata.get('workflow')
            if not workflow:
                raise ValueError("No active workflow found")
            
            current_stage = workflow['stages'][workflow['current_stage']]
            
            # Add comment
            comment_obj = {
                'user_id': user_id,
                'comment': comment,
                'timestamp': datetime.utcnow().isoformat()
            }
            current_stage['comments'].append(comment_obj)
            
            # Update document
            document.metadata['workflow'] = workflow
            self.db.commit()
            
            # Create audit log
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                document_id=document_id,
                user_id=user_id,
                action="workflow_comment",
                details={'comment': comment}
            )
            self.db.add(audit_log)
            self.db.commit()
            
            return workflow
            
        except Exception as e:
            logger.error(f"Error adding comment: {str(e)}")
            raise
    
    async def _notify_approvers(
        self,
        document: Document,
        stage: WorkflowStage
    ) -> None:
        """Notify approvers of pending review."""
        try:
            for approver_id in stage.approvers:
                approver = self.db.query(User).filter(User.id == approver_id).first()
                if approver:
                    await self.notification_service.send_email_notification(
                        to_email=approver.email,
                        subject=f"Document Approval Required: {document.title}",
                        html_content=f"""
                        <h2>Document Approval Required</h2>
                        <p>Your approval is required for the following document:</p>
                        <p><strong>{document.title}</strong></p>
                        <p>Stage: {stage.name}</p>
                        <p>Click <a href="{os.getenv('FRONTEND_URL')}/documents/{document.id}/approve">here</a> to review and approve.</p>
                        """
                    )
                    
        except Exception as e:
            logger.error(f"Error notifying approvers: {str(e)}")
    
    async def _notify_workflow_completion(
        self,
        document: Document,
        approved: bool
    ) -> None:
        """Notify relevant users of workflow completion."""
        try:
            # Get document owner
            owner = self.db.query(User).filter(User.id == document.owner_id).first()
            if owner:
                status = "approved" if approved else "rejected"
                await self.notification_service.send_email_notification(
                    to_email=owner.email,
                    subject=f"Document Workflow {status.capitalize()}: {document.title}",
                    html_content=f"""
                    <h2>Document Workflow {status.capitalize()}</h2>
                    <p>The workflow for document <strong>{document.title}</strong> has been {status}.</p>
                    <p>Click <a href="{os.getenv('FRONTEND_URL')}/documents/{document.id}">here</a> to view the document.</p>
                    """
                )
                
        except Exception as e:
            logger.error(f"Error notifying workflow completion: {str(e)}")

    async def _auto_assign_approvers(self, workflow_state: Dict) -> None:
        """Auto-assign approvers based on workload and expertise."""
        try:
            for stage in workflow_state['stages']:
                if not stage['approvers']:
                    # Get available approvers based on role and workload
                    approvers = await self._get_available_approvers(
                        role=stage.get('required_role'),
                        max_workload=5  # Maximum number of active approvals
                    )
                    stage['approvers'] = [a['id'] for a in approvers]
        except Exception as e:
            logger.error(f"Error auto-assigning approvers: {str(e)}")

    async def _start_sla_tracking(self, document: Document, stage: WorkflowStage) -> None:
        """Start tracking SLA for a workflow stage."""
        try:
            if stage.sla_hours:
                # Schedule SLA check
                check_time = datetime.utcnow() + timedelta(hours=stage.sla_hours)
                self.scheduler.add_job(
                    self._check_sla_status,
                    'date',
                    run_date=check_time,
                    kwargs={
                        'document_id': document.id,
                        'stage_name': stage.name
                    }
                )
        except Exception as e:
            logger.error(f"Error starting SLA tracking: {str(e)}")

    async def _check_sla_status(self, document_id: str, stage_name: str) -> None:
        """Check and handle SLA status for a workflow stage."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return
            
            workflow = document.metadata.get('workflow')
            if not workflow:
                return
            
            current_stage = next(
                (s for s in workflow['stages'] if s['name'] == stage_name),
                None
            )
            
            if current_stage and current_stage['sla_status'] == 'pending':
                # SLA breached, escalate if path exists
                if current_stage['escalation_path']:
                    await self._escalate_workflow(document, current_stage)
                
                # Update SLA status
                current_stage['sla_status'] = 'breached'
                document.metadata['workflow'] = workflow
                self.db.commit()
                
                # Notify relevant parties
                await self._notify_sla_breach(document, current_stage)
        except Exception as e:
            logger.error(f"Error checking SLA status: {str(e)}")

    async def _escalate_workflow(self, document: Document, stage: Dict) -> None:
        """Escalate workflow to next level of approvers."""
        try:
            for approver_id in stage['escalation_path']:
                approver = self.db.query(User).filter(User.id == approver_id).first()
                if approver:
                    await self.notification_service.send_email_notification(
                        to_email=approver.email,
                        subject=f"URGENT: Workflow Escalation - {document.title}",
                        html_content=f"""
                        <h2>⚠️ Workflow Escalation</h2>
                        <p>The following document requires urgent attention:</p>
                        <p><strong>{document.title}</strong></p>
                        <p>Stage: {stage['name']}</p>
                        <p>SLA has been breached. Your immediate action is required.</p>
                        <p>Click <a href="{os.getenv('FRONTEND_URL')}/documents/{document.id}/approve">here</a> to review.</p>
                        """
                    )
        except Exception as e:
            logger.error(f"Error escalating workflow: {str(e)}")

    async def _notify_sla_breach(self, document: Document, stage: Dict) -> None:
        """Notify relevant parties about SLA breach."""
        try:
            # Notify document owner
            owner = self.db.query(User).filter(User.id == document.owner_id).first()
            if owner:
                await self.notification_service.send_email_notification(
                    to_email=owner.email,
                    subject=f"SLA Breach Alert - {document.title}",
                    html_content=f"""
                    <h2>⚠️ SLA Breach Alert</h2>
                    <p>The following document has breached its SLA:</p>
                    <p><strong>{document.title}</strong></p>
                    <p>Stage: {stage['name']}</p>
                    <p>Please follow up with the approvers.</p>
                    <p>Click <a href="{os.getenv('FRONTEND_URL')}/documents/{document.id}">here</a> to view.</p>
                    """
                )
        except Exception as e:
            logger.error(f"Error notifying SLA breach: {str(e)}") 