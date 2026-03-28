"""
analysis/ecosystem.py
Build a network graph of shared dependencies across repositories using pyvis.
"""

from pyvis.network import Network
import tempfile
import os

def build_ecosystem_graph(repo_deps: dict) -> str:
    """
    Build a pyvis network graph from repo_deps {repo_name: [deps]}.
    Returns the HTML content of the graph.
    """
    if not repo_deps:
        return ""

    # Initialize Pyvis Network
    # Use dark theme settings
    net = Network(height="500px", width="100%", bgcolor="#0f0c29", font_color="white")
    
    # Configure physics for better layout
    net.force_atlas_2based()
    
    # Track nodes to avoid duplicates
    added_nodes = set()
    
    for repo, deps in repo_deps.items():
        # Add Repo node
        if repo not in added_nodes:
            net.add_node(repo, label=repo, title=f"Repository: {repo}", color="#6C63FF", size=25, shape="dot")
            added_nodes.add(repo)
            
        for dep in deps:
            # Add Dependency node
            if dep not in added_nodes:
                net.add_node(dep, label=dep, title=f"Dependency: {dep}", color="#EC4899", size=15, shape="diamond")
                added_nodes.add(dep)
            
            # Add Edge
            net.add_edge(repo, dep, color="rgba(255,255,255,0.2)")

    # Save to a temporary HTML file and read it back
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        path = tmp.name
        net.save_graph(path)
        
    with open(path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    os.remove(path)
    return html_content
