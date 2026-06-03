import os
import time
from threading import Lock
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader, UnstructuredExcelLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RateLimiter:
    """A thread-safe rate limiter to enforce Requests Per Minute (RPM) limits."""
    def __init__(self, rpm: int):
        self.interval = 60.0 / rpm
        self.last_called = 0.0
        self.lock = Lock()
        
    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_called
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                logger.info(f"RateLimiter active: Sleeping for {sleep_time:.2f}s to respect RPM limit.")
                time.sleep(sleep_time)
            self.last_called = time.time()

class RAGManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        
        # Enforce exactly the user's constraints:
        # LLM: max 6 requests per minute
        # Embeddings: max 70 requests per minute
        self.llm_limiter = RateLimiter(rpm=6)
        self.embed_limiter = RateLimiter(rpm=70)
        
        # Using Gemini 3.1 Flash Lite as requested for LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite",
            temperature=0,
            max_retries=3
        )
        
        # Using Gemini Embedding 2 for embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-2"
        )
        
        self.vectorstore = None
        self.retriever = None

    def initialize(self):
        """Loads data, chunks, and initializes the vector store."""
        logger.info("Initializing RAG Pipeline with Google AI Studio...")
        data_path = Path(self.data_dir)
        if not data_path.exists() or not data_path.is_dir():
            raise FileNotFoundError(f"Data directory {self.data_dir} not found.")

        documents = []
        
        # Load files safely
        for file_path in data_path.iterdir():
            try:
                if file_path.suffix == '.txt':
                    loader = TextLoader(str(file_path), encoding='utf-8')
                    documents.extend(loader.load())
                    logger.info(f"Loaded {file_path.name}")
                elif file_path.suffix == '.xlsx':
                    loader = UnstructuredExcelLoader(str(file_path))
                    documents.extend(loader.load())
                    logger.info(f"Loaded {file_path.name}")
            except Exception as e:
                logger.error(f"Failed to load {file_path.name}: {e}")
                
        if not documents:
            raise ValueError("No valid documents found in data directory.")

        # Chunking: Keep chunks reasonable so we don't hit the 200k token limit easily
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Split documents into {len(chunks)} chunks.")

        # Rate limit before embedding initialization
        self.embed_limiter.wait()
        try:
            self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
            # Top-3 chunk retrieval
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
            logger.info("FAISS vector store initialized successfully with Gemini Embeddings.")
        except Exception as e:
            logger.error(f"Failed to create vector store: {e}")
            raise e

    def get_answer(self, query: str, chat_history: list = None) -> str:
        if not self.retriever:
            return "System is not properly initialized. Data missing."

        template = """You are a helpful company chatbot. Answer the question based ONLY on the following context.
If the answer is not contained in the context, you MUST say "I don't know". Do not try to make up an answer.

Context:
{context}

Recent Chat History:
{chat_history}

Question:
{question}

Answer:"""
        prompt = ChatPromptTemplate.from_template(template)

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        if chat_history is None:
            chat_history = []
            
        # Format the last 6 messages (3 interactions) to preserve token limits
        formatted_history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history[-6:]])

        rag_chain = (
            {
                "context": self.retriever | format_docs, 
                "question": RunnablePassthrough(),
                "chat_history": lambda x: formatted_history
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )

        try:
            # Enforce 6 RPM limit before invoking LLM
            # Note: embeddings happen during retrieval as well, so we should throttle that too
            self.embed_limiter.wait() # For the query embedding
            self.llm_limiter.wait()   # For the LLM generation
            
            return rag_chain.invoke(query)
        except Exception as e:
            logger.error(f"LLM chain failed: {e}")
            return "I'm sorry, I'm currently experiencing technical difficulties. Please try again later."
