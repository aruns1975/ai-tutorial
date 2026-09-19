from langchain_ollama import OllamaEmbeddings

# Pinned to the 0.6b tag (1024-dim output) rather than a larger variant:
# pgvector's HNSW index has a hard 2000-dimension limit, and larger
# qwen3-embedding tags (e.g. 4b -> 2560 dims) exceed it.
qwen3_embedding_model = OllamaEmbeddings(
    model="qwen3-embedding:0.6b"
)
