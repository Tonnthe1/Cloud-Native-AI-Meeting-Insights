#!/usr/bin/env python3
"""
Ray Serve deployment script
Run this to deploy the summarization service to Ray
"""

import ray
from ray import serve
import time
import logging

# Import our service
from summarization_service import deploy_services

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main deployment function."""
    try:
        # Connect to Ray cluster
        logger.info("Connecting to Ray cluster...")
        ray.init(address="ray://localhost:10001", ignore_reinit_error=True)
        
        # Start Ray Serve
        logger.info("Starting Ray Serve...")
        serve.start(detached=True, http_options={"host": "0.0.0.0", "port": 10001})
        
        # Deploy services
        deploy_services()
        
        # Wait a moment for services to start
        time.sleep(5)
        
        # Check service status
        logger.info("Checking service status...")
        deployments = serve.list_deployments()
        
        for name, deployment in deployments.items():
            logger.info(f"Deployment '{name}': {deployment.status}")
        
        logger.info("Deployment completed successfully!")
        logger.info("Ray Dashboard: http://localhost:8265")
        logger.info("Services available at: http://localhost:10001")
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise

if __name__ == "__main__":
    main()