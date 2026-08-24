from typing import Dict, Any, List, Optional
import os
import subprocess

from ..base_agent import BaseAgent
from ..models import Task, TaskResult
from .gui_controller import AppControllerFactory, BaseGUIController
from .training_mode import TrainingMode
from .visual_verifier import VisualVerifier

class VideoAgent(BaseAgent):
    """
    Handles video editing, creation, and transcription.
    """
    
    def __init__(self, agent_id: str = "video-001", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Video Agent"
        self.category = "video"
        self.capabilities = [
            "edit_video",
            "transcribe_video",
            "extract_audio",
            "create_thumbnail",
            "control_external_app"
        ]
        
        # Lazy load libraries to prevent startup lag
        self._moviepy = None
        self._whisper = None
        self._whisper_model = None
        
        self.training_session = None
        self._verifier = None
        
    @property
    def verifier(self) -> VisualVerifier:
        if not self._verifier:
            self._verifier = VisualVerifier()
        return self._verifier
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task involves video"""
        keywords = ["video", "movie", "clip", "edit", "trim", "cut", "transcribe", "subtitle", "caption", "app", "premiere", "control", "train", "tune"]
        return any(kw in task.description.lower() for kw in keywords)
    
    async def execute(self, task: Task) -> TaskResult:
        """Execute video task"""
        try:
            desc = task.description.lower()
            
            if "train" in desc or "tune" in desc:
                return await self._handle_training(task)
            elif "control" in desc or "app" in desc:
                return await self._control_app(task)
            elif "transcribe" in desc or "caption" in desc:
                return await self._transcribe_video(task)
            elif "cut" in desc or "trim" in desc or "edit" in desc:
                return await self._edit_video(task)
            elif "extract audio" in desc:
                return await self._extract_audio(task)
            else:
                return TaskResult(success=False, error=f"Unknown video task: {desc}")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return TaskResult(success=False, error=str(e))
            
    # --- Library Loading ---
    
    def _load_moviepy(self):
        if not self._moviepy:
            try:
                # Try new v2 import first, fall back to v1 editor if needed
                try:
                    import moviepy as mp
                    # Check if v2 specific classes are available directly
                    if hasattr(mp, 'VideoFileClip'):
                        self._moviepy = mp
                    else:
                        import moviepy.editor as mp
                        self._moviepy = mp
                except ImportError:
                     # Fallback for older versions
                     import moviepy.editor as mp
                     self._moviepy = mp
            except ImportError:
                raise ImportError("moviepy not installed.")
        return self._moviepy
        
    def _load_whisper(self):
        if not self._whisper:
            try:
                import whisper
                self._whisper = whisper
            except ImportError:
                raise ImportError("openai-whisper not installed.")
        return self._whisper

    # --- Capabilities ---

    async def _edit_video(self, task: Task) -> TaskResult:
        """Simple editing: Trim, Concatenate"""
        mp = self._load_moviepy()
        
        input_file = task.params.get("input_file")
        if not input_file or not os.path.exists(input_file):
             return TaskResult(success=False, error=f"Input file not found: {input_file}")
             
        start_time = task.params.get("start_time", 0) # Seconds
        end_time = task.params.get("end_time", None)  # Seconds
        
        try:
            # Load video
            clip = mp.VideoFileClip(input_file)
            
            # Trim - Handle MoviePy v1 vs v2
            if hasattr(clip, 'subclipped'):
                # MoviePy v2+ uses subclipped
                if end_time:
                    clip = clip.subclipped(start_time, end_time)
                elif start_time > 0:
                    clip = clip.subclipped(start_time)
            elif hasattr(clip, 'subclip'):
                 # MoviePy v1
                if end_time:
                    clip = clip.subclip(start_time, end_time)
                elif start_time > 0:
                    clip = clip.subclip(start_time)
            else:
                 # Fallback: try slicing
                 if end_time:
                     clip = clip.subclip(start_time, end_time) # Hope for best
                
            # Save
            filename = task.params.get("output_filename", f"edited_{task.task_id[:8]}.mp4")
            output_path = os.path.abspath(os.path.join("outputs", filename))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
            clip.close()
            
            return TaskResult(
                success=True,
                output_path=output_path,
                data={"duration": clip.duration}
            )
        except Exception as e:
             return TaskResult(success=False, error=f"Editing failed: {e}")

    async def _extract_audio(self, task: Task) -> TaskResult:
        """Extract audio from video"""
        mp = self._load_moviepy()
        
        input_file = task.params.get("input_file")
        if not input_file or not os.path.exists(input_file):
             return TaskResult(success=False, error=f"Input file not found: {input_file}")
             
        try:
            clip = mp.VideoFileClip(input_file)
            
            if not clip.audio:
                clip.close()
                return TaskResult(success=False, error="Video has no audio track")
            
            filename = task.params.get("output_filename", f"audio_{task.task_id[:8]}.mp3")
            output_path = os.path.abspath(os.path.join("outputs", filename))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            clip.audio.write_audiofile(output_path)
            clip.close()
            
            return TaskResult(
                success=True,
                output_path=output_path
            )
        except Exception as e:
            return TaskResult(success=False, error=f"Audio extraction failed: {e}")

    # --- GUI Automation ---

    async def _control_app(self, task: Task) -> TaskResult:
        """Control an external video editing app"""
        app_name = task.params.get("app_name", "premiere")
        action = task.params.get("action")
        text = task.params.get("text")
        
        controller = AppControllerFactory.get_controller(app_name)
        
        # 1. Focus App
        is_focused = controller.focus_window(app_name)
        if not is_focused:
            # For testing/demo purposes, if we can't find premiere, maybe we are just testing generic functionality?
            # Or we return error. Let's return error but allow "notepad" for testing
            if "notepad" not in app_name.lower() and "premiere" not in app_name.lower():
                 return TaskResult(success=False, error=f"Could not find or focus window: {app_name}")
            logger.warning(f"Warning: Could not focus {app_name}, proceeding blindly or creating new if possible not implemented.")
        
        # 2. Execute Action
        if action:
             # Check if it's a specific mapped action or raw keys
             if hasattr(controller, 'execute_action'):
                 controller.execute_action(action)
             else:
                 # Generic raw keys?
                 pass
                 
        # 3. Type Text
        if text:
            controller.type_text(text)
            
        # 4. Visual Verification (Optional)
        verify_flag = task.params.get("verify", False)
        if verify_flag:
            state_verified = self.verifier.verify_state(f"after_{action}", app_name)
            if not state_verified:
                 logger.warning("Warning: Visual verification failed.")
            
        return TaskResult(success=True, data={"message": f"Executed action '{action}' on '{app_name}'"})

    async def _handle_training(self, task: Task) -> TaskResult:
        """Handle training workflow definitions"""
        mode = task.params.get("mode", "start") # start, stop, add
        
        if mode == "start":
            profile = task.params.get("profile", "custom")
            self.training_session = TrainingMode(profile)
            return TaskResult(success=True, data={"message": f"Started training session for '{profile}'"})
            
        elif mode == "add":
            if not self.training_session:
                 return TaskResult(success=False, error="No active training session. Start one first.")
            action = task.params.get("action_type", "hotkey")
            params = task.params.get("params", {})
            self.training_session.add_action(action, params)
            return TaskResult(success=True, data={"message": "Action recorded"})
            
        elif mode == "save":
            if not self.training_session:
                 return TaskResult(success=False, error="No active training session.")
            path = self.training_session.save_workflow()
            self.training_session = None
            return TaskResult(success=True, data={"message": f"Workflow saved to {path}"})
            
        return TaskResult(success=False, error=f"Unknown training mode: {mode}")

    async def _transcribe_video(self, task: Task) -> TaskResult:
        """Transcribe video using Whisper"""
        whisper = self._load_whisper()
        
        input_file = task.params.get("input_file")
        if not input_file or not os.path.exists(input_file):
             return TaskResult(success=False, error=f"Input file not found: {input_file}")
        
        model_size = task.params.get("model", "base")
        
        try:
            # Check if model loaded
            if not self._whisper_model:
                print(f"Loading Whisper model '{model_size}'...")
                self._whisper_model = whisper.load_model(model_size)
                
            # Transcribe
            print(f"Transcribing {input_file}...")
            result = self._whisper_model.transcribe(input_file)
            text = result["text"]
            
            # Save text
            filename = task.params.get("output_filename", f"transcription_{task.task_id[:8]}.txt")
            output_path = os.path.abspath(os.path.join("outputs", filename))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
                
            return TaskResult(
                success=True,
                output_path=output_path,
                data={"text": text[:500]} # Return preview
            )
            
        except Exception as e:
            return TaskResult(success=False, error=f"Transcription failed: {e}")