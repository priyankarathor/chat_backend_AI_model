import os
from typing import Any

import requests
from langchain_core.embeddings import Embeddings


class HuggingFaceApiEmbeddings(Embeddings):
    def __init__(self):
        self.api_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        self.model = os.getenv(
            "HUGGINGFACE_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.api_url = (
            "https://api-inference.huggingface.co/pipeline/"
            f"feature-extraction/{self.model}"
        )

        if not self.api_token:
            raise ValueError(
                "HUGGINGFACEHUB_API_TOKEN environment variable is missing"
            )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": texts,
                "options": {
                    "wait_for_model": True
                }
            },
            timeout=60,
        )
        response.raise_for_status()

        data: Any = response.json()

        if not data:
            return []

        if isinstance(data[0][0], list):
            return [
                self._mean_pool(token_embeddings)
                for token_embeddings in data
            ]

        return data

    @staticmethod
    def _mean_pool(token_embeddings: list[list[float]]) -> list[float]:
        dimensions = len(token_embeddings[0])
        pooled = [0.0] * dimensions

        for token in token_embeddings:
            for index, value in enumerate(token):
                pooled[index] += value

        return [
            value / len(token_embeddings)
            for value in pooled
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


def get_embeddings():
    return HuggingFaceApiEmbeddings()


get_enbeddings = get_embeddings
