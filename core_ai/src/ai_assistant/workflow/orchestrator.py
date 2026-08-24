from typing import Dict, Any, List
from ..agents.models import Task, TaskResult
from ..agents.registry import AgentRegistry

class WorkflowOrchestrator:
    """
    Manages high-level workflows that require coordination between multiple agents.
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        
    async def run_video_pipeline(self, topic: str) -> Dict[str, Any]:
        """
        Executes a full video production pipeline:
        1. Research Topic
        2. Write Script
        3. Generate Assets (Audio/Image)
        4. (Optional) Create Video
        """
        print(f"🎬 [Orchestrator] Starting Video Pipeline for: {topic}")
        pipeline_results = {}
        
        # 1. Research
        research_task = Task(description=f"Research key facts about: {topic}")
        research_agent = await self.registry.find_best_agent(research_task)
        if not research_agent:
            return {"error": "No Research Agent found"}
            
        print(f"   -> Delegating to {research_agent.name}...")
        res_research = await research_agent.execute(research_task)
        if not res_research.success:
            return {"error": f"Research failed: {res_research.error}"}
        pipeline_results["research"] = res_research.data
        
        # 2. Write Script
        # Pass research findings to writer
        context = res_research.data.get("summary", "No summary found")
        script_task = Task(
            description=f"Write a short video script about {topic} based on this context: {context[:200]}...",
            params={"tone": "engaging"}
        )
        writer_agent = await self.registry.find_best_agent(script_task)
        if not writer_agent:
             return {"error": "No Writer Agent found"}
             
        print(f"   -> Delegating to {writer_agent.name}...")
        res_script = await writer_agent.execute(script_task)
        if not res_script.success:
            return {"error": f"Script writing failed: {res_script.error}"}
        pipeline_results["script"] = res_script.data
        
        # 3. Creative Assets
        # a. Voiceover
        audio_task = Task(description="Generate voiceover for the script", params={"content": str(res_script.data)})
        creative_agent = await self.registry.find_best_agent(audio_task)
        
        if creative_agent:
            print(f"   -> Delegating Audio to {creative_agent.name}...")
            res_audio = await creative_agent.execute(audio_task)
            pipeline_results["audio"] = res_audio.data if res_audio.success else "Failed"
            
            # b. Thumbnail
            image_task = Task(description=f"Create a thumbnail for video about {topic}")
            print(f"   -> Delegating Image to {creative_agent.name}...")
            res_image = await creative_agent.execute(image_task)
            pipeline_results["image"] = res_image.data if res_image.success else "Failed"
            
        logger.info("✅ [Orchestrator] Pipeline Completed!")
        return pipeline_results