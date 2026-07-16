"""Development server: serve ``public/`` with file watching and live reload.

On startup we do a build, then serve ``public/`` over HTTP. A background thread
watches ``content/``, ``templates/``, ``static/`` and ``config.toml``; on any
change it runs an incremental rebuild and pushes a reload event to connected
browsers over Server-Sent Events (SSE). The reload ``<script>`` is injected into
HTML responses on the fly, so built output stays clean.
"""

from __future__ import annotations

import mimetypes
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from watchfiles import watch

from cuttlefish.errors import CuttlefishError

from cuttlefish.build import PUBLIC_DIR, STATIC_DIR, build_site
from cuttlefish.config import CONFIG_FILENAME

RELOAD_PATH = "/__reload"

_RELOAD_SCRIPT = (
    "<script>\n"
    "(function(){\n"
    f"  var es = new EventSource('{RELOAD_PATH}');\n"
    "  es.onmessage = function(e){ if(e.data === 'reload'){ location.reload(); } };\n"
    "})();\n"
    "</script>\n"
)

_WATCH_DIRS = (STATIC_DIR, "content", "templates")


def _watch_filter(_change, path: str) -> bool:
    """Include only inputs; ignore generated output and the cache."""
    parts = Path(path).parts
    if PUBLIC_DIR in parts or ".ctf" in parts:
        return False
    if path.endswith(CONFIG_FILENAME):
        return True
    return any(d in parts for d in _WATCH_DIRS)


class _Handler(BaseHTTPRequestHandler):
    server_version = "cuttlefish-dev"

    def log_message(self, *_args) -> None:  # quiet by default
        pass

    # -- routing -----------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        path = self.path.split("?", 1)[0]
        if path == RELOAD_PATH:
            self._serve_sse()
            return
        self._serve_file(path)

    def do_HEAD(self) -> None:  # noqa: N802 (http.server API)
        path = self.path.split("?", 1)[0]
        if path == RELOAD_PATH:
            self.send_error(405, "Method Not Allowed")
            return
        self._serve_file(path, head_only=True)

    # -- live reload (SSE) -------------------------------------------------

    def _serve_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        sub: queue.Queue[str] = queue.Queue()
        self.server.subscribers.add(sub)  # type: ignore[attr-defined]
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    msg = sub.get(timeout=15)
                    self.wfile.write(f"data: {msg}\n\n".encode())
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")  # heartbeat keeps proxies happy
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ValueError):
            pass
        finally:
            self.server.subscribers.discard(sub)  # type: ignore[attr-defined]

    # -- static file serving ----------------------------------------------

    def _resolve(self, url_path: str) -> Path | None:
        rel = url_path.lstrip("/")
        target = (self.server.public_dir / rel).resolve()  # type: ignore[attr-defined]
        public = self.server.public_dir.resolve()  # type: ignore[attr-defined]
        # Prevent path traversal outside public/.
        if public not in target.parents and target != public:
            return None
        if target.is_dir() or url_path.endswith("/") or rel == "":
            target = target / "index.html"
        return target

    def _inject_reload(self, html: str) -> str:
        """Insert the live-reload SSE script so built output stays clean."""
        if "</body>" in html:
            return html.replace("</body>", _RELOAD_SCRIPT + "</body>", 1)
        return html + _RELOAD_SCRIPT

    def _serve_file(self, url_path: str, *, head_only: bool = False) -> None:
        target = self._resolve(url_path)
        if target is None or not target.is_file():
            self._serve_404(head_only=head_only)
            return
        body = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype == "text/html":
            body = self._inject_reload(body.decode("utf-8")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _serve_404(self, *, head_only: bool = False) -> None:
        """Serve the site's ``404.html`` (status 404) for a missing path.

        Static hosts (GitHub Pages, Netlify, …) serve a root ``404.html`` on a
        miss; doing the same here keeps local preview honest. If the site ships
        no ``404.html``, fall back to a plain error.
        """
        page = self.server.public_dir / "404.html"  # type: ignore[attr-defined]
        if not page.is_file():
            self.send_error(404, "Not Found")
            return
        body = self._inject_reload(page.read_text(encoding="utf-8")).encode("utf-8")
        self.send_response(404)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)


class _DevServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr, handler, public_dir: Path):
        super().__init__(addr, handler)
        self.public_dir = public_dir
        self.subscribers: set[queue.Queue[str]] = set()

    def broadcast(self, msg: str = "reload") -> None:
        for sub in list(self.subscribers):
            sub.put(msg)


def _watch_loop(
    root: Path,
    server: _DevServer,
    stop: threading.Event,
    drafts: bool,
    console: Console,
) -> None:
    for _changes in watch(root, watch_filter=_watch_filter, stop_event=stop):
        try:
            stats = build_site(root, drafts=drafts, base_path="", console=Console(quiet=True))
            console.print(
                f"[cyan]↻[/cyan] Rebuilt in {stats.elapsed_str} [dim]·[/dim] {stats.counts_str}"
            )
            server.broadcast("reload")
        except CuttlefishError as exc:  # keep the server alive on build errors
            console.print(
                f"[bold red]error:[/bold red] {escape(exc.summary)} "
                f"[dim]·[/dim] {escape(exc.detail)}"
            )
        except Exception as exc:  # unexpected bug: still don't kill the server
            console.print(f"[bold red]error:[/bold red] Build failed: {escape(str(exc))}")


def serve_site(
    root: Path,
    *,
    port: int = 8000,
    drafts: bool = True,
    reload: bool = True,
    console: Console | None = None,
) -> None:
    console = console or Console()
    root = root.resolve()
    public_dir = root / PUBLIC_DIR

    # Preview at the local root: ignore base_url's subpath so links resolve
    # against http://127.0.0.1:<port>/ rather than a deploy prefix like /repo.
    build_site(root, drafts=drafts, base_path="", console=console)

    server = _DevServer(("127.0.0.1", port), _Handler, public_dir)
    stop = threading.Event()

    watcher: threading.Thread | None = None
    if reload:
        watcher = threading.Thread(
            target=_watch_loop, args=(root, server, stop, drafts, console), daemon=True
        )
        watcher.start()

    url = f"http://127.0.0.1:{port}/"
    console.print(f"  Serving [bold]{PUBLIC_DIR}/[/bold]  →  [link={url}]{url}[/link]")
    if reload:
        watched = ", ".join(("content", "templates", STATIC_DIR, CONFIG_FILENAME))
        console.print(f"  Watching {watched} [dim]·[/dim] live reload on")
    console.print("  [dim]Press Ctrl+C to stop[/dim]")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/dim]")
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
