import random
import numpy as np
from database import Neo4jConnection
from typing import Optional
from models.balance_rules import BalanceRule, ClassicBalanceRule
from models.action_strategies import ActionStrategy, ClassicActionStrategy
from models.relationship_types import RelationshipType, DiscreteRelationship
from models.mechanisms import DecayMechanism, NoDecay
from sklearn.manifold import MDS
from sklearn.decomposition import PCA


class SocialBalanceModel:
    """
    Implements the social balance model based on structural balance theory.

    Now supports pluggable strategies for balance rules, actions, and relationship types.
    """

    def __init__(
        self,
        db: Neo4jConnection,
        balance_rule: Optional[BalanceRule] = None,
        action_strategy: Optional[ActionStrategy] = None,
        relationship_type: Optional[RelationshipType] = None,
        decay: Optional[DecayMechanism] = None
    ):
        self.db = db

        # Use dependency injection with defaults for backward compatibility
        self.balance_rule = balance_rule or ClassicBalanceRule()
        self.action_strategy = action_strategy or ClassicActionStrategy()
        self.relationship_type = relationship_type or DiscreteRelationship()
        self.decay = decay or NoDecay()

    async def initialize_random_graph(self, num_people, positive_prob=0.3, negative_prob=0.3):
        """
        Create a random graph with specified probabilities for relationship types.

        Args:
            num_people: Number of person nodes to create
            positive_prob: Probability of positive relationship
            negative_prob: Probability of negative relationship
            (remaining probability is for no relationship/neutral)
        """
        # Clear existing graph
        print(f"Clearing database...")
        await self.db.clear_database()
        print(f"Database cleared")

        # Create person nodes
        print(f"Creating {num_people} person nodes...")
        for i in range(num_people):
            await self.db.create_person(i)
        print(f"Created {num_people} person nodes")

        # Create relationships between all pairs (batched for performance)
        print(f"Creating relationships...")
        relationships = []

        print(f"[DEBUG] Starting relationship loop for {num_people} people...")
        for i in range(num_people):
            for j in range(i + 1, num_people):
                rand_val = random.random()

                if rand_val < positive_prob:
                    # Create positive edge - use appropriate positive value for the relationship type
                    if isinstance(self.relationship_type, DiscreteRelationship):
                        value = 1.0
                    else:
                        # For continuous/bipolar, get a random positive value
                        value = self.relationship_type.get_random_value()

                    rel_type = self.relationship_type.encode_to_storage(value)
                    relationships.append({
                        "person1_id": i,
                        "person2_id": j,
                        "rel_type": rel_type,
                        "value": value
                    })

                elif rand_val < positive_prob + negative_prob:
                    # Create negative edge - use appropriate negative value for the relationship type
                    if isinstance(self.relationship_type, DiscreteRelationship):
                        value = -1.0
                        rel_type = self.relationship_type.encode_to_storage(value)
                        relationships.append({
                            "person1_id": i,
                            "person2_id": j,
                            "rel_type": rel_type,
                            "value": value
                        })
                    elif hasattr(self.relationship_type, 'min_val') and self.relationship_type.min_val < 0:
                        # Only BipolarRelationship supports negative values
                        # For bipolar, get a random negative value
                        value = self.relationship_type.get_random_value()
                        # Ensure it's negative
                        while value >= 0:
                            value = self.relationship_type.get_random_value()

                        rel_type = self.relationship_type.encode_to_storage(value)
                        relationships.append({
                            "person1_id": i,
                            "person2_id": j,
                            "rel_type": rel_type,
                            "value": value
                        })
                    # else: ContinuousRelationship doesn't support negative values, skip
                # else: NEUTRAL - no relationship created

        print(f"[DEBUG] Finished loop, built {len(relationships)} relationships")
        print("Creating relationships batch")
        # Batch create all relationships at once
        if relationships:
            print(f"[DEBUG] About to call create_relationships_batch with {len(relationships)} items")
            await self.db.create_relationships_batch(relationships)
            print(f"[DEBUG] Batch call completed")

        print(f"Created {len(relationships)} relationships")
        print(f"Initialized graph with {num_people} people using {self.relationship_type.get_name()}")

    def is_triangle_balanced(self, edge_types):
        """
        Check if a triangle is balanced using the configured balance rule.

        Args:
            edge_types: List of 3 edge types (strings or numeric values)

        Returns:
            True if balanced, False if unbalanced, None if incomplete
        """
        # Convert edge types to numeric values for the balance rule
        edge_values = [self.relationship_type.decode_from_storage(e) for e in edge_types]

        # Use the injected balance rule
        return self.balance_rule.is_balanced(edge_values)

    async def change_triangle_edge(self, n1, n2, n3, e1, e2, e3):
        """
        Change one random edge in a triangle to a different type (POSITIVE, NEGATIVE, or NEUTRAL).
        Returns the edge that was changed, or None if no change made.
        """
        edges = [(n1, n2, e1), (n2, n3, e2), (n3, n1, e3)]

        # Randomly pick an edge to change
        edge_to_change = random.choice(edges)
        person1, person2, current_type = edge_to_change

        # Pick a random new type different from current type
        possible_types = ["POSITIVE", "NEGATIVE", "NEUTRAL"]
        possible_types.remove(current_type)
        new_type = random.choice(possible_types)

        # Update in database
        if new_type == "NEUTRAL":
            # Delete the relationship
            await self.db.delete_relationship(person1, person2)
        else:
            # Check if relationship exists, if not create it
            await self.db.update_relationship(person1, person2, new_type)

        return {
            "person1": person1,
            "person2": person2,
            "old_type": current_type,
            "new_type": new_type
        }

    async def _execute_action(self, action):
        """
        Execute an action returned by the action strategy.

        Args:
            action: Dictionary describing the action

        Returns:
            Dictionary describing the change made
        """
        action_type = action.get("type")

        if action_type == "change_edge":
            person1 = action["person1"]
            person2 = action["person2"]
            new_value = action["new_value"]
            old_value = action.get("old_value")

            # Encode the new value for storage
            new_type = self.relationship_type.encode_to_storage(new_value)

            # Check if it's neutral (delete edge)
            if self.relationship_type.is_neutral(new_value):
                await self.db.delete_relationship(person1, person2)
            else:
                await self.db.update_relationship(person1, person2, new_type, value=new_value)

            return {
                "action": "change_edge",
                "person1": person1,
                "person2": person2,
                "old_value": old_value,
                "new_value": new_value
            }

        elif action_type == "create_edge":
            person1 = action["person1"]
            person2 = action["person2"]
            new_value = action["new_value"]

            # Encode for storage
            new_type = self.relationship_type.encode_to_storage(new_value)
            await self.db.create_relationship(person1, person2, new_type, value=new_value)

            return {
                "action": "create_edge",
                "person1": person1,
                "person2": person2,
                "new_value": new_value
            }

        elif action_type == "delete_edge":
            person1 = action["person1"]
            person2 = action["person2"]

            await self.db.delete_relationship(person1, person2)

            return {
                "action": "delete_edge",
                "person1": person1,
                "person2": person2
            }

        return None

    async def run_single_iteration(self, action_probability=0.5):
        """
        Run one iteration of the balance algorithm using configured action strategy.

        Args:
            action_probability: Probability that a person takes action (given they're in an unbalanced triangle)

        Returns:
            Dictionary with iteration results
        """
        # Get all people
        people_query = "MATCH (p:Person) RETURN p.id as id"
        people = await self.db.execute_query(people_query)
        person_ids = [p["id"] for p in people]

        changes_made = []

        for person_id in person_ids:
            # Get all triangles this person is part of
            triangles = await self.db.get_person_triangles(person_id)

            if not triangles:
                # No triangles at all - do nothing
                continue

            # Find unbalanced triangles
            unbalanced = []
            for triangle in triangles:
                edge_types = [triangle["e1"], triangle["e2"], triangle["e3"]]
                is_balanced = self.is_triangle_balanced(edge_types)

                if is_balanced is False:  # Explicitly unbalanced
                    unbalanced.append(triangle)

            if not unbalanced:
                # Not in any unbalanced triangles - do nothing
                continue

            # Person is in at least one unbalanced triangle
            # Person acts with given probability
            if random.random() > action_probability:
                continue

            # Get neighbors of neighbors for potential new connections
            neighbors_of_neighbors = await self.db.get_neighbors_of_neighbors(person_id)

            # Use the action strategy to select an action
            action = self.action_strategy.select_action(
                person_id,
                unbalanced,
                neighbors_of_neighbors,
                self.relationship_type
            )

            if action:
                # Execute the action
                change = await self._execute_action(action)
                if change:
                    changes_made.append(change)

        stats = await self.get_statistics()

        return {
            "changes_made": len(changes_made),
            "changes": changes_made,
            "stats": stats
        }

    async def run_simulation(self, max_iterations=100, action_probability=0.5):
        """
        Run the simulation until all triangles are balanced or max iterations reached.

        Returns:
            Dictionary with simulation results
        """
        iteration_count = 0
        history = []
        no_change_streak = 0

        for i in range(max_iterations):
            stats = await self.get_statistics()
            history.append(stats)

            # Check if all triangles are balanced
            if stats["unbalanced_triangles"] == 0 and stats["total_triangles"] > 0:
                print(f"All triangles balanced after {i} iterations")
                break

            # Run one iteration
            result = await self.run_single_iteration(action_probability)
            iteration_count += 1

            # Track consecutive iterations with no changes
            if result["changes_made"] == 0:
                no_change_streak += 1
            else:
                no_change_streak = 0

            # Only stop if no changes for 10 consecutive iterations
            # This indicates true stable state (not just random chance)
            if no_change_streak >= 10:
                print(f"Stable state reached after {i} iterations (10 iterations with no changes)")
                break

        final_stats = await self.get_statistics()

        return {
            "iterations": iteration_count,
            "final_stats": final_stats,
            "history": history,
            "converged": final_stats["unbalanced_triangles"] == 0
        }

    async def get_statistics(self):
        """Get current graph statistics"""
        # Count nodes
        num_people = await self.db.count_nodes()

        # Count relationships by type
        rel_counts = await self.db.count_relationships()
        rel_stats = {r["type"]: int(r["count"]) for r in rel_counts}

        # Count triangles
        triangles = await self.db.get_triangles()
        total_triangles = len(triangles)

        balanced_count = 0
        unbalanced_count = 0

        for triangle in triangles:
            edge_types = [triangle["e1"], triangle["e2"], triangle["e3"]]
            is_balanced = self.is_triangle_balanced(edge_types)

            if is_balanced is True:
                balanced_count += 1
            elif is_balanced is False:
                unbalanced_count += 1

        # Debug: Print a few sample triangles to verify balance
        if triangles and balanced_count > 0:
            print(f"\n[DEBUG] Sample balanced triangles:")
            sample_count = 0
            for triangle in triangles:
                edge_types = [triangle["e1"], triangle["e2"], triangle["e3"]]
                is_balanced = self.is_triangle_balanced(edge_types)
                if is_balanced and sample_count < 3:
                    e1, e2, e3 = edge_types
                    print(f"  Triangle ({triangle['n1']}, {triangle['n2']}, {triangle['n3']}): e1={e1}, e2={e2}, e3={e3}")
                    if isinstance(e1, float) and isinstance(e2, float) and isinstance(e3, float):
                        print(f"    Check: {e1:.3f}+{e2:.3f}={e1+e2:.3f} >= {e3:.3f}? {e1+e2 >= e3}")
                        print(f"    Check: {e2:.3f}+{e3:.3f}={e2+e3:.3f} >= {e1:.3f}? {e2+e3 >= e1}")
                        print(f"    Check: {e3:.3f}+{e1:.3f}={e3+e1:.3f} >= {e2:.3f}? {e3+e1 >= e2}")
                    sample_count += 1

        return {
            "num_people": num_people,
            "relationships": rel_stats,
            "total_triangles": total_triangles,
            "balanced_triangles": balanced_count,
            "unbalanced_triangles": unbalanced_count,
            "balance_ratio": balanced_count / total_triangles if total_triangles > 0 else 0
        }

    async def get_node_triangle_status(self):
        """Classify each node based on their triangle participation.
        Returns dict: {person_id: 'unbalanced' | 'balanced' | 'none'}
        """
        # Get all people
        people_query = "MATCH (p:Person) RETURN p.id as id"
        people = await self.db.execute_query(people_query)

        # Initialize all as having no triangles
        node_status = {p["id"]: "none" for p in people}

        # Check each person's triangles
        for person_id in node_status.keys():
            triangles = await self.db.get_person_triangles(person_id)

            if not triangles:
                continue  # No triangles - stays 'none'

            # Check if any triangle is unbalanced
            has_unbalanced = False
            has_balanced = False

            for triangle in triangles:
                edge_types = [triangle["e1"], triangle["e2"], triangle["e3"]]
                is_balanced = self.is_triangle_balanced(edge_types)

                if is_balanced is False:
                    has_unbalanced = True
                    break  # If even one is unbalanced, mark as unbalanced
                elif is_balanced is True:
                    has_balanced = True

            # Priority: unbalanced > balanced > none
            if has_unbalanced:
                node_status[person_id] = "unbalanced"
            elif has_balanced:
                node_status[person_id] = "balanced"

        return node_status

    async def get_graph_data(self):
        """Get graph data formatted for D3.js visualization"""
        nodes_and_edges = await self.db.get_all_nodes_and_edges()
        node_status = await self.get_node_triangle_status()

        nodes = {}
        links = []

        for record in nodes_and_edges:
            # Add person node
            p = record["p"]
            person_id = p["id"]
            if person_id not in nodes:
                nodes[person_id] = {
                    "id": person_id,
                    "name": p["name"],
                    "status": node_status.get(person_id, "none")
                }

            # Add relationship if exists
            if record["r"] and record["p2"]:
                p2 = record["p2"]
                p2_id = p2["id"]

                if p2_id not in nodes:
                    nodes[p2_id] = {
                        "id": p2_id,
                        "name": p2["name"],
                        "status": node_status.get(p2_id, "none")
                    }

                rel = record["r"]
                # Only add edges that are not NEUTRAL
                if rel["type"] != "NEUTRAL":
                    edge_value = rel.get("value")
                    print(f"[DEBUG] Edge {person_id}->{p2_id}: type={rel['type']}, value={edge_value}")
                    links.append({
                        "source": person_id,
                        "target": p2_id,
                        "type": rel["type"],
                        "value": edge_value  # Include numeric value if present
                    })

        return {
            "nodes": list(nodes.values()),
            "links": links
        }

    async def reset_graph(self):
        """Clear the entire graph"""
        await self.db.clear_database()

    async def get_graph_data_mds(self):
        """
        Get graph data with MDS-computed positions for optimal distance representation.

        Returns:
            Dictionary with nodes (with x,y from MDS), links, PCA info, and compromise info
        """
        nodes_and_edges = await self.db.get_all_nodes_and_edges()
        node_status = await self.get_node_triangle_status()

        # Build node list and distance matrix
        nodes_dict = {}
        node_id_to_idx = {}
        idx = 0

        for record in nodes_and_edges:
            p = record["p"]
            person_id = p["id"]
            if person_id not in nodes_dict:
                nodes_dict[person_id] = {
                    "id": person_id,
                    "name": p["name"],
                    "status": node_status.get(person_id, "none")
                }
                node_id_to_idx[person_id] = idx
                idx += 1

        n_nodes = len(nodes_dict)

        # Initialize distance matrix with large values (for missing edges)
        # Using a large value instead of inf to avoid MDS issues
        distance_matrix = np.full((n_nodes, n_nodes), 10.0)
        np.fill_diagonal(distance_matrix, 0)

        # Fill in actual edge distances
        links = []
        for record in nodes_and_edges:
            if record["r"] and record["p2"]:
                p1_id = record["p"]["id"]
                p2_id = record["p2"]["id"]
                rel = record["r"]

                if rel["type"] != "NEUTRAL":
                    edge_value = rel.get("value")
                    initial_value = rel.get("initial_value", edge_value)

                    # Update distance matrix
                    if edge_value is not None:
                        i = node_id_to_idx[p1_id]
                        j = node_id_to_idx[p2_id]
                        distance_matrix[i, j] = edge_value
                        distance_matrix[j, i] = edge_value

                    # Calculate change
                    change = None
                    if initial_value is not None and edge_value is not None:
                        change = edge_value - initial_value

                    links.append({
                        "source": p1_id,
                        "target": p2_id,
                        "type": rel["type"],
                        "value": edge_value,
                        "initial_value": initial_value,
                        "change": change
                    })

        # Compute MDS if we have enough nodes
        if n_nodes < 2:
            # Not enough nodes for MDS, return empty
            return {
                "nodes": list(nodes_dict.values()),
                "links": links,
                "pca_info": None,
                "compromise_info": None
            }

        # Apply MDS directly to 2D for best distance preservation
        mds = MDS(n_components=2, dissimilarity='precomputed', random_state=42, metric=True)
        coords_2d = mds.fit_transform(distance_matrix)

        print(f"[DEBUG] MDS stress: {mds.stress_}")

        # Compute actual distances in MDS coordinates
        from scipy.spatial.distance import pdist, squareform
        mds_dist_matrix = squareform(pdist(coords_2d))

        # Find the scale factor: compare MDS distances to input distances for actual edges
        scale_sum_input = 0
        scale_sum_mds = 0
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                if distance_matrix[i, j] < 10.0:  # Real edge (not the 10.0 placeholder)
                    scale_sum_input += distance_matrix[i, j]
                    scale_sum_mds += mds_dist_matrix[i, j]

        # Scale factor to make MDS distances match input distances
        if scale_sum_mds > 0:
            mds_scale_factor = scale_sum_input / scale_sum_mds
            coords_2d = coords_2d * mds_scale_factor
            print(f"[DEBUG] MDS scale factor: {mds_scale_factor:.4f}")

        # Now scale by DISTANCE_SCALE (300) to convert to pixels
        coords_2d = coords_2d * 300

        # Compute PCA on high-dim MDS for variance analysis
        mds_highd = MDS(n_components=min(n_nodes - 1, 5), dissimilarity='precomputed', random_state=42)
        coords_high_dim = mds_highd.fit_transform(distance_matrix)
        pca = PCA()
        pca.fit(coords_high_dim)

        # Update nodes with MDS positions
        nodes_list = []
        for person_id, node_data in nodes_dict.items():
            idx = node_id_to_idx[person_id]
            node_data["x"] = float(coords_2d[idx, 0])
            node_data["y"] = float(coords_2d[idx, 1])
            nodes_list.append(node_data)

        # Calculate variance explained by first 5 PCs
        variance_explained = (pca.explained_variance_ratio_ * 100).tolist()[:5]
        variance_explained = [round(v, 1) for v in variance_explained]

        # Pad with zeros if less than 5 components
        while len(variance_explained) < 5:
            variance_explained.append(0.0)

        # Calculate compromise statistics
        total_compromise = 0.0
        total_initial_distances = 0.0
        n_edges_with_change = 0

        for link in links:
            if link["change"] is not None:
                total_compromise += abs(link["change"])
                n_edges_with_change += 1
            if link["initial_value"] is not None:
                total_initial_distances += link["initial_value"]

        compromise_percentage = 0.0
        if total_initial_distances > 0:
            compromise_percentage = (total_compromise / total_initial_distances) * 100

        return {
            "nodes": nodes_list,
            "links": links,
            "pca_info": {
                "variance_explained": variance_explained,
                "total_variance_2d": round(sum(variance_explained[:2]), 1)
            },
            "compromise_info": {
                "total_absolute": round(total_compromise, 3),
                "percentage": round(compromise_percentage, 1),
                "n_edges_changed": n_edges_with_change
            }
        }
