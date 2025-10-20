import re

def generate_mermaid_mindmap(url_map):
    mermaid = "mindmap\n  root((Site Map))\n"
    for parent in sorted(url_map):
        mermaid += f"    {re.sub(r'[^a-zA-Z0-9 ]', '_', parent)}\n"
        for child in sorted(url_map.get(parent, [])):
            mermaid += f"      {re.sub(r'[^a-zA-Z0-9 ]', '_', child)}\n"
    return mermaid
