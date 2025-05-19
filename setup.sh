#!/bin/bash

# Setup script for the LLM Agent

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is not installed. Please install pip3 and try again."
    exit 1
fi


# Create a virtual environment
echo "Creating a virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if required Ollama models are available
echo "Checking for required Ollama models..."

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "Ollama is not running. Starting Ollama..."
    ollama serve &
    # Wait for Ollama to start
    sleep 5
fi

# Get available models
available_models=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*' | sed 's/"name":"//')

# Check for LLM model
if ! echo "$available_models" | grep -q "llama3.2"; then
    echo "Pulling llama3.2 model..."
    ollama pull llama3.2
fi

# Check for embedding model
if ! echo "$available_models" | grep -q "nomic-embed-text-v1.5"; then
    echo "Pulling nomic-embed-text-v1.5 model..."
    ollama pull nomic-embed-text-v1.5
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
fi

echo "Setup complete! You can now run the agent with:"
echo "cd app && python main.py"
