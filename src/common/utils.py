import re
from typing import Dict, List


def generate_mermaid_mindmap(url_map: Dict[str, List[str]]) -> str:
    """
    Generate a Mermaid.js mindmap diagram from a URL map, representing site structure as a hierarchical tree.

    Args:
        url_map (Dict[str, List[str]]): Mapping of parent URLs to lists of child URLs (e.g., {'/dashboard': ['/module1', '/module2']}).

    Returns:
        str: Mermaid syntax string for a mindmap, with safe node names (replacing invalid chars with '_').

    Raises:
        ValueError: If url_map is empty or malformed.

    Example:
        url_map = {'/gymnasium': ['/cryptography', '/network']}
        mermaid = generate_mermaid_mindmap(url_map)
        # Output: mindmap\n  root((CyberSkyline Gymnasium))\n    /gymnasium\n      /cryptography\n      /network\n
    """
    if not url_map:
        raise ValueError("URL map cannot be empty")

    mermaid = "mindmap\n  root((CyberSkyline Gymnasium))\n"
    for parent in sorted(url_map.keys()):
        safe_parent = re.sub(r'[^a-zA-Z0-9 ]', '_', parent)
        mermaid += f"    {safe_parent}\n"
        for child in sorted(url_map.get(parent, [])):
            safe_child = re.sub(r'[^a-zA-Z0-9 ]', '_', child)
            mermaid += f"      {safe_child}\n"
    return mermaid
