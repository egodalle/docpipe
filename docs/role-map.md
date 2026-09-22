# Role map (frozen Day 1)

1. An AI Data Engineer builds the pipelines that feed models: ingest, clean, chunk, embed, index, and keep that data fresh.
2. Their customer is a model, not a dashboard; quality shows up as retrieval accuracy, citation correctness, and index freshness.
3. A Data Engineer builds warehouses, batch/stream ETL, and serving layers so people and BI tools can query trusted tables.
4. A Data Engineer does not own embedding strategy, vector indexes, or RAG evaluation as the product job.
5. An ML Engineer owns training loops, feature stores, experiment tracking, and model serving.
6. An ML Engineer does not own document contracts, chunking, or keeping a RAG corpus current.
7. An AI Engineer wires products on top of models: orchestration, tools, agents, and application UX.
8. DocPipe practices the AI Data Engineer lane; a thin API/UI is the only AI Engineer slice, and we do not train models.
