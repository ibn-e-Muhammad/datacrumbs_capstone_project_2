# Lumiere AI Assistant - Development Report

## Overview
Lumiere AI Assistant is a Retrieval-Augmented Generation (RAG) chatbot designed to answer internal questions securely based on the company's local data files. It provides a premium, aesthetic chat interface using Streamlit, supported by a sophisticated LangChain processing pipeline.

## Architectural Decisions & Development Steps

### 1. The Tech Stack
- **Web UI: Streamlit**
  *Why:* Streamlit allows for rapid prototyping of data applications in pure Python. It natively handles state management, caching, and chat interfaces (`st.chat_message`, `st.chat_input`), making it the ideal framework for deploying a chat application quickly without writing complex frontend code.
- **RAG Framework: LangChain**
  *Why:* LangChain provides modular building blocks (Loaders, Splitters, Chains) that drastically reduce the boilerplate needed to implement chunking, embedding, and LLM querying.
- **Vector Database: FAISS**
  *Why:* Since our data files (`company_info.txt`, `products.xlsx`) are static and loaded locally on startup, FAISS (Facebook AI Similarity Search) is the perfect choice. It operates entirely in memory, meaning we do not have to provision or pay for an external cloud database like Pinecone.

### 2. Migration from OpenAI to Google AI Studio
- **Initial Plan:** We originally designed the system around OpenAI's API using `gpt-4o-mini` and `text-embedding-3-small` due to their robustness. 
- **The Problem:** The free tier of OpenAI imposes a strict "zero-credit" barrier, immediately resulting in HTTP 429 RateLimitErrors.
- **The Solution:** We migrated the pipeline to **Google AI Studio** using `langchain-google-genai`.
  - **Models Chosen:** `gemini-3.1-flash-lite` for LLM generation and `models/embedding-002` for embeddings. These provide an excellent balance of speed and contextual understanding while keeping token limits in check (~200k tokens).

### 3. Rate Limiting Strategy
- **Constraint:** The free tier of Google AI Studio has specific limits. We needed to ensure we do not exceed **6 requests per minute for the LLM** and **70 requests per minute for the Embeddings**.
- **Implementation:** 
  - We engineered a thread-safe `RateLimiter` class in `rag.py`. 
  - Before making any call to the Embedding model or the Chat model, the system calculates the time elapsed since the last call. 
  - If the rate exceeds the threshold (e.g., trying to call the LLM faster than every 10 seconds), the system intelligently pauses execution using `time.sleep()`. 
  - This absolutely guarantees we will never hit a 429 RateLimitError, prioritizing stability over speed.

### 4. Contextual Chat History
- To make the assistant feel natural and capable of follow-up questions, we implemented conversational memory.
- Rather than using a complex two-step ConversationalRetrievalChain (which would consume 2 LLM requests per query and severely cripple our 6 RPM limit), we format the last 6 messages (3 interactions) and inject them directly into the system prompt.
- This provides the LLM with immediate context while preserving API requests and adhering strictly to rate limits.

### 5. Data Processing & Chunking
- **Loaders:** We used LangChain's `TextLoader` for unstructured text and `UnstructuredExcelLoader` for our Excel product database.
- **Chunking Strategy:** Documents are split using `RecursiveCharacterTextSplitter` with `chunk_size=500` and `chunk_overlap=50`. This smaller chunk size was explicitly chosen to:
  1. Retrieve highly focused context snippets.
  2. Prevent overflowing the prompt context window and unnecessarily consuming the 200k token limit.

### 5. UI/UX Aesthetics
- **Design System:** The app features a custom CSS file (`style.css`) that overrides Streamlit's default components.
- **Color Palette:** A premium combination of **Light Cream Red** (`#E6B8B8`) and **Warm Off-White** (`#FAFAF8`).
- **Experience:** Hover animations on chat bubbles, custom rounded inputs, and hidden default branding create a polished, production-ready feel rather than a generic template.

### 6. Error Handling
- The pipeline is surrounded by `try/except` blocks. If files are missing, the UI gracefully informs the user rather than crashing. 
- The system prompt strictly enforces hallucination prevention: if the answer isn't in the retrieved chunks, the LLM will explicitly respond with "I don't know."

---

## Setup Instructions

1. Ensure Python 3.9+ is installed.
2. Install dependencies:
   ```bash
   pip install streamlit langchain langchain-google-genai langchain-community faiss-cpu unstructured openpyxl python-dotenv
   ```
3. Insert your API Key:
   Create a `.env` file at the root of the project with:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```
