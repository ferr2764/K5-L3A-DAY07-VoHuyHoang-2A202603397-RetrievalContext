from starter.dense_retriever import DenseRetriever

retriever = DenseRetriever()
try:
    hits = retriever.search(
        "Agile chia dự án thành những đơn vị nào?",
        filters=None,
        top_k=3,
    )
    for hit in hits:
        print(hit["id"], hit["page"], hit["score"])
finally:
    retriever.close()