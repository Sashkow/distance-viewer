#!/bin/bash
export DOCKER_HOST=unix:///var/run/docker.sock

# Start Neo4j if not running
if ! docker ps --format '{{.Names}}' | grep -q '^neo4j$'; then
    if docker ps -a --format '{{.Names}}' | grep -q '^neo4j$'; then
        echo "Starting existing Neo4j container..."
        docker start neo4j
    else
        echo "Creating Neo4j container..."
        docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest
    fi
    echo "Waiting for Neo4j to start..."
    sleep 5
else
    echo "Neo4j already running"
fi

# Run the app
uv run python app.py
