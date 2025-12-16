from fastapi import FastAPI
import psycopg2
import chromadb
from pydantic import BaseModel

db_params = {
    "host": "postgres",
    "database": "onboard_db",
    "user": "user",
    "password": "password",
    "port": 5432
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

@app.post("/test-pipeline")
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