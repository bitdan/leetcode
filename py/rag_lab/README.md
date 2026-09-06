# Evidence Graph RAG Lab

This module is a small, offline, explainable RAG implementation. It is designed for learning and experimentation rather
than production-scale storage.

## Why this design

The implementation borrows practical ideas from popular open-source RAG projects without importing their full runtime:

- [RAGFlow](https://github.com/infiniflow/ragflow): explainable chunking, multiple recall, fused reranking, and grounded
  citations.
- [LightRAG](https://github.com/HKUDS/LightRAG) and
  [Microsoft GraphRAG](https://github.com/microsoft/graphrag): use relationships between evidence instead of treating
  every chunk as isolated.
- [Advanced RAG Techniques](https://github.com/NirDiamant/RAG_Techniques): query expansion, fusion retrieval,
  reranking, MMR diversity, reliable RAG, and explainable retrieval.

## Pipeline

```text
Markdown-aware chunking
  -> BM25 lexical retrieval
  -> hashed character n-gram semantic retrieval
  -> evidence graph diffusion
  -> MMR diversity reranking
  -> confidence calibration and cited evidence brief
```

The hashed semantic vector is intentionally simple. It runs offline and handles Chinese, English, and code-like
identifiers, but it is not a replacement for a trained embedding model.

## API

- `POST /api/v1/rag/index`: build an in-memory collection from documents.
- `POST /api/v1/rag/query`: query the collection and return scores, citations, graph edges, and diagnostics.
- `GET /api/v1/rag/collections/{collection_id}`: inspect index statistics.
- `DELETE /api/v1/rag/collections/{collection_id}`: clear a collection.

## Production upgrade path

1. Replace hashed semantic vectors with a multilingual embedding model.
2. Persist chunks and vectors in PostgreSQL with pgvector.
3. Replace the lightweight reranker with a cross-encoder reranker.
4. Extract entities and relations with an LLM or NLP pipeline.
5. Generate answers with an LLM, while preserving the current evidence and diagnostics contract.
6. Add a retrieval evaluation set with Recall@K, MRR, citation correctness, and groundedness.
