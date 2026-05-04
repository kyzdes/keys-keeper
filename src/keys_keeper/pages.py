"""Server-rendered HTML pages."""
from pathlib import Path
from keys_keeper.paths import Paths


def render_dashboard(*, paths: Paths, token: str) -> str:
    # Minimal HTML that includes the token in the URL initially and strips it via JS.
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>keys-keeper · admin</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body>
<noscript>JavaScript required.</noscript>
<div id="app">Loading dashboard…</div>
<script>
const TOKEN = "{token}";
sessionStorage.setItem("kk_token", TOKEN);
history.replaceState({{}}, "", "/");
</script>
<script src="/static/app.js"></script>
</body>
</html>
"""
