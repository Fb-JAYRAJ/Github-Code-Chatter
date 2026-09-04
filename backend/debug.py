from backend.vector_store import CodeVectorStore

db = CodeVectorStore()
results = db.collection.get(limit=1)

print("\n--- CHUNKS IN DATABASE ---")
print(f"Total chunks: {db.count()}")
print("\n--- METADATA FOR FIRST CHUNK ---")
print(results["metadatas"][0])