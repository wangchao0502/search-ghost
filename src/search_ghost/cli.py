"""
ghost CLI — Typer-based command line interface.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="ghost",
    help="search-ghost: local-first personal knowledge base",
    no_args_is_help=True,
)
console = Console()


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


@app.command()
def serve(
    kb_path: str = typer.Option("./kb", "--kb-path", "-k", help="Knowledge base root path"),
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev)"),
) -> None:
    """Start the search-ghost API server."""
    import uvicorn

    os.environ.setdefault("GHOST_KB_PATH", kb_path)
    console.print(f"[bold green]Starting search-ghost[/bold green] — KB: [cyan]{kb_path}[/cyan]")
    uvicorn.run(
        "search_ghost.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ---------------------------------------------------------------------------
# ingest
# ---------------------------------------------------------------------------


@app.command()
def ingest(
    path: Path = typer.Argument(..., help="File or directory to ingest"),
    kb_path: str = typer.Option("./kb", "--kb-path", "-k"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags"),
    base_url: str = typer.Option("http://localhost:8000", "--api"),
) -> None:
    """Ingest a file (or directory with --batch) into the knowledge base."""
    import httpx

    async def _ingest_file(p: Path) -> None:
        async with httpx.AsyncClient(base_url=base_url, timeout=60) as client:
            with p.open("rb") as f:
                resp = await client.post(
                    "/api/ingest",
                    files={"file": (p.name, f, _guess_mime(p))},
                    params={"title": title or p.stem, "tags": tags},
                )
            resp.raise_for_status()
            data = resp.json()
            console.print(f"[green]Queued[/green] {p.name} → task [cyan]{data['task_id']}[/cyan]")

    if path.is_dir():
        files = list(path.glob("**/*"))
        files = [f for f in files if f.is_file()]
        console.print(f"Ingesting {len(files)} files from [cyan]{path}[/cyan]")
        for f in files:
            asyncio.run(_ingest_file(f))
    else:
        asyncio.run(_ingest_file(path))


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    kb_path: str = typer.Option("./kb", "--kb-path", "-k"),
    top_k: int = typer.Option(6, "--top-k", "-n"),
    base_url: str = typer.Option("http://localhost:8000", "--api"),
) -> None:
    """Search the knowledge base."""
    import httpx

    async def _search() -> None:
        async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
            resp = await client.get("/api/search", params={"q": query, "top_k": top_k})
            resp.raise_for_status()
            data = resp.json()

        table = Table(title=f'Results for "{query}"', show_lines=True)
        table.add_column("Score", width=8)
        table.add_column("Title", width=24)
        table.add_column("Excerpt")

        for r in data["results"]:
            table.add_row(
                f"{r['score']:.4f}",
                r.get("doc_title") or r["doc_id"][:8],
                r["text"][:120].replace("\n", " "),
            )
        console.print(table)

    asyncio.run(_search())


# ---------------------------------------------------------------------------
# chat
# ---------------------------------------------------------------------------


@app.command()
def chat(
    question: str = typer.Argument(..., help="Question to ask"),
    kb_path: str = typer.Option("./kb", "--kb-path", "-k"),
    base_url: str = typer.Option("http://localhost:8000", "--api"),
) -> None:
    """Ask a question using RAG chat (streams the answer)."""
    import httpx

    async def _chat() -> None:
        async with httpx.AsyncClient(base_url=base_url, timeout=120) as client:
            async with client.stream(
                "POST",
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": question}],
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                console.print(f"\n[bold]Q:[/bold] {question}\n[bold]A:[/bold] ", end="")
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    import json

                    event = json.loads(line[6:])
                    if event["type"] == "delta":
                        console.print(event["content"], end="", highlight=False)
                    elif event["type"] == "done":
                        console.print()

    asyncio.run(_chat())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _guess_mime(path: Path) -> str:
    import mimetypes

    mime, _ = mimetypes.guess_type(str(path))
    return mime or "text/plain"


if __name__ == "__main__":
    app()
