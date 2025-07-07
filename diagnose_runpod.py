#!/usr/bin/env python3
"""
RunPod Endpoint Diagnostic Script
This script helps diagnose issues with RunPod endpoints
"""

import os
import sys
import time
import requests
from datetime import datetime

def main():
    print("🔍 RunPod Endpoint Diagnostic")
    print("=" * 50)
    
    # Get environment variables
    api_key = os.getenv("RUNPOD_API_KEY")
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
    
    if not api_key:
        print("❌ RUNPOD_API_KEY not found in environment variables")
        return False
    
    if not endpoint_id:
        print("❌ RUNPOD_ENDPOINT_ID not found in environment variables") 
        return False
    
    print(f"✅ API Key: {api_key[:8]}...")
    print(f"✅ Endpoint ID: {endpoint_id}")
    print()
    
    # Test 1: Basic connectivity
    print("🌐 Test 1: Basic API connectivity")
    try:
        response = requests.get(
            "https://api.runpod.ai/v2",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        if response.status_code == 200:
            print("✅ RunPod API is reachable")
        else:
            print(f"⚠️  RunPod API returned status {response.status_code}")
    except requests.Timeout:
        print("❌ Timeout connecting to RunPod API")
    except Exception as e:
        print(f"❌ Error connecting to RunPod API: {e}")
    print()
    
    # Test 2: Endpoint status
    print("🎯 Test 2: Endpoint status check")
    base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{base_url}/status",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Endpoint is accessible")
        elif response.status_code == 404:
            print("❌ Endpoint not found - check your endpoint ID")
            print("   Go to https://www.runpod.io/console/serverless to verify your endpoint")
        else:
            print(f"⚠️  Endpoint returned status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except requests.Timeout:
        print("❌ Timeout checking endpoint status")
    except Exception as e:
        print(f"❌ Error checking endpoint: {e}")
    print()
    
    # Test 3: Simple job submission
    print("🚀 Test 3: Simple job submission")
    try:
        test_payload = {
            "input": {
                "type": "test",
                "message": "Hello from diagnostic script"
            }
        }
        
        response = requests.post(
            f"{base_url}/run",
            headers=headers,
            json=test_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "id" in data:
                job_id = data["id"]
                print(f"✅ Job submitted successfully: {job_id}")
                
                # Test 4: Job status polling
                print("⏳ Test 4: Job status polling (30 seconds)")
                start_time = time.time()
                timeout = 30
                
                while time.time() - start_time < timeout:
                    try:
                        status_response = requests.get(
                            f"{base_url}/status/{job_id}",
                            headers=headers,
                            timeout=10
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            status = status_data.get("status", "UNKNOWN")
                            elapsed = time.time() - start_time
                            print(f"   Status: {status} (elapsed: {elapsed:.1f}s)")
                            
                            if status in ["COMPLETED", "FAILED", "CANCELLED"]:
                                if status == "COMPLETED":
                                    print("✅ Job completed successfully")
                                else:
                                    print(f"❌ Job ended with status: {status}")
                                    if "error" in status_data:
                                        print(f"   Error: {status_data['error']}")
                                break
                        else:
                            print(f"   Status check failed: {status_response.status_code}")
                            break
                            
                    except requests.Timeout:
                        print("   Timeout checking job status")
                        break
                    except Exception as e:
                        print(f"   Error checking job status: {e}")
                        break
                    
                    time.sleep(5)
                else:
                    print("⚠️  Job did not complete within 30 seconds")
                    print("   This may indicate the endpoint worker is not running")
                    
            else:
                print(f"❌ Invalid response format: {data}")
        else:
            print(f"❌ Job submission failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except requests.Timeout:
        print("❌ Timeout submitting job")
    except Exception as e:
        print(f"❌ Error submitting job: {e}")
    
    print()
    print("🎯 Diagnostic Summary")
    print("=" * 50)
    print("If you see errors above, here's what to check:")
    print("1. Go to https://www.runpod.io/console/serverless")
    print("2. Find your endpoint and check its status")
    print("3. Make sure the endpoint is 'Active' and has workers running")
    print("4. Check the endpoint logs for any error messages")
    print("5. If using GitHub integration, make sure your code is up to date")
    print()
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 