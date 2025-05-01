#!/usr/bin/env python3
import os
import sys
import logging
import subprocess
import json
import requests
from datetime import datetime
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityScanner:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = []
        
    def scan_dependencies(self) -> None:
        """Scan Python dependencies for known vulnerabilities"""
        try:
            logger.info("Scanning Python dependencies...")
            
            # Run safety check
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                vulnerabilities = json.loads(result.stdout)
                for vuln in vulnerabilities:
                    self.results.append({
                        "type": "dependency",
                        "severity": vuln.get("severity", "unknown"),
                        "package": vuln.get("package", "unknown"),
                        "description": vuln.get("description", "No description available"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
        except Exception as e:
            logger.error(f"Dependency scan failed: {str(e)}")
    
    def scan_code_quality(self) -> None:
        """Scan code for quality and security issues"""
        try:
            logger.info("Scanning code quality...")
            
            # Run bandit for security issues
            result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                issues = json.loads(result.stdout)
                for issue in issues.get("results", []):
                    self.results.append({
                        "type": "code_quality",
                        "severity": issue.get("issue_severity", "unknown"),
                        "file": issue.get("filename", "unknown"),
                        "line": issue.get("line_number", 0),
                        "description": issue.get("issue_text", "No description available"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
        except Exception as e:
            logger.error(f"Code quality scan failed: {str(e)}")
    
    def scan_docker_images(self) -> None:
        """Scan Docker images for vulnerabilities"""
        try:
            logger.info("Scanning Docker images...")
            
            # Run Trivy scan
            result = subprocess.run(
                ["trivy", "image", "--format", "json", "compliwave-backend:latest"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                vulnerabilities = json.loads(result.stdout)
                for vuln in vulnerabilities.get("Vulnerabilities", []):
                    self.results.append({
                        "type": "docker",
                        "severity": vuln.get("Severity", "unknown"),
                        "package": vuln.get("PkgName", "unknown"),
                        "description": vuln.get("Description", "No description available"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
        except Exception as e:
            logger.error(f"Docker scan failed: {str(e)}")
    
    def scan_network_security(self) -> None:
        """Scan network security configuration"""
        try:
            logger.info("Scanning network security...")
            
            # Check SSL/TLS configuration
            response = requests.get(self.config['BACKEND_URL'], verify=False)
            if not response.ok:
                self.results.append({
                    "type": "network",
                    "severity": "high",
                    "description": f"Backend service not accessible: {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check for open ports
            result = subprocess.run(
                ["nmap", "-p", "1-1000", self.config['BACKEND_HOST']],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "open" in line:
                        self.results.append({
                            "type": "network",
                            "severity": "medium",
                            "description": f"Open port found: {line.strip()}",
                            "timestamp": datetime.now().isoformat()
                        })
                        
        except Exception as e:
            logger.error(f"Network security scan failed: {str(e)}")
    
    def scan_database_security(self) -> None:
        """Scan database security configuration"""
        try:
            logger.info("Scanning database security...")
            
            # Check for default credentials
            if self.config['DB_PASSWORD'] in ['postgres', 'admin', 'password']:
                self.results.append({
                    "type": "database",
                    "severity": "high",
                    "description": "Default database password detected",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Check for exposed database port
            result = subprocess.run(
                ["nc", "-zv", self.config['DB_HOST'], self.config['DB_PORT']],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.results.append({
                    "type": "database",
                    "severity": "high",
                    "description": f"Database port {self.config['DB_PORT']} is publicly accessible",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Database security scan failed: {str(e)}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate security scan report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_issues": len(self.results),
            "issues_by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "issues_by_type": {},
            "details": self.results
        }
        
        # Count issues by severity and type
        for issue in self.results:
            severity = issue["severity"].lower()
            if severity in report["issues_by_severity"]:
                report["issues_by_severity"][severity] += 1
            
            issue_type = issue["type"]
            if issue_type not in report["issues_by_type"]:
                report["issues_by_type"][issue_type] = 0
            report["issues_by_type"][issue_type] += 1
        
        return report
    
    def run_scan(self) -> Dict[str, Any]:
        """Run all security scans"""
        logger.info("Starting security scan...")
        
        self.scan_dependencies()
        self.scan_code_quality()
        self.scan_docker_images()
        self.scan_network_security()
        self.scan_database_security()
        
        report = self.generate_report()
        
        # Save report to file
        report_file = f"security_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Security scan completed. Report saved to {report_file}")
        return report

def main():
    # Load configuration from environment variables
    config = {
        'BACKEND_URL': os.getenv('BACKEND_URL', 'http://localhost:8000'),
        'BACKEND_HOST': os.getenv('BACKEND_HOST', 'localhost'),
        'DB_HOST': os.getenv('DB_HOST', 'localhost'),
        'DB_PORT': os.getenv('DB_PORT', '5432'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD', '')
    }
    
    scanner = SecurityScanner(config)
    report = scanner.run_scan()
    
    # Print summary
    print("\nSecurity Scan Summary:")
    print(f"Total Issues: {report['total_issues']}")
    print("\nIssues by Severity:")
    for severity, count in report['issues_by_severity'].items():
        print(f"{severity.capitalize()}: {count}")
    print("\nIssues by Type:")
    for issue_type, count in report['issues_by_type'].items():
        print(f"{issue_type}: {count}")

if __name__ == "__main__":
    main() 