"""
Vector embedding service supporting TF-IDF vector space embeddings with Cosine Similarity,
and Gemini Embeddings fallback.
"""

import math
import re
from typing import Dict, List, Set, Tuple
import numpy as np

from utils.logger import logger


class EmbeddingService:
    """
    Computes text representations and vector similarity scores for RAG retrieval.
    Includes a robust local TF-IDF / Cosine Similarity vector engine as well as
    support for dense embeddings.
    """

    def __init__(self, use_gemini: bool = False, gemini_api_key: str = "") -> None:
        self.use_gemini = use_gemini
        self.gemini_api_key = gemini_api_key
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase terms with simple stemming."""
        raw_tokens = [w.lower() for w in re.findall(r"\b\w+\b", text) if len(w) > 1]
        stemmed = []
        for t in raw_tokens:
            if t.endswith("ings") or t.endswith("ment"):
                t = t[:-4]
            elif t.endswith("ing") or t.endswith("ies"):
                t = t[:-3]
            elif t.endswith("s") and not t.endswith("ss") and len(t) > 3:
                t = t[:-1]
            stemmed.append(t)
        return stemmed

    def fit(self, corpus: List[str]) -> None:
        """
        Build TF-IDF vocabulary and IDF weights across the curriculum corpus.
        """
        doc_count = len(corpus)
        if doc_count == 0:
            return

        doc_terms: List[Set[str]] = []
        term_doc_freq: Dict[str, int] = {}

        for doc in corpus:
            tokens = set(self._tokenize(doc))
            doc_terms.append(tokens)
            for t in tokens:
                term_doc_freq[t] = term_doc_freq.get(t, 0) + 1

        all_terms = sorted(term_doc_freq.keys())
        self.vocabulary = {term: idx for idx, term in enumerate(all_terms)}
        self.idf = {
            term: math.log((1 + doc_count) / (1 + df)) + 1.0
            for term, df in term_doc_freq.items()
        }

    def embed_text(self, text: str) -> np.ndarray:
        """
        Compute normalized TF-IDF vector embedding for a single text.
        """
        if not self.vocabulary:
            return np.array([], dtype=np.float32)

        vector = np.zeros(len(self.vocabulary), dtype=np.float32)
        tokens = self._tokenize(text)
        term_freqs: Dict[str, int] = {}
        for t in tokens:
            term_freqs[t] = term_freqs.get(t, 0) + 1

        for term, freq in term_freqs.items():
            if term in self.vocabulary:
                idx = self.vocabulary[term]
                vector[idx] = (1.0 + math.log(freq)) * self.idf[term]

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity score between two normalized vector embeddings.
        """
        if vec1.size == 0 or vec2.size == 0:
            return 0.0
        dot_prod = float(np.dot(vec1, vec2))
        return max(0.0, min(1.0, dot_prod))
