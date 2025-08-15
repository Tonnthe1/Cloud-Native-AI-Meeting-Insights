"""
Ray Serve deployment for fast summarization service
Demonstrates real-time processing capabilities
"""

import ray
from ray import serve
import logging
from typing import Dict, Any
import time
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@serve.deployment(num_replicas=2, ray_actor_options={"num_cpus": 1})
class SummarizationService:
    """
    Fast summarization service using Ray Serve
    CPU-only deployment for demonstration
    """
    
    def __init__(self):
        self.model_name = "fast-summarizer"
        logger.info(f"Initialized {self.model_name} service")
        
        # Simple keyword-based summarization (placeholder)
        self.keywords = [
            "meeting", "discussion", "action", "decision", "follow-up",
            "task", "deadline", "progress", "update", "review",
            "budget", "timeline", "project", "team", "goal"
        ]
    
    def extract_key_sentences(self, text: str, max_sentences: int = 3) -> list:
        """Extract key sentences based on keyword density."""
        sentences = text.split('.')
        scored_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short sentences
                continue
                
            score = 0
            sentence_lower = sentence.lower()
            
            # Score based on keyword presence
            for keyword in self.keywords:
                if keyword in sentence_lower:
                    score += 1
            
            # Boost score for sentences with numbers (dates, metrics)
            if any(char.isdigit() for char in sentence):
                score += 0.5
            
            scored_sentences.append((score, sentence))
        
        # Sort by score and return top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        return [sentence for score, sentence in scored_sentences[:max_sentences]]
    
    def generate_summary(self, text: str) -> str:
        """Generate a fast summary of the input text."""
        if not text or len(text.strip()) < 50:
            return "Text too short for meaningful summary."
        
        key_sentences = self.extract_key_sentences(text, max_sentences=3)
        
        if not key_sentences:
            return "No key information found in the text."
        
        # Create structured summary
        summary_parts = [
            "**Key Points:**",
            *[f"• {sentence.strip()}." for sentence in key_sentences],
            "",
            f"**Summary generated from {len(text)} characters of input text.**"
        ]
        
        return "\n".join(summary_parts)
    
    async def __call__(self, request) -> Dict[str, Any]:
        """Handle incoming summarization requests."""
        start_time = time.time()
        
        try:
            # Parse request
            if hasattr(request, 'json'):
                data = await request.json()
            else:
                data = request
            
            text = data.get("text", "")
            options = data.get("options", {})
            
            if not text:
                return {
                    "error": "No text provided",
                    "processing_time_ms": 0
                }
            
            # Generate summary
            summary = self.generate_summary(text)
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            return {
                "summary": summary,
                "input_length": len(text),
                "processing_time_ms": round(processing_time_ms, 2),
                "service": self.model_name,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return {
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000
            }

# Health check deployment
@serve.deployment
class HealthCheck:
    """Health check endpoint for Ray Serve."""
    
    async def __call__(self, request):
        return {
            "status": "healthy",
            "service": "ray-serve-summarization",
            "timestamp": time.time(),
            "ray_version": ray.__version__
        }

def deploy_services():
    """Deploy all Ray Serve services."""
    logger.info("Deploying Ray Serve services...")
    
    # Deploy summarization service
    SummarizationService.deploy()
    
    # Deploy health check
    HealthCheck.deploy()
    
    logger.info("Services deployed successfully!")
    logger.info("Summarization service available at: http://localhost:10001/SummarizationService")
    logger.info("Health check available at: http://localhost:10001/HealthCheck")

if __name__ == "__main__":
    # Initialize Ray if not already connected
    if not ray.is_initialized():
        ray.init(address="ray://localhost:10001", ignore_reinit_error=True)
    
    # Start Serve
    serve.start(detached=True, http_options={"host": "0.0.0.0", "port": 10001})
    
    # Deploy services
    deploy_services()
    
    logger.info("Ray Serve deployment completed. Services are running...")