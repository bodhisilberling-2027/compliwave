#!/usr/bin/env python3
import os
import sys
import time
import logging
import requests
import psycopg2
import redis
from prometheus_client import start_http_server, Gauge, Counter
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
http_requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
response_time = Gauge('response_time_seconds', 'Response time in seconds', ['endpoint'])
error_rate = Gauge('error_rate', 'Error rate per endpoint', ['endpoint'])
database_connections = Gauge('database_connections', 'Number of active database connections')
redis_connections = Gauge('redis_connections', 'Number of active Redis connections')
memory_usage = Gauge('memory_usage_bytes', 'Memory usage in bytes')
cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')

class MonitoringSystem:
    def __init__(self, config):
        self.config = config
        self.db_conn = None
        self.redis_conn = None
        self.setup_connections()
        
    def setup_connections(self):
        """Set up database and Redis connections"""
        try:
            # Database connection
            self.db_conn = psycopg2.connect(
                host=self.config['DB_HOST'],
                port=self.config['DB_PORT'],
                database=self.config['DB_NAME'],
                user=self.config['DB_USER'],
                password=self.config['DB_PASSWORD']
            )
            
            # Redis connection
            self.redis_conn = redis.Redis(
                host=self.config['REDIS_HOST'],
                port=self.config['REDIS_PORT'],
                password=self.config['REDIS_PASSWORD']
            )
            
        except Exception as e:
            logger.error(f"Failed to set up connections: {str(e)}")
            sys.exit(1)
    
    def check_database_health(self):
        """Check database health and update metrics"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM pg_stat_activity")
                active_connections = cur.fetchone()[0]
                database_connections.set(active_connections)
                
                # Check for long-running queries
                cur.execute("""
                    SELECT pid, query, now() - pg_stat_activity.query_start AS duration
                    FROM pg_stat_activity
                    WHERE state = 'active'
                    AND now() - pg_stat_activity.query_start > interval '5 minutes'
                """)
                long_running = cur.fetchall()
                
                if long_running:
                    logger.warning(f"Found {len(long_running)} long-running queries")
                    for pid, query, duration in long_running:
                        logger.warning(f"Query {pid} running for {duration}: {query}")
                
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
    
    def check_redis_health(self):
        """Check Redis health and update metrics"""
        try:
            info = self.redis_conn.info()
            redis_connections.set(info['connected_clients'])
            
            # Check memory usage
            memory_usage.set(info['used_memory'])
            
            # Check for slow commands
            slow_commands = self.redis_conn.slowlog_get(10)
            if slow_commands:
                logger.warning(f"Found {len(slow_commands)} slow Redis commands")
                for cmd in slow_commands:
                    logger.warning(f"Slow command: {cmd['command']} took {cmd['duration']}ms")
                    
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
    
    def check_application_health(self):
        """Check application health endpoints"""
        try:
            # Check backend health
            response = requests.get(f"{self.config['BACKEND_URL']}/health")
            http_requests_total.labels(
                method='GET',
                endpoint='/health',
                status=response.status_code
            ).inc()
            
            if response.status_code != 200:
                logger.error(f"Backend health check failed: {response.status_code}")
            
            # Check frontend health
            response = requests.get(f"{self.config['FRONTEND_URL']}/health")
            http_requests_total.labels(
                method='GET',
                endpoint='/health',
                status=response.status_code
            ).inc()
            
            if response.status_code != 200:
                logger.error(f"Frontend health check failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Application health check failed: {str(e)}")
    
    def send_alert(self, message, severity="warning"):
        """Send alert to configured notification system"""
        try:
            # Example: Send to Slack
            if self.config.get('SLACK_WEBHOOK_URL'):
                payload = {
                    "text": f"[{severity.upper()}] {message}",
                    "username": "Compliwave Monitoring"
                }
                requests.post(self.config['SLACK_WEBHOOK_URL'], json=payload)
            
            # Example: Send email
            if self.config.get('SMTP_SERVER'):
                # Implement email sending logic here
                pass
                
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")
    
    def run(self):
        """Run the monitoring system"""
        logger.info("Starting monitoring system...")
        
        # Start Prometheus metrics server
        start_http_server(self.config['METRICS_PORT'])
        
        while True:
            try:
                self.check_database_health()
                self.check_redis_health()
                self.check_application_health()
                
                # Sleep for the configured interval
                time.sleep(self.config['CHECK_INTERVAL'])
                
            except Exception as e:
                logger.error(f"Monitoring cycle failed: {str(e)}")
                self.send_alert(f"Monitoring system error: {str(e)}", severity="error")
                time.sleep(self.config['CHECK_INTERVAL'])

def main():
    # Load configuration from environment variables
    config = {
        'DB_HOST': os.getenv('DB_HOST', 'localhost'),
        'DB_PORT': os.getenv('DB_PORT', '5432'),
        'DB_NAME': os.getenv('DB_NAME', 'compliwave'),
        'DB_USER': os.getenv('DB_USER', 'compliwave'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD', ''),
        'REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
        'REDIS_PORT': os.getenv('REDIS_PORT', '6379'),
        'REDIS_PASSWORD': os.getenv('REDIS_PASSWORD', ''),
        'BACKEND_URL': os.getenv('BACKEND_URL', 'http://localhost:8000'),
        'FRONTEND_URL': os.getenv('FRONTEND_URL', 'http://localhost:3000'),
        'METRICS_PORT': int(os.getenv('METRICS_PORT', '9090')),
        'CHECK_INTERVAL': int(os.getenv('CHECK_INTERVAL', '60')),
        'SLACK_WEBHOOK_URL': os.getenv('SLACK_WEBHOOK_URL', ''),
        'SMTP_SERVER': os.getenv('SMTP_SERVER', '')
    }
    
    monitoring = MonitoringSystem(config)
    monitoring.run()

if __name__ == "__main__":
    main() 