from typing import List
from .registry import AgentRegistry, AgentMetadata

class AgentLoader:
    """
    Helper to load agents into the registry using Lazy Loading
    """
    
    @staticmethod
    def register_agent_definitions(registry: AgentRegistry):
        """Register agent definitions (metadata + lazy factory) without instantiating"""
        
        # 1. Productivity Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="productivity-001",
                name="Productivity Agent",
                description="Handles Word, Excel, PowerPoint creation and editing",
                capabilities=["create_word_document", "create_excel_spreadsheet", "create_powerpoint", "edit_document", "convert_formats"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_productivity()
        )

        # 2. Research Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="research-001",
                name="Research Agent",
                description="Performs web searches, scraping, and information gathering",
                capabilities=["web_search", "wikipedia_summary", "scrape_url", "research_topic"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_research()
        )

        # 3. Writer Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="writer-001",
                name="Writer Agent",
                description="Generates high-quality text content, emails, and summaries",
                capabilities=["write_article", "summarize_text", "draft_email", "proofread", "creative_writing"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_writer()
        )

        # 4. Video Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="video-001",
                name="Video Agent",
                description="Handles video creation, editing, and processing",
                capabilities=["create_video", "edit_video", "add_subtitles", "process_video"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_video()
        )

        # 5. Creative Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="creative-001",
                name="Creative Agent",
                description="Generates images, art, and creative visual concepts",
                capabilities=["generate_image", "create_art", "design_layout", "image_editing"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_creative()
        )

        # 6. Data Analyst Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="data-001",
                name="Data Analyst Agent",
                description="Analyzes data, creates visualizations, and finds patterns",
                capabilities=["analyze_data", "visualize_data", "create_chart", "statistical_analysis"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_data()
        )

        # 7. Database Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="database-001",
                name="Database Agent",
                description="Manages SQL/NoSQL databases and executes queries",
                capabilities=["query_database", "manage_schema", "optimize_query", "db_migration"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_database()
        )

        # 8. Communication Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="comm-001",
                name="Communication Agent",
                description="Handles emails, messaging, and scheduling",
                capabilities=["send_email", "send_message", "schedule_meeting", "manage_calendar"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_communication()
        )

        # 9. Web Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="web-001",
                name="Web Agent",
                description="Browses the web, interacts with pages, and automates browser tasks",
                capabilities=["browse_web", "interact_page", "fill_form", "monitor_site"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_web()
        )

        # 10. Student (Learning) Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="student-001",
                name="Student Agent",
                description="Learns new topics and organizes knowledge",
                capabilities=["learn_topic", "take_notes", "summarize_learning", "create_flashcards"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_student()
        )

        # 11. File Manager Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="file-001",
                name="File Manager Agent",
                description="Organizes, searches, and manages local files",
                capabilities=["organize_files", "search_files", "move_files", "backup_files"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_file()
        )

        # 12. Audio Agent
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="audio-001",
                name="Audio Agent",
                description="Processes audio, transcribes speech, and synthesizes voice",
                capabilities=["transcribe_audio", "synthesize_speech", "edit_audio", "audio_processing"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_audio()
        )

        # 13. Deep Research Agent (last30days-skill replica)
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="deep-research-001",
                name="Deep Research Agent",
                description="Performs deep topic analysis, parallel search, and LLM synthesis",
                capabilities=["deep_research", "social_synthesis", "multi_source_scrape"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_deep_research()
        )

        # 14. Autonomous Learning Agent (hermes-agent replica)
        registry.register_agent_definition(
            AgentMetadata(
                agent_id="autonomous-001",
                name="Autonomous Learning Agent",
                description="Observes interactions and learns preferences to persist knowledge",
                capabilities=["memory_persistence", "behavior_learning", "skill_generation"],
                status="standby"
            ),
            factory=lambda: AgentLoader._load_autonomous()
        )

        print("✅ Registered 14 Agent Definitions (Lazy Load)")

    # --- Lazy Factories ---

    @staticmethod
    def _load_productivity():
        from .productivity.productivity_agent import ProductivityAgent
        return ProductivityAgent()

    @staticmethod
    def _load_research():
        from .research.research_agent import ResearchAgent
        return ResearchAgent()

    @staticmethod
    def _load_writer():
        from .writer.writer_agent import WriterAgent
        return WriterAgent()

    @staticmethod
    def _load_video():
        from .video.video_agent import VideoAgent
        return VideoAgent()

    @staticmethod
    def _load_creative():
        from .creative.creative_agent import CreativeAgent
        return CreativeAgent()

    @staticmethod
    def _load_data():
        from .data.data_analyst_agent import DataAnalystAgent
        return DataAnalystAgent()

    @staticmethod
    def _load_database():
        from .data.database_agent import DatabaseAgent
        return DatabaseAgent()

    @staticmethod
    def _load_communication():
        from .communication.communication_agent import CommunicationAgent
        return CommunicationAgent()

    @staticmethod
    def _load_web():
        from .web.web_agent import WebAgent
        return WebAgent()

    @staticmethod
    def _load_student():
        from .teacher.student_agent import StudentAgent
        return StudentAgent()

    @staticmethod
    def _load_file():
        from .file.file_manager_agent import FileManagerAgent
        return FileManagerAgent()

    @staticmethod
    def _load_audio():
        from .audio.audio_agent import AudioAgent
        return AudioAgent()

    @staticmethod
    def _load_deep_research():
        from .research.deep_research_agent import DeepResearchAgent
        return DeepResearchAgent()

    @staticmethod
    def _load_autonomous():
        from .core.autonomous_agent import AutonomousAgent
        return AutonomousAgent()
