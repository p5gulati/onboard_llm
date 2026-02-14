from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import psycopg2
import chromadb
import uuid
from langchain_text_splitters import CharacterTextSplitter
from sentence_transformers import SentenceTransformer
import random
from services import generate_answer, search_similar_chunks, ingest_repository

db_params = {
    "host": "postgres",
    "database": "onboard_db",
    "user": "user",
    "password": "password",
    "port": 5432
}

chroma_params = {
    "host": "chromadb",
    "port": 8000
}

app = FastAPI()

@app.get("/")
async def test_endpoint():
    return {"message" : "Hello from inside Docker."}

@app.get("/health")
async def health_check():

    postgres_status = "disconnected"
    chromadb_status = "disconnected"

    connection = None
    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        postgres_status = "connected"

    except Exception as error:
        postgres_status = f"error: {str(error)}"
    
    finally:
        if connection:
            cursor.close()
            connection.close()

    try:
        chroma_client = chromadb.HttpClient(host='chromadb', port=8000)
        chroma_connection = chroma_client.heartbeat()
        chromadb_status = "connected"

    except Exception as error:
        chroma_status = f"error: {str(error)}"

    return {
        "fastapi": "ok",
        "postgres": postgres_status,
        "chromadb": chromadb_status
    }

class TextInput(BaseModel):
    text: str

@app.post("/write-pg")
async def insert_data(data: TextInput):
    text = data.text

    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_data (
                id SERIAL PRIMARY KEY,
                text_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                chromadb_id VARCHAR(255))
        """)
        cursor.execute("INSERT INTO test_data (text_content) VALUES (%s) RETURNING id", (text,))
        inserted_id = cursor.fetchone()[0]
        connection.commit()
        cursor.close()
        connection.close()
        return {
            "status": "success",
            "message": "Data inserted",
            "id": inserted_id,
            "text": text
        }
    
    except Exception as error:
        return ({"status": "error", "message": str(error)})

@app.get("/read-pg")
async def read_data():

    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        cursor.execute("SELECT * from test_data")
        records = cursor.fetchall()
        cursor.close()
        connection.close()
        return {
            "status": "success",
            "data": records}

    except Exception as error:
        return ({"status" : "error", "message" : str(error)})

@app.post("/write-chroma")
async def write_chroma(data: TextInput):
    text = data.text
    client = chromadb.HttpClient(**chroma_params)

    try:
        collection = client.create_collection(name=str("collection_" + str(random.randint(1, 1000))))
        collection.add(documents = [text], ids = [str(uuid.uuid4())])

        return {
            "status" : "success",
            "message" : "Data inserted into ChromaDB",
            "col_count" : collection.count(),
            "collection_name": collection.name
        }

    except Exception as error:
        return {"status" : "error", "message" : str(error)}

@app.get("/get-chroma")
async def read_chroma():
    client = chromadb.HttpClient(**chroma_params)
    collections = client.list_collections(limit = 1)

    try:
        return {
            "collection" : [c.name for c in collections],
            "status" : "retrieved successfully"
        }

    except Exception as error:
        return {"status" : "error", "message" : str(error)}
    
class IngestInput(BaseModel):
    file_name: str
    file_text: str

text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base", chunk_size=100, chunk_overlap=0
)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

@app.post("/ingest")
async def ingest_code(data: IngestInput):

    file_name = data.file_name
    file_text = data.file_text

    try:
        texts = text_splitter.split_text(file_text)
        embeddings = embedding_model.encode(texts).tolist()
        client = chromadb.HttpClient(**chroma_params)
        collection = client.get_or_create_collection(name = file_name)

    
        ids = [str(uuid.uuid4()) for _ in texts]
        collection.add(documents = texts, ids = ids)

        return {
            "status": "success",
            "message": f"Ingested {len(texts)} chunks into collection '{file_name}'",
            "doc_count": collection.count()
        }

    except Exception as error:
        return {"status": "error", "message": str(error)}

class QueryInput(BaseModel):
    question: str
    repo_name: str  # User provides repo name, not collection name

@app.post("/query")
async def query_code(data: QueryInput):
    try:
        collection_name = f"repo_{data.repo_name}"  # Translate to collection name
        
        code_chunks = search_similar_chunks(
            question=data.question,
            collection_name=collection_name,
            top_k=5
        )
        
        if not code_chunks:
            return {"status": "error", "message": "No code found"}
        
        answer = generate_answer(
            question=data.question,
            code_chunks=code_chunks
        )
        
        return {
            "status": "success",
            "question": data.question,
            "answer": answer,
            "sources": code_chunks
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

class IngestRepoInput(BaseModel):
    repo_url: str
    repo_name: str

jobs = {}

@app.post("/ingest-repo")
async def ingest_repo(data: IngestRepoInput, background_tasks: BackgroundTasks):
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "repo_name": data.repo_name}
    
    background_tasks.add_task(
        run_ingestion,
        job_id,
        data.repo_url,
        data.repo_name
    )
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": f"Started ingesting {data.repo_name}. Check /status/{job_id}"
    }


def run_ingestion(job_id: str, repo_url: str, repo_name: str):

    result = ingest_repository(repo_url, repo_name)
    jobs[job_id] = result


@app.get("/status/{job_id}")
async def check_status(job_id: str):

    if job_id not in jobs:
        return {"status": "error", "message": "Job not found"}
    return jobs[job_id]


@app.get("/repos")
async def list_repos():

    completed = {
        job_id: info 
        for job_id, info in jobs.items() 
        if info.get("status") == "success"
    }
    return {"repos": completed}