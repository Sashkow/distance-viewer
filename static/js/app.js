// Global variables
let simulation;
let svg;
let width, height;
let nodesGroup, linksGroup, linkLabelsGroup;
let currentSimulationId = null;
let pollingInterval = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initializeGraph();
    attachEventListeners();
    loadGraph();
    setupScrollDetection();
});

function initializeGraph() {
    const container = document.getElementById('graph-container');
    width = container.clientWidth;
    height = container.clientHeight;

    svg = d3.select('#graph')
        .attr('width', width)
        .attr('height', height);

    linksGroup = svg.append('g').attr('class', 'links');
    linkLabelsGroup = svg.append('g').attr('class', 'link-labels');
    nodesGroup = svg.append('g').attr('class', 'nodes');

    // Initialize force simulation
    simulation = d3.forceSimulation()
        .force('link', d3.forceLink().id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(30));
}

function attachEventListeners() {
    document.getElementById('init-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await initializeNewGraph();
    });

    // Add real-time validation for probability sum
    const probInputs = ['positive-prob', 'negative-prob', 'neutral-prob'];
    probInputs.forEach(id => {
        document.getElementById(id).addEventListener('input', validateProbabilitySum);
    });

    document.getElementById('step-btn').addEventListener('click', async () => {
        await runIteration();
    });

    document.getElementById('run-btn').addEventListener('click', async () => {
        await runSimulation();
    });

    document.getElementById('stop-btn').addEventListener('click', async () => {
        await stopSimulation();
    });

    document.getElementById('reset-btn').addEventListener('click', async () => {
        if (confirm('Are you sure you want to reset the graph?')) {
            await resetGraph();
        }
    });

    // Toggle edge visibility
    document.getElementById('toggle-positive').addEventListener('click', (e) => {
        e.preventDefault();
        toggleEdgeVisibility('POSITIVE');
    });

    document.getElementById('toggle-negative').addEventListener('click', (e) => {
        e.preventDefault();
        toggleEdgeVisibility('NEGATIVE');
    });

    // Toggle MDS layout
    document.getElementById('use-mds-layout').addEventListener('change', async (e) => {
        await loadGraph(); // Reload graph with current toggle state
    });
}

function validateProbabilitySum() {
    const positiveProb = parseFloat(document.getElementById('positive-prob').value) || 0;
    const negativeProb = parseFloat(document.getElementById('negative-prob').value) || 0;
    const neutralProb = parseFloat(document.getElementById('neutral-prob').value) || 0;

    const sum = positiveProb + negativeProb + neutralProb;
    const warning = document.getElementById('prob-sum-warning');

    if (Math.abs(sum - 1.0) > 0.001) {
        warning.style.display = 'block';
        warning.textContent = `⚠️ Probabilities sum to ${sum.toFixed(3)}, must equal 1.0`;
        return false;
    } else {
        warning.style.display = 'none';
        return true;
    }
}

function autoAdjustNeutralProbability() {
    const positiveProb = parseFloat(document.getElementById('positive-prob').value) || 0;
    const negativeProb = parseFloat(document.getElementById('negative-prob').value) || 0;

    // Calculate required neutral to make sum = 1.0
    const neutralProb = 1.0 - positiveProb - negativeProb;

    // Clamp to [0, 1]
    const adjustedNeutral = Math.max(0, Math.min(1, neutralProb));

    document.getElementById('neutral-prob').value = adjustedNeutral.toFixed(3);

    // Update warning display
    validateProbabilitySum();

    return adjustedNeutral;
}

async function initializeNewGraph() {
    const numPeople = parseInt(document.getElementById('num-people').value);
    const positiveProb = parseFloat(document.getElementById('positive-prob').value);
    const negativeProb = parseFloat(document.getElementById('negative-prob').value);

    // Auto-adjust neutral probability to make sum = 1.0
    const neutralProb = autoAdjustNeutralProbability();

    setLoading(true);
    showStatus('Initializing graph...', 'info');

    try {
        const response = await fetch('/api/initialize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                num_people: numPeople,
                positive_prob: positiveProb,
                negative_prob: negativeProb,
                neutral_prob: neutralProb
            })
        });

        const data = await response.json();

        if (data.success) {
            showStatus('Graph initialized successfully!', 'success');
            await loadGraph();
            updateStats(data.stats);
        }
    } catch (error) {
        showStatus('Error initializing graph: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

async function loadGraph() {
    try {
        const useMDS = document.getElementById('use-mds-layout').checked;
        const endpoint = useMDS ? '/api/graph/mds' : '/api/graph';

        const response = await fetch(endpoint);
        const data = await response.json();

        // Display PCA info if using MDS
        if (useMDS && data.pca_info) {
            displayPCAInfo(data.pca_info);
        } else {
            document.getElementById('pca-info').style.display = 'none';
        }

        // Display compromise info if available
        if (useMDS && data.compromise_info && data.compromise_info.n_edges_changed > 0) {
            displayCompromiseInfo(data.compromise_info);
        } else {
            document.getElementById('compromise-info').style.display = 'none';
        }

        renderGraph(data, useMDS);
        await updateStatsFromServer();
    } catch (error) {
        console.error('Error loading graph:', error);
        showStatus('Error loading graph: ' + error.message, 'error');
    }
}

function getDivergenceColor(actualDistance, desiredDistance) {
    /**
     * Returns color based on how the actual distance compares to desired.
     * - Green: actual ≈ desired (within 5%)
     * - Blue: actual > desired (stretched, too far)
     * - Red: actual < desired (compressed, too close)
     */

    const diff = actualDistance - desiredDistance;
    const divergence = Math.abs(diff) / desiredDistance;

    if (divergence < 0.02) {
        // Perfect or near-perfect match - green (within 2%)
        return '#4caf50';
    }

    // Map divergence to intensity (cap at 100%)
    const intensity = Math.min(divergence * 1.5, 1);

    if (diff > 0) {
        // Stretched: actual > desired -> Blue gradient
        const red = Math.floor(76 * (1 - intensity));
        const green = Math.floor(175 * (1 - intensity));
        const blue = Math.floor(255 * intensity + 100 * (1 - intensity)); // More blue as it stretches
        return `rgb(${red}, ${green}, ${blue})`;
    } else {
        // Compressed: actual < desired -> Red gradient
        const red = Math.floor(255 * intensity + 76 * (1 - intensity)); // More red as it compresses
        const green = Math.floor(76 * (1 - intensity));
        const blue = Math.floor(100 * (1 - intensity));
        return `rgb(${red}, ${green}, ${blue})`;
    }
}

function displayPCAInfo(pcaInfo) {
    const variance = pcaInfo.variance_explained;
    const total2D = pcaInfo.total_variance_2d;

    const html = `
        <div style="font-size: 0.9em;">
            PC1: ${variance[0]}% | PC2: ${variance[1]}% | PC3: ${variance[2]}% | PC4: ${variance[3]}% | PC5: ${variance[4]}%
        </div>
        <div style="margin-top: 5px; font-weight: 600; color: ${total2D > 80 ? '#4caf50' : total2D > 60 ? '#ff9800' : '#f44336'};">
            2D captures: ${total2D}% of distance variance
        </div>
    `;

    document.getElementById('pca-variance').innerHTML = html;
    document.getElementById('pca-info').style.display = 'block';
}

function displayCompromiseInfo(compromiseInfo) {
    const html = `
        <div style="font-size: 0.9em;">
            Total compromise: ${compromiseInfo.total_absolute.toFixed(3)} (${compromiseInfo.percentage.toFixed(1)}% of initial distances)
        </div>
        <div style="margin-top: 5px;">
            ${compromiseInfo.n_edges_changed} edges modified during simulation
        </div>
    `;

    document.getElementById('compromise-stats').innerHTML = html;
    document.getElementById('compromise-info').style.display = 'block';
}

function renderGraph(data, useMDS = false) {
    // Compute clusters based on positive relationships
    const clusters = computeClusters(data);

    // Assign cluster to each node
    data.nodes.forEach(node => {
        node.cluster = clusters.nodeToCluster.get(node.id) || -1;
        // Set cluster center position
        if (node.cluster >= 0) {
            const clusterInfo = clusters.clusterCenters[node.cluster];
            node.clusterX = clusterInfo.x;
            node.clusterY = clusterInfo.y;
        }
    });

    // Scale factor for converting float values to pixel distances
    const DISTANCE_SCALE = 300; // 1.0 float value = 300 pixels

    // Update links
    const link = linksGroup
        .selectAll('line')
        .data(data.links, d => `${d.source.id || d.source}-${d.target.id || d.target}`);

    link.exit().remove();

    const linkEnter = link.enter()
        .append('line');

    const linkUpdate = linkEnter.merge(link)
        .attr('class', d => {
            // For continuous edges (with values), don't add type class to avoid CSS override
            if (d.value !== null && d.value !== undefined) {
                return 'link';
            }
            // For discrete edges, add type class for CSS coloring
            return `link ${d.type}`;
        });

    // Update link labels (for continuous values)
    const linkLabel = linkLabelsGroup
        .selectAll('text')
        .data(data.links, d => `${d.source.id || d.source}-${d.target.id || d.target}`);

    linkLabel.exit().remove();

    const linkLabelEnter = linkLabel.enter()
        .append('text')
        .attr('class', 'link-label')
        .attr('text-anchor', 'middle')
        .attr('dy', -3);

    const linkLabelUpdate = linkLabelEnter.merge(linkLabel)
        .text(d => {
            if (d.value === null || d.value === undefined) return '';

            let text = d.value.toFixed(2);

            // Add change indicator if available (+/-)
            if (d.change !== null && d.change !== undefined && Math.abs(d.change) > 0.001) {
                const changeSign = d.change > 0 ? '+' : '';
                text += ` (${changeSign}${d.change.toFixed(2)})`;
            }

            return text;
        })
        .attr('fill', d => {
            // Color the change text
            if (d.change !== null && d.change !== undefined && Math.abs(d.change) > 0.001) {
                return d.change > 0 ? '#4caf50' : '#f44336'; // Green for increase, red for decrease
            }
            return '#333'; // Default color
        });

    // Update nodes
    const node = nodesGroup
        .selectAll('g')
        .data(data.nodes, d => d.id);

    node.exit().remove();

    const nodeEnter = node.enter()
        .append('g')
        .call(d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded));

    nodeEnter.append('circle')
        .attr('r', 15);

    nodeEnter.append('text')
        .attr('dy', 1)
        .text(d => d.id);

    const nodeUpdate = nodeEnter.merge(node);

    // Update class based on status (unbalanced, balanced, or none)
    nodeUpdate.attr('class', d => `node ${d.status || 'none'}`);

    // Update text for existing nodes in case IDs changed
    nodeUpdate.select('text').text(d => d.id);

    // Update simulation with clustering forces (or disable if using MDS)
    if (useMDS) {
        // MDS mode: use fixed positions from backend, center and scale to viewport
        const centerX = width / 2;
        const centerY = height / 2;

        // Find bounds of MDS coordinates
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        data.nodes.forEach(node => {
            if (node.x < minX) minX = node.x;
            if (node.x > maxX) maxX = node.x;
            if (node.y < minY) minY = node.y;
            if (node.y > maxY) maxY = node.y;
        });

        const rangeX = maxX - minX || 1;
        const rangeY = maxY - minY || 1;
        const scale = Math.min(width / rangeX, height / rangeY) * 0.8;

        // Center and scale nodes
        data.nodes.forEach(node => {
            node.fx = centerX + (node.x - (minX + maxX) / 2) * scale;
            node.fy = centerY + (node.y - (minY + maxY) / 2) * scale;
        });

        // Disable force simulation, just render fixed positions
        simulation.stop();

        // Manually update positions once
        // Update simulation nodes so D3 can resolve source/target IDs to objects
        simulation.nodes(data.nodes);
        simulation.force('link').links(data.links);

        linkUpdate
            .attr('x1', d => d.source.fx || d.source.x)
            .attr('y1', d => d.source.fy || d.source.y)
            .attr('x2', d => d.target.fx || d.target.x)
            .attr('y2', d => d.target.fy || d.target.y)
            .attr('stroke', d => {
                // For continuous values, color by divergence
                if (d.value !== null && d.value !== undefined) {
                    const x1 = d.source.fx || d.source.x;
                    const y1 = d.source.fy || d.source.y;
                    const x2 = d.target.fx || d.target.x;
                    const y2 = d.target.fy || d.target.y;
                    const actualDistance = Math.sqrt(
                        Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2)
                    );
                    const desiredDistance = d.value * DISTANCE_SCALE;
                    return getDivergenceColor(actualDistance, desiredDistance);
                }
                return null;
            });

        linkLabelUpdate
            .attr('x', d => ((d.source.fx || d.source.x) + (d.target.fx || d.target.x)) / 2)
            .attr('y', d => ((d.source.fy || d.source.y) + (d.target.fy || d.target.y)) / 2);

        nodeUpdate
            .attr('transform', d => `translate(${d.fx || d.x},${d.fy || d.y})`);

    } else {
        // Force simulation mode: dynamic layout
        // Remove fixed positions if any
        data.nodes.forEach(node => {
            delete node.fx;
            delete node.fy;
        });

        simulation
            .nodes(data.nodes)
            .on('tick', () => {
            linkUpdate
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y)
                .attr('stroke', d => {
                    // For continuous values, color by divergence
                    if (d.value !== null && d.value !== undefined) {
                        const actualDistance = Math.sqrt(
                            Math.pow(d.target.x - d.source.x, 2) +
                            Math.pow(d.target.y - d.source.y, 2)
                        );
                        const desiredDistance = d.value * DISTANCE_SCALE;
                        const color = getDivergenceColor(actualDistance, desiredDistance);
                        // Debug: log first edge color calculation
                        if (Math.random() < 0.01) {
                            console.log(`Edge color: actual=${actualDistance.toFixed(1)}, desired=${desiredDistance.toFixed(1)}, color=${color}`);
                        }
                        return color;
                    }
                    // For discrete values, use default colors
                    return null; // Will use CSS classes
                });

            linkLabelUpdate
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);

                nodeUpdate
                    .attr('transform', d => `translate(${d.x},${d.y})`);
            });

        // Update forces
        simulation.force('link')
            .links(data.links)
            .distance(d => {
                // Use float value as distance if available
                if (d.value !== null && d.value !== undefined) {
                    return d.value * DISTANCE_SCALE;
                }
                // Default distances for discrete types
                return d.type === 'POSITIVE' ? 80 : 150;
            })
            .strength(d => {
                // For continuous values, use strong force to achieve target distance
                if (d.value !== null && d.value !== undefined) {
                    return 1.5;
                }
                // Default strength for discrete types
                return d.type === 'POSITIVE' ? 1 : 0.3;
            });

        // Add clustering force for positive relationships
        simulation.force('cluster', forceCluster());

        // Add collision to prevent overlap
        simulation.force('collision', d3.forceCollide().radius(25));

        simulation.alpha(1).restart();
    }
}

function computeClusters(data) {
    // Build adjacency list for positive relationships only
    const adjacency = new Map();
    data.nodes.forEach(node => adjacency.set(node.id, new Set()));

    data.links.forEach(link => {
        if (link.type === 'POSITIVE') {
            const sourceId = link.source.id || link.source;
            const targetId = link.target.id || link.target;
            adjacency.get(sourceId).add(targetId);
            adjacency.get(targetId).add(sourceId);
        }
    });

    // Find connected components (clusters) using DFS
    const visited = new Set();
    const nodeToCluster = new Map();
    const clusters = [];
    let clusterIndex = 0;

    data.nodes.forEach(node => {
        if (!visited.has(node.id)) {
            const cluster = [];
            const stack = [node.id];

            while (stack.length > 0) {
                const current = stack.pop();
                if (visited.has(current)) continue;

                visited.add(current);
                cluster.push(current);
                nodeToCluster.set(current, clusterIndex);

                // Add all positive neighbors
                adjacency.get(current).forEach(neighbor => {
                    if (!visited.has(neighbor)) {
                        stack.push(neighbor);
                    }
                });
            }

            if (cluster.length > 0) {
                clusters.push(cluster);
                clusterIndex++;
            }
        }
    });

    // Compute cluster centers in a circular layout
    const clusterCenters = clusters.map((cluster, i) => {
        const angle = (i / clusters.length) * 2 * Math.PI;
        const radius = Math.min(width, height) * 0.3;
        return {
            x: width / 2 + radius * Math.cos(angle),
            y: height / 2 + radius * Math.sin(angle),
            size: cluster.length
        };
    });

    return { nodeToCluster, clusterCenters, clusters };
}

function forceCluster() {
    let nodes;
    const strength = 0.2;

    function force(alpha) {
        nodes.forEach(node => {
            if (node.cluster >= 0 && node.clusterX !== undefined) {
                node.vx -= (node.x - node.clusterX) * strength * alpha;
                node.vy -= (node.y - node.clusterY) * strength * alpha;
            }
        });
    }

    force.initialize = function(_) {
        nodes = _;
    };

    return force;
}

async function runIteration() {
    const actionProb = parseFloat(document.getElementById('action-prob').value);

    setLoading(true);
    showStatus('Running iteration...', 'info');

    try {
        const response = await fetch('/api/iterate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action_probability: actionProb
            })
        });

        const data = await response.json();

        showStatus(`Iteration complete. Made ${data.changes_made} changes.`, 'success');
        await loadGraph();
        updateStats(data.stats);
    } catch (error) {
        showStatus('Error running iteration: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

async function runSimulation() {
    const actionProb = parseFloat(document.getElementById('action-prob').value);
    const maxIterations = parseInt(document.getElementById('max-iterations').value);

    setLoading(true);
    showStatus('Starting simulation...', 'info');
    showProgress(true);

    try {
        // Start the simulation
        const response = await fetch('/api/simulate/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                max_iterations: maxIterations,
                action_probability: actionProb
            })
        });

        const data = await response.json();
        currentSimulationId = data.simulation_id;

        // Show stop button
        document.getElementById('run-btn').style.display = 'none';
        document.getElementById('stop-btn').style.display = 'block';

        // Poll for progress
        pollingInterval = setInterval(async () => {
            await checkSimulationStatus();
        }, 500); // Check every 500ms

    } catch (error) {
        showStatus('Error starting simulation: ' + error.message, 'error');
        setLoading(false);
        showProgress(false);
    }
}

async function checkSimulationStatus() {
    if (!currentSimulationId) return;

    try {
        const response = await fetch(`/api/simulate/status/${currentSimulationId}`);
        const data = await response.json();

        // Update progress bar
        const progress = (data.current_iteration / data.max_iterations) * 100;
        updateProgress(progress, data.current_iteration, data.max_iterations);

        // Update graph and stats every 10 iterations (when current_stats is available)
        if (data.current_stats && data.current_iteration % 10 === 0) {
            await loadGraph();
            updateStats(data.current_stats);
        }

        // Check if simulation is complete
        if (data.status === 'completed') {
            clearInterval(pollingInterval);
            pollingInterval = null;
            currentSimulationId = null;

            const message = data.result.converged
                ? `Simulation converged after ${data.result.iterations} iterations!`
                : `Simulation stopped after ${data.result.iterations} iterations.`;

            showStatus(message, data.result.converged ? 'success' : 'info');
            await loadGraph();
            updateStats(data.result.final_stats);

            setLoading(false);
            showProgress(false);
            document.getElementById('run-btn').style.display = 'block';
            document.getElementById('stop-btn').style.display = 'none';

        } else if (data.status === 'stopped') {
            clearInterval(pollingInterval);
            pollingInterval = null;
            currentSimulationId = null;

            showStatus('Simulation stopped by user', 'info');
            await loadGraph();
            await updateStatsFromServer();

            setLoading(false);
            showProgress(false);
            document.getElementById('run-btn').style.display = 'block';
            document.getElementById('stop-btn').style.display = 'none';

        } else if (data.status === 'timeout') {
            clearInterval(pollingInterval);
            pollingInterval = null;
            currentSimulationId = null;

            showStatus('Simulation timed out after 5 minutes', 'error');
            await loadGraph();
            await updateStatsFromServer();

            setLoading(false);
            showProgress(false);
            document.getElementById('run-btn').style.display = 'block';
            document.getElementById('stop-btn').style.display = 'none';

        } else if (data.status === 'error') {
            clearInterval(pollingInterval);
            pollingInterval = null;
            currentSimulationId = null;

            showStatus('Simulation error: ' + data.error, 'error');

            setLoading(false);
            showProgress(false);
            document.getElementById('run-btn').style.display = 'block';
            document.getElementById('stop-btn').style.display = 'none';
        }

    } catch (error) {
        console.error('Error checking simulation status:', error);
    }
}

async function stopSimulation() {
    if (!currentSimulationId) return;

    try {
        await fetch(`/api/simulate/stop/${currentSimulationId}`, {
            method: 'POST'
        });

        showStatus('Stopping simulation...', 'info');

    } catch (error) {
        showStatus('Error stopping simulation: ' + error.message, 'error');
    }
}

async function resetGraph() {
    setLoading(true);
    showStatus('Resetting graph...', 'info');

    try {
        const response = await fetch('/api/reset', {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('Graph reset successfully!', 'success');
            await loadGraph();
            updateStats({
                num_people: 0,
                relationships: {},
                total_triangles: 0,
                balanced_triangles: 0,
                unbalanced_triangles: 0,
                balance_ratio: 0
            });
        }
    } catch (error) {
        showStatus('Error resetting graph: ' + error.message, 'error');
    } finally {
        setLoading(false);
    }
}

async function updateStatsFromServer() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        updateStats(stats);
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

function updateStats(stats) {
    const statsDiv = document.getElementById('stats');

    if (stats.num_people === 0) {
        statsDiv.innerHTML = '<p>No graph loaded</p>';
        return;
    }

    const relationships = stats.relationships || {};
    const positive = relationships.POSITIVE || 0;
    const negative = relationships.NEGATIVE || 0;
    const neutral = relationships.NEUTRAL || 0;

    const balancePercentage = (stats.balance_ratio * 100).toFixed(1);

    statsDiv.innerHTML = `
        <p><strong>People:</strong> ${stats.num_people}</p>
        <p><strong>Relationships:</strong></p>
        <p style="margin-left: 15px;">
            Positive: ${positive}<br>
            Negative: ${negative}<br>
            Neutral: ${neutral}
        </p>
        <p><strong>Triangles:</strong> ${stats.total_triangles}</p>
        <p><strong>Balanced:</strong> ${stats.balanced_triangles}</p>
        <p><strong>Unbalanced:</strong> ${stats.unbalanced_triangles}</p>
        <p><strong>Balance Ratio:</strong> ${balancePercentage}%</p>
    `;
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = message;
    statusDiv.className = type;
    statusDiv.style.display = 'block';

    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

function setLoading(loading) {
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
        // Don't disable stop button during loading
        if (button.id === 'stop-btn' && loading) {
            return;
        }
        button.disabled = loading;
    });
}

function showProgress(show) {
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.display = show ? 'block' : 'none';
    if (!show) {
        updateProgress(0, 0, 0);
    }
}

function updateProgress(percentage, current, max) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    progressFill.style.width = percentage + '%';
    progressText.textContent = `Iteration ${current} / ${max}`;
}

function toggleEdgeVisibility(edgeType) {
    const toggleBtn = document.getElementById(`toggle-${edgeType.toLowerCase()}`);
    const isActive = toggleBtn.getAttribute('data-active') === 'true';

    // Toggle state
    const newState = !isActive;
    toggleBtn.setAttribute('data-active', newState);
    toggleBtn.textContent = newState ? 'Hide' : 'Show';

    // Update edge visibility
    d3.selectAll(`.link.${edgeType}`)
        .classed('hidden', !newState);
}

// Drag functions for D3
function dragStarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
}

function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
}

function dragEnded(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
}

// Scroll detection for footer mascot
function setupScrollDetection() {
    function checkScroll() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollHeight = document.documentElement.scrollHeight;
        const clientHeight = document.documentElement.clientHeight;

        // Check if scrolled to bottom (within 50px threshold)
        if (scrollTop + clientHeight >= scrollHeight - 50) {
            document.body.classList.add('scrolled-to-bottom');
        } else {
            document.body.classList.remove('scrolled-to-bottom');
        }
    }

    window.addEventListener('scroll', checkScroll);
    checkScroll(); // Check on load
}
