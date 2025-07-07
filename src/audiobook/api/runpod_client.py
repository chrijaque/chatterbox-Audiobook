"""RunPod API client for GPU-accelerated voice cloning and TTS."""

import os
import base64
import json
import time
from typing import Optional, Dict, Any, Tuple
import requests
import logging
from dataclasses import dataclass

@dataclass
class RunPodResult:
    """RunPod result type."""
    is_success: bool
    message: str

    @classmethod
    def error(cls, message: str) -> 'RunPodResult':
        """Create an error result."""
        return cls(is_success=False, message=message)

    @classmethod
    def success(cls, message: str) -> 'RunPodResult':
        """Create a success result."""
        return cls(is_success=True, message=message)

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
        
        # Configure logging
        self.logger = logging.getLogger("RunPodClient")
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
    
    def clone_voice(
        self,
        audio_path: str,
        voice_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, float]] = None
    ) -> RunPodResult:
        """Clone a voice using RunPod's GPU.
        
        Args:
            audio_path: Path to reference audio file
            voice_name: Name for the cloned voice
            display_name: Display name (defaults to voice_name)
            description: Optional description
            parameters: Optional parameters for voice cloning
        
        Returns:
            RunPodResult: Result with success status and message
        """
        self.logger.info(f"Starting voice cloning for {voice_name}")
        self.logger.debug(f"Parameters: audio_path={audio_path}, display_name={display_name}, parameters={parameters}")
        
        try:
            # Read and encode audio file
            self.logger.debug("Reading audio file...")
            with open(audio_path, 'rb') as f:
                audio_data = f.read()
            audio_b64 = base64.b64encode(audio_data).decode()
            self.logger.debug("Audio file encoded successfully")
            
            # Prepare request data
            input_params = {
                "display_name": display_name or voice_name,
                "description": description or "",
                **(parameters or {})
            }
            
            # Create input data
            input_data: Dict[str, Any] = {
                "type": "clone",
                "text": None,
                "reference_audio": audio_b64,
                "voice_name": voice_name,
                "parameters": input_params
            }
            
            # Submit job with timeout
            self.logger.info("Submitting cloning job to RunPod...")
            try:
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json={"input": input_data},
                    timeout=30  # 30 second timeout for initial request
            )
            response.raise_for_status()
            except requests.Timeout:
                self.logger.error("Timeout while submitting job to RunPod")
                return RunPodResult.error("Timeout while submitting job to RunPod")
            except requests.RequestException as e:
                self.logger.error(f"Error submitting job to RunPod: {str(e)}")
                return RunPodResult.error(f"Error submitting job: {str(e)}")
            
            # Parse response
            response_data = response.json()
            
            # Check for errors
            if "error" in response_data:
                error_msg = str(response_data["error"])
                self.logger.error(f"Error in RunPod response: {error_msg}")
                return RunPodResult.error(error_msg)
            
            # Get task ID
            task_id = response_data.get("id")
            if not task_id:
                self.logger.error("No job ID in response")
                return RunPodResult.error("Invalid response format")
                
            self.logger.info(f"Job submitted successfully. Task ID: {task_id}")
            
            # Poll for completion with timeout
            start_time = time.time()
            max_wait_time = 120  # Reduced to 2 minutes for faster feedback
            poll_interval = 5  # Check every 5 seconds
            consecutive_timeouts = 0
            max_consecutive_timeouts = 3
            
            while True:
                elapsed_time = time.time() - start_time
                if elapsed_time > max_wait_time:
                    self.logger.error(f"Timeout waiting for voice cloning to complete after {max_wait_time} seconds")
                    return RunPodResult.error("RunPod endpoint not responding. Please check if your endpoint is running in the RunPod console.")
                
                try:
                    status_response = requests.get(
                    f"{self.base_url}/status/{task_id}",
                    headers=self.headers,
                    timeout=10
                    )
                    status_response.raise_for_status()
                    consecutive_timeouts = 0  # Reset timeout counter on success
                    
                    # Parse status response
                    status_data: Dict[str, Any] = status_response.json()
                    
                    # Check for errors
                    if "error" in status_data:
                        error_msg = str(status_data["error"])
                        self.logger.error(f"Error in job status: {error_msg}")
                        return RunPodResult.error(error_msg)
                    
                    # Check status
                    status = status_data.get("status")
                    self.logger.debug(f"Current status: {status} (elapsed: {elapsed_time:.1f}s)")
                    
                    if status == "COMPLETED":
                        self.logger.info("Voice cloning completed successfully")
                        return RunPodResult.success("Voice cloned successfully")
                    elif status == "FAILED":
                        error_msg = status_data.get("error", "Unknown error")
                        self.logger.error(f"Job failed: {error_msg}")
                        return RunPodResult.error(f"Voice cloning failed: {error_msg}")
                    elif status == "CANCELLED":
                        self.logger.error("Job was cancelled")
                        return RunPodResult.error("Voice cloning was cancelled")
                    elif status == "IN_QUEUE" and elapsed_time > 60:
                        self.logger.warning(f"Job has been in queue for {elapsed_time:.1f} seconds - endpoint may be overloaded or down")
                    
                except requests.Timeout:
                    consecutive_timeouts += 1
                    self.logger.warning(f"Timeout while checking job status ({consecutive_timeouts}/{max_consecutive_timeouts})")
                    if consecutive_timeouts >= max_consecutive_timeouts:
                        self.logger.error("Too many consecutive timeouts - endpoint appears to be down")
                        return RunPodResult.error("RunPod endpoint is not responding. Please check if the endpoint is running in your RunPod console.")
                except requests.RequestException as e:
                    self.logger.error(f"Error checking job status: {str(e)}")
                    if "404" in str(e):
                        return RunPodResult.error("RunPod endpoint not found. Please check your endpoint ID in the RunPod console.")
                    return RunPodResult.error(f"Error checking job status: {str(e)}")
                
                time.sleep(poll_interval)
                
        except Exception as e:
            self.logger.error(f"Unexpected error during voice cloning: {str(e)}", exc_info=True)
            return RunPodResult.error(f"Unexpected error: {str(e)}")
    
    def generate_speech(
        self,
        text: str,
        voice_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> RunPodResult:
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
            RunPodResult: Result with success status and message
        """
        try:
            # Prepare request data
            input_data: Dict[str, Any] = {
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
                error_msg = str(data["error"])
                return RunPodResult.error(error_msg)
            
            task_id = data.get("id")
            if not task_id:
                return RunPodResult.error("Invalid response format")
            
            # Poll for completion
            start_time = time.time()
            max_wait_time = 300  # 5 minutes timeout
            poll_interval = 2  # Check every 2 seconds
            
            while True:
                if time.time() - start_time > max_wait_time:
                    return RunPodResult.error("TTS generation timed out")
                
                try:
                    status_response = requests.get(
                        f"{self.base_url}/status/{task_id}",
                        headers=self.headers,
                        timeout=10
                    )
                    status_response.raise_for_status()
                    status_data: Dict[str, Any] = status_response.json()
                    
                    if "error" in status_data:
                        error_msg = str(status_data["error"])
                        return RunPodResult.error(error_msg)
                    
                    status = status_data.get("status")
                    if status == "COMPLETED":
                        return RunPodResult.success("TTS generation completed")
                    elif status == "FAILED":
                        error_msg = status_data.get("error", "Unknown error")
                        return RunPodResult.error(f"TTS generation failed: {error_msg}")
                    elif status == "CANCELLED":
                        return RunPodResult.error("TTS generation was cancelled")
                    
                except requests.RequestException as e:
                    return RunPodResult.error(f"Error checking status: {str(e)}")
                
                time.sleep(poll_interval)
                
        except Exception as e:
            return RunPodResult.error(f"Unexpected error: {str(e)}")

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a RunPod job."""
        response = requests.get(
            f"{self.base_url}/status/{task_id}",
            headers=self.headers
        )
        return response.json()

    def generate_tts(
        self,
        text: str,
        voice_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[bytes], str]:
        """Generate TTS audio using RunPod endpoint - backward compatibility method.
        
        Returns:
            Tuple: (audio_data, error_message)
        """
        try:
            # Prepare request data
            input_data: Dict[str, Any] = {
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
            
            task_id = data.get("id")
            if not task_id:
                return None, "Invalid response format"
            
            # Poll for completion
            start_time = time.time()
            max_wait_time = 300  # 5 minutes timeout
            poll_interval = 2  # Check every 2 seconds
            
            while True:
                if time.time() - start_time > max_wait_time:
                    return None, "TTS generation timed out"
                
                try:
                    status_response = requests.get(
                    f"{self.base_url}/status/{task_id}",
                    headers=self.headers,
                    timeout=10
                    )
                    status_response.raise_for_status()
                    status_data: Dict[str, Any] = status_response.json()
                    
                    if "error" in status_data:
                        return None, str(status_data["error"])
                    
                    status = status_data.get("status")
                    if status == "COMPLETED":
                        # Get audio data from output
                        output = status_data.get("output", {})
                        if "audio_data" in output:
                            try:
                                audio_data = base64.b64decode(output["audio_data"])
                                return audio_data, ""
                            except Exception as e:
                                return None, f"Failed to decode audio data: {str(e)}"
                        else:
                            return None, "No audio data in response"
                    elif status == "FAILED":
                        error_msg = status_data.get("error", "Unknown error")
                        return None, f"TTS generation failed: {error_msg}"
                    elif status == "CANCELLED":
                        return None, "TTS generation was cancelled"
                    
                except requests.RequestException as e:
                    return None, f"Error checking status: {str(e)}"
                
                time.sleep(poll_interval)
                
        except Exception as e:
            return None, f"Error generating TTS: {str(e)}"

    def convert_voice(
        self,
        source_audio_path: str,
        target_voice_name: str,
        output_name: str
    ) -> Tuple[Optional[bytes], str]:
        """Convert source audio to target voice using RunPod's ChatterboxVC.
        
        Args:
            source_audio_path: Path to source audio file to convert
            target_voice_name: Name of target voice in voice library
            output_name: Name for the output file
            
        Returns:
            Tuple: (audio_data, error_message)
        """
        self.logger.info(f"Starting voice conversion: {source_audio_path} -> {target_voice_name}")
        
        try:
            # Read and encode source audio file
            self.logger.debug("Reading source audio file...")
            with open(source_audio_path, 'rb') as f:
                source_audio_data = f.read()
            source_audio_b64 = base64.b64encode(source_audio_data).decode()
            self.logger.debug("Source audio file encoded successfully")
            
            # Create input data for voice conversion
            input_data: Dict[str, Any] = {
                "type": "voice_convert",
                "source_audio": source_audio_b64,
                "target_voice_name": target_voice_name,
                "output_name": output_name
            }
            
            # Submit job with timeout
            self.logger.info("Submitting voice conversion job to RunPod...")
            try:
                response = requests.post(
                    f"{self.base_url}/run",
                    headers=self.headers,
                    json={"input": input_data},
                    timeout=30
                )
                response.raise_for_status()
            except requests.Timeout:
                self.logger.error("Timeout while submitting voice conversion job")
                return None, "Timeout while submitting job to RunPod"
            except requests.RequestException as e:
                self.logger.error(f"Error submitting voice conversion job: {str(e)}")
                return None, f"Error submitting job: {str(e)}"
            
            # Parse response
            response_data = response.json()
            
            # Check for errors
            if "error" in response_data:
                error_msg = str(response_data["error"])
                self.logger.error(f"Error in RunPod response: {error_msg}")
                return None, error_msg
            
            # Get task ID
            task_id = response_data.get("id")
            if not task_id:
                self.logger.error("No job ID in response")
                return None, "Invalid response format"
                
            self.logger.info(f"Voice conversion job submitted. Task ID: {task_id}")
            
            # Poll for completion with timeout
            start_time = time.time()
            max_wait_time = 600  # 10 minutes timeout for voice conversion
            poll_interval = 5  # Check every 5 seconds
            
            while True:
                if time.time() - start_time > max_wait_time:
                    self.logger.error("Timeout waiting for voice conversion to complete")
                    return None, "Voice conversion timed out after 10 minutes"
                
                try:
                    status_response = requests.get(
                        f"{self.base_url}/status/{task_id}",
                        headers=self.headers,
                        timeout=10
                    )
                    status_response.raise_for_status()
                    
                    # Parse status response
                    status_data: Dict[str, Any] = status_response.json()
                    
                    # Check for errors
                    if "error" in status_data:
                        error_msg = str(status_data["error"])
                        self.logger.error(f"Error in job status: {error_msg}")
                        return None, error_msg
                    
                    # Check status
                    status = status_data.get("status")
                    self.logger.debug(f"Current status: {status}")
                    
                    if status == "COMPLETED":
                        self.logger.info("Voice conversion completed successfully")
                        # Get audio data from output
                        output = status_data.get("output", {})
                        if "audio_data" in output:
                            try:
                                audio_data = base64.b64decode(output["audio_data"])
                                return audio_data, ""
                            except Exception as e:
                                return None, f"Failed to decode audio data: {str(e)}"
                        else:
                            return None, "No audio data in response"
                    elif status == "FAILED":
                        error_msg = status_data.get("error", "Unknown error")
                        self.logger.error(f"Job failed: {error_msg}")
                        return None, f"Voice conversion failed: {error_msg}"
                    elif status == "CANCELLED":
                        self.logger.error("Job was cancelled")
                        return None, "Voice conversion was cancelled"
                    
                except requests.Timeout:
                    self.logger.warning("Timeout while checking job status, will retry")
                except requests.RequestException as e:
                    self.logger.error(f"Error checking job status: {str(e)}")
                    return None, f"Error checking job status: {str(e)}"
                
                time.sleep(poll_interval)
            
        except Exception as e:
            self.logger.error(f"Unexpected error during voice conversion: {str(e)}", exc_info=True)
            return None, f"Unexpected error: {str(e)}"

 