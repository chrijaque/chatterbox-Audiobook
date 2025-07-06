from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import runpod
import base64
from pydantic import BaseModel
from typing import Optional
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
runpod.api_key = RUNPOD_API_KEY

class TTSRequest(BaseModel):
    text: str
    voice_name: Optional[str] = None

class VoiceCloneRequest(BaseModel):
    voice_name: str

@app.post("/api/tts/generate")
async def generate_tts(request: TTSRequest):
    """Generate TTS from text and return audio data"""
    try:
        response = runpod.run(
            endpoint_id=ENDPOINT_ID,
            input={
                "type": "tts",
                "text": request.text,
                "voice_name": request.voice_name
            }
        )
        
        if "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
            
        # Decode base64 audio data
        audio_data = base64.b64decode(response["audio_data"])
        
        # Return audio file directly
        return Response(
            content=audio_data,
            media_type=response["content_type"],
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
        # Read and encode audio file
        audio_data = await audio_file.read()
        audio_base64 = base64.b64encode(audio_data).decode()
        
        response = runpod.run(
            endpoint_id=ENDPOINT_ID,
            input={
                "type": "clone",
                "reference_audio": audio_base64,
                "voice_name": request.voice_name
            }
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 