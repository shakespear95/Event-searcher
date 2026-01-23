"""Web scraping services with stealth capabilities (optional - requires playwright)"""
# Lazy imports to avoid failing when playwright is not installed
__all__ = ["ScraperEngine", "StealthBrowser"]

def __getattr__(name):
    """Lazy import to avoid ImportError when playwright is not installed."""
    if name == "ScraperEngine":
        from .engine import ScraperEngine
        return ScraperEngine
    elif name == "StealthBrowser":
        from .stealth import StealthBrowser
        return StealthBrowser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
