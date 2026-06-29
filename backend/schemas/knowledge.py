from pydantic import BaseModel


class KnowledgeSearchRequest(BaseModel):
    query: str
    n_results: int = 10
    top_k: int = 10
    project: str = ''
    source_types: list[str] = []
    case_types: list[str] = []
    collection: str = ''


class KnowledgeSearchResult(BaseModel):
    content: str
    source: str
    source_type: str
    case_type: str = ''
    heading: str = ''
    collection: str = ''
    score: float = 0.0
    rerank_score: float = 0.0
