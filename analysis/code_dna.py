"""
analysis/code_dna.py
Extract stylistic "Code DNA" from raw source files and render as SVG.
"""

import re

def analyze_style(samples: list[dict]) -> dict:
    """
    Analyze stylistic patterns across provided code samples.
    """
    if not samples:
        return {}

    total_lines = 0
    comment_lines = 0
    blank_lines = 0
    
    # Brace styles
    same_line_braces = 0
    next_line_braces = 0
    
    # Naming conventions
    snake_cases = 0
    camel_cases = 0
    
    # Indentation
    spaces = 0
    tabs = 0
    
    # Function lengths
    func_counts = 0
    func_total_lines = 0

    for sample in samples:
        content = sample["content"]
        lines = content.splitlines()
        total_lines += len(lines)
        
        # 1. Basic counts
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
                continue
            if stripped.startswith(("#", "//", "/*", "*", '"""', "'''")):
                comment_lines += 1
            
            # 2. Braces (heuristic)
            if "{" in line and stripped.endswith("{"):
                same_line_braces += 1
            elif stripped == "{":
                next_line_braces += 1
                
            # 3. Naming (heuristic for variables/functions)
            # snake_case: lowercase words separated by underscores
            # camelCase: lowercase start, then uppercase letters
            snake_matches = len(re.findall(r"\b[a-z]+_[a-z0-9_]+\b", line))
            camel_matches = len(re.findall(r"\b[a-z]+[A-Z][a-zA-Z0-9]+\b", line))
            snake_cases += snake_matches
            camel_cases += camel_matches
            
            # 4. Indent
            if line.startswith("\t"):
                tabs += 1
            elif line.startswith("  "):
                spaces += 1

        # 5. Function length (very simplified)
        # Count lines between 'def ' or 'function ' or 'func '
        func_starts = [i for i, l in enumerate(lines) if re.search(r"\b(def|function|func)\s+\w+", l)]
        func_counts += len(func_starts)
        # Approximate length as distance between starts
        for i in range(len(func_starts)-1):
            func_total_lines += (func_starts[i+1] - func_starts[i])

    # Aggregates
    return {
        "comment_density": (comment_lines / total_lines * 100) if total_lines else 0,
        "blank_ratio": (blank_lines / total_lines * 100) if total_lines else 0,
        "brace_style": "same_line" if same_line_braces >= next_line_braces else "next_line",
        "naming": "snake_case" if snake_cases >= camel_cases else "camelCase",
        "indent": "spaces" if spaces >= tabs else "tabs",
        "avg_func_len": (func_total_lines / func_counts) if func_counts else 15,
    }

def generate_dna_svg(traits: dict) -> str:
    """
    Generate a literal DNA double-helix SVG where bands represent traits.
    """
    if not traits:
        return ""

    # DNA Constants
    width = 300
    height = 500
    steps = 15
    y_step = height / steps
    
    # Colors mapped to traits
    # comment_density -> green intensity
    # blank_ratio -> blue intensity
    # naming -> purple (snake) vs yellow (camel)
    # indent -> cyan (spaces) vs orange (tabs)
    
    c_dens = min(traits.get("comment_density", 10) * 5, 255)
    b_ratio = min(traits.get("blank_ratio", 10) * 5, 255)
    name_color = "#A855F7" if traits.get("naming") == "snake_case" else "#F9A826"
    indent_color = "#22D3EE" if traits.get("indent") == "spaces" else "#FB923C"
    
    svg = f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
    svg += '<defs><linearGradient id="helixGrad" x1="0%" y1="0%" x2="100%" y2="0%">'
    svg += f'<stop offset="0%" style="stop-color:{name_color};stop-opacity:1" />'
    svg += f'<stop offset="100%" style="stop-color:{indent_color};stop-opacity:1" />'
    svg += '</linearGradient></defs>'
    
    for i in range(steps):
        y = i * y_step + 20
        # Sine wave for helix
        import math
        x1 = 150 + 80 * math.sin(i * 0.6)
        x2 = 150 + 80 * math.sin(i * 0.6 + math.pi)
        
        # Horizontal bands (the traits)
        if i % 2 == 0:
            color = f"rgba(108,99,255,{0.3 + (i/steps)*0.7})" # Varied opacity
            svg += f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="4" stroke-linecap="round" />'
            
        # Helix circles
        svg += f'<circle cx="{x1}" cy="{y}" r="6" fill="{name_color}" />'
        svg += f'<circle cx="{x2}" cy="{y}" r="6" fill="{indent_color}" />'
        
    svg += '</svg>'
    return svg
