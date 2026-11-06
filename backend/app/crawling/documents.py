"""Preserve table rows/headers and PDF page provenance for semantic extraction."""
from io import BytesIO
import re


def clean(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def html_blocks(root):
    blocks, heading, remaining = [], '', 16000
    nodes = root.xpath('.//*[self::h1 or self::h2 or self::h3 or self::p or self::li or self::tr]'
                       '[not(ancestor::nav) and not(ancestor::footer) and not(ancestor::aside)'
                       ' and not(ancestor::script) and not(ancestor::style)]')
    for i, node in enumerate(nodes):
        if node.root.tag != 'tr' and node.xpath('ancestor::tr'):
            continue
        if node.root.tag == 'tr':
            cells = [clean(' '.join(cell.xpath('.//text()').getall())) for cell in node.xpath('./th|./td')]
            table = node.xpath('ancestor::table[1]')
            headers = [clean(' '.join(cell.xpath('.//text()').getall())) for cell in table.xpath('(.//tr)[1]/th | ./thead/tr[1]/td')]
            value = ' | '.join(f'{headers[j]}: {v}' if j < len(headers) else v for j, v in enumerate(cells))
        else:
            value = clean(' '.join(node.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]').getall()))
        if node.root.tag in ('h1', 'h2', 'h3'):
            heading = value[:120]
        if not value or remaining <= 0:
            continue
        value = value[:remaining]
        blocks.append({'locator': f'html:{i}:{heading}', 'text': value})
        remaining -= len(value)
    return blocks


def pdf_document(body):
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(body))
    if reader.is_encrypted:
        return None
    blocks, remaining = [], 16000
    for n, page in enumerate(reader.pages):
        if remaining <= 0:
            break
        value = (page.extract_text(extraction_mode='layout') or '').strip()[:remaining]
        if value:
            blocks.append({'locator': f'pdf:page:{n + 1}', 'text': value})
            remaining -= len(value)
    if not blocks:
        return None
    return {'content': '\n'.join(b['text'] for b in blocks)[:16000], 'content_blocks': blocks,
            'title': str((reader.metadata or {}).get('/Title') or '')[:300], 'comments': [],
            'discussion_status': 'not_available', 'document_format': 'pdf',
            'document_pages': len(reader.pages), 'content_truncated': remaining <= 0}
