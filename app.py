from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
from pathlib import Path
import asyncio
import uuid
from datetime import datetime, timedelta

from database import Neo4jConnection
from social_balance import SocialBalanceModel
from models.factory import ModelFactory

app = FastAPI(title="Social Balance Graph Viewer")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# Request models
class InitializeRequest(BaseModel):
    num_people: int = 20
    positive_prob: float = 0.3
    negative_prob: float = 0.3
    neutral_prob: float = 0.4  # For validation, actual neutral = 1 - positive - negative


class IterationRequest(BaseModel):
    action_probability: float = 0.5


class SimulationRequest(BaseModel):
    max_iterations: int = 100
    action_probability: float = 0.5

# Initialize database connection
db = Neo4jConnection()

# Create model with configured strategies from factory
model_components = ModelFactory.create_from_config()
model = SocialBalanceModel(
    db=db,
    balance_rule=model_components['balance_rule'],
    action_strategy=model_components['action_strategy'],
    relationship_type=model_components['relationship_type'],
    decay=model_components['decay']
)

# Print model configuration on startup
print("=" * 60)
print(ModelFactory.get_model_description())
print("=" * 60)

# Track running simulations
running_simulations = {}


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    await db.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    await db.close()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render main page"""
    # Get model description for display
    model_info = {
        "balance_rule": model.balance_rule.get_name(),
        "action_strategy": model.action_strategy.get_name(),
        "relationship_type": model.relationship_type.get_name(),
        "decay": model.decay.get_name()
    }
    return templates.TemplateResponse("index.html", {
        "request": request,
        "model_info": model_info
    })


@app.post("/api/initialize")
async def initialize_graph(request: InitializeRequest):
    """Initialize a random graph with positive, negative, and neutral relationships"""
    print(f"[API] Initialize request received: {request.num_people} people")
    # Validate probabilities sum to 1.0
    total = request.positive_prob + request.negative_prob + request.neutral_prob
    if abs(total - 1.0) > 0.001:
        return {"success": False, "error": f"Probabilities must sum to 1.0 (got {total})"}

    print(f"[API] Starting graph initialization...")
    await model.initialize_random_graph(request.num_people, request.positive_prob, request.negative_prob)
    print(f"[API] Graph initialized, fetching statistics...")
    stats = await model.get_statistics()
    print(f"[API] Statistics fetched, returning response")
    return {"success": True, "stats": stats}


@app.get("/api/graph")
async def get_graph():
    """Get current graph data for visualization"""
    print(f"[API] Fetching graph data...")
    graph_data = await model.get_graph_data()
    print(f"[API] Graph data: {len(graph_data['nodes'])} nodes, {len(graph_data['links'])} links")
    return graph_data


@app.get("/api/graph/mds")
async def get_graph_mds():
    """Get graph data with MDS-computed positions and PCA analysis"""
    print(f"[API] Fetching graph data with MDS layout...")
    graph_data = await model.get_graph_data_mds()
    print(f"[API] MDS graph data: {len(graph_data['nodes'])} nodes, {len(graph_data['links'])} links")
    if graph_data.get('pca_info'):
        print(f"[API] PCA variance: {graph_data['pca_info']['variance_explained'][:2]}, 2D captures {graph_data['pca_info']['total_variance_2d']}%")
    return graph_data


@app.post("/api/iterate")
async def run_iteration(request: IterationRequest):
    """Run one iteration of the balance algorithm"""
    result = await model.run_single_iteration(request.action_probability)
    return result


@app.post("/api/simulate/start")
async def start_simulation(request: SimulationRequest):
    """Start an asynchronous simulation"""
    sim_id = str(uuid.uuid4())

    # Store simulation state
    running_simulations[sim_id] = {
        "status": "running",
        "current_iteration": 0,
        "max_iterations": request.max_iterations,
        "action_probability": request.action_probability,
        "result": None,
        "error": None,
        "started_at": datetime.now(),
        "timeout": 300  # 5 minutes timeout
    }

    # Start simulation in background
    asyncio.create_task(run_simulation_async(sim_id, request.max_iterations, request.action_probability))

    return {"simulation_id": sim_id, "status": "started"}


@app.get("/api/simulate/status/{sim_id}")
async def get_simulation_status(sim_id: str):
    """Get status of a running simulation"""
    if sim_id not in running_simulations:
        return {"error": "Simulation not found"}, 404

    sim = running_simulations[sim_id]

    # Check for timeout
    if datetime.now() - sim["started_at"] > timedelta(seconds=sim["timeout"]):
        sim["status"] = "timeout"
        sim["error"] = "Simulation timed out after 5 minutes"

    return {
        "status": sim["status"],
        "current_iteration": sim["current_iteration"],
        "max_iterations": sim["max_iterations"],
        "current_stats": sim.get("current_stats"),
        "result": sim["result"],
        "error": sim["error"]
    }


@app.post("/api/simulate/stop/{sim_id}")
async def stop_simulation(sim_id: str):
    """Stop a running simulation"""
    if sim_id in running_simulations:
        running_simulations[sim_id]["status"] = "stopped"
        return {"success": True, "message": "Simulation stopped"}
    return {"success": False, "message": "Simulation not found"}


async def run_simulation_async(sim_id: str, max_iterations: int, action_probability: float):
    """Run simulation asynchronously with progress updates"""
    try:
        sim = running_simulations[sim_id]
        iteration_count = 0
        history = []
        no_change_streak = 0

        for i in range(max_iterations):
            # Check if simulation was stopped or timed out
            if sim["status"] != "running":
                break

            # Check timeout
            if datetime.now() - sim["started_at"] > timedelta(seconds=sim["timeout"]):
                sim["status"] = "timeout"
                sim["error"] = "Simulation timed out"
                break

            stats = await model.get_statistics()
            history.append(stats)

            # Update progress and current stats every 10 iterations
            sim["current_iteration"] = i
            if i % 10 == 0 or i == 0:
                sim["current_stats"] = stats

            # Check if all triangles are balanced
            if stats["unbalanced_triangles"] == 0 and stats["total_triangles"] > 0:
                sim["status"] = "completed"
                sim["result"] = {
                    "iterations": i,
                    "final_stats": stats,
                    "history": history,
                    "converged": True
                }
                break

            # Run one iteration
            result = await model.run_single_iteration(action_probability)
            iteration_count += 1

            # Track consecutive iterations with no changes
            if result["changes_made"] == 0:
                no_change_streak += 1
            else:
                no_change_streak = 0

            # Only stop if no changes for 10 consecutive iterations
            # This indicates true stable state (not just random chance)
            if no_change_streak >= 10:
                sim["status"] = "completed"
                final_stats = await model.get_statistics()
                sim["result"] = {
                    "iterations": iteration_count,
                    "final_stats": final_stats,
                    "history": history,
                    "converged": final_stats["unbalanced_triangles"] == 0
                }
                break

            # Small delay to allow other operations and checking stop signal
            await asyncio.sleep(0.01)

        # If we finished all iterations
        if sim["status"] == "running":
            final_stats = await model.get_statistics()
            sim["status"] = "completed"
            sim["result"] = {
                "iterations": iteration_count,
                "final_stats": final_stats,
                "history": history,
                "converged": final_stats["unbalanced_triangles"] == 0
            }

    except Exception as e:
        sim["status"] = "error"
        sim["error"] = str(e)


@app.post("/api/simulate")
async def run_simulation(request: SimulationRequest):
    """Legacy endpoint - run complete simulation (with timeout)"""
    # Use a timeout of 60 seconds for synchronous simulations
    timeout = 60
    start_time = datetime.now()

    iteration_count = 0
    history = []
    no_change_streak = 0

    try:
        for i in range(request.max_iterations):
            # Check timeout
            if datetime.now() - start_time > timedelta(seconds=timeout):
                return {
                    "error": "Simulation timed out after 60 seconds",
                    "iterations": iteration_count,
                    "final_stats": await model.get_statistics()
                }

            stats = await model.get_statistics()
            history.append(stats)

            # Check if all triangles are balanced
            if stats["unbalanced_triangles"] == 0 and stats["total_triangles"] > 0:
                return {
                    "iterations": i,
                    "final_stats": stats,
                    "history": history,
                    "converged": True
                }

            # Run one iteration
            result = await model.run_single_iteration(request.action_probability)
            iteration_count += 1

            # Track consecutive iterations with no changes
            if result["changes_made"] == 0:
                no_change_streak += 1
            else:
                no_change_streak = 0

            # Only stop if no changes for 10 consecutive iterations
            if no_change_streak >= 10:
                final_stats = await model.get_statistics()
                return {
                    "iterations": iteration_count,
                    "final_stats": final_stats,
                    "history": history,
                    "converged": final_stats["unbalanced_triangles"] == 0
                }

        # Finished all iterations
        final_stats = await model.get_statistics()
        return {
            "iterations": iteration_count,
            "final_stats": final_stats,
            "history": history,
            "converged": final_stats["unbalanced_triangles"] == 0
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/api/stats")
async def get_statistics():
    """Get current graph statistics"""
    stats = await model.get_statistics()
    return stats


@app.post("/api/reset")
async def reset_graph():
    """Clear the entire graph"""
    await model.reset_graph()
    return {"success": True, "message": "Graph cleared"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True)
