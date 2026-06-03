import streamlit as st
import os
from rag import RAGManager
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Lumiere AI Assistant", page_icon="✨", layout="centered")

# Load CSS
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("✨ Lumiere AI Assistant")

@st.cache_resource
def get_rag_manager():
    if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your_google_api_key_here":
        st.error("Missing or invalid GOOGLE_API_KEY environment variable. Please check your .env file.")
        st.stop()
    
    manager = RAGManager(data_dir="data")
    with st.spinner("Initializing Knowledge Base..."):
        try:
            manager.initialize()
        except Exception as e:
            st.error(f"Failed to initialize RAG system: {str(e)}")
            st.stop()
    return manager

# Initialize system
manager = get_rag_manager()

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add a greeting message
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I'm the Lumiere AI Assistant. I can answer questions about our company policies, products, and roadmap. How can I help you today?"})

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about Lumiere..."):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get bot response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Pass the previous messages as chat history
            history = st.session_state.messages[:-1]
            response = manager.get_answer(prompt, chat_history=history)
        st.markdown(response)
    
    # Append assistant message
    st.session_state.messages.append({"role": "assistant", "content": response})
