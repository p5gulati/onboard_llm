import chromadb
from typing import List
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
chroma_client = chromadb.HttpClient(host="chromadb", port=8000)

def search_similar_chunks(question: str, collection_name: str, top_k: int = 5) -> List[str]:

    client = chromadb.HttpClient(host="chromadb", port=8000)

    try:
        collection = client.get_collection(name=collection_name)
    except Exception:
        raise ValueError(f"Collection '{collection_name}' not found. Did you ingest data first ?")
    
    question_embedding = embedding_model.encode([question]).tolist()
    results = collection.query(
        query_embeddings=question_embedding,
        n_results=top_k
    )
    
    return results['documents'][0]
