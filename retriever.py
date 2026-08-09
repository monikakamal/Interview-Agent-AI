"""
Compatibility shim forwarding imports to rag.retriever.
"""

from rag.retriever import RAGRetriever as DataRetriever
from rag.retriever import RAGRetriever

__all__ = ["RAGRetriever", "DataRetriever"]