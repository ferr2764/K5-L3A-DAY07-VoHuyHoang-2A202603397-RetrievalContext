import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from openai import OpenAI


class DenseRetriever:
    def __init__(self):
        load_dotenv(Path(__file__).resolve().parent / ".env")

        self.database_url = os.environ["DATABASE_URL"]
        self.model = os.environ["EMBEDDING_MODEL"]

        # Phải khớp index DAY06 hiện có.
        if self.model != "openai/text-embedding-3-small":
            raise ValueError("Model không khớp index DAY06.")

        self.client = OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
            timeout=60,
            max_retries=2,
        )

    def search(self, query, *, filters=None, top_k=3):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query không được rỗng.")
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k phải là số nguyên dương.")

        filters = filters or {}
        if set(filters) - {"section", "language", "year"}:
            raise ValueError("Filter không được hỗ trợ.")

        response = self.client.embeddings.create(
            model=self.model,
            input=query,
            encoding_format="float",
        )
        vector = response.data[0].embedding

        if len(vector) != 1536:
            raise ValueError("Vector query phải có 1536 chiều.")

        vector_text = json.dumps(vector)

        with psycopg.connect(
            self.database_url, connect_timeout=5
        ) as connection:
            rows = connection.execute(
                """
                SELECT chunk_id, document_id, source, page,
                       text, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM day6_chunks
                WHERE strategy = %s
                  AND metadata @> %s::jsonb
                ORDER BY embedding <=> %s::vector, chunk_id
                LIMIT %s
                """,
                (
                    vector_text,
                    "B",
                    json.dumps(filters),
                    vector_text,
                    top_k,
                ),
            ).fetchall()

        fields = (
            "id", "source_id", "source", "page",
            "text", "metadata", "score",
        )
        return [dict(zip(fields, row)) for row in rows]

    def close(self):
        self.client.close()