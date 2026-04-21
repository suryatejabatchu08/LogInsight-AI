"""
Vercel Serverless Function Handler for LogInsight AI
This file serves as the entry point for Vercel's Python runtime
"""

from api.main import app

# Export the FastAPI app as a handler for Vercel
__all__ = ['app']
