from fastapi import FastAPI
from pydantic import BaseModel
import psycopg2
import chromadb
import uuid
from langchain_text_splitters import CharacterTextSplitter
from sentence_transformers import SentenceTransformer

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
        collection = client.create_collection(name="my_collection")
        collection.add(documents = [text], ids = [str(uuid.uuid4())])

        return {
            "status" : "success",
            "message" : "Data inserted into ChromaDB",
            "doc_count" : collection.count()
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
