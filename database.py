from neo4j import AsyncGraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()


class Neo4jConnection:
    """Handles Neo4j database connection and queries (async)"""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None

    async def connect(self):
        """Establish connection to Neo4j database"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Test connection
            await self.driver.verify_connectivity()
            print(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            raise

    async def close(self):
        """Close database connection"""
        if self.driver:
            await self.driver.close()
            print("Neo4j connection closed")

    async def execute_query(self, query, parameters=None):
        """Execute a Cypher query and return results"""
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {})
            records = []
            async for record in result:
                # Convert Neo4j objects to dictionaries
                data = {}
                for key in record.keys():
                    value = record[key]
                    # Convert Node objects to dicts
                    if hasattr(value, '__class__') and value.__class__.__name__ == 'Node':
                        data[key] = dict(value)
                    # Convert Relationship objects to dicts
                    elif hasattr(value, '__class__') and value.__class__.__name__ == 'Relationship':
                        data[key] = dict(value)
                    else:
                        data[key] = value
                records.append(data)
            return records

    async def execute_write(self, query, parameters=None):
        """Execute a write query with proper transaction management"""
        async def _tx_function(tx):
            result = await tx.run(query, parameters or {})
            summary = await result.consume()
            return summary.counters

        print(f"[DB] Executing write query...")
        async with self.driver.session() as session:
            counters = await session.execute_write(_tx_function)
            print(f"[DB] Write query completed")
            return counters

    async def clear_database(self):
        """Delete all nodes and relationships"""
        query = "MATCH (n) DETACH DELETE n"
        await self.execute_write(query)

    async def create_person(self, person_id):
        """Create a person node"""
        query = """
        CREATE (p:Person {id: $person_id, name: $name})
        RETURN p
        """
        parameters = {
            "person_id": person_id,
            "name": f"Person_{person_id}"
        }
        return await self.execute_write(query, parameters)

    async def create_relationship(self, person1_id, person2_id, rel_type, value=None, initial_value=None):
        """
        Create a relationship between two people
        rel_type: 'POSITIVE', 'NEGATIVE', or 'NEUTRAL'
        value: optional numeric value for continuous/bipolar relationship types
        initial_value: optional initial value (for tracking changes during simulation)
        Creates bidirectional relationships
        """
        # Simplified: just create one directed relationship
        # Queries will use undirected pattern matching
        # Store initial_value to track changes during simulation
        if initial_value is None:
            initial_value = value

        query = """
        MATCH (p1:Person {id: $person1_id}), (p2:Person {id: $person2_id})
        CREATE (p1)-[:RELATION {type: $rel_type, value: $value, initial_value: $initial_value}]->(p2)
        """
        parameters = {
            "person1_id": person1_id,
            "person2_id": person2_id,
            "rel_type": rel_type,
            "value": value,
            "initial_value": initial_value
        }
        return await self.execute_write(query, parameters)

    async def create_relationships_batch(self, relationships):
        """
        Create multiple relationships in a single batch operation.

        Args:
            relationships: list of dicts with keys: person1_id, person2_id, rel_type, value, initial_value (optional)
        """
        print(f"[DB] Creating {len(relationships)} relationships in batch...")
        # Add initial_value to each relationship if not present
        for rel in relationships:
            if 'initial_value' not in rel:
                rel['initial_value'] = rel['value']

        query = """
        UNWIND $relationships AS rel
        MATCH (p1:Person {id: rel.person1_id})
        MATCH (p2:Person {id: rel.person2_id})
        CREATE (p1)-[:RELATION {type: rel.rel_type, value: rel.value, initial_value: rel.initial_value}]->(p2)
        """
        result = await self.execute_write(query, {"relationships": relationships})
        print(f"[DB] Batch relationship creation completed")
        return result

    async def update_relationship(self, person1_id, person2_id, new_type, value=None):
        """
        Update relationship type between two people.
        Note: initial_value is NOT updated, it preserves the original value for tracking changes.
        """
        query = """
        MATCH (p1:Person {id: $person1_id})-[r:RELATION]-(p2:Person {id: $person2_id})
        SET r.type = $new_type, r.value = $value
        RETURN r
        """
        parameters = {
            "person1_id": person1_id,
            "person2_id": person2_id,
            "new_type": new_type,
            "value": value
        }
        return await self.execute_write(query, parameters)

    async def delete_relationship(self, person1_id, person2_id):
        """Delete relationship between two people (convert to NEUTRAL)"""
        query = """
        MATCH (p1:Person {id: $person1_id})-[r:RELATION]-(p2:Person {id: $person2_id})
        DELETE r
        """
        parameters = {
            "person1_id": person1_id,
            "person2_id": person2_id
        }
        return await self.execute_write(query, parameters)

    async def get_all_nodes_and_edges(self):
        """Retrieve all persons and their relationships"""
        query = """
        MATCH (p:Person)
        OPTIONAL MATCH (p)-[r:RELATION]-(p2:Person)
        WHERE id(p) < id(p2)
        RETURN p, r, p2
        """
        return await self.execute_query(query)

    async def get_triangles(self):
        """Find all triangles in the graph with 3 actual edges (no NEUTRAL)"""
        query = """
        MATCH (p1:Person)-[r1:RELATION]-(p2:Person)-[r2:RELATION]-(p3:Person)-[r3:RELATION]-(p1)
        WHERE id(p1) < id(p2) AND id(p2) < id(p3)
        AND r1.type <> 'NEUTRAL' AND r2.type <> 'NEUTRAL' AND r3.type <> 'NEUTRAL'
        RETURN p1.id as n1, p2.id as n2, p3.id as n3,
               COALESCE(r1.value, r1.type) as e1,
               COALESCE(r2.value, r2.type) as e2,
               COALESCE(r3.value, r3.type) as e3
        """
        return await self.execute_query(query)

    async def get_person_triangles(self, person_id):
        """Get all triangles that include a specific person with 3 actual edges (no NEUTRAL)"""
        query = """
        MATCH (p1:Person {id: $person_id})-[r1:RELATION]-(p2:Person)-[r2:RELATION]-(p3:Person)-[r3:RELATION]-(p1)
        WHERE id(p2) < id(p3)
        AND r1.type <> 'NEUTRAL' AND r2.type <> 'NEUTRAL' AND r3.type <> 'NEUTRAL'
        RETURN p1.id as n1, p2.id as n2, p3.id as n3,
               COALESCE(r1.value, r1.type) as e1,
               COALESCE(r2.value, r2.type) as e2,
               COALESCE(r3.value, r3.type) as e3
        """
        return await self.execute_query(query, {"person_id": person_id})

    async def get_neighbors_of_neighbors(self, person_id):
        """Get people who are neighbors of this person's neighbors but not direct neighbors.
        A neighbor is someone with a POSITIVE or NEGATIVE relationship (not NEUTRAL)."""
        query = """
        MATCH (p:Person {id: $person_id})-[r1:RELATION]-(neighbor:Person)-[r2:RELATION]-(fof:Person)
        WHERE fof.id <> $person_id
        AND r1.type <> 'NEUTRAL' AND r2.type <> 'NEUTRAL'
        AND NOT EXISTS((p)-[:RELATION {type: 'POSITIVE'}]-(fof))
        AND NOT EXISTS((p)-[:RELATION {type: 'NEGATIVE'}]-(fof))
        RETURN DISTINCT fof.id as id
        """
        return await self.execute_query(query, {"person_id": person_id})

    async def get_neighbors(self, person_id):
        """Get all direct neighbors of a person (POSITIVE or NEGATIVE relationships only)"""
        query = """
        MATCH (p:Person {id: $person_id})-[r:RELATION]-(neighbor:Person)
        WHERE r.type <> 'NEUTRAL'
        RETURN DISTINCT neighbor.id as id
        """
        return await self.execute_query(query, {"person_id": person_id})

    async def count_nodes(self):
        """Count total number of person nodes"""
        query = "MATCH (p:Person) RETURN count(p) as count"
        result = await self.execute_query(query)
        return result[0]["count"] if result else 0

    async def count_relationships(self):
        """Count relationships by type"""
        query = """
        MATCH ()-[r:RELATION]-()
        RETURN r.type as type, count(r)/2 as count
        """
        return await self.execute_query(query)
