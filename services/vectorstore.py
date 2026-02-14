import chromadb
import uuid
from typing import List, Dict
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

def store_code_chunks(collection_name: str, code_chunks: List[str], metadatas: List[Dict] = None) -> None:

    # Generate embeddings for all chunks at once (batch = faster)
    embeddings = embedding_model.encode(code_chunks).tolist()

    ids = [str(uuid.uuid4()) for _ in code_chunks]
    
    collection = chroma_client.get_or_create_collection(name=collection_name)
    
    collection.add(
        documents=code_chunks,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas if metadatas else [{} for _ in code_chunks]
    )