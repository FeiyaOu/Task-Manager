"""TF-IDF module index (commit-message enrichment).

Builds a per-module document from commit messages + file-path tokens, fits a
TF-IDF vectorizer, and scores a bug's text against each module by cosine
similarity. This lets words developers actually write (e.g. "billing") find a
module even when the folder is named differently (e.g. "payments/").
"""
from __future__ import annotations

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlmodel import Session, select

from app.models.commit import Commit
from app.services.scoring import module_of


def _path_tokens(file_path: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", file_path.lower()))


class ModuleIndex:
    def __init__(self) -> None:
        self._modules: list[str] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    @property
    def is_ready(self) -> bool:
        return self._vectorizer is not None and bool(self._modules)

    def build(self, session: Session, module_depth: int = 1) -> None:
        docs: dict[str, list[str]] = {}
        for c in session.exec(select(Commit)).all():
            module = module_of(c.file_path, module_depth)
            docs.setdefault(module, []).append(
                f"{c.message} {_path_tokens(c.file_path)}"
            )

        self._modules = sorted(docs)
        corpus = [" ".join(docs[m]) for m in self._modules]
        if not corpus:
            self._vectorizer = None
            self._matrix = None
            return
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            self._matrix = vectorizer.fit_transform(corpus)
            self._vectorizer = vectorizer
        except ValueError:
            # Corpus was all stop-words / empty vocabulary.
            self._vectorizer = None
            self._matrix = None

    def relevance(self, text: str) -> dict[str, float]:
        if not self.is_ready:
            return {}
        query = self._vectorizer.transform([text])
        sims = cosine_similarity(query, self._matrix)[0]
        return {m: float(s) for m, s in zip(self._modules, sims) if s > 0}
