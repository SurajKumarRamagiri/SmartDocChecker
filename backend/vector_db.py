import weaviate

client = weaviate.Client("http://localhost:8080")

def store_embedding(id, embedding):
    # Store embedding in vector DB
    client.data_object.create({"embedding": embedding}, "DocumentEmbedding", id=id)
