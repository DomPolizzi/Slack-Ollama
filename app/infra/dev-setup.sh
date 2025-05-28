#!/bin/bash
echo "=========================================================="
echo " "
echo "Creating local directories for Docker volumes"
echo " "
mkdir -p data/open-webui data/chromadb data/ollama
echo " "
echo "Creating Docker Network . . ."
echo " "
docker network create --driver overlay --attachable internal-net
echo " "
echo "Deploying Docker Services . . ."
echo " "
docker stack deploy -c docker-stack.yml ai
echo " "
echo "=========================================================="
echo " "
echo "Services Deployed..."
echo " "
echo "When finished, run 'docker stack rm ai' to stop services"
echo " "
echo "=========================================================="