from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import runpod
import base64
from pydantic import BaseModel
from typing import Optional
import os

# Initialize RunPod client
def init_runpod():
    """Initialize RunPod client with credentials"""
    api_key = os.environ.get("RUNPOD_API_KEY")
    endpoint_id = os.environ.get("ENDPOINT_ID")
    
    if not api_key or not endpoint_id:
        raise ValueError(
            "Please set RUNPOD_API_KEY and ENDPOINT_ID environment variables"
        )
    
    runpod.api_key = api_key
    return endpoint_id

try:
    ENDPOINT_ID = init_runpod()
except ValueError as e:
    print(f"Error initializing RunPod client: {str(e)}")
    raise

app = FastAPI(title="Chatterbox TTS API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TTSRequest(BaseModel):
    text: str
    voice_name: Optional[str] = None
    exaggeration: Optional[float] = 0.5
    cfg_weight: Optional[float] = 0.5

class VoiceCloneRequest(BaseModel):
    voice_name: str
    description: Optional[str] = None

@app.post("/api/tts/generate")
async def generate_tts(request: TTSRequest):
    """Generate TTS from text and return audio data"""
    try:
        response = runpod.run(
            endpoint_id=ENDPOINT_ID,
            input={
                "type": "tts",
                "text": request.text,
                "voice_name": request.voice_name,
                "exaggeration": request.exaggeration,
                "cfg_weight": request.cfg_weight
            }
        )
        
        if "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
            
        if "audio_data" not in response:
            raise HTTPException(status_code=500, detail="No audio data in response")
            
        # Decode base64 audio data
        try:
            audio_data = base64.b64decode(response["audio_data"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Invalid audio data: {str(e)}")
        
        # Return audio file directly
        return Response(
            content=audio_data,
            media_type=response.get("content_type", "audio/wav"),
            headers={
                "Content-Disposition": f'attachment; filename="audio.wav"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/clone")
async def clone_voice(request: VoiceCloneRequest, audio_file: UploadFile = File(...)):
    """Clone a voice from reference audio"""
    try:
        # Validate audio file
        if not audio_file.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=400,
                detail="File must be an audio file"
            )
        
        # Read and encode audio file
        try:
            audio_data = await audio_file.read()
            audio_base64 = base64.b64encode(audio_data).decode()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error reading audio file: {str(e)}"
            )
        
        response = runpod.run(
            endpoint_id=ENDPOINT_ID,
            input={
                "type": "clone",
                "reference_audio": audio_base64,
                "voice_name": request.voice_name,
                "description": request.description
            }
        )
        
        if "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
            
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Check if the API is running and RunPod is configured"""
    return {
        "status": "healthy",
        "runpod_configured": bool(ENDPOINT_ID)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 