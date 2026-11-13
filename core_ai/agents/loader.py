import logging
import threading
from typing import Optional

from .registry import AgentMetadata, AgentRegistry

logger = logging.getLogger(__name__)

_global_registry_lock = threading.RLock()
_global_registry: Optional[AgentRegistry] = None


def get_global_registry(eager: bool = False) -> AgentRegistry:
    """Return the process-wide singleton AgentRegistry populated with definitions."""
    global _global_registry
    with _global_registry_lock:
        if _global_registry is None:
            _global_registry = AgentLoader.load_all_agents(eager=eager)
        elif eager:
            for meta in _global_registry.get_all_metadata():
                _global_registry.get_agent(meta.agent_id)
        return _global_registry


class AgentLoader:
    """Helper to register and load all agents into an AgentRegistry."""

    @staticmethod
    def register_agent_definitions(registry: AgentRegistry) -> None:
        """Register all 14 agent definitions (metadata + lazy factory) without instantiating."""

        # 1. Productivity Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="productivity-001",
                name="Productivity Agent",
                description="Handles Word, Excel, PowerPoint, PDF creation and format conversion",
                category="productivity",
                capabilities=[
                    "create_word_document",
                    "create_excel_spreadsheet",
                    "create_powerpoint",
                    "create_pdf",
                    "edit_document",
                    "convert_formats",
                ],
                keywords=[
                    "word", "docx", "excel", "xlsx", "spreadsheet", "powerpoint",
                    "pptx", "slides", "presentation", "pdf", "document", "report",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_productivity(),
        )

        # 2. Research Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="research-001",
                name="Research Agent",
                description="Performs web searches, Wikipedia lookups, scraping, and info gathering",
                category="research",
                capabilities=[
                    "web_search",
                    "wikipedia_summary",
                    "scrape_url",
                    "research_topic",
                ],
                keywords=[
                    "research", "search", "wikipedia", "lookup", "scrape",
                    "find", "investigate", "google", "facts",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_research(),
        )

        # 3. Writer Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="writer-001",
                name="Writer Agent",
                description="Generates high-quality text content, articles, emails, and summaries",
                category="writer",
                capabilities=[
                    "write_article",
                    "summarize_text",
                    "draft_email",
                    "proofread",
                    "creative_writing",
                ],
                keywords=[
                    "write", "draft", "essay", "article", "blog", "summarize",
                    "summary", "proofread", "script", "content",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_writer(),
        )

        # 4. Video Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="video-001",
                name="Video Agent",
                description="Handles video editing, transcription, audio extraction, and GUI app control",
                category="video",
                capabilities=[
                    "create_video",
                    "edit_video",
                    "transcribe_video",
                    "extract_audio",
                    "create_thumbnail",
                    "add_subtitles",
                    "control_external_app",
                ],
                keywords=[
                    "video", "movie", "clip", "trim", "cut", "transcribe",
                    "subtitle", "caption", "premiere", "davinci", "filmora", "capcut",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_video(),
        )

        # 5. Creative Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="creative-001",
                name="Creative Agent",
                description="Generates images, banners, layouts, and voiceover audio assets",
                category="creative",
                capabilities=[
                    "generate_image",
                    "create_art",
                    "design_layout",
                    "image_editing",
                    "generate_voiceover",
                ],
                keywords=[
                    "image", "art", "picture", "thumbnail", "photo", "logo",
                    "banner", "poster", "voiceover", "narrate", "tts", "design",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_creative(),
        )

        # 6. Data Analyst Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="data-001",
                name="Data Analyst Agent",
                description="Analyzes datasets, creates charts/visualizations, and computes statistics",
                category="data",
                capabilities=[
                    "analyze_data",
                    "visualize_data",
                    "create_chart",
                    "statistical_analysis",
                ],
                keywords=[
                    "chart", "graph", "plot", "bar", "line", "pie", "scatter",
                    "analyze", "data", "statistics", "metrics", "visualize", "csv",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_data(),
        )

        # 7. Database Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="database-001",
                name="Database Agent",
                description="Manages SQLite/SQL databases, inspects schemas, and executes queries",
                category="data",
                capabilities=[
                    "query_database",
                    "manage_schema",
                    "optimize_query",
                    "db_migration",
                    "sql_analysis",
                ],
                keywords=[
                    "sql", "database", "sqlite", "query", "schema", "table", "db", "migration",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_database(),
        )

        # 8. Communication Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="comm-001",
                name="Communication Agent",
                description="Handles emails, messaging, and calendar scheduling",
                category="communication",
                capabilities=[
                    "send_email",
                    "send_message",
                    "schedule_meeting",
                    "manage_calendar",
                    "post_social",
                ],
                keywords=[
                    "email", "gmail", "send", "message", "whatsapp",
                    "calendar", "meeting", "schedule",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_communication(),
        )

        # 9. Web Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="web-001",
                name="Web Agent",
                description="Browses web pages, monitors sites, and automates browser interactions",
                category="web",
                capabilities=[
                    "browse_web",
                    "interact_page",
                    "fill_form",
                    "monitor_site",
                    "scrape_dynamic",
                ],
                keywords=[
                    "browser", "website", "browse", "fill", "form",
                    "click", "selenium", "monitor", "webpage",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_web(),
        )

        # 10. Student Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="student-001",
                name="Student Agent",
                description="Supports studying, math solving, flashcards, and RAG over local notes",
                category="education",
                capabilities=[
                    "learn_topic",
                    "take_notes",
                    "summarize_learning",
                    "create_flashcards",
                    "study_folder",
                    "answer_exam_questions",
                    "solve_math",
                ],
                keywords=[
                    "study", "exam", "homework", "notes", "flashcard",
                    "quiz", "equation", "solve", "math", "rag", "tutor",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_student(),
        )

        # 11. File Manager Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="file-001",
                name="File Manager Agent",
                description="Organizes, searches, renames, moves, and backs up local files",
                category="file",
                capabilities=[
                    "organize_files",
                    "search_files",
                    "move_files",
                    "backup_files",
                    "rename_files",
                    "list_files",
                ],
                keywords=[
                    "file", "folder", "directory", "organize", "rename",
                    "move", "copy", "backup", "cleanup", "list files",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_file(),
        )

        # 12. Audio Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="audio-001",
                name="Audio Agent",
                description="Synthesizes speech, transcribes audio, cleans noise, and generates audio",
                category="audio",
                capabilities=[
                    "transcribe_audio",
                    "synthesize_speech",
                    "text_to_speech",
                    "edit_audio",
                    "audio_processing",
                    "generate_music",
                    "generate_sfx",
                    "clean_audio",
                ],
                keywords=[
                    "music", "song", "sfx", "sound effect", "clean audio",
                    "remove noise", "transcribe audio", "synthesize", "speech", "audio",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_audio(),
        )

        # 13. Deep Research Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="deep-research-001",
                name="Deep Research Agent",
                description="Performs multi-query deep research, scraping, and LLM report synthesis",
                category="research",
                capabilities=[
                    "deep_research",
                    "social_synthesis",
                    "multi_source_scrape",
                ],
                keywords=[
                    "deep research", "comprehensive analysis", "market research",
                    "synthesize", "in-depth", "multi-source",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_deep_research(),
        )

        # 14. Autonomous Learning Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="autonomous-001",
                name="Autonomous Learning Agent",
                description="Observes interactions and persists knowledge and user preferences",
                category="core",
                capabilities=[
                    "memory_persistence",
                    "behavior_learning",
                    "skill_generation",
                    "reflection",
                ],
                keywords=[
                    "remember", "learn", "reflect", "what did i say",
                    "my preferences", "save this", "memory",
                ],
                status="standby",
            ),
            factory=lambda: AgentLoader._load_autonomous(),
        )

        logger.info("Registered 14 Agent Definitions (Lazy Load)")

    @staticmethod
    def load_all_agents(
        registry: Optional[AgentRegistry] = None,
        eager: bool = False,
    ) -> AgentRegistry:
        """Create or populate an AgentRegistry with all 14 agent definitions."""
        reg = registry or AgentRegistry()
        AgentLoader.register_agent_definitions(reg)
        if eager:
            for meta in reg.get_all_metadata():
                reg.get_agent(meta.agent_id)
        return reg

    # --- Lazy Factories ---

    @staticmethod
    def _load_productivity():
        from .productivity.productivity_agent import ProductivityAgent
        return ProductivityAgent(agent_id="productivity-001")

    @staticmethod
    def _load_research():
        from .research.research_agent import ResearchAgent
        return ResearchAgent(agent_id="research-001")

    @staticmethod
    def _load_writer():
        from .writer.writer_agent import WriterAgent
        return WriterAgent(agent_id="writer-001")

    @staticmethod
    def _load_video():
        from .video.video_agent import VideoAgent
        return VideoAgent(agent_id="video-001")

    @staticmethod
    def _load_creative():
        from .creative.creative_agent import CreativeAgent
        return CreativeAgent(agent_id="creative-001")

    @staticmethod
    def _load_data():
        from .data.data_analyst_agent import DataAnalystAgent
        return DataAnalystAgent(agent_id="data-001")

    @staticmethod
    def _load_database():
        from .data.database_agent import DatabaseAgent
        return DatabaseAgent(agent_id="database-001")

    @staticmethod
    def _load_communication():
        from .communication.communication_agent import CommunicationAgent
        return CommunicationAgent(agent_id="comm-001")

    @staticmethod
    def _load_web():
        from .web.web_agent import WebAgent
        return WebAgent(agent_id="web-001")

    @staticmethod
    def _load_student():
        from .student.student_agent import StudentAgent
        return StudentAgent(agent_id="student-001")

    @staticmethod
    def _load_file():
        from .file.file_manager_agent import FileManagerAgent
        return FileManagerAgent(agent_id="file-001")

    @staticmethod
    def _load_audio():
        from .audio.audio_agent import AudioAgent
        return AudioAgent(agent_id="audio-001")

    @staticmethod
    def _load_deep_research():
        from .research.deep_research_agent import DeepResearchAgent
        return DeepResearchAgent(agent_id="deep-research-001")

    @staticmethod
    def _load_autonomous():
        from .core.autonomous_agent import AutonomousAgent
        return AutonomousAgent(agent_id="autonomous-001")
