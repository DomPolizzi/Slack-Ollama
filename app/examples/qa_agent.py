"""
Example: Question-Answering Agent

This example demonstrates how to use the LLM Agent for question answering
with a specific document.
"""

import os
import sys

# Add the parent directory to the path so we can import from the app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import run_agent
from document_loader import load_documents

def main():
    """Run a simple QA agent example."""
    print("=" * 50)
    print("Question-Answering Agent Example")
    print("=" * 50)
    
    # Check if a document path was provided
    if len(sys.argv) > 1:
        doc_path = sys.argv[1]
        print(f"\nLoading document: {doc_path}")
        
        try:
            # Load the document into the vector store
            num_docs = load_documents(doc_path)
            print(f"Successfully loaded {num_docs} document chunks into the vector store.")
        except Exception as e:
            print(f"Error loading document: {str(e)}")
            return
    else:
        print("\nNo document path provided. Using existing vector store if available.")
    
    print("\nAgent is ready. Type 'q' to quit at any time.")
    
    # Example questions to suggest to the user
    example_questions = [
        "What are the main topics covered in this document?",
        "Can you summarize the key points?",
        "What are the conclusions or recommendations?",
        "Who are the main entities mentioned?",
        "What is the historical context of this document?"
    ]
    
    print("\nExample questions you might ask:")
    for i, question in enumerate(example_questions, 1):
        print(f"{i}. {question}")
    
    # Main interaction loop
    while True:
        query = input("\nEnter your question: ")
        if query.lower() == 'q':
            break
        
        # Run the agent
        result = run_agent(query)
        
        # Display the response
        print("\nAgent response:")
        print(result["messages"][-1]["content"])

if __name__ == "__main__":
    main()
