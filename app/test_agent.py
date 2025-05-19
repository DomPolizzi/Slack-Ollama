"""
Test script to verify that all components of the LLM Agent are working correctly.
"""

import os
import sys
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_chroma import Chroma
from langfuse.callback import CallbackHandler
from config import config

def test_ollama_connection():
    """Test connection to Ollama."""
    print("Testing Ollama connection...")
    try:
        llm = OllamaLLM(
            model=config.ollama.llm_model,
            base_url=config.ollama.base_url
        )
        result = llm.invoke("Hello, are you working?")
        print(f"Ollama LLM response: {result}")
        print("✅ Ollama LLM connection successful")
        return True
    except Exception as e:
        print(f"❌ Ollama LLM connection failed: {str(e)}")
        return False

def test_embeddings():
    """Test Ollama embeddings."""
    print("\nTesting Ollama embeddings...")
    try:
        embeddings = OllamaEmbeddings(
            model=config.ollama.embedding_model,
            base_url=config.ollama.base_url
        )
        result = embeddings.embed_query("Test query for embeddings")
        print(f"Embedding vector length: {len(result)}")
        print("✅ Ollama embeddings successful")
        return True
    except Exception as e:
        print(f"❌ Ollama embeddings failed: {str(e)}")
        return False

def test_chroma():
    """Test ChromaDB connection."""
    print("\nTesting ChromaDB...")
    try:
        embeddings = OllamaEmbeddings(
            model=config.ollama.embedding_model,
            base_url=config.ollama.base_url
        )
        
        # Create a temporary collection for testing
        db = Chroma(
            collection_name="test_collection",
            embedding_function=embeddings
        )
        
        # Add a test document
        db.add_texts(["This is a test document for ChromaDB"])
        
        # Query the collection
        results = db.similarity_search("test document", k=1)
        print(f"ChromaDB query result: {results[0].page_content}")
        
        # Delete the test collection
        db._collection.delete()
        
        print("✅ ChromaDB connection successful")
        return True
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {str(e)}")
        return False

def test_langfuse():
    """Test Langfuse connection."""
    print("\nTesting Langfuse connection...")
    
    # Skip the test if no API keys are provided
    if not config.langfuse.public_key or not config.langfuse.secret_key:
        print("⚠️ Langfuse API keys not provided, skipping test")
        return True
    
    try:
        handler = CallbackHandler(
            public_key=config.langfuse.public_key,
            secret_key=config.langfuse.secret_key,
            host=config.langfuse.host
        )
        
        # Log a test event
        handler.log_event(
            name="test_event",
            input="test input",
            output="test output"
        )
        
        print("✅ Langfuse connection successful")
        return True
    except Exception as e:
        print(f"❌ Langfuse connection failed: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("LLM Agent Component Tests")
    print("=" * 50)
    
    # Run tests
    ollama_success = test_ollama_connection()
    embeddings_success = test_embeddings()
    chroma_success = test_chroma()
    langfuse_success = test_langfuse()
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"Ollama LLM: {'✅ PASS' if ollama_success else '❌ FAIL'}")
    print(f"Ollama Embeddings: {'✅ PASS' if embeddings_success else '❌ FAIL'}")
    print(f"ChromaDB: {'✅ PASS' if chroma_success else '❌ FAIL'}")
    print(f"Langfuse: {'✅ PASS' if langfuse_success else '❌ FAIL'}")
    
    # Overall result
    if ollama_success and embeddings_success and chroma_success:
        print("\n✅ All critical components are working correctly!")
        if not langfuse_success and config.langfuse.public_key and config.langfuse.secret_key:
            print("⚠️ Langfuse is not working, but the agent can still function without it.")
    else:
        print("\n❌ Some critical components are not working. Please fix the issues before using the agent.")

if __name__ == "__main__":
    main()
