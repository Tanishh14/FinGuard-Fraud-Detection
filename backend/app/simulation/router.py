from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, require_admin
import subprocess
import os

router = APIRouter()

@router.post("/start-story/{story_name}")
def start_fraud_story(
    story_name: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """
    Triggers the loading of a specific fraud story into the DB.
    """
    if story_name == "mumbai_ring":
        script_path = os.path.join(os.getcwd(), "backend", "scripts", "load_fraud_story.py")
        try:
            # Run the story loader script as a separate process
            subprocess.run(["python", script_path], check=True)
            return {"status": "success", "message": "Mumbai ATM Ring story loaded."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load story: {str(e)}")
    
    raise HTTPException(status_code=404, detail="Story not found")

@router.post("/play-step")
def play_simulation_step(
    admin=Depends(require_admin)
):
    """
    Placeholder for granular step-by-step playback logic.
    For MVP: Returns a success message.
    """
    return {"status": "success", "message": "Simulation step triggered."}

from pydantic import BaseModel
class SimulationStep(BaseModel):
    tx_id: int
    delay_ms: int
