import os
from agents.agent import run_agent
from components.document_loader import load_documents

def main():
    """Main entry point for the LLM Agent application."""
    print("=" * 50)
    print("LLM Agent with LangGraph, Langfuse, Ollama, and ChromaDB")
    print("=" * 50)
    
    # Check if we need to load documents
    load_docs = input("\nDo you want to load documents into the vector store? (y/n): ").lower() == 'y'
    
    if load_docs:
        doc_path = input("Enter the path to the document or directory: ")
        if os.path.exists(doc_path):
            num_docs = load_documents(doc_path)
            print(f"Successfully loaded {num_docs} documents into the vector store.")
        else:
            print(f"Path '{doc_path}' does not exist.")
    
    print("\nAgent is ready. Type 'q' to quit at any time.")
    
    # Main interaction loop
    while True:
        query = input("\nEnter your question: ")
        if query.lower() == 'q':
            break
        
        result = run_agent(query)
        
        # Display the response
        print("\nAgent response:")
        print(result["messages"][-1]["content"])

if __name__ == "__main__":
    main()
