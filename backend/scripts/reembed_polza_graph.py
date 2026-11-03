"""Prepare and atomically apply a Polza vector migration with a JSON backup.

--prepare FILE generates vectors without modifying Neo4j. Copy FILE to a
private backup location before --apply FILE. Application refuses to replace
vectors changed since preparation, and retains the original vectors in FILE.
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neo4j import GraphDatabase
from app.config import Config
from app.storage.embedding_service import EmbeddingService


def main():
    parser = argparse.ArgumentParser()
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--prepare', type=Path)
    operation.add_argument('--apply', type=Path)
    args = parser.parse_args()
    with GraphDatabase.driver(Config.NEO4J_URI, auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)) as driver:
        if args.prepare:
            entities = driver.execute_query('MATCH (n:Entity) RETURN n.uuid AS uuid, n.embedding AS old, n.name AS name, labels(n) AS labels').records
            facts = driver.execute_query('MATCH ()-[r:RELATION]->() RETURN r.uuid AS uuid, r.fact_embedding AS old, r.fact AS fact, r.name AS name').records
            rows = []
            for entity in entities:
                label = next((label for label in entity['labels'] if label != 'Entity'), 'Entity')
                rows.append({'kind': 'entity', 'uuid': entity['uuid'], 'old': entity['old'], 'text': f"{entity['name']} ({label})"})
            for fact in facts:
                rows.append({'kind': 'fact', 'uuid': fact['uuid'], 'old': fact['old'], 'text': fact['fact'] or fact['name'] or ''})
            if any(not row['uuid'] or not row['text'].strip() for row in rows):
                raise ValueError('Migration requires UUIDs and non-empty text on every record')
            vectors = EmbeddingService().embed_batch([row['text'] for row in rows])
            for row, vector in zip(rows, vectors):
                row['new'] = vector
            with args.prepare.open('x', encoding='utf-8') as stream:
                json.dump({'provider': Config.LLM_BASE_URL, 'model': Config.EMBEDDING_MODEL, 'rows': rows}, stream)
            args.prepare.chmod(0o600)
            print(f'Prepared {len(entities)} entity vectors and {len(facts)} fact vectors; Neo4j unchanged')
        else:
            plan = json.loads(args.apply.read_text(encoding='utf-8'))
            if plan['provider'] != Config.LLM_BASE_URL or plan['model'] != Config.EMBEDDING_MODEL:
                raise ValueError('Migration model does not match current configuration')
            def apply(tx):
                for row in plan['rows']:
                    entity = row['kind'] == 'entity'
                    match = 'MATCH (n:Entity {uuid: $uuid})' if entity else 'MATCH ()-[n:RELATION {uuid: $uuid}]->()'
                    prop = 'embedding' if entity else 'fact_embedding'
                    current = tx.run(f'{match} RETURN n.{prop} AS vector', uuid=row['uuid']).single()
                    if current is None or current['vector'] != row['old']:
                        raise ValueError('Graph changed since migration preparation; no vectors applied')
                    if len(row['new']) != 768:
                        raise ValueError('Incorrect vector dimension')
                    tx.run(f'{match} SET n.{prop} = $vector, n.embedding_model = $model',
                        uuid=row['uuid'], vector=row['new'], model=plan['model']).consume()
                tx.run('MATCH (g:Graph) SET g.embedding_model = $model', model=plan['model']).consume()
            with driver.session() as session:
                session.execute_write(apply)
            print(f"Applied {len(plan['rows'])} vectors atomically; original vectors retained in backup")


if __name__ == '__main__':
    main()
