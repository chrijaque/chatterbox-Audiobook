from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import runpod
import base64
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os

app = FastAPI(title="Chatterbox TTS API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RunPod
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID")

if not RUNPOD_API_KEY or not ENDPOINT_ID:
    raise ValueError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set")

# Set RunPod configuration
runpod.api_key = RUNPOD_API_KEY

# Create endpoint runner once
endpoint = runpod.Endpoint(str(ENDPOINT_ID))

class TTSRequest(BaseModel):
    text: str
    voice_name: Optional[str] = None

class VoiceCloneRequest(BaseModel):
    voice_name: str

@app.post("/api/tts/generate")
async def generate_tts(request: TTSRequest):
    """Generate TTS from text and return audio data"""
    try:
        # Run inference
        request_input: Dict[str, Any] = {
            "type": "tts",
            "text": request.text,
            "voice_name": request.voice_name
        }
        
        response = endpoint.run(request_input)
        result = response.output()
        
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])
            
        # Get audio data
        if not isinstance(result, dict):
            raise HTTPException(status_code=500, detail="Invalid response format")
            
        if "audio_url" in result:
            # Return URL for streaming
            return {"audio_url": result["audio_url"]}
        elif "audio_data" in result:
            # Return audio file directly
            audio_data = base64.b64decode(result["audio_data"])
            return Response(
                content=audio_data,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f'attachment; filename="audio.wav"'
                }
            )
        else:
            raise HTTPException(status_code=500, detail="No audio data in response")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/clone")
async def clone_voice(request: VoiceCloneRequest, audio_file: UploadFile = File(...)):
    """Clone a voice from reference audio"""
    try:
        # Read and encode audio file
        audio_data = await audio_file.read()
        audio_base64 = base64.b64encode(audio_data).decode()
        
        # Run inference
        request_input: Dict[str, Any] = {
            "type": "clone",
            "reference_audio": audio_base64,
            "voice_name": request.voice_name
        }
        
        response = endpoint.run(request_input)
        result = response.output()
        
        if isinstance(result, dict) and result.get("error"):
            raise HTTPException(status_code=500, detail=result["error"])
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 