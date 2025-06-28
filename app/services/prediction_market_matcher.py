from typing import List, Dict, Any

import faiss
import numpy as np
import pandas as pd
import torch
import torch.backends.mps
from sentence_transformers import SentenceTransformer, CrossEncoder

from app.utils.matching_helper_functions import _unit_normalize, _passes_rules


class PredictionMarketMatcher:
    DEFAULT_THRESHOLD: float = 0.75

    def __init__(
            self,
            kalshi_df: pd.DataFrame,
            polymarket_df: pd.DataFrame,
            *,
            embed_model: str = "BAAI/bge-large-en-v1.5",
            rerank_model: str = "BAAI/bge-reranker-base",
            device: str | None = None,
    ) -> None:
        """
        Initializes the PredictionMarketMatcher class.
        """
        # Picking device
        if device is None:
            device = "mps" if torch.backends.mps.is_available() else "cpu"

        self.device_name = device
        self.torch_device = torch.device(device)

        # Clean data
        self.kalshi_df = kalshi_df.copy()
        self.polymarket_df = polymarket_df.copy()
        self._prepare_text()

        # Models
        self.encoder = SentenceTransformer(embed_model, device=self.device_name)
        self.encoder.max_seq_length = 512
        self.reranker = CrossEncoder(rerank_model, device=self.device_name)

        # index
        self._build_index()

    def match_events(self, *, k: int =10, threshold: float = DEFAULT_THRESHOLD) -> pd.DataFrame:
        """
        Finds matching Kalshi events for each event in the Polymarket DataFrame.

        This method perform the full matching pipeline:
        1. Encodes Polymarket events into embeddings.
        2. Searches the FAISS index for the top `k` Kalshi candidates
        3. Reranks these candidates using the CrossEncoder
        4. Filters matches based on the `threshold` and heuristic rules.

        Args:
            k (int): The number of initial candidates to retrieve from the FAISS index for
                each Polymarket event.
            threshold (float): The minimum rerank score required to consider
                an event pair a match.

        Returns:
            pd.DataFrame: A DataFrame containing the successful matches, with columns
            for Polymarket ID, Kalshi ID, and various similarity scores.
        """
        k = min(k, self._index.ntotal)
        polymarket_emb = _unit_normalize(
            self.encoder.encode(
                self.polymarket_df["text"].tolist(),
                convert_to_numpy=True,
                show_progress_bar=True,
            )
        ).astype("float32")
        polymarket_emb = np.ascontiguousarray(polymarket_emb)

        sim, idx = self._index.search(polymarket_emb, k)
        matches: List[Dict[str, Any]] = []

        for row, (cands, recall_sims) in enumerate(zip(idx, sim)):
            p_text = self.polymarket_df.loc[row, "text"]
            p_id = self.polymarket_df.loc[row, "id"]
            k_texts = self.kalshi_df.loc[cands, "text"].tolist()
            pairs = [[p_text, kt] for kt in k_texts]
            rerank_scores = self.reranker.predict(pairs)
            best_i = int(np.argmax(rerank_scores))
            best_score = float(rerank_scores[best_i])

            if best_score >= threshold and _passes_rules(p_text, k_texts[best_i]):
                matches.append({
                    "polymarket_id": p_id,
                    "kalshi_ticker": self.kalshi_df.loc[cands[best_i], "ticker"],
                    "recall_rank": best_i + 1,
                    "recall_score": float(recall_sims[best_i]),
                    "rerank_score": best_score,
                })
        return pd.DataFrame(matches)


    def _prepare_text(self) -> None:
        """
        Preprocesses and combines text fields into a single 'text' column.

        This helper method cleans and concatenates relevant text columns from
        both the Kalshi and Polymarket DataFrames to create a unified 'text'
        field for each, which is then used for embedding. The cleaning process
        involves lowercasing, stripping whitespace, and filling null values.
        This method modifies the instance's DataFrames in place.
        """
        def _clean(s: pd.Series) -> pd.Series:
            """
            Cleans a pandas Series of strings.
            """
            return (
                s.fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .str.replace(r"\s+", " ", regex=True)
            )

        # Concatenate relevant text fields for each data source
        self.kalshi_df["text"] = (
                _clean(self.kalshi_df["title"]) + " " +
                _clean(self.kalshi_df["subtitle"]) + " " +
                _clean(self.kalshi_df["rules_primary"]) + " " +
                _clean(self.kalshi_df["rules_secondary"])
        )

        self.polymarket_df["text"] = (
                _clean(self.polymarket_df["title"]) + " " +
                _clean(self.polymarket_df["description"])
        )

        # Drop rows with no text content after cleaning
        for df in (self.kalshi_df, self.polymarket_df):
            df.dropna(subset=["text"], inplace=True)
            df.reset_index(drop=True, inplace=True)

    def _build_index(self):
        """
        Encodes Kalshi texts and builds a FAISS index for fast searching.

        This method generates embeddings for all texts in the Kalshi DataFrame,
        normalizes them, and then adds them to a `faiss.IndexFlatIP` index.
        This index is stored in the `self._index` attribute and is used for
        the initial recall stage of the matching process.
        """
        emb = _unit_normalize(
            self.encoder.encode(
                self.kalshi_df["text"].tolist(),
                convert_to_numpy=True,
                show_progress_bar=True,
            )
        ).astype("float32")
        emb = np.ascontiguousarray(emb)
        self._index = faiss.IndexFlatIP(emb.shape[1])
        self._index.add(emb)