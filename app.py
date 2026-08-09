"""
Entry point wrapper for uvicorn and app deployment.
Re-exports `app` from `app.main` for full backwards compatibility with uvicorn app:app.
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn
    from utils.constants import DEFAULT_HOST, DEFAULT_PORT

    uvicorn.run(
        "app:app",
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        reload=True,
    )
