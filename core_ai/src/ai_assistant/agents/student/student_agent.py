import os
import chromadb
from typing import Dict, Any, List

from ...models import Task, TaskResult
from ..base_agent import BaseAgent

class StudentAgent(BaseAgent):
    """
    Handles educational tasks using RAG on local folders.
    """
    
    def __init__(self, agent_id: str = "student_01", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Student Agent"
        self.description = "Helps with studying by reading your notes/folders using RAG."
        self.capabilities = ["study_folder", "answer_exam_questions"]
        
        # Setup RAG storage
        self.persist_directory = os.path.join(os.getcwd(), "data", "rag_db")
        os.makedirs(self.persist_directory, exist_ok=True)
        self.vector_store = None
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task is educational/folder RAG"""
        keywords = ["study", "exam", "prepare", "folder", "notes", "read my", "retrieve", "rag"]
        return any(kw in task.description.lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute student RAG tasks"""
        description = task.description.lower()
        
        if "folder" in description or "prepare" in description or "read" in description:
            return await self._ingest_folder(task)
            
        return await self._answer_question(task)

    async def _ingest_folder(self, task: Task) -> TaskResult:
        """Read a folder and create VectorDB"""
        try:
            from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            except ImportError:
                from langchain.text_splitter import RecursiveCharacterTextSplitter
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain_community.vectorstores import Chroma
        except ImportError as e:
            return TaskResult(success=False, error=f"Missing RAG dependency: {e}")
            
        folder_path = task.params.get("path")
        if not folder_path or not os.path.exists(folder_path):
             import re
             paths = re.findall(r'([A-Za-z]:\\[^ \n]+|/[^ \n]+)', task.description)
             if paths and os.path.exists(paths[0]):
                 folder_path = paths[0]
             else:
                 return TaskResult(success=False, error="Please provide a valid folder path. (e.g. D:\\MyNotes)")
             
        print(f"[{self.name}] 📚 Ingesting folder for exam prep: {folder_path}...")
        
        try:
            pdf_loader = DirectoryLoader(folder_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
            txt_loader = DirectoryLoader(folder_path, glob="**/*.txt", loader_cls=TextLoader)
            
            docs = []
            docs.extend(pdf_loader.load())
            docs.extend(txt_loader.load())
            
            if not docs:
                return TaskResult(success=False, error="No PDF or TXT files found in the folder.")
                
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            splits = text_splitter.split_documents(docs)
            
            print(f"[{self.name}] 🧠 Creating Vector embeddings for {len(splits)} chunks using ChromaDB...")
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            self.vector_store = Chroma.from_documents(
                documents=splits, 
                embedding=embeddings, 
                persist_directory=self.persist_directory
            )
            self.vector_store.persist()
            
            return TaskResult(
                success=True,
                data={"message": f"Successfully read {len(docs)} files and learned the content. Ask me exam questions now!"}
            )
        except Exception as e:
            return TaskResult(success=False, error=f"Failed to read folder: {e}")

    async def _answer_question(self, task: Task) -> TaskResult:
        """Answer question using RAG"""
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain_community.vectorstores import Chroma
            from ai_assistant.ai.gguf_model_manager import GGUFModelManager
        except ImportError as e:
            return TaskResult(success=False, error=f"Missing dependency: {e}")
            
        if not self.vector_store:
            if os.path.exists(self.persist_directory):
                embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                self.vector_store = Chroma(persist_directory=self.persist_directory, embedding_function=embeddings)
            else:
                return TaskResult(success=False, error="I haven't read any folders yet. Please tell me to read a folder first.")
                
        question = task.params.get("query", task.description)
        
        print(f"[{self.name}] 🔍 Searching notes for: {question}...")
        docs = self.vector_store.similarity_search(question, k=3)
        
        context = "\n\n".join([doc.page_content for doc in docs])
        sources = [doc.metadata.get('source', 'Unknown') for doc in docs]
        
        prompt = f"<|start_header_id|>system<|end_header_id|>\nYou are a helpful AI tutor preparing the user for an exam.\nUse the following notes from the user's folder to answer the question. If the answer is not in the notes, say so.\n\nNOTES CONTEXT:\n{context}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
        
        print(f"[{self.name}] 🤖 Generating answer via Local Llama Model...")
        model_manager = GGUFModelManager()
        llm = model_manager.get_model()
        
        response = llm(prompt, max_tokens=500, stop=['<|eot_id|>'], echo=False)
        answer = response['choices'][0]['text'].strip()
        
        return TaskResult(
            success=True,
            data={"answer": answer, "sources": sources}
        )