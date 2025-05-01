#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import logging
import yaml
import docker
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_docker_images():
    """Build Docker images for the application"""
    try:
        # Build backend image
        logger.info("Building backend image...")
        subprocess.run(["docker", "build", "-t", "compliwave-backend", "./backend"], check=True)
        
        # Build frontend image
        logger.info("Building frontend image...")
        subprocess.run(["docker", "build", "-t", "compliwave-frontend", "./frontend"], check=True)
        
        logger.info("Docker images built successfully")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker build failed: {str(e)}")
        sys.exit(1)

def push_docker_images(registry, username, password):
    """Push Docker images to registry"""
    try:
        # Login to registry
        subprocess.run(
            ["docker", "login", "-u", username, "-p", password, registry],
            check=True
        )
        
        # Tag and push backend image
        backend_tag = f"{registry}/compliwave-backend:latest"
        subprocess.run(["docker", "tag", "compliwave-backend", backend_tag], check=True)
        subprocess.run(["docker", "push", backend_tag], check=True)
        
        # Tag and push frontend image
        frontend_tag = f"{registry}/compliwave-frontend:latest"
        subprocess.run(["docker", "tag", "compliwave-frontend", frontend_tag], check=True)
        subprocess.run(["docker", "push", frontend_tag], check=True)
        
        logger.info("Docker images pushed successfully")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker push failed: {str(e)}")
        sys.exit(1)

def deploy_kubernetes(config_file):
    """Deploy application to Kubernetes"""
    try:
        # Apply Kubernetes configurations
        subprocess.run(["kubectl", "apply", "-f", config_file], check=True)
        logger.info("Kubernetes deployment completed successfully")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Kubernetes deployment failed: {str(e)}")
        sys.exit(1)

def create_kubernetes_config(registry, namespace="compliwave"):
    """Create Kubernetes configuration files"""
    config = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": namespace
        }
    }
    
    # Create namespace
    with open("k8s/namespace.yaml", "w") as f:
        yaml.dump(config, f)
    
    # Create deployment configurations
    deployments = {
        "backend": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "compliwave-backend",
                "namespace": namespace
            },
            "spec": {
                "replicas": 3,
                "selector": {
                    "matchLabels": {
                        "app": "compliwave-backend"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "compliwave-backend"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": "compliwave-backend",
                            "image": f"{registry}/compliwave-backend:latest",
                            "ports": [{
                                "containerPort": 8000
                            }]
                        }]
                    }
                }
            }
        },
        "frontend": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "compliwave-frontend",
                "namespace": namespace
            },
            "spec": {
                "replicas": 3,
                "selector": {
                    "matchLabels": {
                        "app": "compliwave-frontend"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "compliwave-frontend"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": "compliwave-frontend",
                            "image": f"{registry}/compliwave-frontend:latest",
                            "ports": [{
                                "containerPort": 3000
                            }]
                        }]
                    }
                }
            }
        }
    }
    
    # Create deployment files
    os.makedirs("k8s", exist_ok=True)
    for name, config in deployments.items():
        with open(f"k8s/{name}-deployment.yaml", "w") as f:
            yaml.dump(config, f)
    
    logger.info("Kubernetes configuration files created successfully")

def main():
    parser = argparse.ArgumentParser(description="Deployment utility")
    parser.add_argument("--action", choices=["build", "push", "deploy", "create-config"], required=True)
    parser.add_argument("--registry", help="Docker registry URL")
    parser.add_argument("--username", help="Registry username")
    parser.add_argument("--password", help="Registry password")
    parser.add_argument("--config", help="Kubernetes config file")
    parser.add_argument("--namespace", default="compliwave", help="Kubernetes namespace")
    
    args = parser.parse_args()
    
    if args.action == "build":
        build_docker_images()
        
    elif args.action == "push":
        if not all([args.registry, args.username, args.password]):
            logger.error("--registry, --username, and --password are required for push action")
            sys.exit(1)
        push_docker_images(args.registry, args.username, args.password)
        
    elif args.action == "deploy":
        if not args.config:
            logger.error("--config is required for deploy action")
            sys.exit(1)
        deploy_kubernetes(args.config)
        
    elif args.action == "create-config":
        if not args.registry:
            logger.error("--registry is required for create-config action")
            sys.exit(1)
        create_kubernetes_config(args.registry, args.namespace)

if __name__ == "__main__":
    main() 