"""
Graph building service.
Uses GraphStorage (Neo4j) to replace Zep Cloud API.
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..storage import GraphStorage
from .text_processor import TextProcessor

logger = logging.getLogger('pitchy.graph_builder')


@dataclass
class GraphInfo:
    """Graph information"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    """
    Graph building service
    Build knowledge graph through GraphStorage interface
    """

    def __init__(self, storage: GraphStorage):
        self.storage = storage
        self.task_manager = TaskManager()

    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "Pitchy Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 3
    ) -> str:
        """
        Build graph asynchronously

        Args:
            text: Input text to process
            ontology: Ontology definition (from ontology generator output)
            graph_name: Name for the graph
            chunk_size: Text chunk size
            chunk_overlap: Chunk overlap size
            batch_size: Number of chunks to send per batch

        Returns:
            Task ID
        """
        # Create task
        task_id = self.task_manager.create_task(
            task_type="graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "text_length": len(text),
            }
        )

        # Execute build in background thread
        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(task_id, text, ontology, graph_name, chunk_size, chunk_overlap, batch_size)
        )
        thread.daemon = True
        thread.start()

        return task_id

    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int
    ):
        """Graph build worker thread"""
        try:
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=5,
                message="Starting graph building..."
            )

            # 1. Create graph
            graph_id = self.create_graph(graph_name)
            self.task_manager.update_task(
                task_id,
                progress=10,
                message=f"Graph created: {graph_id}"
            )

            # 2. Set ontology
            self.set_ontology(graph_id, ontology)
            self.task_manager.update_task(
                task_id,
                progress=15,
                message="Ontology set"
            )

            # 3. Text chunking
            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id,
                progress=20,
                message=f"Text split into {total_chunks} chunks"
            )

            # 4. Send data in batches (NER + embedding + Neo4j insert — synchronous)
            episode_uuids = self.add_text_batches(
                graph_id, chunks, batch_size,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=20 + int(prog * 0.6),  # 20-80%
                    message=msg
                )
            )

            # 5. Wait for processing (no-op for Neo4j — already synchronous)
            self.storage.wait_for_processing(episode_uuids)

            self.task_manager.update_task(
                task_id,
                progress=85,
                message="Data processing completed, getting graph information..."
            )

            # 6. Get graph information
            graph_info = self._get_graph_info(graph_id)

            # Completed
            self.task_manager.complete_task(task_id, {
                "graph_id": graph_id,
                "graph_info": graph_info.to_dict(),
                "chunks_processed": total_chunks,
            })

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.task_manager.fail_task(task_id, error_msg)

    def create_graph(self, name: str) -> str:
        """Create graph"""
        return self.storage.create_graph(
            name=name,
            description="Pitchy Social Simulation Graph"
        )

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """
        SetGraphOntology

        Simply stores ontology as JSON in the Graph node.
        No more dynamic Pydantic class creation (was Zep-specific).
        The NER extractor reads this ontology to guide extraction.
        """
        self.storage.set_ontology(graph_id, ontology)

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """Add text in batches to graph, return uuid list of all episodes"""
        episode_uuids = []
        total_chunks = len(chunks)
        total_batches = (total_chunks + batch_size - 1) // batch_size

        logger.info(f"[graph_build] Starting: {total_chunks} chunks, {total_batches} batches (batch_size={batch_size})")

        for i in range(0, total_chunks, batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1

            if progress_callback:
                progress = (i + len(batch_chunks)) / total_chunks
                progress_callback(
                    f"Processing batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)...",
                    progress
                )

            for j, chunk in enumerate(batch_chunks):
                chunk_idx = i + j + 1
                chunk_preview = chunk[:80].replace('\n', ' ')
                logger.info(
                    f"[graph_build] Chunk {chunk_idx}/{total_chunks} "
                    f"({len(chunk)} chars): \"{chunk_preview}...\""
                )
                t0 = time.time()
                try:
                    episode_id = self.storage.add_text(graph_id, chunk)
                    episode_uuids.append(episode_id)
                    elapsed = time.time() - t0
                    logger.info(
                        f"[graph_build] Chunk {chunk_idx}/{total_chunks} done in {elapsed:.1f}s"
                    )
                except Exception as e:
                    elapsed = time.time() - t0
                    logger.error(
                        f"[graph_build] Chunk {chunk_idx}/{total_chunks} FAILED "
                        f"after {elapsed:.1f}s: {e}"
                    )
                    if progress_callback:
                        progress_callback(f"Batch {batch_num} processing failed: {str(e)}", 0)
                    raise

        logger.info(f"[graph_build] All {total_chunks} chunks processed successfully")
        return episode_uuids

    # --------------------------------------------------------------
    # Deduplication
    # --------------------------------------------------------------

    @staticmethod
    def _normalise_name_for_dedupe(name: str) -> str:
        """Lowercase + strip honorifics/punctuation for fuzzy matching."""
        import re
        if not name:
            return ""
        # Drop common Russian honorifics that don't carry identity
        n = name.lower()
        for prefix in ("г-н ", "г-жа ", "доктор ", "профессор ", "проф. "):
            if n.startswith(prefix):
                n = n[len(prefix):]
        # Drop punctuation and collapse whitespace
        n = re.sub(r"[^\w\s]", " ", n, flags=re.UNICODE)
        n = re.sub(r"\s+", " ", n).strip()
        return n

    def deduplicate_entities(self, graph_id: str) -> Dict[str, Any]:
        """Merge obvious duplicate entities within the same type.

        Strategy (heuristic, no LLM): group nodes by entity type, then within
        each group find pairs where one normalised name is a strict superset
        of the other (token-wise) AND they share at least one full token. This
        catches the common ``Егор Фигурняк`` vs ``Егор Сергеевич Фигурняк``
        pattern without needing embeddings.

        Why heuristic only: an embedding-based pass would need every node
        embedded against every other O(n²) and is fragile when the embedding
        provider is down (as we observed with the 401 from routerai.ru). The
        token-superset rule covers the dominant duplication mode in NER
        output for personal names and organisations.

        Returns: ``{"merged": N, "kept": [...], "dropped": [...]}``.
        """
        all_nodes = self.storage.get_all_nodes(graph_id)
        # Group by entity type label (excluding generic Entity/Node labels)
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for node in all_nodes:
            labels = [l for l in node.get("labels", []) if l not in ("Entity", "Node")]
            etype = labels[0] if labels else "_unknown"
            groups.setdefault(etype, []).append(node)

        merged = 0
        kept_log: List[str] = []
        dropped_log: List[str] = []

        for etype, nodes in groups.items():
            if len(nodes) < 2:
                continue
            # Pair-by-pair check. Number of nodes per type is small (≤10s),
            # so quadratic is fine here.
            # Pre-compute normalised name token sets.
            decorated = []
            for n in nodes:
                tokens = set(self._normalise_name_for_dedupe(n.get("name", "")).split())
                tokens.discard("")
                decorated.append((n, tokens))

            # Greedy: pick richer node (more tokens, or longer summary) as winner.
            decorated.sort(key=lambda x: (len(x[1]), len(x[0].get("summary") or "")), reverse=True)

            consumed: set = set()
            for i, (keep_node, keep_tokens) in enumerate(decorated):
                if keep_node["uuid"] in consumed or len(keep_tokens) < 1:
                    continue
                for j in range(i + 1, len(decorated)):
                    drop_node, drop_tokens = decorated[j]
                    if drop_node["uuid"] in consumed or not drop_tokens:
                        continue
                    # Strict subset AND at least 1 shared token of length ≥ 3
                    if drop_tokens.issubset(keep_tokens) and any(len(t) >= 3 for t in drop_tokens):
                        try:
                            res = self.storage.merge_nodes(
                                keep_uuid=keep_node["uuid"],
                                drop_uuid=drop_node["uuid"],
                            )
                            merged += 1
                            kept_log.append(f"{keep_node['name']} ({etype})")
                            dropped_log.append(f"{drop_node['name']} → into {keep_node['name']}")
                            consumed.add(drop_node["uuid"])
                            logger.info(
                                f"[dedupe] Merged duplicate: kept '{keep_node['name']}' (uuid={keep_node['uuid'][:8]}), "
                                f"dropped '{drop_node['name']}' (uuid={drop_node['uuid'][:8]}), moved {res.get('merged_edges', 0)} edges"
                            )
                        except Exception as e:
                            logger.warning(f"[dedupe] Failed to merge {drop_node['uuid']} into {keep_node['uuid']}: {e}")

        if merged:
            logger.info(f"[dedupe] Done — merged {merged} duplicate entities in graph {graph_id}")
        else:
            logger.info(f"[dedupe] No duplicates found in graph {graph_id}")
        return {"merged": merged, "kept": kept_log, "dropped": dropped_log}

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """Get graph information"""
        info = self.storage.get_graph_info(graph_id)
        return GraphInfo(
            graph_id=info["graph_id"],
            node_count=info["node_count"],
            edge_count=info["edge_count"],
            entity_types=info.get("entity_types", []),
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """Get complete graph data (including details)"""
        return self.storage.get_graph_data(graph_id)

    def delete_graph(self, graph_id: str):
        """Delete graph"""
        self.storage.delete_graph(graph_id)
