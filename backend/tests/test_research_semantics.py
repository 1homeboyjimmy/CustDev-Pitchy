import json
from io import BytesIO
from types import SimpleNamespace

import scrapy
from scrapy.http import HtmlResponse, Response
from pypdf import PdfWriter

from app.crawling import worker
from app.services import signals_research as research
from app.services.research_evidence import extraction_material, validate_pages, interview_context


def page(quote='Я управляю кафе в России. Плачу 6000 рублей, но не готов менять кассу.'):
    return {'url': 'https://vendor.example/pricing', 'title': 'Опыт', 'crawl_status': 'fetched',
            'content_blocks': [{'locator': 'html:1:Опыт', 'text': quote}], 'content': quote}


def payload(source_type='discussion', **fields):
    return {'pages': [{'source_index': 0, 'source_type': source_type, 'claims': [{
        'statement': 'Есть условие перехода', 'quote': page()['content'], 'locator': 'html:1:Опыт',
        'evidence_type': 'self_report', 'signal': 'current_spend', 'question': 'purchase',
        'role_quote': 'Я управляю кафе', 'actor_role': 'управляющий',
        'geography': 'russia', 'geography_quote': 'в России', **fields}]}]}


def extract(data, source=None):
    sources = [source or page()]
    return validate_pages(data, sources, extraction_material(sources, 'смена кассы'))[0]


def test_pricing_is_not_payment_even_if_model_calls_it_customer_experience():
    source = extract(payload('pricing'))
    assert source['claims'][0]['evidence_type'] == 'vendor_statement'
    assert not source['claims'][0]['demand_eligible']
    result = research._normalise_analysis({'verdict': 'Есть', 'willingness_evidence': {'paying': [0]}}, [source])
    assert result['willingness']['paying'] == 0


def test_fake_quotes_or_locator_and_inferred_geography_are_rejected():
    assert extract(payload(quote='Никогда не существовавшая цитата'))['claims'] == []
    assert extract(payload(locator='invented'))['claims'] == []
    source = extract(payload(geography_quote='Московский ресторан'))
    assert source['market_scope'] == 'unknown'
    assert not source['claims'][0]['demand_eligible']


def test_budget_is_not_current_payment_and_synthetic_never_counts():
    source = extract(payload(signal='budget'))
    result = research._normalise_analysis({'willingness_evidence': {'paying': [0]}}, [source])
    assert result['willingness']['paying'] == 0
    synthetic = extract(payload('model_example'))
    assert not synthetic['claims'][0]['demand_eligible']
    assert synthetic['claims'][0]['evidence_type'] == 'synthetic'


def test_broken_llm_types_do_not_crash_validation():
    source = extract(payload(source_type={}, evidence_type=[], question={}, signal={}, relation=[]))
    assert source['claims'][0]['evidence_type'] == 'assumption'
    assert source['claims'][0]['question'] == 'context'


def test_unknown_extraction_cannot_inherit_russian_geography():
    source = extract(None, dict(page(), market_scope='russian_market'))
    assert source['market_scope'] == 'unknown'
    assert source['extraction_status'] == 'unavailable'


def test_findings_require_real_claim_ids_and_brief_does_not_prescribe_answers():
    source = extract(payload())
    analysis = research._normalise_analysis({'findings': [
        {'question': 'Как отреагируют?', 'conclusion': 'Есть ограничение', 'claim_ids': ['0:0'], 'status': 'conditional'},
        {'conclusion': 'Придуманный вывод', 'claim_ids': ['99:0'], 'status': 'supported'}],
        'interview_questions': ['Что изменится в вашей работе?'],
        'interview_hypotheses': ['Некоторые участники могут отказаться']}, [source])
    assert analysis['findings'][1]['status'] == 'gap'
    assert analysis['findings'][1]['claim_ids'] == []
    context = interview_context({'evidence_version': 2, 'query': 'Стоит ли изменить сайт?', 'sources': [source], 'analysis': analysis})
    assert 'Что изменится в вашей работе?' in context
    assert 'персонаж вправе не согласиться' in context
    assert 'Спрос есть' not in context


def test_topic_relevant_interior_survives_long_page_and_small_context():
    source = page()
    source['content_blocks'] = [
        {'locator': 'head', 'text': 'Ненужное вступление. ' * 500},
        {'locator': 'terms', 'text': 'Ограничение интеграции: нельзя переносить бонусы.'}]
    material = extraction_material([source] * 48, 'интеграции бонусы')
    assert 'нельзя переносить бонусы' in str(material[0])


def test_html_table_keeps_headers_with_prices_and_conditions():
    response = HtmlResponse('https://vendor.example', body=('''<main><h1>Тариф</h1>
        <table><tr><th>Пакет</th><th>Цена</th></tr><tr><td>Базовый</td><td>6000 ₽ / месяц при оплате за год</td></tr></table>
        <p>Комиссия 3%, доставка оплачивается отдельно. Интеграция с лояльностью ограничена.</p></main>''').encode(), encoding='utf-8')
    result = worker.extract_html(response)
    assert 'Цена: 6000 ₽ / месяц при оплате за год' in str(result['content_blocks'])
    assert 'доставка оплачивается отдельно' in str(result['content_blocks'])


def test_pdf_goes_through_scrapy_callback_and_scanned_pdf_is_explicit(tmp_path, monkeypatch):
    output = tmp_path / 'out.jsonl'
    spider = worker.MarketSpider(job={'sources': [{'url': 'https://example.test/report.pdf'}], 'proxy': ''}, output=str(output))
    request = scrapy.Request('https://example.test/report.pdf', meta={'_index': 0})
    response = Response(request.url, body=b'%PDF-test', request=request)
    monkeypatch.setattr(worker, 'pdf_document', lambda body: {'content': 'Исследование', 'title': '', 'comments': [],
        'content_blocks': [{'locator': 'pdf:page:2', 'text': 'Исследование'}]})
    assert list(spider.parse_page(response)) == []
    assert json.loads(output.read_text())['content_blocks'][0]['locator'] == 'pdf:page:2'
    writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
    stream = BytesIO(); writer.write(stream)
    from app.crawling.documents import pdf_document
    assert pdf_document(stream.getvalue()) is None


def test_arbitrary_product_question_has_no_modes_and_keeps_provider_count(monkeypatch):
    from app.config import Config
    seen = []
    def create(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            'context': {'research_objective': 'Реакция на обязательную регистрацию'},
            'plans': {a['id']: {'query': 'mandatory signup user frustration', 'questions': ['reaction', 'trust'],
                               'expected_evidence': 'опыт затронутых пользователей'} for a in research.AGENTS}
        })))])
    monkeypatch.setattr(Config, 'LLM_API_KEY', 'test')
    monkeypatch.setattr(research, 'OpenAI', lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    plan = research._plan_search_queries('Как отреагируют на обязательную регистрацию на сайте?', [])
    assert len([key for key in plan if not key.startswith('_')]) == 7
    assert plan['_intents']['reviews']['questions'] == ['reaction', 'trust']
    assert all(a['domains'] == [] for a in research.AGENTS if a['kind'] == 'web')
    prompt = seen[0]['messages'][0]['content']
    assert 'Не классифицируй задачу по режимам' in prompt
    assert 'Не навязывай размер рынка' in prompt


def test_personas_have_no_predetermined_purchase_answer():
    from app.services.oasis_profile_generator import OasisProfileGenerator
    generator = OasisProfileGenerator.__new__(OasisProfileGenerator)
    prompt = generator._get_system_prompt(True, 'target_audience', 'Проверяем реакцию на регистрацию')
    assert 'Не становись покупателем автоматически' in prompt
    assert 'Архетип задаёт стиль и склонности, но не готовый ответ' in prompt
    assert 'ОТЛИЧАЙ ЦИТАТЫ' in prompt


def test_synthetic_quotes_can_only_support_a_conditional_finding():
    source = extract(payload('model_example'))
    result = research._normalise_analysis({'findings': [
        {'conclusion': 'Модельный сценарий', 'claim_ids': ['0:0'], 'status': 'supported'}]}, [source])
    assert result['findings'][0]['status'] == 'conditional'


def test_truncated_model_output_retains_only_complete_grounded_pages():
    from app.services.research_evidence import parse_pages
    complete = payload()['pages'][0]
    interrupted = '{"pages": [' + json.dumps(complete) + ', {"source_index": 1, "claims": ['
    parsed = parse_pages(interrupted)
    assert parsed == {'pages': [complete]}
    assert len(extract(parsed)['claims']) == 1
    assert parse_pages('{"pages": [{"source_index":0,"claims":[{"quote":"partial') is None


def test_source_extraction_uses_configured_extraction_model(monkeypatch):
    from app.config import Config
    seen = []
    def create(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload())))])
    monkeypatch.setattr(Config, 'LLM_API_KEY', 'test')
    monkeypatch.setattr(research, 'OpenAI', lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    assert research._extract_evidence('Смена кассы', [page()], 10)[0]['claims']
    assert seen[0]['model'] == Config.model_for('extraction')
    assert seen[0]['extra_body'] == {'reasoning': {'enabled': False}}
