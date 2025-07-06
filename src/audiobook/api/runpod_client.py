"""RunPod API client for GPU-accelerated voice cloning and TTS."""

import os
import base64
import json
import time
from typing import Optional, Dict, Any, Tuple
import requests
from ..models import RunPodJobInput, RunPodJobOutput
from dataclasses import dataclass

@dataclass
class RunPodResponse:
    success: bool
    error: Optional[str] = None
    files: Dict[str, bytes] = None

class RunPodClient:
    def __init__(self, api_key: str, endpoint_id: str):
        """Initialize RunPod client.
        
        Args:
            api_key: RunPod API key
            endpoint_id: RunPod endpoint ID
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def clone_voice(
        self,
        audio_path: str,
        voice_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, float]] = None
    ) -> Tuple[bool, str]:
        """Clone a voice using RunPod's GPU.
        
        Args:
            audio_path: Path to reference audio file
            voice_name: Name for the cloned voice
            display_name: Display name (defaults to voice_name)
            description: Optional description
            parameters: Optional parameters for voice cloning
                - exaggeration: Voice emotion exaggeration (0-1)
                - cfg_weight: Classifier-free guidance weight (0-1)
                - temperature: Generation temperature (0-1)
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Read and encode audio file
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            audio_b64 = base64.b64encode(audio_data).decode()
            
            # Prepare request data
            input_data = {
                "type": "clone",
                "reference_audio": audio_b64,
                "voice_name": voice_name,
                "display_name": display_name or voice_name,
                "description": description or "",
                "parameters": parameters or {}
            }
            
            # Submit job
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json={"input": input_data},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                return False, str(data["error"])
            
            # Poll for completion
            task_id = data["id"]
            while True:
                status = requests.get(
                    f"{self.base_url}/status/{task_id}",
                    headers=self.headers,
                    timeout=10
                ).json()
                
                if status["status"] == "COMPLETED":
                    result = status["output"]
                    return result["success"], result["message"]
                    
                elif status["status"] in ["FAILED", "CANCELLED"]:
                    return False, status.get("error", "Task failed or was cancelled")
                    
                time.sleep(2)
                
        except Exception as e:
            return False, f"Error cloning voice: {str(e)}"
    
    def generate_speech(
        self,
        text: str,
        voice_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[bytes], str]:
        """Generate speech using RunPod's GPU.
        
        Args:
            text: Text to convert to speech
            voice_name: Name of the voice to use
            parameters: Optional TTS parameters
                - exaggeration: Voice emotion exaggeration (0-1)
                - cfg_weight: Classifier-free guidance weight (0-1)
                - temperature: Generation temperature (0-1)
                - chunk_size: Number of words per chunk
        
        Returns:
            Tuple[Optional[bytes], str]: (audio_data, error_message)
        """
        try:
            # Prepare request data
            input_data = {
                "type": "tts",
                "text": text,
                "voice_name": voice_name,
                "parameters": parameters or {}
            }
            
            # Submit job
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json={"input": input_data},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if "error" in data:
                return None, str(data["error"])
            
            # Poll for completion
            task_id = data["id"]
            while True:
                status = requests.get(
                    f"{self.base_url}/status/{task_id}",
                    headers=self.headers,
                    timeout=10
                ).json()
                
                if status["status"] == "COMPLETED":
                    result = status["output"]
                    audio_data = base64.b64decode(result["audio_data"])
                    return audio_data, ""
                    
                elif status["status"] in ["FAILED", "CANCELLED"]:
                    return None, status.get("error", "Task failed or was cancelled")
                    
                time.sleep(2)
                
        except Exception as e:
            return None, f"Error generating speech: {str(e)}"

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a RunPod task.
        
        Args:
            task_id: RunPod task ID
            
        Returns:
            Dict with task status information
        """
        try:
            response = requests.get(
                f"{self.base_url}/status/{task_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

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