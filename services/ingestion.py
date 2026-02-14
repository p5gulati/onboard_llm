import uuid
from pathlib import Path
from typing import Dict
from langchain_text_splitters import CharacterTextSplitter
from services.github import clone_repository, get_code_files, cleanup_repo
from services.vectorstore import store_code_chunks

text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base",
    chunk_size=100,
    chunk_overlap=20
)


def ingest_repository(repo_url: str, repo_name: str) -> Dict:

    repo_path = None
    
    try:
       
        repo_path = clone_repository(repo_url, repo_name)
    
        code_files = get_code_files(repo_path)
        
        if not code_files:
            raise ValueError(f"No supported code files found in {repo_name}")
        
        total_chunks = 0
        files_processed = 0
        collection_name = f"repo_{repo_name}"
        
        for file_info in code_files:
            
            chunks = text_splitter.split_text(file_info['content'])
            
            if not chunks:
                continue
            
            metadatas = [{
                "file_path": file_info['path'],
                "language": file_info['language'],
                "chunk_index": i
            } for i, _ in enumerate(chunks)]
            
            store_code_chunks(
                collection_name=collection_name,
                code_chunks=chunks,
                metadatas=metadatas
            )
            
            total_chunks += len(chunks)
            files_processed += 1
        
        return {
            "status": "success",
            "repo_name": repo_name,
            "collection_name": collection_name,
            "files_processed": files_processed,
            "total_chunks": total_chunks
        }
    
    except Exception as e:
        return {
            "status": "error",
            "repo_name": repo_name,
            "error": str(e)
        }
    
    finally:
        if repo_path:
            cleanup_repo(repo_path)