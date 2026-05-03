"""HTTP route handlers, organized by resource."""

from . import agents as agents_routes
from . import ask as ask_routes
from . import documents as documents_routes
from . import mcp as mcp_routes
from . import threads as threads_routes


def all_routers():
    """Return every APIRouter in deterministic order, ready for app.include_router."""
    return [
        threads_routes.router,
        documents_routes.router,
        agents_routes.router,
        mcp_routes.router,
        ask_routes.router,
    ]
