from fastapi import FastAPI
import psycopg2
import chromadb

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