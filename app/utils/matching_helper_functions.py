import importlib
import re
import subprocess
import sys

import numpy as np
import spacy

# Regular expression to find numbers
_NUM_RE  = re.compile(r"\b\d+(?:\.\d+)?%?\b")
# Load small English model for spaCy NLP tasks
def _get_spacy_model(name: str = "en_core_web_sm"):
    """Load spaCy model, auto-install if absent (nice for fresh venvs)."""
    try:
        return spacy.load(name)
    except OSError:
        print(f"[matcher] spaCy model '{name}' not found – downloading once…", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "spacy", "download", name], check=True)
        importlib.invalidate_caches()
        return spacy.load(name)

_spacy_nlp = _get_spacy_model()

def _unit_normalize(arr: np.ndarray) -> np.ndarray:
    """
    Normalizes vectors in a numpy array to unit length.
    """
    norm = np.linalg.norm(arr, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return arr / norm

def _entities(text: str) -> set[str]:
    """
    Extracts key named entities from a text string using spaCy

    This function process a given text to identify and extract named entities corresponding to people (PERSON),
    organization (ORG), and geopolitical entities (GPE).
    """
    return {ent.text.lower() for ent in _spacy_nlp(text).ents if ent.label_ in {"PERSON", "ORG", "GPE"}}

def _numbers(text: str) -> set[str]:
    """
    Finds all numeric tokens within a text string.

    This function uses a regular expression to identify and extract all
    numbers from the input text. It can find integers, floating-point
    numbers, and percentages
    """
    return set(_NUM_RE.findall(text))

def _passes_rules(a: str, b: str) -> bool:
    """
    Return True if strings *a* and *b* pass heuristic sanity checks.

    This function applies two heuristic rules to determine if two strings are
    semantically similar:
    1.  Entity Check: The Jaccard similarity of their named entities
        (PERSON, ORG, GPE) must be 0.5 or greater.
    2.  Numeric Check: The set of numeric tokens in both strings must be
        identical.

    Args:
        a: The first string for comparison.
        b: The second string for comparison.

    Returns:
        True if both strings pass the heuristic rules, False otherwise.
    """
    # entity Jaccard ≥ 0.5
    e1, e2 = _entities(a), _entities(b)
    if e1 or e2:
        if len(e1 & e2) / max(1, len(e1 | e2)) < 0.5:
            return False
    # numeric tokens must match
    if _numbers(a) != _numbers(b):
        return False
    return True