import os
import base64
import json
import time
from typing import Optional, Dict, Any, Tuple
import requests
from ..models import RunPodJobInput, RunPodJobOutput

class RunPodClient:
    def __init__(self, api_key: str, endpoint_id: str):
        """Initialize RunPod client with API key and endpoint ID"""
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = "https://api.runpod.ai/v2"
        
    def _make_request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to RunPod API"""
        url = f"{self.base_url}/{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.request(
            method,
            url,
            headers=headers,
            json=data
        )
        
        try:
            return response.json()
        except:
            return {"error": response.text}
            
    def run_inference(self, job_input: RunPodJobInput, timeout: int = 300) -> RunPodJobOutput:
        """Run inference job and wait for completion"""
        # Submit job
        response = self._make_request(
            "POST",
            f"{self.endpoint_id}/run",
            data={"input": job_input.dict()}
        )
        
        if "error" in response:
            return RunPodJobOutput(
                success=False,
                message="Failed to submit job",
                error=str(response["error"])
            )
            
        job_id = response.get("id")
        if not job_id:
            return RunPodJobOutput(
                success=False,
                message="No job ID in response",
                error="Invalid response format"
            )
            
        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self._make_request("GET", f"{self.endpoint_id}/status/{job_id}")
            
            if "error" in status:
                return RunPodJobOutput(
                    success=False,
                    message="Failed to check job status",
                    error=str(status["error"])
                )
                
            if status.get("status") == "COMPLETED":
                output = status.get("output", {})
                return RunPodJobOutput(
                    success=True,
                    message="Job completed successfully",
                    audio_data=output.get("audio_data"),
                    content_type=output.get("content_type")
                )
                
            if status.get("status") == "FAILED":
                return RunPodJobOutput(
                    success=False,
                    message="Job failed",
                    error=status.get("error", "Unknown error")
                )
                
            time.sleep(1)
            
        return RunPodJobOutput(
            success=False,
            message="Job timed out",
            error=f"Job did not complete within {timeout} seconds"
        )
        
    def generate_tts(
        self,
        text: str,
        voice_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[bytes], Optional[str], str]:
        """Generate TTS audio using RunPod endpoint"""
        job_input = RunPodJobInput(
            type="tts",
            text=text,
            voice_name=voice_name,
            parameters=parameters or {}
        )
        
        result = self.run_inference(job_input)
        
        if not result.success:
            return None, None, result.error or result.message
            
        try:
            audio_data = base64.b64decode(result.audio_data)
            return audio_data, result.content_type, "Success"
        except Exception as e:
            return None, None, f"Failed to decode audio data: {str(e)}"
            
    def clone_voice(
        self,
        reference_audio: bytes,
        voice_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Clone voice from reference audio using RunPod endpoint"""
        # Encode audio data
        audio_b64 = base64.b64encode(reference_audio).decode()
        
        job_input = RunPodJobInput(
            type="clone",
            reference_audio=audio_b64,
            voice_name=voice_name,
            parameters=parameters or {}
        )
        
        result = self.run_inference(job_input)
        return result.message if result.success else (result.error or "Unknown error") 