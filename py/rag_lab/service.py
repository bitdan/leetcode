import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple

from rag_lab.schemas import (
    RagDocumentInput,
    RagEvidence,
    RagGraphEdge,
    RagIndexSummary,
    RagQueryDiagnostics,
    RagQueryResult,
)


ASCII_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_./:-]*|\d+(?:\.\d+)?")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]+")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SENTENCE_RE = re.compile(r"(?<=[。！？.!?])\s+|\n+")

QUERY_EXPANSIONS = {
    "rag": ["检索增强", "召回", "引用"],
    "检索": ["召回", "搜索", "retrieve"],
    "召回": ["检索", "搜索", "retrieve"],
    "向量": ["embedding", "语义"],
    "embedding": ["向量", "语义"],
    "切块": ["chunk", "分段"],
    "chunk": ["切块", "分段"],
    "引用": ["citation", "证据", "来源"],
    "图": ["graph", "关系", "实体"],
    "graph": ["图", "关系", "实体"],
    "重排": ["rerank", "排序"],
    "rerank": ["重排", "排序"],
}


@dataclass
class Chunk:
    id: str
    document_id: str
    title: str
    heading: str
    source: str
    content: str
    terms: Counter
    semantic: Counter
    neighbors: Dict[str, Tuple[float, str]] = field(default_factory=dict)


@dataclass
class Collection:
    chunks: List[Chunk]
    document_count: int
    document_frequency: Counter
    average_length: float
    vocabulary: Set[str]


class RagLabService:
    """Small offline RAG engine that exposes every retrieval score."""

    def __init__(self):
        self._collections: Dict[str, Collection] = {}

    def index(self, collection_id: str, documents: List[RagDocumentInput]) -> RagIndexSummary:
        if sum(len(document.content) for document in documents) > 160000:
            raise ValueError("单次索引内容不能超过 160000 个字符")
        chunks: List[Chunk] = []
        for document_index, document in enumerate(documents):
            document_id = document.id or f"doc_{document_index + 1}"
            chunks.extend(self._chunk_document(document_id, document))

        if not chunks:
            raise ValueError("文档没有可索引内容")
        if len(chunks) > 300:
            raise ValueError("单个知识库最多包含 300 个上下文块")

        document_frequency: Counter = Counter()
        vocabulary: Set[str] = set()
        for chunk in chunks:
            document_frequency.update(chunk.terms.keys())
            vocabulary.update(chunk.terms.keys())

        self._build_graph(chunks)
        collection = Collection(
            chunks=chunks,
            document_count=len(documents),
            document_frequency=document_frequency,
            average_length=sum(sum(chunk.terms.values()) for chunk in chunks) / len(chunks),
            vocabulary=vocabulary,
        )
        self._collections[collection_id] = collection
        return self.stats(collection_id)

    def stats(self, collection_id: str) -> RagIndexSummary:
        collection = self._collections.get(collection_id)
        if not collection:
            return RagIndexSummary(
                collection_id=collection_id,
                document_count=0,
                chunk_count=0,
                graph_edge_count=0,
                vocabulary_size=0,
            )
        edge_count = sum(len(chunk.neighbors) for chunk in collection.chunks) // 2
        return RagIndexSummary(
            collection_id=collection_id,
            document_count=collection.document_count,
            chunk_count=len(collection.chunks),
            graph_edge_count=edge_count,
            vocabulary_size=len(collection.vocabulary),
        )

    def reset(self, collection_id: str) -> RagIndexSummary:
        self._collections.pop(collection_id, None)
        return self.stats(collection_id)

    def query(self, collection_id: str, question: str, top_k: int = 5) -> RagQueryResult:
        collection = self._collections.get(collection_id)
        if not collection:
            raise ValueError("知识库尚未建立，请先索引文档")

        query_terms = tokenize(question)
        expanded_terms = self._expand_terms(query_terms)
        weighted_query = Counter(query_terms)
        for term in expanded_terms:
            weighted_query[term] += 0.35
        query_semantic = semantic_vector(question)

        raw_scores = []
        for chunk in collection.chunks:
            lexical = self._bm25(weighted_query, chunk, collection)
            semantic = cosine(query_semantic, chunk.semantic)
            raw_scores.append({
                "chunk": chunk,
                "lexical_raw": lexical,
                "semantic": semantic,
                "lexical": 0.0,
                "graph": 0.0,
                "base": 0.0,
                "final": 0.0,
                "penalty": 0.0,
            })

        max_lexical = max((item["lexical_raw"] for item in raw_scores), default=0.0) or 1.0
        by_id = {}
        for item in raw_scores:
            item["lexical"] = item["lexical_raw"] / max_lexical
            item["base"] = 0.58 * item["lexical"] + 0.42 * item["semantic"]
            by_id[item["chunk"].id] = item

        for item in raw_scores:
            neighbor_signals = [
                by_id[neighbor_id]["base"] * weight
                for neighbor_id, (weight, _) in item["chunk"].neighbors.items()
                if neighbor_id in by_id
            ]
            item["graph"] = min(1.0, sum(sorted(neighbor_signals, reverse=True)[:2]))
            item["final"] = item["base"] + 0.22 * item["graph"]

        selected = self._mmr_rerank(raw_scores, top_k)
        evidence = self._build_evidence(selected, set(query_terms + expanded_terms))
        confidence, confidence_label = self._confidence(evidence, query_terms)
        graph_edges = self._result_edges(selected)
        knowledge_gap = self._knowledge_gap(confidence, evidence)
        return RagQueryResult(
            answer=self._compose_answer(question, evidence, confidence_label, knowledge_gap),
            evidence=evidence,
            graph_edges=graph_edges,
            diagnostics=RagQueryDiagnostics(
                query_terms=dedupe(query_terms),
                expanded_terms=expanded_terms,
                retrieval_strategy="BM25 + hashed semantic + evidence graph diffusion + MMR",
                confidence=round(confidence, 4),
                confidence_label=confidence_label,
                knowledge_gap=knowledge_gap,
            ),
        )

    def _chunk_document(self, document_id: str, document: RagDocumentInput) -> List[Chunk]:
        heading = document.title
        paragraphs: List[Tuple[str, str]] = []
        buffer: List[str] = []
        buffer_length = 0

        def flush():
            nonlocal buffer, buffer_length
            if buffer:
                paragraphs.append((heading, "\n\n".join(buffer).strip()))
                buffer = []
                buffer_length = 0

        for raw_line in document.content.replace("\r\n", "\n").split("\n"):
            line = raw_line.strip()
            heading_match = HEADING_RE.match(line)
            if heading_match:
                flush()
                heading = heading_match.group(2).strip()
                continue
            if not line:
                if buffer_length >= 280:
                    flush()
                continue
            if buffer and buffer_length + len(line) > 720:
                flush()
            buffer.append(line)
            buffer_length += len(line)
        flush()

        chunks = []
        for index, (chunk_heading, content) in enumerate(paragraphs):
            if not content:
                continue
            chunks.append(Chunk(
                id=f"{document_id}:chunk:{index + 1}",
                document_id=document_id,
                title=document.title,
                heading=chunk_heading,
                source=document.source,
                content=content,
                terms=Counter(tokenize(f"{document.title} {chunk_heading} {content}")),
                semantic=semantic_vector(f"{document.title} {chunk_heading} {content}"),
            ))
        return chunks

    def _build_graph(self, chunks: List[Chunk]) -> None:
        by_document: Dict[str, List[Chunk]] = defaultdict(list)
        for chunk in chunks:
            by_document[chunk.document_id].append(chunk)
        for document_chunks in by_document.values():
            for left, right in zip(document_chunks, document_chunks[1:]):
                self._link(left, right, 0.72, "文档相邻")

        for index, left in enumerate(chunks):
            left_terms = set(term for term, _ in left.terms.most_common(24))
            for right in chunks[index + 1:]:
                if left.document_id == right.document_id and right.id in left.neighbors:
                    continue
                right_terms = set(term for term, _ in right.terms.most_common(24))
                shared = left_terms & right_terms
                if len(shared) < 2:
                    continue
                weight = min(0.62, 0.18 + len(shared) * 0.07)
                self._link(left, right, weight, f"共享概念: {', '.join(sorted(shared)[:3])}")

    @staticmethod
    def _link(left: Chunk, right: Chunk, weight: float, reason: str) -> None:
        left.neighbors[right.id] = (weight, reason)
        right.neighbors[left.id] = (weight, reason)

    @staticmethod
    def _expand_terms(query_terms: List[str]) -> List[str]:
        expanded = []
        for term in query_terms:
            expanded.extend(QUERY_EXPANSIONS.get(term, []))
        return [term for term in dedupe(expanded) if term not in query_terms]

    @staticmethod
    def _bm25(query: Counter, chunk: Chunk, collection: Collection) -> float:
        score = 0.0
        chunk_length = max(1, sum(chunk.terms.values()))
        for term, query_weight in query.items():
            frequency = chunk.terms.get(term, 0)
            if not frequency:
                continue
            document_frequency = collection.document_frequency.get(term, 0)
            idf = math.log(1 + (len(collection.chunks) - document_frequency + 0.5) / (document_frequency + 0.5))
            denominator = frequency + 1.2 * (1 - 0.75 + 0.75 * chunk_length / collection.average_length)
            score += query_weight * idf * frequency * 2.2 / denominator
        return score

    @staticmethod
    def _mmr_rerank(items: List[dict], top_k: int) -> List[dict]:
        candidates = sorted(items, key=lambda item: item["final"], reverse=True)
        selected: List[dict] = []
        while candidates and len(selected) < top_k:
            best = None
            best_score = -1.0
            for item in candidates:
                redundancy = max(
                    (cosine(item["chunk"].semantic, chosen["chunk"].semantic) for chosen in selected),
                    default=0.0,
                )
                source_bonus = 0.04 if selected and all(
                    chosen["chunk"].document_id != item["chunk"].document_id for chosen in selected
                ) else 0.0
                mmr_score = item["final"] - 0.24 * redundancy + source_bonus
                if mmr_score > best_score:
                    best_score = mmr_score
                    best = item
                    best["penalty"] = 0.24 * redundancy
            selected.append(best)
            candidates.remove(best)
        return selected

    @staticmethod
    def _build_evidence(selected: List[dict], query_terms: Set[str]) -> List[RagEvidence]:
        evidence = []
        for index, item in enumerate(selected):
            chunk = item["chunk"]
            evidence.append(RagEvidence(
                rank=index + 1,
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                title=chunk.title,
                heading=chunk.heading,
                source=chunk.source,
                content=chunk.content,
                matched_terms=sorted(query_terms & set(chunk.terms.keys()))[:12],
                lexical_score=round(item["lexical"], 4),
                semantic_score=round(item["semantic"], 4),
                graph_score=round(item["graph"], 4),
                diversity_penalty=round(item["penalty"], 4),
                final_score=round(item["final"], 4),
            ))
        return evidence

    @staticmethod
    def _confidence(evidence: List[RagEvidence], query_terms: List[str]) -> Tuple[float, str]:
        if not evidence:
            return 0.0, "低"
        top_score = min(1.0, evidence[0].final_score)
        matched = set(term for item in evidence[:3] for term in item.matched_terms)
        coverage = len(matched) / max(1, len(set(query_terms)))
        confidence = min(1.0, top_score * 0.68 + coverage * 0.32)
        label = "高" if confidence >= 0.72 else "中" if confidence >= 0.42 else "低"
        return confidence, label

    @staticmethod
    def _knowledge_gap(confidence: float, evidence: List[RagEvidence]) -> str:
        if not evidence or confidence < 0.28:
            return "现有文档缺少直接证据，建议补充相关资料或换一种问法。"
        if confidence < 0.58:
            return "证据存在但覆盖不完整，回答应作为线索而不是最终结论。"
        return "未发现明显知识缺口，但仍建议核对首条引用。"

    @staticmethod
    def _compose_answer(question: str, evidence: List[RagEvidence], confidence_label: str, gap: str) -> str:
        if not evidence:
            return f"问题“{question}”没有检索到可用证据。{gap}"
        findings = []
        for item in evidence[:3]:
            sentences = [sentence.strip() for sentence in SENTENCE_RE.split(item.content) if sentence.strip()]
            excerpt = (sentences[0] if sentences else item.content).strip()
            if len(excerpt) > 180:
                excerpt = excerpt[:177] + "..."
            findings.append(f"[{item.rank}] {excerpt}")
        return f"证据置信度：{confidence_label}。\n\n" + "\n\n".join(findings) + f"\n\n知识缺口：{gap}"

    def _result_edges(self, selected: List[dict]) -> List[RagGraphEdge]:
        selected_ids = {item["chunk"].id for item in selected}
        edges = []
        seen = set()
        for item in selected:
            chunk = item["chunk"]
            for neighbor_id, (weight, reason) in chunk.neighbors.items():
                pair = tuple(sorted((chunk.id, neighbor_id)))
                if neighbor_id not in selected_ids or pair in seen:
                    continue
                seen.add(pair)
                edges.append(RagGraphEdge(
                    source_chunk_id=chunk.id,
                    target_chunk_id=neighbor_id,
                    weight=round(weight, 4),
                    reason=reason,
                ))
        return sorted(edges, key=lambda edge: edge.weight, reverse=True)[:12]


def tokenize(text: str) -> List[str]:
    normalized = str(text or "").lower()
    terms: List[str] = []
    for word in ASCII_WORD_RE.findall(normalized):
        terms.append(word)
        terms.extend(part for part in re.split(r"[_./:-]+", word) if len(part) > 1 and part != word)
    for sequence in CHINESE_RE.findall(normalized):
        if len(sequence) <= 6:
            terms.append(sequence)
        if len(sequence) == 1:
            terms.append(sequence)
        else:
            terms.extend(sequence[index:index + 2] for index in range(len(sequence) - 1))
    return terms


def semantic_vector(text: str, dimensions: int = 384) -> Counter:
    compact = re.sub(r"\s+", "", str(text or "").lower())
    vector: Counter = Counter()
    for size in (2, 3, 4):
        for index in range(max(0, len(compact) - size + 1)):
            feature = compact[index:index + size]
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=4).digest()
            bucket = int.from_bytes(digest, "big") % dimensions
            vector[bucket] += 1.0 / size
    return vector


def cosine(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 0.0
    shared = set(left.keys()) & set(right.keys())
    dot = sum(left[key] * right[key] for key in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def dedupe(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))
