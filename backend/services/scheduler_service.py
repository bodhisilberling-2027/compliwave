from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from ..models import Document, User, Organization
from .notification_service import NotificationService
import asyncio
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for managing automated document reviews and reminders."""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
        self.scheduler = AsyncIOScheduler(
            jobstores={
                'default': SQLAlchemyJobStore(url=os.getenv('DATABASE_URL'))
            },
            timezone=pytz.UTC
        )
        self.scheduler.start()
        self.workload_cache = {}  # Cache for workload tracking
        self.analytics_cache = {}  # Cache for analytics data
    
    async def schedule_document_review(
        self,
        document_id: str,
        review_frequency: str,
        reviewers: List[str],
        start_date: Optional[datetime] = None,
        priority: str = "normal",
        workload_balance: bool = True,
        smart_scheduling: bool = True
    ) -> Dict:
        """Schedule periodic document reviews with enhanced features."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError("Document not found")
            
            if not start_date:
                start_date = datetime.utcnow()
            
            # Calculate interval with smart scheduling
            if smart_scheduling:
                start_date = await self._optimize_start_date(
                    start_date,
                    reviewers,
                    review_frequency
                )
            
            # Balance workload if enabled
            if workload_balance:
                reviewers = await self._balance_workload(reviewers, start_date)
            
            # Calculate interval
            intervals = {
                'daily': {'days': 1},
                'weekly': {'weeks': 1},
                'monthly': {'months': 1},
                'quarterly': {'months': 3},
                'annually': {'years': 1}
            }
            
            interval = intervals.get(review_frequency)
            if not interval:
                raise ValueError(f"Invalid review frequency: {review_frequency}")
            
            # Create job with enhanced tracking
            job_id = f"review_{document_id}_{review_frequency}"
            self.scheduler.add_job(
                self._send_review_reminder,
                'interval',
                **interval,
                id=job_id,
                replace_existing=True,
                start_date=start_date,
                kwargs={
                    'document_id': document_id,
                    'reviewers': reviewers,
                    'priority': priority
                }
            )
            
            # Track workload
            await self._track_workload(reviewers, start_date, document_id)
            
            # Update analytics
            await self._update_analytics(document_id, 'review_scheduled')
            
            return {
                'job_id': job_id,
                'document_id': document_id,
                'frequency': review_frequency,
                'next_review': start_date.isoformat(),
                'reviewers': reviewers,
                'priority': priority,
                'workload_balanced': workload_balance,
                'smart_scheduled': smart_scheduling
            }
            
        except Exception as e:
            logger.error(f"Error scheduling document review: {str(e)}")
            raise
    
    async def schedule_compliance_check(
        self,
        document_id: str,
        frequency: str,
        rules: List[str] = None
    ) -> Dict:
        """Schedule automated compliance checks."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError("Document not found")
            
            job_id = f"compliance_{document_id}_{frequency}"
            self.scheduler.add_job(
                self._run_compliance_check,
                'interval',
                **self._get_interval(frequency),
                id=job_id,
                replace_existing=True,
                kwargs={
                    'document_id': document_id,
                    'rules': rules
                }
            )
            
            return {
                'job_id': job_id,
                'document_id': document_id,
                'frequency': frequency,
                'rules': rules
            }
            
        except Exception as e:
            logger.error(f"Error scheduling compliance check: {str(e)}")
            raise
    
    async def schedule_document_expiry(
        self,
        document_id: str,
        expiry_date: datetime,
        notification_days: List[int] = [30, 14, 7, 1]
    ) -> Dict:
        """Schedule document expiry notifications."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError("Document not found")
            
            # Schedule notifications for each notification day
            jobs = []
            for days in notification_days:
                notify_date = expiry_date - timedelta(days=days)
                if notify_date > datetime.utcnow():
                    job_id = f"expiry_{document_id}_{days}"
                    self.scheduler.add_job(
                        self._send_expiry_notification,
                        'date',
                        run_date=notify_date,
                        id=job_id,
                        replace_existing=True,
                        kwargs={
                            'document_id': document_id,
                            'days_remaining': days
                        }
                    )
                    jobs.append({
                        'job_id': job_id,
                        'notification_date': notify_date.isoformat(),
                        'days_remaining': days
                    })
            
            # Schedule final expiry notification
            job_id = f"expired_{document_id}"
            self.scheduler.add_job(
                self._send_expiry_notification,
                'date',
                run_date=expiry_date,
                id=job_id,
                replace_existing=True,
                kwargs={
                    'document_id': document_id,
                    'days_remaining': 0
                }
            )
            jobs.append({
                'job_id': job_id,
                'notification_date': expiry_date.isoformat(),
                'days_remaining': 0
            })
            
            return {
                'document_id': document_id,
                'expiry_date': expiry_date.isoformat(),
                'notifications': jobs
            }
            
        except Exception as e:
            logger.error(f"Error scheduling document expiry: {str(e)}")
            raise
    
    async def _optimize_start_date(
        self,
        proposed_date: datetime,
        reviewers: List[str],
        frequency: str
    ) -> datetime:
        """Optimize start date based on reviewer availability and workload."""
        try:
            # Get reviewer availability
            availability = await self._get_reviewer_availability(reviewers)
            
            # Find optimal date
            optimal_date = proposed_date
            while not self._is_date_optimal(optimal_date, availability):
                optimal_date += timedelta(days=1)
            
            return optimal_date
        except Exception as e:
            logger.error(f"Error optimizing start date: {str(e)}")
            return proposed_date
    
    async def _balance_workload(
        self,
        reviewers: List[str],
        start_date: datetime
    ) -> List[str]:
        """Balance workload among reviewers."""
        try:
            # Get current workload for each reviewer
            workloads = await self._get_reviewer_workloads(reviewers)
            
            # Sort reviewers by workload
            sorted_reviewers = sorted(
                reviewers,
                key=lambda x: workloads.get(x, 0)
            )
            
            # Return reviewers with balanced workload
            return sorted_reviewers[:len(reviewers)]
        except Exception as e:
            logger.error(f"Error balancing workload: {str(e)}")
            return reviewers
    
    async def _track_workload(
        self,
        reviewers: List[str],
        start_date: datetime,
        document_id: str
    ) -> None:
        """Track reviewer workload."""
        try:
            for reviewer_id in reviewers:
                if reviewer_id not in self.workload_cache:
                    self.workload_cache[reviewer_id] = []
                
                self.workload_cache[reviewer_id].append({
                    'document_id': document_id,
                    'start_date': start_date,
                    'status': 'scheduled'
                })
        except Exception as e:
            logger.error(f"Error tracking workload: {str(e)}")
    
    async def _update_analytics(self, document_id: str, event_type: str) -> None:
        """Update analytics data."""
        try:
            if document_id not in self.analytics_cache:
                self.analytics_cache[document_id] = {
                    'events': [],
                    'metrics': {}
                }
            
            self.analytics_cache[document_id]['events'].append({
                'type': event_type,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Update metrics
            await self._calculate_metrics(document_id)
        except Exception as e:
            logger.error(f"Error updating analytics: {str(e)}")
    
    async def _calculate_metrics(self, document_id: str) -> None:
        """Calculate analytics metrics."""
        try:
            events = self.analytics_cache[document_id]['events']
            
            # Calculate review completion rate
            scheduled = len([e for e in events if e['type'] == 'review_scheduled'])
            completed = len([e for e in events if e['type'] == 'review_completed'])
            
            if scheduled > 0:
                completion_rate = (completed / scheduled) * 100
                self.analytics_cache[document_id]['metrics']['completion_rate'] = completion_rate
            
            # Calculate average review time
            review_times = []
            for i in range(len(events) - 1):
                if events[i]['type'] == 'review_scheduled' and events[i+1]['type'] == 'review_completed':
                    start = datetime.fromisoformat(events[i]['timestamp'])
                    end = datetime.fromisoformat(events[i+1]['timestamp'])
                    review_times.append((end - start).total_seconds())
            
            if review_times:
                avg_review_time = sum(review_times) / len(review_times)
                self.analytics_cache[document_id]['metrics']['avg_review_time'] = avg_review_time
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
    
    async def get_analytics(self, document_id: str) -> Dict:
        """Get analytics data for a document."""
        try:
            if document_id in self.analytics_cache:
                return self.analytics_cache[document_id]
            return {'events': [], 'metrics': {}}
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            return {'events': [], 'metrics': {}}
    
    async def _send_review_reminder(
        self,
        document_id: str,
        reviewers: List[str],
        priority: str = "normal"
    ) -> None:
        """Send review reminder notifications with priority handling."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return
            
            # Update analytics
            await self._update_analytics(document_id, 'reminder_sent')
            
            for reviewer_id in reviewers:
                reviewer = self.db.query(User).filter(User.id == reviewer_id).first()
                if reviewer:
                    # Customize message based on priority
                    priority_emoji = {
                        'high': '🔴',
                        'normal': '🟡',
                        'low': '🟢'
                    }.get(priority, '🟡')
                    
                    await self.notification_service.send_email_notification(
                        to_email=reviewer.email,
                        subject=f"{priority_emoji} Document Review Required: {document.title}",
                        html_content=f"""
                        <h2>Document Review Reminder</h2>
                        <p>Priority: {priority.upper()}</p>
                        <p>The following document requires your review:</p>
                        <p><strong>{document.title}</strong></p>
                        <p>Please review the document and update its status as needed.</p>
                        <p>Click <a href="{os.getenv('FRONTEND_URL')}/documents/{document.id}">here</a> to review.</p>
                        """
                    )
            
        except Exception as e:
            logger.error(f"Error sending review reminder: {str(e)}")
    
    def _is_date_optimal(self, date: datetime, availability: Dict) -> bool:
        """Check if a date is optimal for all reviewers."""
        try:
            for reviewer_id, available_dates in availability.items():
                if date.date() not in available_dates:
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking date optimality: {str(e)}")
            return True
    
    async def _get_reviewer_availability(self, reviewers: List[str]) -> Dict:
        """Get reviewer availability data."""
        try:
            availability = {}
            for reviewer_id in reviewers:
                # Get reviewer's calendar data
                # This would integrate with your calendar system
                # For now, return all dates as available
                availability[reviewer_id] = set()
                for i in range(30):  # Check next 30 days
                    date = datetime.utcnow().date() + timedelta(days=i)
                    availability[reviewer_id].add(date)
            return availability
        except Exception as e:
            logger.error(f"Error getting reviewer availability: {str(e)}")
            return {}
    
    async def _get_reviewer_workloads(self, reviewers: List[str]) -> Dict:
        """Get current workload for each reviewer."""
        try:
            workloads = {}
            for reviewer_id in reviewers:
                # Count active reviews
                active_reviews = len([
                    w for w in self.workload_cache.get(reviewer_id, [])
                    if w['status'] == 'scheduled'
                ])
                workloads[reviewer_id] = active_reviews
            return workloads
        except Exception as e:
            logger.error(f"Error getting reviewer workloads: {str(e)}")
            return {}
    
    async def _run_compliance_check(
        self,
        document_id: str,
        rules: List[str] = None
    ) -> None:
        """Run automated compliance check."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return
            
            # Trigger compliance check
            # This would integrate with your compliance checking service
            # For now, we'll just log it
            logger.info(f"Running automated compliance check for document {document_id}")
            
        except Exception as e:
            logger.error(f"Error running compliance check: {str(e)}")
    
    async def _send_expiry_notification(
        self,
        document_id: str,
        days_remaining: int
    ) -> None:
        """Send document expiry notification."""
        try:
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                return
            
            # Get document owner and organization admins
            owner = self.db.query(User).filter(User.id == document.owner_id).first()
            admins = self.db.query(User).filter(
                User.organization_id == document.organization_id,
                User.role == 'admin'
            ).all()
            
            # Prepare notification content
            if days_remaining > 0:
                subject = f"Document Expiring Soon: {document.title}"
                html_content = f"""
                <h2>⚠️ Document Expiring Soon</h2>
                <p>The following document will expire in {days_remaining} days:</p>
                <p><strong>{document.title}</strong></p>
                <p>Please review and update the document if needed.</p>
                <p>Click <a href="{os.getenv('FRONTEND_URL')}/documents/{document.id}">here</a> to view.</p>
                """
            else:
                subject = f"Document Expired: {document.title}"
                html_content = f"""
                <h2>🚫 Document Expired</h2>
                <p>The following document has expired:</p>
                <p><strong>{document.title}</strong></p>
                <p>Please update or archive the document as needed.</p>
                <p>Click <a href="{os.getenv('FRONTEND_URL')}/documents/{document.id}">here</a> to view.</p>
                """
            
            # Send notifications
            if owner:
                await self.notification_service.send_email_notification(
                    to_email=owner.email,
                    subject=subject,
                    html_content=html_content
                )
            
            for admin in admins:
                if admin.id != document.owner_id:
                    await self.notification_service.send_email_notification(
                        to_email=admin.email,
                        subject=subject,
                        html_content=html_content
                    )
            
        except Exception as e:
            logger.error(f"Error sending expiry notification: {str(e)}")
    
    def _get_interval(self, frequency: str) -> Dict:
        """Convert frequency string to interval dict."""
        intervals = {
            'hourly': {'hours': 1},
            'daily': {'days': 1},
            'weekly': {'weeks': 1},
            'monthly': {'months': 1},
            'quarterly': {'months': 3},
            'annually': {'years': 1}
        }
        return intervals.get(frequency, {'days': 1}) 