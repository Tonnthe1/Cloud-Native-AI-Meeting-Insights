#!/usr/bin/env python3
"""
Test script for Triton inference server
Demonstrates keyword extraction model
"""

import requests
import json
import time
import sys

def test_triton_health(base_url="http://localhost:8003"):
    """Test if Triton server is healthy."""
    try:
        response = requests.get(f"{base_url}/v2/health/ready", timeout=5)
        if response.status_code == 200:
            print("✅ Triton server is ready")
            return True
        else:
            print(f"❌ Triton server not ready: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Triton server not reachable: {e}")
        return False

def test_keyword_extraction(base_url="http://localhost:8003"):
    """Test keyword extraction model."""
    
    # Sample meeting text
    test_text = """
    Good morning everyone. Today's meeting will focus on reviewing our project timeline 
    and discussing action items from last week. We need to make important decisions 
    about the budget allocation and set deadlines for the upcoming tasks. 
    The team has made significant progress on the development phase, but we need to 
    address some concerns about the testing strategy. Let's review the status update 
    and plan our next steps for the following week.
    """
    
    # Prepare inference request
    inference_request = {
        "inputs": [
            {
                "name": "INPUT_TEXT",
                "shape": [1, 1],
                "datatype": "BYTES",
                "data": [test_text]
            }
        ]
    }
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/v2/models/keyword_extractor/infer",
            json=inference_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract outputs
            keywords = [k for k in result["outputs"][0]["data"]]
            scores = result["outputs"][1]["data"]
            
            print("✅ Keyword extraction successful!")
            print(f"📊 Processing time: {processing_time:.2f}ms")
            print(f"📝 Input length: {len(test_text)} characters")
            print(f"🔑 Extracted {len(keywords)} keywords:")
            
            for i, (keyword, score) in enumerate(zip(keywords, scores)):
                print(f"   {i+1}. {keyword} (score: {score:.3f})")
            
            return True
        else:
            print(f"❌ Inference failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Inference error: {e}")
        return False

def test_triton_model_info(base_url="http://localhost:8003"):
    """Get model information from Triton."""
    try:
        response = requests.get(f"{base_url}/v2/models/keyword_extractor", timeout=5)
        if response.status_code == 200:
            model_info = response.json()
            print("📋 Model Information:")
            print(f"   Name: {model_info['name']}")
            print(f"   Backend: {model_info['backend']}")
            print(f"   Max Batch Size: {model_info['max_batch_size']}")
            print(f"   Inputs: {len(model_info['inputs'])}")
            print(f"   Outputs: {len(model_info['outputs'])}")
            return True
        else:
            print(f"❌ Failed to get model info: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Model info error: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Testing Triton Inference Server")
    print("=" * 50)
    
    base_url = "http://localhost:8003"
    
    # Test server health
    if not test_triton_health(base_url):
        print("\n💡 Make sure Triton server is running:")
        print("   docker compose up triton-server")
        sys.exit(1)
    
    print()
    
    # Test model info
    test_triton_model_info(base_url)
    print()
    
    # Test inference
    success = test_keyword_extraction(base_url)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All Triton tests passed!")
        print("\n📖 Example curl command:")
        print(f'''
curl -X POST {base_url}/v2/models/keyword_extractor/infer \\
  -H "Content-Type: application/json" \\
  -d '{{
    "inputs": [{{
      "name": "INPUT_TEXT",
      "shape": [1, 1],
      "datatype": "BYTES",
      "data": ["Your meeting text here"]
    }}]
  }}'
        ''')
    else:
        print("❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()