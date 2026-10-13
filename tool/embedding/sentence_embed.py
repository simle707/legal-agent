import numpy as np

from sentence_transformers import SentenceTransformer
_model = SentenceTransformer('BAAI/bge-m3')

def embed(texts: list[str]) -> np.ndarray:
    return _model.encode(texts, normalize_embeddings=True, batch_size=16)