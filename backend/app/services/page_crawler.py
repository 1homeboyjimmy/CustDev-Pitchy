"""Bounded Scrapy jobs, isolated from Flask threads and Twisted's reactor."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

from ..config import Config


def source_diagnostics(sources):
    """Keep coverage without duplicating full articles/replies in every task."""
    keys = ('url', 'title', 'domain', 'source', 'search_angle', 'market_scope', 'crawl_status',
            'http_status', 'error_type', 'egress', 'discussion_status')
    return [{**{key: source[key] for key in keys if key in source},
             'content_characters': len(source.get('content') or ''),
             'comments_count': len(source.get('comments') or [])} for source in sources]


def collect_pages(sources: list[dict], timeout: float | None = None) -> list[dict]:
    if not sources:
        return []
    budget = max(0, min(timeout if timeout is not None else Config.SIGNAL_CRAWL_SECONDS,
                        Config.SIGNAL_CRAWL_SECONDS))
    originals = [dict(source, crawl_status='not_attempted', evidence_level='search_snippet')
                 for source in sources]
    if budget < 1:
        return originals
    with tempfile.TemporaryDirectory(prefix='custdev-crawl-') as directory:
        request_path = Path(directory) / 'request.json'
        output_path = Path(directory) / 'pages.jsonl'
        request_path.write_text(json.dumps({
            'sources': originals[:Config.SIGNAL_MAX_PAGES],
            'proxy': Config.SIGNAL_HTTPS_PROXY,
            'seconds': budget,
            'max_comments': Config.SIGNAL_MAX_COMMENTS,
            'browser': Config.SIGNAL_BROWSER_ENABLED,
        }), encoding='utf-8')
        worker = Path(__file__).resolve().parents[1] / 'crawling' / 'worker.py'
        try:
            process = subprocess.Popen(
                [sys.executable, str(worker), str(request_path), str(output_path)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return [dict(source, crawl_status='unavailable') for source in originals]
        timed_out = False
        try:
            process.wait(timeout=budget)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Also reap Chromium children when a deadline interrupts a page.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        collected = {}
        if output_path.exists():
            for line in output_path.read_text(encoding='utf-8').splitlines():
                try:
                    item = json.loads(line)
                    collected[item.pop('_index')] = item
                except (ValueError, KeyError):
                    continue  # A killed worker may leave one incomplete line.
        for index, original in enumerate(originals):
            if index in collected:
                originals[index].update(collected[index])
            elif index < Config.SIGNAL_MAX_PAGES:
                originals[index]['crawl_status'] = 'timed_out' if timed_out else 'unavailable'
        return originals
