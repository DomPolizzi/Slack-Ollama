import os
from typing import List, Union
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    DirectoryLoader,
    UnstructuredMarkdownLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langfuse.callback import CallbackHandler

from config import config

# Initialize Langfuse for observability
langfuse_handler = CallbackHandler(
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
    host=config.langfuse.host
)

# Initialize embeddings
embeddings = OllamaEmbeddings(
    model=config.ollama.embedding_model,
    base_url=config.ollama.base_url
)

# Set up ChromaDB connection
if config.chroma.host:
    # Use ChromaDB running in Docker
    import chromadb
    from chromadb.config import Settings
    
    chroma_client = chromadb.HttpClient(
        host=config.chroma.host,
        port=config.chroma.port,
        settings=Settings(allow_reset=True)
    )
    
    collection_name = config.chroma.collection_name or "llm_agent"
else:
    # Use local ChromaDB
    db_location = config.chroma.persist_directory

def get_loader_for_file(file_path: str):
    """Get the appropriate document loader based on file extension."""
    _, ext = os.path.splitext(file_path)
    
    if ext.lower() == '.pdf':
        return PyPDFLoader(file_path)
    elif ext.lower() == '.md':
        return UnstructuredMarkdownLoader(file_path)
    elif ext.lower() in ['.txt', '.csv', '.json', '.html', '.xml']:
        return TextLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def load_documents(path: str) -> int:
    """
    Load documents from a file or directory into the vector store.
    
    Args:
        path: Path to a file or directory
        
    Returns:
        Number of documents loaded
    """
    # Log the document loading to Langfuse
    langfuse_handler.log_event(
        name="document_loading",
        input=path,
        output="Starting document loading process"
    )
    
    # Load documents
    if os.path.isfile(path):
        # Load a single file
        try:
            loader = get_loader_for_file(path)
            documents = loader.load()
        except Exception as e:
            langfuse_handler.log_event(
                name="document_loading_error",
                input=path,
                output=str(e)
            )
            raise ValueError(f"Error loading file {path}: {str(e)}")
    elif os.path.isdir(path):
        # Load all files in a directory
        try:
            loader = DirectoryLoader(
                path,
                glob="**/*.*",
                loader_cls=lambda file_path: get_loader_for_file(file_path)
            )
            documents = loader.load()
        except Exception as e:
            langfuse_handler.log_event(
                name="document_loading_error",
                input=path,
                output=str(e)
            )
            raise ValueError(f"Error loading directory {path}: {str(e)}")
    else:
        raise ValueError(f"Path {path} does not exist")
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(documents)
    
    # Store document chunks in the vector store
    if config.chroma.host:
        # Use ChromaDB running in Docker
        try:
            # Check if collection exists
            collection = chroma_client.get_collection(collection_name)
        except:
            # Create collection if it doesn't exist
            collection = chroma_client.create_collection(collection_name)
        
        # Create Chroma instance with the client
        db = Chroma(
            client=chroma_client,
            collection_name=collection_name,
            embedding_function=embeddings
        )
        
        # Add documents
        db.add_documents(splits)
    else:
        # Use local ChromaDB
        if os.path.exists(db_location):
            # Add to existing DB
            db = Chroma(persist_directory=db_location, embedding_function=embeddings)
            db.add_documents(splits)
        else:
            # Create new DB
            db = Chroma.from_documents(splits, embeddings, persist_directory=db_location)
        
        # Persist the vector store
        db.persist()
    
    # Log the completion to Langfuse
    langfuse_handler.log_event(
        name="document_loading_complete",
        input=path,
        output=f"Loaded {len(splits)} document chunks"
    )
    
    return len(splits)

if __name__ == "__main__":
    # Test the document loader
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            num_docs = load_documents(file_path)
            print(f"Successfully loaded {num_docs} document chunks into the vector store.")
        except Exception as e:
            print(f"Error: {str(e)}")
    else:
        print("Please provide a file or directory path.")
