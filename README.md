# Social Balance Graph Viewer

An interactive web application for visualizing and simulating social balance theory in graphs using Neo4j database and FastAPI.

## Overview

This application implements a simulation based on **structural balance theory** in social networks. The model represents people as nodes and their relationships (positive, negative, or neutral) as edges. The system iteratively balances triangular relationships according to balance theory principles.

### Social Balance Theory

A triangle in a social network is **balanced** if:
- All three edges are positive (friends of friends are friends)
- One edge is positive and two are negative (enemy of my enemy is my friend)
- All three edges are negative (mutual enemies form a balanced triad)

A triangle is **unbalanced** if:
- Two edges are positive and one is negative (creates cognitive dissonance)

**Note:** Only triangles with three actual edges (positive or negative) are considered. Neutral relationships (no edge) do not form triangles.

### Simulation Model

The model implements a realistic social dynamics simulation where people only act when experiencing social imbalance:

#### Graph Initialization
1. Create `N` person nodes
2. For each pair of people, randomly determine their relationship:
   - **Positive** edge with probability `positive_prob`
   - **Negative** edge with probability `negative_prob`
   - **No edge (Neutral)** with probability `1 - positive_prob - negative_prob`
3. Only positive and negative edges are stored in the database; neutral means no relationship exists

#### Iteration Process

On each iteration, for every person:

1. **Check for unbalanced triangles**: Find all complete triangles (3 edges) the person participates in
2. **If person is NOT in any unbalanced triangle**: Do nothing (person is satisfied)
3. **If person IS in at least one unbalanced triangle**:
   - With probability `action_probability`, the person takes action
   - With probability `1 - action_probability`, the person does nothing
4. **If person decides to act**, randomly choose one of two actions:

   **Action 1: Modify Triangle Edge (50% chance)**
   - Select a random unbalanced triangle the person is in
   - Select a random edge in that triangle
   - Change it to a different type (POSITIVE → NEGATIVE/NEUTRAL or NEGATIVE → POSITIVE/NEUTRAL)
   - If changed to NEUTRAL, the edge is deleted from the graph

   **Action 2: Create New Connection (50% chance)**
   - Find all "friends of friends" (2-hop neighbors via existing edges)
   - Randomly select one friend-of-friend
   - Create a new edge (randomly POSITIVE or NEGATIVE) to that person

#### Neighbor Definition
A person B is considered a **neighbor** of person A if there exists a POSITIVE or NEGATIVE edge between them. NEUTRAL (no edge) does not create a neighbor relationship.

#### Termination Conditions
The simulation continues until:
- All triangles in the graph are balanced (convergence), OR
- Maximum iterations reached, OR
- No changes are made in an iteration (stable state)

## Features

- Interactive D3.js force-directed graph visualization
- Real-time statistics tracking (balanced vs unbalanced triangles)
- Neo4j database backend for efficient graph storage and queries
- RESTful API built with FastAPI
- Drag-and-drop node interaction
- Color-coded edges (green=positive, red=negative)
- Dynamic edge creation and deletion during simulation
- Realistic social dynamics: people only act when experiencing imbalance
- Two action types: modify existing relationships or create new connections
- Step-by-step or full simulation modes

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Start Neo4j (Docker)
export DOCKER_HOST=unix:///var/run/docker.sock
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

# 3. Run the application
uv run python app.py

# 4. Open browser: http://localhost:5000
```

Then in the UI: Click "Initialize" → "Run Simulation" → Watch the graph balance!

## Prerequisites

- Python 3.9+
- Neo4j database (4.0+)
- uv (Python package and project manager) - [Install from astral.sh](https://docs.astral.sh/uv/)

## Installation

### 1. Clone or Download

```bash
cd /home/shivers/py/distance-viewer
```

### 2. Install Python Dependencies with uv

```bash
uv sync
```

This will create a virtual environment (`.venv`) and install all dependencies from `pyproject.toml`.

### 3. Set Up Neo4j Database

#### Option A: Using Docker (Recommended)

```bash
export DOCKER_HOST=unix:///var/run/docker.sock
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

#### Option B: Install Neo4j Desktop

1. Download from [neo4j.com/download](https://neo4j.com/download/)
2. Create a new database
3. Start the database
4. Note the bolt URI (usually `bolt://localhost:7687`)

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your Neo4j credentials:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

## Running the Application

Start the FastAPI server with uv:

```bash
uv run python app.py
```

Or with uvicorn directly:

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

Open your browser and navigate to:
```
http://localhost:5000
```

## Usage Guide

### 1. Initialize a Graph

- **Number of People**: Set how many nodes (3-50)
- **Positive Probability**: Probability of positive relationship (0.0-1.0)
- **Negative Probability**: Probability of negative relationship (0.0-1.0)
- Remaining probability: no edge created (neutral/no relationship)

Click **Initialize** to create the graph.

**Note:** Only positive and negative relationships appear as edges. Neutral means no connection is drawn.

### 2. Run Simulation

**Single Step:**
- Set **Action Probability** (likelihood a person acts *given* they're in an unbalanced triangle)
- Click **Step Once** to run one iteration
- Only people in unbalanced triangles will potentially act

**Full Simulation:**
- Set **Action Probability** (0.0-1.0)
- Set **Max Iterations** (stopping condition)
- Click **Run Simulation**

The simulation will:
- Run until all triangles are balanced (convergence)
- Or stop at max iterations
- Or reach a stable state (no one acts)
- Display results in status message

**How it works:**
- Each person checks if they're in an unbalanced triangle
- If yes, they act with probability `action_probability`
- They either modify an edge in a triangle OR create a new connection to a friend-of-friend
- If no, they do nothing

### 3. View Statistics

The sidebar shows:
- Number of people and relationships by type
- Total triangles in the graph
- Balanced vs unbalanced count
- Balance ratio percentage

### 4. Interact with Graph

- **Drag nodes** to reposition them
- **Observe colors**: Green (positive), Red (negative)
- **Missing edges** mean neutral/no relationship (not just gray edges)
- Watch the graph evolve as:
  - Edges change types (color changes)
  - Edges disappear (changed to neutral)
  - New edges appear (friend-of-friend connections)

### 5. Reset

Click **Reset** to clear the database and start fresh.

## API Endpoints

### `GET /`
Returns the main HTML page

### `POST /api/initialize`
Initialize a random graph
```json
{
  "num_people": 20,
  "positive_prob": 0.3,
  "negative_prob": 0.3
}
```

### `GET /api/graph`
Get current graph data for visualization

### `POST /api/iterate`
Run one iteration
```json
{
  "action_probability": 0.5
}
```

### `POST /api/simulate`
Run full simulation
```json
{
  "max_iterations": 100,
  "action_probability": 0.5
}
```

### `GET /api/stats`
Get current statistics

### `POST /api/reset`
Clear the database

## Model Configuration

**Configure model variations in `models/config.py` - the single place to switch between model types.**

Available mnodel components:
- **Balance Rules**: `classic`, `strict_positive`, `triangle_inequality`, `product`
- **Action Strategies**: `classic`, `conservative`, `aggressive`, `proactive`, `balanced`
- **Relationship Types**: `discrete` (±1), `continuous` (0 to max), `bipolar` (-max to +max)
- **Decay**: `none`, `linear`, `exponential`, `asymmetric`

Example quick switch to continuous model:
```python
# In models/config.py
from models.config import use_preset
use_preset("continuous_closeness")  # or "bipolar_weighted", "grudge_model"
```

## Project Structure

```
distance-viewer/
├── app.py                  # FastAPI application and routes
├── database.py             # Neo4j connection and queries
├── social_balance.py       # Balance algorithm implementation
├── models/                 # ⭐ Model variations (configure in config.py)
│   ├── config.py          # Model configuration - edit here
│   ├── factory.py         # Creates model from config
│   ├── balance_rules.py   # Balance determination strategies
│   ├── action_strategies.py # Action selection strategies
│   ├── relationship_types.py # Edge value systems
│   └── mechanisms.py      # Decay mechanisms
├── pyproject.toml          # Project configuration and dependencies (uv)
├── .env.example           # Environment variables template
├── README.md              # This file
├── templates/
│   └── index.html         # Main web interface
└── static/
    ├── css/
    │   └── style.css      # Styling
    └── js/
        └── app.js         # Client-side JavaScript and D3.js
```

## Algorithm Details

### Triangle Detection

The application uses Neo4j's graph query capabilities to efficiently find all complete triangles (with 3 non-NEUTRAL edges):

```cypher
MATCH (p1:Person)-[r1:RELATION]-(p2:Person)-[r2:RELATION]-(p3:Person)-[r3:RELATION]-(p1)
WHERE id(p1) < id(p2) AND id(p2) < id(p3)
AND r1.type <> 'NEUTRAL' AND r2.type <> 'NEUTRAL' AND r3.type <> 'NEUTRAL'
RETURN p1.id as n1, p2.id as n2, p3.id as n3,
       r1.type as e1, r2.type as e2, r3.type as e3
```

### Balance Check

```python
def is_triangle_balanced(edge_types):
    positive_count = sum(1 for e in edge_types if e == "POSITIVE")
    negative_count = sum(1 for e in edge_types if e == "NEGATIVE")

    # Skip incomplete triangles
    if positive_count + negative_count < 3:
        return None

    # Balanced: 3 positive OR 1 positive + 2 negative OR 3 negative
    if positive_count == 3 or (positive_count == 1 and negative_count == 2) or negative_count == 3:
        return True

    return False
```

### Person Actions

Each person in each iteration:

1. **Checks for unbalanced triangles** - queries all complete triangles they're part of
2. **If not in any unbalanced triangle** - does nothing (satisfied state)
3. **If in at least one unbalanced triangle**:
   - Acts with probability `action_probability`
   - Chooses randomly between two actions:

#### Action 1: Modify Triangle Edge
```python
def change_triangle_edge(n1, n2, n3, e1, e2, e3):
    # Pick random edge in triangle
    edge_to_change = random.choice([(n1,n2,e1), (n2,n3,e2), (n3,n1,e3)])
    person1, person2, current_type = edge_to_change

    # Change to different type
    possible_types = ["POSITIVE", "NEGATIVE", "NEUTRAL"]
    possible_types.remove(current_type)
    new_type = random.choice(possible_types)

    if new_type == "NEUTRAL":
        delete_relationship(person1, person2)  # Remove edge
    else:
        update_relationship(person1, person2, new_type)
```

#### Action 2: Create New Edge
```python
# Find friends-of-friends (2-hop neighbors not directly connected)
neighbors_of_neighbors = get_neighbors_of_neighbors(person_id)

if neighbors_of_neighbors:
    target = random.choice(neighbors_of_neighbors)
    new_type = random.choice(["POSITIVE", "NEGATIVE"])
    create_relationship(person_id, target, new_type)
```

### Finding Neighbors of Neighbors

```cypher
MATCH (p:Person {id: $person_id})-[r1:RELATION]-(neighbor:Person)-[r2:RELATION]-(fof:Person)
WHERE fof.id <> $person_id
AND r1.type <> 'NEUTRAL' AND r2.type <> 'NEUTRAL'
AND NOT EXISTS((p)-[:RELATION {type: 'POSITIVE'}]-(fof))
AND NOT EXISTS((p)-[:RELATION {type: 'NEGATIVE'}]-(fof))
RETURN DISTINCT fof.id as id
```

## Sample Dataset Reference

This project was inspired by Neo4j's example graph datasets, particularly:
- [Twitter Social Network](https://github.com/neo4j-graph-examples/twitter-v2)
- [Neo4j Graph Examples](https://github.com/neo4j-graph-examples)

While the application generates its own random graphs, you can extend it to import real social network data.

## Troubleshooting

### Cannot connect to Neo4j
- Ensure Neo4j is running: `docker ps` or check Neo4j Desktop
- Verify credentials in `.env` file
- Check firewall settings for ports 7474 and 7687

### Graph not displaying
- Check browser console for errors (F12)
- Ensure D3.js is loading (check network tab)
- Try clearing browser cache

### Performance issues with large graphs
- Keep number of people under 30 for smooth visualization
- Large graphs (50+ nodes) may slow down rendering
- Consider reducing force simulation complexity

## Future Enhancements

- Import real social network datasets from CSV/JSON
- Export graph states and simulation history
- Visualization of balance metrics over time
- Different balance strategies (weighted probabilities)
- Multiple simulation runs with statistical analysis
- 3D graph visualization
- Investigate scale-free network behavior (Barabási–Albert model): How does social balance dynamics differ when the initial graph has power-law degree distribution instead of Erdős–Rényi random graphs? Do hub nodes stabilize faster? Does balance converge differently?

## License

MIT License - feel free to use and modify for your projects.

## References

- Heider, F. (1946). Attitudes and cognitive organization. Journal of Psychology.
- Cartwright, D., & Harary, F. (1956). Structural balance: A generalization of Heider's theory.
- Neo4j Graph Database: https://neo4j.com/
- D3.js Visualization: https://d3js.org/
