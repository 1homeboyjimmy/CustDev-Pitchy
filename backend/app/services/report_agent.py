"""
Report Agent Service
Generate simulated reports using ReACT pattern (via GraphStorage / Neo4j)

Features:
1. Generate reports based on simulation requirements and graph information
2. First plan the outline structure, then generate section by section
3. Each section uses ReACT multi-round thinking and reflection pattern
4. Support conversations with users, autonomously call retrieval tools during conversations
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .graph_tools import (
    GraphToolsService,
    SearchResult,
    InsightForgeResult,
    PanoramaResult,
    InterviewResult,
    MarketResearchResult,
)

logger = get_logger('pitchy.report_agent')


class ReportLogger:
    """
    Report Agent Detailed Logger

    Generates agent_log.jsonl file in the report folder, recording detailed actions at each step.
    Each line is a complete JSON object containing timestamp, action type, details, etc.
    """
    
    def __init__(self, report_id: str):
        """
        Initialize the logger

        Args:
            report_id: Report ID, used to determine the log file path
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'agent_log.jsonl'
        )
        self.start_time = datetime.now()
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Ensure the log file directory exists"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _get_elapsed_time(self) -> float:
        """Get elapsed time from start to now (in seconds)"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def log(
        self,
        action: str,
        stage: str,
        details: Dict[str, Any],
        section_title: str = None,
        section_index: int = None
    ):
        """
        Log an entry

        Args:
            action: Action type, e.g. 'start', 'tool_call', 'llm_response', 'section_complete', etc
            stage: Current stage, e.g. 'planning', 'generating', 'completed'
            details: Details dictionary, not truncated
            section_title: Current section title (optional)
            section_index: Current section index (optional)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(self._get_elapsed_time(), 2),
            "report_id": self.report_id,
            "action": action,
            "stage": stage,
            "section_title": section_title,
            "section_index": section_index,
            "details": details
        }
        
        # Append to JSONL file
        with open(self.log_file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def log_start(self, simulation_id: str, graph_id: str, simulation_requirement: str):
        """Log report generation start"""
        self.log(
            action="report_start",
            stage="pending",
            details={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "simulation_requirement": simulation_requirement,
                "message": "Report generation task started"
            }
        )
    
    def log_planning_start(self):
        """Log outline planning start"""
        self.log(
            action="planning_start",
            stage="planning",
            details={"message": "Started planning report outline"}
        )
    
    def log_planning_context(self, context: Dict[str, Any]):
        """Log context information acquired during planning"""
        self.log(
            action="planning_context",
            stage="planning",
            details={
                "message": "Acquired simulation context information",
                "context": context
            }
        )
    
    def log_planning_complete(self, outline_dict: Dict[str, Any]):
        """Log outline planning completion"""
        self.log(
            action="planning_complete",
            stage="planning",
            details={
                "message": "Outline planning completed",
                "outline": outline_dict
            }
        )
    
    def log_section_start(self, section_title: str, section_index: int):
        """Log section generation start"""
        self.log(
            action="section_start",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={"message": f"Started generating section: {section_title}"}
        )
    
    def log_react_thought(self, section_title: str, section_index: int, iteration: int, thought: str):
        """Log ReACT thinking process"""
        self.log(
            action="react_thought",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "thought": thought,
                "message": f"ReACT round {iteration} thought"
            }
        )
    
    def log_tool_call(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        parameters: Dict[str, Any],
        iteration: int
    ):
        """Log tool call"""
        self.log(
            action="tool_call",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "parameters": parameters,
                "message": f"Called tool: {tool_name}"
            }
        )
    
    def log_tool_result(
        self,
        section_title: str,
        section_index: int,
        tool_name: str,
        result: str,
        iteration: int
    ):
        """Log tool call result (full content, not truncated)"""
        self.log(
            action="tool_result",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "tool_name": tool_name,
                "result": result,  # Full result, not truncated
                "result_length": len(result),
                "message": f"Tool {tool_name} returned result"
            }
        )
    
    def log_llm_response(
        self,
        section_title: str,
        section_index: int,
        response: str,
        iteration: int,
        has_tool_calls: bool,
        has_final_answer: bool
    ):
        """Log LLM response (full content, not truncated)"""
        self.log(
            action="llm_response",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "iteration": iteration,
                "response": response,  # Full response, not truncated
                "response_length": len(response),
                "has_tool_calls": has_tool_calls,
                "has_final_answer": has_final_answer,
                "message": f"LLM response (tool calls: {has_tool_calls}, final answer: {has_final_answer})"
            }
        )
    
    def log_section_content(
        self,
        section_title: str,
        section_index: int,
        content: str,
        tool_calls_count: int
    ):
        """Log section content generation completion (records content only, not the whole section completion)"""
        self.log(
            action="section_content",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": content,  # Full content, not truncated
                "content_length": len(content),
                "tool_calls_count": tool_calls_count,
                "message": f"Section {section_title} content generation completed"
            }
        )
    
    def log_section_full_complete(
        self,
        section_title: str,
        section_index: int,
        full_content: str
    ):
        """
        Log section generation completion

        Frontend should listen to this log to determine if a section is truly complete and get full content
        """
        self.log(
            action="section_complete",
            stage="generating",
            section_title=section_title,
            section_index=section_index,
            details={
                "content": full_content,
                "content_length": len(full_content),
                "message": f"Section {section_title} generation completed"
            }
        )
    
    def log_report_complete(self, total_sections: int, total_time_seconds: float):
        """Log report generation completion"""
        self.log(
            action="report_complete",
            stage="completed",
            details={
                "total_sections": total_sections,
                "total_time_seconds": round(total_time_seconds, 2),
                "message": "Report generation completed"
            }
        )
    
    def log_error(self, error_message: str, stage: str, section_title: str = None):
        """Log error"""
        self.log(
            action="error",
            stage=stage,
            section_title=section_title,
            section_index=None,
            details={
                "error": error_message,
                "message": f"Error occurred: {error_message}"
            }
        )


class ReportConsoleLogger:
    """
    Report Agent Console Logger

    Writes console-style logs (INFO, WARNING, etc.) to console_log.txt file in the report folder.
    These logs are different from agent_log.jsonl and are plain text console output.
    """
    
    def __init__(self, report_id: str):
        """
        Initialize console logger

        Args:
            report_id: Report ID, used to determine the log file path
        """
        self.report_id = report_id
        self.log_file_path = os.path.join(
            Config.UPLOAD_FOLDER, 'reports', report_id, 'console_log.txt'
        )
        self._ensure_log_file()
        self._file_handler = None
        self._setup_file_handler()
    
    def _ensure_log_file(self):
        """Ensure the log file directory exists"""
        log_dir = os.path.dirname(self.log_file_path)
        os.makedirs(log_dir, exist_ok=True)
    
    def _setup_file_handler(self):
        """Set up file handler to write logs to file"""
        import logging

        # Create file handler
        self._file_handler = logging.FileHandler(
            self.log_file_path,
            mode='a',
            encoding='utf-8'
        )
        self._file_handler.setLevel(logging.INFO)

        # Use the same concise format as console
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)

        # Add to report_agent related loggers
        loggers_to_attach = [
            'pitchy.report_agent',
            'pitchy.graph_tools',
        ]

        for logger_name in loggers_to_attach:
            target_logger = logging.getLogger(logger_name)
            # Avoid duplicate additions
            if self._file_handler not in target_logger.handlers:
                target_logger.addHandler(self._file_handler)
    
    def close(self):
        """Close file handler and remove it from logger"""
        import logging

        if self._file_handler:
            loggers_to_detach = [
                'pitchy.report_agent',
                'pitchy.graph_tools',
            ]

            for logger_name in loggers_to_detach:
                target_logger = logging.getLogger(logger_name)
                if self._file_handler in target_logger.handlers:
                    target_logger.removeHandler(self._file_handler)

            self._file_handler.close()
            self._file_handler = None
    
    def __del__(self):
        """Ensure file handler is closed during destructor"""
        self.close()


class ReportStatus(str, Enum):
    """Report status"""
    PENDING = "pending"
    PLANNING = "planning"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportSection:
    """Report section"""
    title: str
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content
        }

    def to_markdown(self, level: int = 2) -> str:
        """Convert to Markdown format"""
        md = f"{'#' * level} {self.title}\n\n"
        if self.content:
            md += f"{self.content}\n\n"
        return md


@dataclass
class ReportOutline:
    """Report outline"""
    title: str
    summary: str
    sections: List[ReportSection]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections]
        }
    
    def to_markdown(self) -> str:
        """Convert to Markdown format"""
        md = f"# {self.title}\n\n"
        md += f"> {self.summary}\n\n"
        for section in self.sections:
            md += section.to_markdown()
        return md


@dataclass
class Report:
    """Complete report"""
    report_id: str
    simulation_id: str
    graph_id: str
    simulation_requirement: str
    status: ReportStatus
    outline: Optional[ReportOutline] = None
    markdown_content: str = ""
    created_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "status": self.status.value,
            "outline": self.outline.to_dict() if self.outline else None,
            "markdown_content": self.markdown_content,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error
        }


# ═══════════════════════════════════════════════════════════════
# Prompt Template Constants
# ═══════════════════════════════════════════════════════════════

# ── Tool Descriptions ──

TOOL_DESC_INSIGHT_FORGE = """\
[Углубленный поиск инсайтов — Мощный инструмент поиска]
Это наша мощная функция поиска, предназначенная для глубокого анализа. Она:
1. Автоматически разбивает ваш вопрос на несколько подвопросов.
2. Извлекает информацию из симулированного графа знаний по нескольким измерениям.
3. Объединяет результаты семантического поиска, анализа сущностей и отслеживания цепочек связей.
4. Возвращает наиболее полный и глубокий контент.

[Случаи использования]
- Нужно глубоко проанализировать тему.
- Нужно понять множество аспектов события.
- Нужно получить богатый материал для разделов отчета.

[Содержимое ответа]
- Релевантные факты в оригинальном тексте (можно цитировать напрямую).
- Инсайты по основным сущностям.
- Анализ цепочек связей."""

TOOL_DESC_PANORAMA_SEARCH = """\
[Панорамный поиск — Полный обзор]
Этот инструмент используется для получения полного панорамного вида результатов симуляции, особенно подходит для понимания эволюции событий. Он:
1. Извлекает все релевантные узлы и связи.
2. Различает текущие актуальные факты и исторические/устаревшие факты.
3. Помогает понять, как развивались события.

[Случаи использования]
- Нужно понять полную траекторию развития события.
- Нужно сравнить изменения общественных настроений на разных этапах.
- Нужно получить исчерпывающую информацию о сущностях и связях.

[Содержимое ответа]
- Текущие актуальные факты (последние результаты симуляции).
- Исторические/устаревшие факты (записи об эволюции).
- Все вовлеченные сущности."""

TOOL_DESC_QUICK_SEARCH = """\
[Простой поиск — Быстрое извлечение]
Легкий инструмент быстрого поиска, подходящий для простых и прямых запросов информации.

[Случаи использования]
- Нужно быстро найти конкретную информацию.
- Нужно проверить факт.
- Простой поиск информации.

[Содержимое ответа]
- Список фактов, наиболее релевантных запросу."""

TOOL_DESC_INTERVIEW_AGENTS = """\
[Глубинное интервью — Реальное интервью с агентами (две платформы)]
Вызовите API интервью среды симуляции OASIS для проведения реальных интервью с запущенными симуляционными агентами!
Это не просто симуляция LLM, а вызов реального интерфейса интервью для получения оригинальных ответов от агентов симуляции.
По умолчанию интервью проводятся в Twitter и Reddit одновременно для получения более полных перспектив.

Поток функции:
1. Автоматически читает файлы профилей персонажей, чтобы понять всех агентов симуляции.
2. Интеллектуально выбирает агентов, наиболее релевантных теме интервью (например, студенты, СМИ, официальные лица).
3. Автоматически генерирует вопросы для интервью.
4. Вызывает интерфейс /api/simulation/interview/batch для проведения реальных интервью на двух платформах.
5. Интегрирует все результаты интервью и предоставляет многоперспективный анализ.

[Случаи использования]
- Нужно понять перспективы событий с точек зрения разных ролей (Что думают студенты? Что говорят СМИ? Что заявляет официальное лицо?).
- Нужно собрать разнообразные мнения и позиции.
- Нужно получить реальные ответы от агентов симуляции (из среды симуляции OASIS).
- Хотите сделать отчет более живым, включив в него «записи интервью».

[Содержимое ответа]
- Идентификационная информация опрошенных агентов.
- Ответы на интервью от каждого агента на платформах Twitter и Reddit.
- Ключевые цитаты (можно цитировать напрямую).
- Резюме интервью и сравнение точек зрения.

[Важно] Эта функция требует, чтобы среда симуляции OASIS была запущена!"""

TOOL_DESC_MARKET_RESEARCH = """\
[Внешняя RAG-база pitchy.pro — реальные факты о рынке РФ]
Запрашивает базу знаний pitchy.pro (Фонд содействия инновациям, маркетплейсы РФ, IT-стартапы, юнит-экономика, регуляторика).
Возвращает релевантные фрагменты с источниками и score'ами — их можно цитировать в отчёте как реальные рыночные данные.

[Когда использовать]
- Нужно сравнить прогноз симуляции с реальным состоянием рынка РФ.
- Нужны конкретные цифры/факты (объём рынка, госпрограммы, кейсы конкурентов).
- Нужна привязка к нормативке (ФЗ-152, лицензии и т.п.).

[Параметры]
- query (обязателен): текст запроса на русском, конкретный.
- top_k (опционально): сколько фрагментов вернуть (1–20, по умолчанию 5).
- categories (опционально): фильтр по разделам RAG (например ["finance", "platform_manual"]).

[Что вернётся]
- count: сколько фрагментов найдено.
- chunks: список { text, score, source, category } — используй для прямого цитирования с указанием источника.
- context: объединённый текст всех фрагментов.

[Цитирование в отчёте]
Если используешь фрагмент, ОБЯЗАТЕЛЬНО упоминай источник в формате:
> «Текст фрагмента…» — *источник: <source>*"""

# ── Outline Planning Prompt ──

PLAN_SYSTEM_PROMPT = """\
Ты — эксперт по написанию «отчётов о прогнозировании будущего» с «точкой зрения бога» на симулированный мир — ты видишь поведение, высказывания и взаимодействия каждого агента в симуляции.

[Основная концепция]
Мы построили симулированный мир и инжектировали в него специфические «симуляционные требования» как переменные. Эволюция симулированного мира — это прогноз того, что может произойти в будущем. То, что ты наблюдаешь, — это не «экспериментальные данные», а «репетиция будущего».

[Задача]
Напишите «отчет о прогнозировании будущего», который отвечает на вопросы:
1. Что произошло в будущем при заданных нами условиях?
2. Как реагируют и действуют различные агенты (группы)?
3. Какие будущие тенденции и риски выявляет эта симуляция, на которые стоит обратить внимание?

[Позиционирование отчета]
- ✅ Это отчет о прогнозировании будущего на основе симуляции, раскрывающий, «если это произойдет, как развернется будущее».
- ✅ Сосредоточьтесь на результатах прогнозирования: траекториях событий, реакциях групп, возникающих явлениях, потенциальных рисках.
- ✅ Высказывания и поведение агентов в симулированном мире являются предсказаниями будущего поведения людей.
- ❌ Не анализ текущего состояния реального мира.
- ❌ Не общий обзор общественных настроений.

[Лимит разделов]
- Минимум 2 раздела, максимум 5 разделов.
- Подразделы не нужны, в каждом разделе пишется законченный контент.
- Контент должен быть кратким, сосредоточенным на основных выводах прогноза.

Пожалуйста, выведите план отчета в формате JSON следующим образом:
{
    "title": "Заголовок отчета",
    "summary": "Резюме отчета (одно предложение, обобщающее основные выводы прогноза)",
    "sections": [
        {
            "title": "Название раздела",
            "description": "Описание содержания раздела"
        }
    ]
}

Примечание: массив sections должен содержать от 2 до 5 элементов!
ВАЖНО: Весь план отчета (заголовок, резюме, названия разделов и описания) ДОЛЖЕН быть на русском языке. Никогда не используй английский или другие языки. """

PLAN_USER_PROMPT_TEMPLATE = """\
[Параметры сценария прогнозирования]
Переменная (требование к симуляции), инжектированная в симулированный мир: {simulation_requirement}

[Масштаб симулированного мира]
- Количество сущностей, участвующих в симуляции: {total_nodes}
- Количество связей, сгенерированных между сущностями: {total_edges}
- Распределение типов сущностей: {entity_types}
- Количество активных агентов: {total_entities}

[Выборка фактов будущего, предсказанных симуляцией]
{related_facts_json}

Проанализируй эту репетицию будущего с «точки зрения бога»:
1. В каком состоянии оказывается будущее при заданных нами условиях?
2. Как реагируют и действуют различные группы (агенты)?
3. Какие будущие тренды выявляет эта симуляция, заслуживающие внимания?

Исходя из результатов прогнозирования, спроектируй наиболее подходящую структуру разделов отчёта.

[Напоминание] Количество разделов: минимум 2, максимум 5. Контент должен быть сжатым и сосредоточенным на ключевых выводах прогноза. Весь план отчёта должен быть на русском языке."""

# ── Section Generation Prompt ──

SECTION_SYSTEM_PROMPT_TEMPLATE = """\
Ты — эксперт по написанию «отчётов о прогнозировании будущего» и сейчас пишешь один из разделов отчёта.

Название отчёта: {report_title}
Краткое содержание: {report_summary}
Сценарий прогнозирования (требование к симуляции): {simulation_requirement}

Текущий раздел: {section_title}

═══════════════════════════════════════════════════════════════
[Основная концепция]
═══════════════════════════════════════════════════════════════

Симулированный мир — это репетиция будущего. Мы инжектировали в него специфические условия (требования к симуляции).
Поведение и взаимодействия агентов в симуляции — это прогноз будущего поведения людей.

Твоя задача:
- Раскрыть, что произойдёт в будущем при заданных условиях.
- Предсказать, как реагируют и действуют различные группы (агенты).
- Выявить будущие тренды, риски и возможности, на которые стоит обратить внимание.

❌ Не пиши анализ текущего состояния реального мира.
✅ Сосредоточься на «как развернётся будущее» — результаты симуляции и есть предсказанное будущее.

═══════════════════════════════════════════════════════════════
[Most Important Rules - Must Follow]
═══════════════════════════════════════════════════════════════

1. [Обязательно вызывайте инструменты для наблюдения за симулированным миром]
   - Вы наблюдаете за репетицией будущего с «точки зрения бога».
   - Весь контент должен исходить из событий и высказываний/поведения агентов в симулированном мире.
   - Запрещено использовать собственные знания для написания содержания отчета.
   - В каждом разделе необходимо вызвать инструменты не менее 3 раз (максимум 5 раз), чтобы наблюдать за симулированным миром, который представляет собой будущее.

2. [Обязательно цитируйте оригинальные высказывания и поведение агентов]
   - Высказывания и поведение агентов — это предсказания будущего поведения людей.
   - Используйте формат цитат в отчете для отображения этих прогнозов, например:
     > «Определенные группы заявят: оригинальное содержание...»
   - Эти цитаты являются основным доказательством прогнозов симуляции.

3. [Языковая последовательность — ВСЕГДА пишите на русском языке]
   - Весь отчет ДОЛЖЕН быть написан на русском языке, независимо от языка исходных материалов.
   - Контент, возвращаемый инструментами, может содержать английский, смесь языков или другие языки.
   - При цитировании нерусскоязычного контента, возвращенного инструментами, ВСЕГДА переводите его на беглый русский язык перед написанием в отчет.
   - Сохраняйте исходный смысл неизменным при переводе, обеспечивайте естественность выражения.
   - Это правило относится как к основному тексту, так и к цитируемому контенту (формат >).
   - НИКОГДА не переключайтесь на английский или любой другой язык в середине отчета.

4. [Верно представляйте результаты прогнозирования]
   - Содержание отчета должно отражать результаты симуляции, которые представляют будущее в симулированном мире.
   - Не добавляйте информацию, которой нет в симуляции.
   - Если информации недостаточно в каких-то аспектах, заявляйте об этом правдиво.

═══════════════════════════════════════════════════════════════
[⚠️ Спецификация формата — крайне важно]
═══════════════════════════════════════════════════════════════

[Один раздел = минимальная единица контента]
- Каждый раздел — это минимальная единица контента отчёта.
- ❌ Запрещено использовать любые Markdown-заголовки (#, ##, ###, #### и т.д.) внутри раздела.
- ❌ Запрещено добавлять заголовок раздела в начале контента.
- ✅ Заголовки разделов добавляются системой автоматически — просто пиши чистый основной текст.
- ✅ Используй **полужирный**, разделение абзацев, цитаты и списки для организации контента, но не заголовки.

[Корректный пример]
```
В этом разделе рассматривается, как сдвиг в регуляторике переформатировал стратегию компаний. Глубокий анализ данных симуляции показал...

**Первая реакция отрасли**

Крупные IT-компании быстро пересмотрели свою позицию по соответствию требованиям:

> «OpenAI и Anthropic в спешке готовили инфраструктуру под новые требования прозрачности...»

**Стратегическое расхождение**

Чётко обозначился раскол между компаниями, принявшими регулирование, и теми, кто ему сопротивлялся:

- Проактивный комплаенс как конкурентное преимущество.
- Лоббистские усилия по смягчению правоприменения.
```

[Некорректный пример]
```
## Резюме                     ← Неправильно — не добавляй заголовков
### 1. Начальная фаза         ← Неправильно — не используй ### для подразделов
#### 1.1 Детальный анализ     ← Неправильно — не используй ####

В этом разделе...
```

═══════════════════════════════════════════════════════════════
[Доступные инструменты получения данных] (вызывай 3–5 раз на раздел)
═══════════════════════════════════════════════════════════════

{tools_description}

[Рекомендации по инструментам — обязательно микшируй, не используй один и тот же всё время]
- insight_forge: Глубокий анализ — автоматическая декомпозиция вопросов и многомерное извлечение фактов и связей.
- panorama_search: Широкоугольный панорамный поиск — полная картина события, таймлайн, эволюция.
- quick_search: Быстрая проверка конкретного факта.
- interview_agents: Интервью с симулированными агентами — получаешь реакции от первого лица по разным ролям.
- market_research: Внешняя база pitchy.pro RAG — реальные факты о рынке РФ (фонды, маркетплейсы, регуляторика). Используй для сверки прогнозов симуляции с реальностью и для цитирования внешних источников.

═══════════════════════════════════════════════════════════════
[Рабочий процесс]
═══════════════════════════════════════════════════════════════

В каждом ответе ты можешь сделать ТОЛЬКО ОДНО из двух (нельзя совместить):

Вариант A — Вызов инструмента:
Опубликуй свои размышления, затем вызови инструмент в следующем формате:
<tool_call>
{{"name": "Название инструмента", "parameters": {{"parameter_name": "parameter_value"}}}}
</tool_call>
Система выполнит инструмент и вернёт результат. Тебе НЕ нужно и НЕЛЬЗЯ самому писать «Observation» — это делает система.

Вариант B — Финальный контент:
Когда собрано достаточно информации, начни ответ с «Final Answer:» и выдай тело раздела.

⚠️ Строго запрещено:
- Совмещать в одном ответе вызов инструмента и Final Answer.
- Имитировать ответ инструмента (Observation) — все результаты подаёт система.
- Делать больше одного вызова инструмента за ответ.

═══════════════════════════════════════════════════════════════
[Требования к контенту раздела]
═══════════════════════════════════════════════════════════════

1. Контент основан на данных симуляции, полученных через инструменты.
2. Обильно цитируй оригинальные высказывания агентов — это доказательная база прогноза.
3. Используй Markdown-форматирование (но БЕЗ заголовков):
   - **полужирный** для ключевых моментов вместо подзаголовков.
   - списки (- или 1.2.3.) для тезисов.
   - пустые строки для разделения абзацев.
   - ❌ запрет на синтаксис #, ##, ###, ####.
4. [Формат цитат — обязательно отдельным абзацем]
   Цитаты должны быть отдельным абзацем с пустыми строками до и после:

   ✅ Правильно:
   ```
   Реакция администрации показалась недостаточно содержательной.

   > «Шаблон ответа администрации выглядит ригидным и медленным в условиях быстро меняющейся социальной среды.»

   Эта оценка отражает массовое общественное недовольство.
   ```

   ❌ Неправильно:
   ```
   Реакция администрации показалась недостаточно содержательной.> «Шаблон ответа...» Эта оценка...
   ```
5. Логическая когерентность с другими разделами.
6. [Избегай дублирования] Внимательно прочитай уже написанные разделы, не повторяй описанное.
7. [Ещё раз] Никаких заголовков. **Полужирный** вместо подзаголовков."""

SECTION_USER_PROMPT_TEMPLATE = """\
Уже написанные разделы (внимательно прочитай, чтобы не дублировать):
{previous_content}

═══════════════════════════════════════════════════════════════
[Текущая задача] Написать раздел: {section_title}
═══════════════════════════════════════════════════════════════

[Важные напоминания]
1. Внимательно прочитай уже написанные разделы, чтобы не повторяться.
2. Прежде чем писать раздел, вызови инструменты и собери данные симуляции.
3. Микшируй разные инструменты, не используй один и тот же.
4. Контент основан на результатах инструментов, не на собственных знаниях.

[⚠️ Формат — строго]
- ❌ Никаких заголовков (#, ##, ###, ####).
- ❌ Не начинай раздел с «{section_title}» в качестве заголовка.
- ✅ Заголовок раздела добавляется системой автоматически.
- ✅ Сразу пиши тело раздела, **полужирный** вместо подзаголовков.

Начни так:
1. Сначала Thought — какие данные нужны для этого раздела.
2. Затем Action — вызови инструмент.
3. Когда данных достаточно — Final Answer (чистый текст без заголовков)."""

# ── Шаблоны сообщений ReACT-цикла ──

REACT_OBSERVATION_TEMPLATE = """\
Observation (результат инструмента):

═══ Инструмент {tool_name} вернул ═══
{result}

═══════════════════════════════════════════════════════════════
Инструментов вызвано: {tool_calls_count}/{max_tool_calls} (использованы: {used_tools_str}){unused_hint}
- Если данных хватает: начни ответ с «Final Answer:» и выдай тело раздела (обязательно цитируй оригинальный текст).
- Если данных мало: вызови ещё один инструмент.
═══════════════════════════════════════════════════════════════"""

REACT_INSUFFICIENT_TOOLS_MSG = (
    "[Замечание] Ты вызвал только {tool_calls_count} инструментов, нужно минимум {min_tool_calls}. "
    "Вызови инструмент ещё раз для получения дополнительных данных симуляции, потом выдай Final Answer. {unused_hint}"
)

REACT_INSUFFICIENT_TOOLS_MSG_ALT = (
    "Вызвано инструментов: {tool_calls_count}, нужно минимум {min_tool_calls}. "
    "Вызови инструмент, чтобы получить данные симуляции. {unused_hint}"
)

REACT_TOOL_LIMIT_MSG = (
    "Лимит вызовов инструментов исчерпан ({tool_calls_count}/{max_tool_calls}), больше вызывать нельзя. "
    "Сразу начни ответ с «Final Answer:» и выдай тело раздела на основе уже собранных данных."
)

REACT_UNUSED_TOOLS_HINT = "\n💡 Ещё не использовал: {unused_list}. Попробуй разные инструменты, чтобы получить разносторонний взгляд."

REACT_FORCE_FINAL_MSG = "Лимит инструментов исчерпан — сразу выдай Final Answer: и сгенерируй контент раздела."

# ── Chat Prompt ──

CHAT_SYSTEM_PROMPT_TEMPLATE = """\
Ты — лаконичный и эффективный ассистент по прогнозам симуляции.

[Контекст]
Условие прогноза: {simulation_requirement}

[Сгенерированный аналитический отчёт]
{report_content}

[Правила]
1. Приоритетно отвечай на вопросы по содержанию отчёта выше.
2. Отвечай напрямую, без растянутых рассуждений.
3. Вызывай инструменты только если в отчёте нет нужной информации.
4. Ответы — короткие, чёткие, структурированные.

[Доступные инструменты] (используй по необходимости, не более 1–2 раз)
{tools_description}

[Формат вызова инструмента]
<tool_call>
{{"name": "Название инструмента", "parameters": {{"parameter_name": "parameter_value"}}}}
</tool_call>

[Стиль ответа]
- Кратко и по делу, без длинных пассажей.
- Цитируй ключевое через формат `>`.
- Сначала вывод, потом обоснование.
- ВСЕГДА отвечай на русском языке, независимо от языка исходных материалов и отчёта.
"""

CHAT_OBSERVATION_SUFFIX = "\n\nОтветь на вопрос кратко."


# ═══════════════════════════════════════════════════════════════
# ReportAgent Main Class
# ═══════════════════════════════════════════════════════════════


class ReportAgent:
    """
    Report Agent - Simulation Report Generation Agent

    Uses ReACT (Reasoning + Acting) pattern:
    1. Planning Phase: Analyze simulation requirements, plan report outline structure
    2. Generation Phase: Generate content section by section, each section can call tools multiple times to get information
    3. Reflection Phase: Check content completeness and accuracy
    """
    
    # Maximum tool call count (per section)
    MAX_TOOL_CALLS_PER_SECTION = 2

    # Maximum reflection rounds
    MAX_REFLECTION_ROUNDS = 3

    # Maximum tool call count in conversation
    MAX_TOOL_CALLS_PER_CHAT = 2
    
    def __init__(
        self,
        graph_id: str,
        simulation_id: str,
        simulation_requirement: str,
        llm_client: Optional[LLMClient] = None,
        graph_tools: Optional[GraphToolsService] = None
    ):
        """
        Initialize Report Agent

        Args:
            graph_id: Graph ID
            simulation_id: Simulation ID
            simulation_requirement: Simulation requirement description
            llm_client: LLM client (optional)
            graph_tools: Graph tools service (optional, requires external GraphStorage injection)
        """
        self.graph_id = graph_id
        self.simulation_id = simulation_id
        self.simulation_requirement = simulation_requirement

        self.llm = llm_client or LLMClient()
        if graph_tools is None:
            raise ValueError(
                "graph_tools (GraphToolsService) is required. "
                "Create it via GraphToolsService(storage=...) and pass it in."
            )
        self.graph_tools = graph_tools

        # Tool definitions
        self.tools = self._define_tools()

        # Market context fetched once from the pitchy.pro RAG endpoint when the
        # report starts. Injected into each section's system prompt so the
        # agent can ground claims in real RU market data instead of only the
        # simulation. Lazily populated by ``generate_report``.
        self.market_context: str = ""

        # Logger (initialized in generate_report)
        self.report_logger: Optional[ReportLogger] = None
        # Console logger (initialized in generate_report)
        self.console_logger: Optional[ReportConsoleLogger] = None

        logger.info(f"ReportAgent initialization complete: graph_id={graph_id}, simulation_id={simulation_id}")

    def _fetch_market_context(self) -> str:
        """Pull RU market context from the pitchy.pro RAG once per report.

        Best-effort: if RAG is down or returns nothing we just proceed with an
        empty string. We don't want a flaky external dependency to block
        report generation.
        """
        try:
            import asyncio
            from .rag_service import RagService
            result = asyncio.run(RagService.search(
                self.simulation_requirement,
                top_k=4,
                timeout=5.0,
            ))
            ctx = result.context
            if ctx:
                logger.info(f"Market context for report fetched ({len(ctx)} chars)")
                return ctx
            logger.info("Market context empty (RAG returned nothing)")
        except Exception as e:
            logger.warning(f"Market context fetch failed (non-fatal): {e}")
        return ""
    
    def _define_tools(self) -> Dict[str, Dict[str, Any]]:
        """Define available tools"""
        return {
            "insight_forge": {
                "name": "insight_forge",
                "description": TOOL_DESC_INSIGHT_FORGE,
                "parameters": {
                    "query": "The question or topic you want to deeply analyze",
                    "report_context": "Context of current report section (optional, helps generate more accurate sub-questions)"
                }
            },
            "panorama_search": {
                "name": "panorama_search",
                "description": TOOL_DESC_PANORAMA_SEARCH,
                "parameters": {
                    "query": "Search query, used for relevance sorting",
                    "include_expired": "Whether to include expired/historical content (default True)"
                }
            },
            "quick_search": {
                "name": "quick_search",
                "description": TOOL_DESC_QUICK_SEARCH,
                "parameters": {
                    "query": "Search query string",
                    "limit": "Number of results to return (optional, default 10)"
                }
            },
            "interview_agents": {
                "name": "interview_agents",
                "description": TOOL_DESC_INTERVIEW_AGENTS,
                "parameters": {
                    "interview_topic": "Interview topic or requirement description (e.g. 'understand students' views on the dorm formaldehyde incident')",
                    "max_agents": "Maximum number of agents to interview (optional, default 5, max 10)"
                }
            },
            "market_research": {
                "name": "market_research",
                "description": TOOL_DESC_MARKET_RESEARCH,
                "parameters": {
                    "query": "Конкретный поисковый запрос на русском (например, 'юнит-экономика SaaS для маркетплейсов РФ')",
                    "top_k": "Сколько фрагментов вернуть, 1–20 (опционально, по умолчанию 5)",
                    "categories": "Фильтр по разделам RAG, список строк (опционально)"
                }
            }
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], report_context: str = "") -> str:
        """
        Execute tool call

        Args:
            tool_name: Tool name
            parameters: Tool parameters
            report_context: Report context (for InsightForge)

        Returns:
            Tool execution result (text format)
        """
        logger.info(f"Executing tool: {tool_name}, parameters: {parameters}")
        
        try:
            if tool_name == "insight_forge":
                query = parameters.get("query", "")
                ctx = parameters.get("report_context", "") or report_context
                result = self.graph_tools.insight_forge(
                    graph_id=self.graph_id,
                    query=query,
                    simulation_requirement=self.simulation_requirement,
                    report_context=ctx
                )
                return result.to_text()
            
            elif tool_name == "panorama_search":
                # Breadth search - get complete panorama
                query = parameters.get("query", "")
                include_expired = parameters.get("include_expired", True)
                if isinstance(include_expired, str):
                    include_expired = include_expired.lower() in ['true', '1', 'yes']
                result = self.graph_tools.panorama_search(
                    graph_id=self.graph_id,
                    query=query,
                    include_expired=include_expired
                )
                return result.to_text()
            
            elif tool_name == "quick_search":
                # Simple search - quick retrieval
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                if isinstance(limit, str):
                    limit = int(limit)
                result = self.graph_tools.quick_search(
                    graph_id=self.graph_id,
                    query=query,
                    limit=limit
                )
                return result.to_text()
            
            elif tool_name == "interview_agents":
                # Deep interview - call real OASIS interview API to get simulated agent responses (dual platform)
                interview_topic = parameters.get("interview_topic", parameters.get("query", ""))
                max_agents = parameters.get("max_agents", 5)
                if isinstance(max_agents, str):
                    max_agents = int(max_agents)
                max_agents = min(max_agents, 10)
                result = self.graph_tools.interview_agents(
                    simulation_id=self.simulation_id,
                    interview_requirement=interview_topic,
                    simulation_requirement=self.simulation_requirement,
                    max_agents=max_agents
                )
                return result.to_text()

            elif tool_name == "market_research":
                # External Pitchy RAG — real RU market facts with citations
                query = parameters.get("query", "")
                top_k_raw = parameters.get("top_k", 5)
                try:
                    top_k = int(top_k_raw)
                except (TypeError, ValueError):
                    top_k = 5
                categories = parameters.get("categories")
                if isinstance(categories, str):
                    categories = [c.strip() for c in categories.split(",") if c.strip()]
                result = self.graph_tools.market_research(
                    query=query, top_k=top_k, categories=categories
                )
                return result.to_text()

            # ========== Backward Compatibility: Old Tools (Internal Redirect to New Tools) ==========

            elif tool_name == "search_graph":
                # Redirect to quick_search
                logger.info("search_graph has been redirected to quick_search")
                return self._execute_tool("quick_search", parameters, report_context)
            
            elif tool_name == "get_graph_statistics":
                result = self.graph_tools.get_graph_statistics(self.graph_id)
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_entity_summary":
                entity_name = parameters.get("entity_name", "")
                result = self.graph_tools.get_entity_summary(
                    graph_id=self.graph_id,
                    entity_name=entity_name
                )
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            elif tool_name == "get_simulation_context":
                # Redirect to insight_forge because it's more powerful
                logger.info("get_simulation_context has been redirected to insight_forge")
                query = parameters.get("query", self.simulation_requirement)
                return self._execute_tool("insight_forge", {"query": query}, report_context)
            
            elif tool_name == "get_entities_by_type":
                entity_type = parameters.get("entity_type", "")
                nodes = self.graph_tools.get_entities_by_type(
                    graph_id=self.graph_id,
                    entity_type=entity_type
                )
                result = [n.to_dict() for n in nodes]
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            else:
                return f"Unknown tool: {tool_name}. Please use one of the following tools: insight_forge, panorama_search, quick_search"

        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}, error: {str(e)}")
            return f"Tool execution failed: {str(e)}"
    
    # Valid tool names set, used for validation when parsing raw JSON fallback
    VALID_TOOL_NAMES = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from LLM response

        Supported formats (in priority order):
        1. <tool_call>{"name": "tool_name", "parameters": {...}}</tool_call>
        2. Raw JSON (the entire response or a single line is a tool call JSON)
        """
        tool_calls = []

        # Format 1: XML-style (standard format)
        xml_pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
        for match in re.finditer(xml_pattern, response, re.DOTALL):
            try:
                call_data = json.loads(match.group(1))
                tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        if tool_calls:
            return tool_calls

        # Format 2: Fallback - LLM directly outputs raw JSON (not wrapped in <tool_call> tags)
        # Only try if format 1 didn't match to avoid mismatching JSON in body text
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            try:
                call_data = json.loads(stripped)
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
                    return tool_calls
            except json.JSONDecodeError:
                pass

        # Response may contain thinking text + raw JSON, try to extract the last JSON object
        json_pattern = r'(\{"(?:name|tool)"\s*:.*?\})\s*$'
        match = re.search(json_pattern, stripped, re.DOTALL)
        if match:
            try:
                call_data = json.loads(match.group(1))
                if self._is_valid_tool_call(call_data):
                    tool_calls.append(call_data)
            except json.JSONDecodeError:
                pass

        return tool_calls

    def _is_valid_tool_call(self, data: dict) -> bool:
        """Validate if the parsed JSON is a valid tool call"""
        # Support both {"name": ..., "parameters": ...} and {"tool": ..., "params": ...} key names
        tool_name = data.get("name") or data.get("tool")
        if tool_name and tool_name in self.VALID_TOOL_NAMES:
            # Normalize key names to name / parameters
            if "tool" in data:
                data["name"] = data.pop("tool")
            if "params" in data and "parameters" not in data:
                data["parameters"] = data.pop("params")
            return True
        return False
    
    def _get_tools_description(self) -> str:
        """Generate tool description text"""
        desc_parts = ["Available Tools:"]
        for name, tool in self.tools.items():
            params_desc = ", ".join([f"{k}: {v}" for k, v in tool["parameters"].items()])
            desc_parts.append(f"- {name}: {tool['description']}")
            if params_desc:
                desc_parts.append(f"  Parameters: {params_desc}")
        return "\n".join(desc_parts)
    
    def plan_outline(
        self,
        progress_callback: Optional[Callable] = None
    ) -> ReportOutline:
        """
        Plan report outline

        Use LLM to analyze simulation requirements and plan the report structure

        Args:
            progress_callback: Progress callback function

        Returns:
            ReportOutline: Report outline
        """
        logger.info("Starting to plan report outline...")

        if progress_callback:
            progress_callback("planning", 0, "Analyzing simulation requirements...")

        # First get simulation context
        context = self.graph_tools.get_simulation_context(
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement
        )

        if progress_callback:
            progress_callback("planning", 30, "Generating report outline...")
        
        system_prompt = PLAN_SYSTEM_PROMPT
        user_prompt = PLAN_USER_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            total_nodes=context.get('graph_statistics', {}).get('total_nodes', 0),
            total_edges=context.get('graph_statistics', {}).get('total_edges', 0),
            entity_types=list(context.get('graph_statistics', {}).get('entity_types', {}).keys()),
            total_entities=context.get('total_entities', 0),
            related_facts_json=json.dumps(context.get('related_facts', [])[:10], ensure_ascii=False, indent=2),
        )

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=800,
            )
            
            if progress_callback:
                progress_callback("planning", 80, "Parsing outline structure...")

            # Parse outline
            sections = []
            for section_data in response.get("sections", [])[:3]:
                sections.append(ReportSection(
                    title=section_data.get("title", ""),
                    content=""
                ))
            if len(sections) < 2:
                raise ValueError("LLM outline must contain at least two sections")
            
            outline = ReportOutline(
                title=response.get("title", "Simulation Analysis Report"),
                summary=response.get("summary", ""),
                sections=sections
            )

            if progress_callback:
                progress_callback("planning", 100, "Outline planning completed")

            logger.info(f"Outline planning completed: {len(sections)} sections")
            return outline

        except Exception as e:
            logger.error(f"Outline planning failed: {str(e)}")
            # Return default outline (3 sections as fallback)
            return ReportOutline(
                title="Результаты CustDev-исследования",
                summary="Ключевые выводы, реакции персон и риски по результатам симуляции.",
                sections=[
                    ReportSection(title="Главные выводы и подтверждённые боли"),
                    ReportSection(title="Реакции сегментов и возражения"),
                    ReportSection(title="Рекомендации, риски и следующие проверки")
                ]
            )

    def _fixed_custdev_outline(self) -> ReportOutline:
        """Evidence-first outline: stable, fast and resistant to topic drift."""
        return ReportOutline(
            title=f"CustDev-вердикт: {self.simulation_requirement[:100]}",
            summary="Реальный рынок имеет приоритет над синтетической симуляцией; допущения отмечены явно.",
            sections=[
                ReportSection(title="Реальные сигналы рынка и подтверждённые боли"),
                ReportSection(title="Синтетические реакции сегментов и ценовые возражения"),
                ReportSection(title="Решение: риски, эксперимент и следующие проверки"),
            ],
        )

    def _generate_section_fast(
        self,
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        section_index: int,
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """Generate one evidence-bound section with a single LLM request.

        The previous ReACT path required 3–5 tools and up to six LLM calls per
        section. A three-section report could therefore make 15–20 paid calls
        and take tens of minutes. Retrieval is deterministic here and the LLM
        only performs the final synthesis. Provider failures degrade to the
        retrieved evidence instead of leaving the report in an endless state.
        """
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)

        query = f"{section.title}. {self.simulation_requirement}"
        try:
            evidence = self._execute_tool("quick_search", {"query": query, "limit": 12})
        except Exception as exc:
            logger.warning("Fast report retrieval failed: %s", exc)
            evidence = ""

        evidence = (evidence or "").strip()[:6000]
        market = (self.market_context or "").strip()[:2000]
        previous = "\n\n".join(previous_sections[-2:])[-2500:]
        try:
            from .verdict_service import (
                load_saved_signals, load_simulation_reactions,
                _signals_digest, _answers_digest,
            )
            saved_signals = load_saved_signals(self.simulation_id) or {}
            real_market = _signals_digest(saved_signals.get('sources', []), limit=30)
            synthetic_reactions = _answers_digest(load_simulation_reactions(self.simulation_id), limit=30)
        except Exception as exc:
            logger.warning('Report evidence bundle unavailable: %s', exc)
            real_market = ''
            synthetic_reactions = ''

        if self.report_logger:
            self.report_logger.log_tool_call(
                section.title, section_index, "quick_search", {"query": query, "limit": 12}, 1
            )
            self.report_logger.log_tool_result(
                section.title, section_index, "quick_search", evidence, 1
            )
        if progress_callback:
            progress_callback("generating", 45, "Доказательства собраны, формируем выводы")

        system_prompt = (
            "Ты аналитик CustDev. Напиши один компактный раздел отчёта на русском языке. "
            "Опирайся только на предоставленные данные, явно отмечай нехватку фактов. "
            "Реальные рыночные источники имеют вес 70%, синтетические реакции — 30%. "
            "Не называй агентов реальными пользователями и не придумывай цитаты или статистику. "
            "Не используй Markdown-заголовки. Дай вывод, доказательства, возражения и практический следующий шаг. "
            "Объём: 250–400 слов."
        )
        user_prompt = (
            f"Отчёт: {outline.title}\nРаздел: {section.title}\n"
            f"Гипотеза: {self.simulation_requirement}\n\n"
            f"Данные симуляции:\n{evidence or 'Данные графа не найдены.'}\n\n"
            f"Реальные рыночные источники:\n{real_market or 'Подтверждённые внешние сигналы не найдены.'}\n\n"
            f"Синтетические реакции общества:\n{synthetic_reactions or 'Реакции агентов не найдены.'}\n\n"
            f"Контекст рынка:\n{market or 'Внешний контекст недоступен.'}\n\n"
            f"Предыдущие выводы (не повторяй):\n{previous or 'Это первый раздел.'}"
        )

        try:
            content = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.35,
                max_tokens=1200,
            ).strip()
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section.title, section_index, content, 1, False, True
                )
        except Exception as exc:
            logger.warning("LLM unavailable for section %s; using evidence fallback: %s", section.title, exc)
            if self.report_logger:
                self.report_logger.log_error(str(exc), "degraded", section.title)
            readable_error = "Сервис языковой модели временно недоступен"
            if "402" in str(exc) or "средств" in str(exc).lower():
                readable_error = "Лимит провайдера языковой модели исчерпан"
            content = (
                f"**Режим ограниченного отчёта.** {readable_error}; раздел собран напрямую из доступных данных.\n\n"
                f"**Проверяемая гипотеза:** {self.simulation_requirement}\n\n"
                f"**Наблюдения симуляции:**\n\n{evidence or 'В графе симуляции недостаточно фактов для достоверного вывода.'}\n\n"
                f"**Реальные рыночные сигналы:**\n\n{real_market or 'Подтверждённые внешние сигналы не найдены.'}\n\n"
                f"**Синтетические реакции:**\n\n{synthetic_reactions or 'Реакции агентов не найдены.'}\n\n"
                f"**Рыночный контекст:**\n\n{market or 'Внешние рыночные данные не были получены.'}\n\n"
                "**Следующий шаг:** подтвердить выводы прямыми интервью и повторить расширенный синтез после восстановления LLM-провайдера."
            )

        if self.report_logger:
            self.report_logger.log_section_content(
                section.title, section_index, content, 1
            )
        return content
    
    def _generate_section_react(
        self, 
        section: ReportSection,
        outline: ReportOutline,
        previous_sections: List[str],
        progress_callback: Optional[Callable] = None,
        section_index: int = 0
    ) -> str:
        """
        Generate individual section content using ReACT pattern

        ReACT loop:
        1. Thought - Analyze what information is needed
        2. Action - Call tool to get information
        3. Observation - Analyze tool return results
        4. Repeat until information is sufficient or maximum iterations reached
        5. Final Answer - Generate section content

        Args:
            section: Section to generate
            outline: Complete outline
            previous_sections: Content of previous sections (for maintaining coherence)
            progress_callback: Progress callback
            section_index: Section index (for logging)

        Returns:
            Section content (Markdown format)
        """
        logger.info(f"ReACT generating section: {section.title}")
        
        # Log section start
        if self.report_logger:
            self.report_logger.log_section_start(section.title, section_index)
        
        system_prompt = SECTION_SYSTEM_PROMPT_TEMPLATE.format(
            report_title=outline.title,
            report_summary=outline.summary,
            simulation_requirement=self.simulation_requirement,
            section_title=section.title,
            tools_description=self._get_tools_description(),
        )

        # Append real-market context (RAG) so the report grounds prediction
        # against actual RU market facts rather than only simulation output.
        if self.market_context:
            system_prompt += (
                "\n\n═══════════════════════════════════════════════════════════════\n"
                "[Контекст реального рынка РФ — из RAG pitchy.pro]\n"
                "═══════════════════════════════════════════════════════════════\n"
                f"{self.market_context[:4000]}\n"
                "Используй эти факты как реальную почву для выводов отчёта. "
                "Если симуляция говорит одно, а рынок — другое, отметь расхождение явно.\n"
            )

        # Build user prompt - pass maximum 4000 characters for each completed section
        if previous_sections:
            previous_parts = []
            for sec in previous_sections:
                # Maximum 4000 characters per section
                truncated = sec[:4000] + "..." if len(sec) > 4000 else sec
                previous_parts.append(truncated)
            previous_content = "\n\n---\n\n".join(previous_parts)
        else:
            previous_content = "(This is the first section)"
        
        user_prompt = SECTION_USER_PROMPT_TEMPLATE.format(
            previous_content=previous_content,
            section_title=section.title,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # ReACT loop
        tool_calls_count = 0
        max_iterations = 5  # Maximum iterations
        min_tool_calls = 3  # Minimum tool calls
        conflict_retries = 0  # Consecutive conflicts where tool calls and Final Answer appear simultaneously
        used_tools = set()  # Record tool names already called
        all_tools = {"insight_forge", "panorama_search", "quick_search", "interview_agents"}

        # Report context for InsightForge sub-question generation
        report_context = f"Section Title: {section.title}\nSimulation Requirement: {self.simulation_requirement}"
        
        for iteration in range(max_iterations):
            if progress_callback:
                progress_callback(
                    "generating", 
                    int((iteration / max_iterations) * 100),
                    f"Deep retrieval and writing in progress ({tool_calls_count}/{self.MAX_TOOL_CALLS_PER_SECTION})"
                )
            
            # Call LLM
            response = self.llm.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=4096
            )

            # Check if LLM return is None (API exception or empty content)
            if response is None:
                logger.warning(f"Section {section.title} round {iteration + 1} iteration: LLM returned None")
                # If there are more iterations, add message and retry
                if iteration < max_iterations - 1:
                    messages.append({"role": "assistant", "content": "(Response empty)"})
                    messages.append({"role": "user", "content": "Please continue generating content."})
                    continue
                # Last iteration also returned None, exit loop and enter forced conclusion
                break

            logger.debug(f"LLM response: {response[:200]}...")

            # Parse once, reuse result
            tool_calls = self._parse_tool_calls(response)
            has_tool_calls = bool(tool_calls)
            has_final_answer = "Final Answer:" in response

            # ── Conflict handling: LLM simultaneously output tool calls and Final Answer ──
            if has_tool_calls and has_final_answer:
                conflict_retries += 1
                logger.warning(
                    f"Section {section.title} round {iteration+1} : "
                    f"LLM simultaneously output tool calls and Final Answer (round {conflict_retries} conflicts)"
                )

                if conflict_retries <= 2:
                    # First two times: discard this response and request LLM to reply again
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "[Format Error] You cannot include both tool calls and Final Answer in one reply.\n"
                            "Each reply can only do one of the following:\n"
                            "- Call a tool (output a <tool_call> block, don't write Final Answer)\n"
                            "- Output final content (starting with 'Final Answer:', don't include <tool_call>)\n"
                            "Please reply again and only do one of these."
                        ),
                    })
                    continue
                else:
                    # Third time: downgrade, truncate to first tool call, force execution
                    logger.warning(
                        f"Section {section.title}: consecutive {conflict_retries} conflicts，"
                        "downgraded to truncate and execute first tool call"
                    )
                    first_tool_end = response.find('</tool_call>')
                    if first_tool_end != -1:
                        response = response[:first_tool_end + len('</tool_call>')]
                        tool_calls = self._parse_tool_calls(response)
                        has_tool_calls = bool(tool_calls)
                    has_final_answer = False
                    conflict_retries = 0

            # Log LLM response
            if self.report_logger:
                self.report_logger.log_llm_response(
                    section_title=section.title,
                    section_index=section_index,
                    response=response,
                    iteration=iteration + 1,
                    has_tool_calls=has_tool_calls,
                    has_final_answer=has_final_answer
                )

            # ── Case 1: LLM output Final Answer ──
            if has_final_answer:
                # Insufficient tool calls, reject and request to continue calling tools
                if tool_calls_count < min_tool_calls:
                    messages.append({"role": "assistant", "content": response})
                    unused_tools = all_tools - used_tools
                    unused_hint = f"(These tools have not been used, recommend using them: {', '.join(unused_tools)}）" if unused_tools else ""
                    messages.append({
                        "role": "user",
                        "content": REACT_INSUFFICIENT_TOOLS_MSG.format(
                            tool_calls_count=tool_calls_count,
                            min_tool_calls=min_tool_calls,
                            unused_hint=unused_hint,
                        ),
                    })
                    continue

                # Normal completion
                final_answer = response.split("Final Answer:")[-1].strip()
                logger.info(f"Section {section.title} generation completed (tool calls: {tool_calls_count}times)")

                if self.report_logger:
                    self.report_logger.log_section_content(
                        section_title=section.title,
                        section_index=section_index,
                        content=final_answer,
                        tool_calls_count=tool_calls_count
                    )
                return final_answer

            # ── Case 2: LLM attempts to call tools ──
            if has_tool_calls:
                # Tool quota exhausted → inform clearly, request output Final Answer
                if tool_calls_count >= self.MAX_TOOL_CALLS_PER_SECTION:
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": REACT_TOOL_LIMIT_MSG.format(
                            tool_calls_count=tool_calls_count,
                            max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        ),
                    })
                    continue

                # Only execute the first tool call
                call = tool_calls[0]
                if len(tool_calls) > 1:
                    logger.info(f"LLM attempted to call {len(tool_calls)} tools, only execute the first: {call['name']}")

                if self.report_logger:
                    self.report_logger.log_tool_call(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        parameters=call.get("parameters", {}),
                        iteration=iteration + 1
                    )

                result = self._execute_tool(
                    call["name"],
                    call.get("parameters", {}),
                    report_context=report_context
                )

                if self.report_logger:
                    self.report_logger.log_tool_result(
                        section_title=section.title,
                        section_index=section_index,
                        tool_name=call["name"],
                        result=result,
                        iteration=iteration + 1
                    )

                tool_calls_count += 1
                used_tools.add(call['name'])

                # Build unused tools hint
                unused_tools = all_tools - used_tools
                unused_hint = ""
                if unused_tools and tool_calls_count < self.MAX_TOOL_CALLS_PER_SECTION:
                    unused_hint = REACT_UNUSED_TOOLS_HINT.format(unused_list="、".join(unused_tools))

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": REACT_OBSERVATION_TEMPLATE.format(
                        tool_name=call["name"],
                        result=result,
                        tool_calls_count=tool_calls_count,
                        max_tool_calls=self.MAX_TOOL_CALLS_PER_SECTION,
                        used_tools_str=", ".join(used_tools),
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # ── Case 3: NeitherTool call，nor Final Answer ──
            messages.append({"role": "assistant", "content": response})

            if tool_calls_count < min_tool_calls:
                # Tool callcount insufficient，recommend unused tools
                unused_tools = all_tools - used_tools
                unused_hint = f"(These tools have not been used, recommend using them: {', '.join(unused_tools)}）" if unused_tools else ""

                messages.append({
                    "role": "user",
                    "content": REACT_INSUFFICIENT_TOOLS_MSG_ALT.format(
                        tool_calls_count=tool_calls_count,
                        min_tool_calls=min_tool_calls,
                        unused_hint=unused_hint,
                    ),
                })
                continue

            # Directly adopt this content as final answer, no more waiting
            # directlyconvertthis contentas finalanswer, no more waiting
            logger.info(f"Section {section.title} did not detectto 'Final Answer:' prefix, directlyadoptLLM outputas finalcontent（Tool call: {tool_calls_count}times)")
            final_answer = response.strip()

            if self.report_logger:
                self.report_logger.log_section_content(
                    section_title=section.title,
                    section_index=section_index,
                    content=final_answer,
                    tool_calls_count=tool_calls_count
                )
            return final_answer
        
        # Reachedmaximum iterations, forcegeneratecontent
        logger.warning(f"Section {section.title} reachedmaximumiterationscount，Forcegenerate")
        messages.append({"role": "user", "content": REACT_FORCE_FINAL_MSG})
        
        response = self.llm.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=4096
        )

        # Check forceconclusion when LLM return is None
        if response is None:
            final_answer = f"(This section generation failed: LLM returned empty response, please retry later)"
            final_answer = f"(ThisSectiongeneratefailed: LLM returnedemptyresponse, pleaselaterretry)"
        elif "Final Answer:" in response:
            final_answer = response.split("Final Answer:")[-1].strip()
        else:
            final_answer = response
        
        # Log sectioncontentgeneratecompletion log
        if self.report_logger:
            self.report_logger.log_section_content(
                section_title=section.title,
                section_index=section_index,
                content=final_answer,
                tool_calls_count=tool_calls_count
            )
        
        return final_answer
    
    def generate_report(
        self, 
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
        report_id: Optional[str] = None
    ) -> Report:
        """
        Generate complete report (realtime output per section)
        
        File structure:
        File structure:
        reports/{report_id}/
            outline.json    - Report outline
            progress.json   - Generation progress
            section_01.md   - Section 1
            section_02.md   - Section 2
            section_02.md   - Section 2
            ...
            full_report.md  - Complete report
        
        Args:
            report_id: Report ID (optional, auto-generate if not provided)
            report_id: Report ID (optional, auto-generate if not provided)
            
        Returns:
            Report: Complete report
        """
        import uuid
        
        # If not provided report_id，then autogenerate
        if not report_id:
            report_id = f"report_{uuid.uuid4().hex[:12]}"
        start_time = datetime.now()
        
        report = Report(
            report_id=report_id,
            simulation_id=self.simulation_id,
            graph_id=self.graph_id,
            simulation_requirement=self.simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        
        # CompletedSection Titlelist（for progress tracking）
        completed_section_titles = []
        
        try:
            # Initialize: Create report folder and save initial state
            ReportManager._ensure_report_folder(report_id)

            # Fetch real-market context from pitchy.pro RAG once; sections will
            # inject it into their system prompt below.
            self.market_context = self._fetch_market_context()

            # Initialize logslogger（structured logs agent_log.jsonl）
            self.report_logger = ReportLogger(report_id)
            self.report_logger.log_start(
                simulation_id=self.simulation_id,
                graph_id=self.graph_id,
                simulation_requirement=self.simulation_requirement
            )
            
            # Initialize console logslogger（console_log.txt）
            self.console_logger = ReportConsoleLogger(report_id)
            
            ReportManager.update_progress(
                report_id, "pending", 0, "Initializereport...",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            # phase1: planoutline
            report.status = ReportStatus.PLANNING
            ReportManager.update_progress(
                report_id, "planning", 5, "Start planning report outline...",
                completed_sections=[]
            )
            
            # Log outline planning start
            self.report_logger.log_planning_start()
            
            if progress_callback:
                progress_callback("planning", 0, "Start planning report outline...")
            
            outline = self._fixed_custdev_outline()
            if progress_callback:
                progress_callback("planning", 15, "Evidence-first outline prepared")
            report.outline = outline
            
            # recordplancompletion log
            self.report_logger.log_planning_complete(outline.to_dict())
            
            # saveoutlinetofile
            ReportManager.save_outline(report_id, outline)
            ReportManager.update_progress(
                report_id, "planning", 15, f"Outline planning completed, total{len(outline.sections)}sections",
                completed_sections=[]
            )
            ReportManager.save_report(report)
            
            logger.info(f"outlinesavedtofile: {report_id}/outline.json")
            
            # Phase 2: Sequentially generate sectionsgeneration (per sectionsave）
            report.status = ReportStatus.GENERATING
            
            total_sections = len(outline.sections)
            generated_sections = []  # savecontentfor context
            
            for i, section in enumerate(outline.sections):
                section_num = i + 1
                base_progress = 20 + int((i / total_sections) * 70)
                
                # Update progress
                ReportManager.update_progress(
                    report_id, "generating", base_progress,
                    f"generatinggenerateSection: {section.title} ({section_num}/{total_sections})",
                    current_section=section.title,
                    completed_sections=completed_section_titles
                )
                
                if progress_callback:
                    progress_callback(
                        "generating", 
                        base_progress, 
                        f"generatinggenerateSection: {section.title} ({section_num}/{total_sections})"
                    )
                
                # Generate main sectioncontent
                section_content = self._generate_section_fast(
                    section=section,
                    outline=outline,
                    previous_sections=generated_sections,
                    progress_callback=lambda stage, prog, msg:
                        progress_callback(
                            stage, 
                            base_progress + int(prog * 0.7 / total_sections),
                            msg
                        ) if progress_callback else None,
                    section_index=section_num
                )
                
                section.content = section_content
                generated_sections.append(f"## {section.title}\n\n{section_content}")

                # saveSection
                ReportManager.save_section(report_id, section_num, section)
                completed_section_titles.append(section.title)

                # Log sectioncompletion log
                full_section_content = f"## {section.title}\n\n{section_content}"

                if self.report_logger:
                    self.report_logger.log_section_full_complete(
                        section_title=section.title,
                        section_index=section_num,
                        full_content=full_section_content.strip()
                    )

                logger.info(f"Sectionsaved: {report_id}/section_{section_num:02d}.md")
                
                # Update progress
                ReportManager.update_progress(
                    report_id, "generating", 
                    base_progress + int(70 / total_sections),
                    f"Section {section.title} completed",
                    current_section=None,
                    completed_sections=completed_section_titles
                )
            
            # phase3: assembleComplete report
            if progress_callback:
                progress_callback("generating", 95, "generatingassemblecompletereport...")
            
            ReportManager.update_progress(
                report_id, "generating", 95, "generatingassemblecompletereport...",
                completed_sections=completed_section_titles
            )
            
            # Using ReportManagerassembleComplete report
            report.markdown_content = ReportManager.assemble_full_report(report_id, outline)
            report.status = ReportStatus.COMPLETED
            report.completed_at = datetime.now().isoformat()
            
            # Calculate total elapsed time
            total_time_seconds = (datetime.now() - start_time).total_seconds()
            
            # recordReportcompletion log
            if self.report_logger:
                self.report_logger.log_report_complete(
                    total_sections=total_sections,
                    total_time_seconds=total_time_seconds
                )
            
            # savefinalReport
            ReportManager.save_report(report)
            ReportManager.update_progress(
                report_id, "completed", 100, "reportgeneratecomplete",
                completed_sections=completed_section_titles
            )
            
            if progress_callback:
                progress_callback("completed", 100, "reportgeneratecomplete")
            
            logger.info(f"reportgeneratecomplete: {report_id}")
            
            # Closeconsoleloglogger
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
            
        except Exception as e:
            logger.error(f"reportgeneratefailed: {str(e)}")
            report.status = ReportStatus.FAILED
            report.error = str(e)
            
            # recorderrorlog
            if self.report_logger:
                self.report_logger.log_error(str(e), "failed")
            
            # savefailedstatus
            try:
                ReportManager.save_report(report)
                ReportManager.update_progress(
                    report_id, "failed", -1, f"reportgeneratefailed: {str(e)}",
                    completed_sections=completed_section_titles
                )
            except Exception:
                pass  # ignoresavefailederror
            
            # Closeconsoleloglogger
            if self.console_logger:
                self.console_logger.close()
                self.console_logger = None
            
            return report
    
    def chat(
        self, 
        message: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        andReport Agentchat
        
        inchatinAgentcan autonomouslycallretrievaltoolto answer questions
        
        Args:
            message: user message
            chat_history: chathistory
            
        Returns:
            {
                "response": "Agentresponse",
                "tool_calls": [calltoollist],
                "sources": [informationsource]
            }
        """
        logger.info(f"Report Agentchat: {message[:50]}...")
        
        chat_history = chat_history or []
        
        # GetalreadygenerateReportcontent
        report_content = ""
        try:
            report = ReportManager.get_report_by_simulation(self.simulation_id)
            if report and report.markdown_content:
                # limitReportlength，avoid overly long context
                report_content = report.markdown_content[:15000]
                if len(report.markdown_content) > 15000:
                    report_content += "\n\n... [reportcontenthasTruncate] ..."
        except Exception as e:
            logger.warning(f"getreportcontentfailed: {e}")
        
        system_prompt = CHAT_SYSTEM_PROMPT_TEMPLATE.format(
            simulation_requirement=self.simulation_requirement,
            report_content=report_content if report_content else "（nonereport）",
            tools_description=self._get_tools_description(),
        )

        # Buildmessage
        messages = [{"role": "system", "content": system_prompt}]
        
        # add historychat
        for h in chat_history[-10:]:  # limithistorylength
            messages.append(h)
        
        # add user message
        messages.append({
            "role": "user", 
            "content": message
        })
        
        # ReACT loop（simplified version）
        tool_calls_made = []
        max_iterations = 2  # reduce iterations
        
        for iteration in range(max_iterations):
            response = self.llm.chat(
                messages=messages,
                temperature=0.5
            )
            
            # parseTool call
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                # noTool call，directlyReturnresponse
                clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', response, flags=re.DOTALL)
                clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
                
                return {
                    "response": clean_response.strip(),
                    "tool_calls": tool_calls_made,
                    "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
                }
            
            # Execute toolcall（limitcount）
            tool_results = []
            for call in tool_calls[:1]:  # at mostExecute1 time tool call
                if len(tool_calls_made) >= self.MAX_TOOL_CALLS_PER_CHAT:
                    break
                result = self._execute_tool(call["name"], call.get("parameters", {}))
                tool_results.append({
                    "tool": call["name"],
                    "result": result[:1500]  # limitresultlength
                })
                tool_calls_made.append(call)
            
            # convertresultadd to message
            messages.append({"role": "assistant", "content": response})
            observation = "\n".join([f"[{r['tool']}result]\n{r['result']}" for r in tool_results])
            messages.append({
                "role": "user",
                "content": observation + CHAT_OBSERVATION_SUFFIX
            })
        
        # Reachedmaximum iteration，Getfinalresponse
        final_response = self.llm.chat(
            messages=messages,
            temperature=0.5
        )
        
        # cleanresponse
        clean_response = re.sub(r'<tool_call>.*?</tool_call>', '', final_response, flags=re.DOTALL)
        clean_response = re.sub(r'\[TOOL_CALL\].*?\)', '', clean_response)
        
        return {
            "response": clean_response.strip(),
            "tool_calls": tool_calls_made,
            "sources": [tc.get("parameters", {}).get("query", "") for tc in tool_calls_made]
        }


class ReportManager:
    """
    ReportManagemanager
    
    responsible forReportpersistence storage and retrieval
    
    filestructure（perSectionoutput）：
    reports/
      {report_id}/
        meta.json          - Reportmetainformationand status
        outline.json       - Reportoutline
        progress.json      - generateProgress
        section_01.md      - Section 1
        section_02.md      - Section 2
        ...
        full_report.md     - Complete report
    """
    
    # Reportstorage directory
    REPORTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'reports')
    
    @classmethod
    def _ensure_reports_dir(cls):
        """ensurereportroot directory exists"""
        os.makedirs(cls.REPORTS_DIR, exist_ok=True)
    
    @classmethod
    def _get_report_folder(cls, report_id: str) -> str:
        """getreportfolderpath"""
        return os.path.join(cls.REPORTS_DIR, report_id)
    
    @classmethod
    def _ensure_report_folder(cls, report_id: str) -> str:
        """ensurereportfolderexists andreturnedpath"""
        folder = cls._get_report_folder(report_id)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    @classmethod
    def _get_report_path(cls, report_id: str) -> str:
        """getreportmetainformationfile path"""
        return os.path.join(cls._get_report_folder(report_id), "meta.json")
    
    @classmethod
    def _get_report_markdown_path(cls, report_id: str) -> str:
        """getcompletereportMarkdownfile path"""
        return os.path.join(cls._get_report_folder(report_id), "full_report.md")
    
    @classmethod
    def _get_outline_path(cls, report_id: str) -> str:
        """getoutlinefile path"""
        return os.path.join(cls._get_report_folder(report_id), "outline.json")
    
    @classmethod
    def _get_progress_path(cls, report_id: str) -> str:
        """getprogressfile path"""
        return os.path.join(cls._get_report_folder(report_id), "progress.json")
    
    @classmethod
    def _get_section_path(cls, report_id: str, section_index: int) -> str:
        """getSectionMarkdownfile path"""
        return os.path.join(cls._get_report_folder(report_id), f"section_{section_index:02d}.md")
    
    @classmethod
    def _get_agent_log_path(cls, report_id: str) -> str:
        """get Agent logsfile path"""
        return os.path.join(cls._get_report_folder(report_id), "agent_log.jsonl")
    
    @classmethod
    def _get_console_log_path(cls, report_id: str) -> str:
        """getconsolelogsfile path"""
        return os.path.join(cls._get_report_folder(report_id), "console_log.txt")
    
    @classmethod
    def get_console_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Getconsolelogcontent
        
        This isReportgenerateduring processconsoleoutputlog（INFO、WARNINGetc），
        and agent_log.jsonl structured logsdifferent。
        
        Args:
            report_id: ReportID
            from_line: from which rowrowStartRead（for incrementalGet，0 means from the beginningStart）
            
        Returns:
            {
                "logs": [logrowlist],
                "total_lines": totalrownumber,
                "from_line": startrownumber,
                "has_more": whether there are morelog
            }
        """
        log_path = cls._get_console_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    # keeporiginallogrow，remove trailingrowcharacter
                    logs.append(line.rstrip('\n\r'))
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # alreadyReadto the end
        }
    
    @classmethod
    def get_console_log_stream(cls, report_id: str) -> List[str]:
        """
        GetCompleteconsolelog（one-timeGetall）
        
        Args:
            report_id: ReportID
            
        Returns:
            logrowlist
        """
        result = cls.get_console_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def get_agent_log(cls, report_id: str, from_line: int = 0) -> Dict[str, Any]:
        """
        Get Agent logcontent
        
        Args:
            report_id: ReportID
            from_line: from which rowrowStartRead（for incrementalGet，0 means from the beginningStart）
            
        Returns:
            {
                "logs": [logentrylist],
                "total_lines": totalrownumber,
                "from_line": startrownumber,
                "has_more": whether there are morelog
            }
        """
        log_path = cls._get_agent_log_path(report_id)
        
        if not os.path.exists(log_path):
            return {
                "logs": [],
                "total_lines": 0,
                "from_line": 0,
                "has_more": False
            }
        
        logs = []
        total_lines = 0
        
        with open(log_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines = i + 1
                if i >= from_line:
                    try:
                        log_entry = json.loads(line.strip())
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # skip parsingfailedrow
                        continue
        
        return {
            "logs": logs,
            "total_lines": total_lines,
            "from_line": from_line,
            "has_more": False  # alreadyReadto the end
        }
    
    @classmethod
    def get_agent_log_stream(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        GetComplete Agent log（for one-timeGetall）
        
        Args:
            report_id: ReportID
            
        Returns:
            logentrylist
        """
        result = cls.get_agent_log(report_id, from_line=0)
        return result["logs"]
    
    @classmethod
    def save_outline(cls, report_id: str, outline: ReportOutline) -> None:
        """
        saveReportoutline
        
        in planningphasecompleteimmediately aftercall
        """
        cls._ensure_report_folder(report_id)
        
        with open(cls._get_outline_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(outline.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"outlinesaved: {report_id}")
    
    @classmethod
    def save_section(
        cls,
        report_id: str,
        section_index: int,
        section: ReportSection
    ) -> str:
        """
        savesinglesections

        inEach sectiongeneration completed afterimmediatelycall，implementperSectionoutput

        Args:
            report_id: ReportID
            section_index: Sectionindex（from1Start）
            section: Sectionobject

        Returns:
            savefile path
        """
        cls._ensure_report_folder(report_id)

        # BuildSectionMarkdowncontent - clean possibleduplicatetitle
        cleaned_content = cls._clean_section_content(section.content, section.title)
        md_content = f"## {section.title}\n\n"
        if cleaned_content:
            md_content += f"{cleaned_content}\n\n"

        # savefile
        file_suffix = f"section_{section_index:02d}.md"
        file_path = os.path.join(cls._get_report_folder(report_id), file_suffix)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"Sectionsaved: {report_id}/{file_suffix}")
        return file_path
    
    @classmethod
    def _clean_section_content(cls, content: str, section_title: str) -> str:
        """
        cleanSectioncontent
        
        1. removecontentbeginningandSection TitleduplicateMarkdowntitlerow
        2. convertall ### and below levelstitleconvert toboldtext
        
        Args:
            content: originalcontent
            section_title: Section Title
            
        Returns:
            after cleaningcontent
        """
        import re
        
        if not content:
            return content
        
        content = content.strip()
        lines = content.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Checkwhether isMarkdowntitlerow
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                
                # Checkwhether isandSection Titleduplicatetitle（skip first5rowwithinduplicate）
                if i < 5:
                    if title_text == section_title or title_text.replace(' ', '') == section_title.replace(' ', ''):
                        skip_next_empty = True
                        continue
                
                # convertallleveltitle（#, ##, ###, ####etc）convert tobold
                # becauseSection Titleadded by system，contentshould not have anytitle
                cleaned_lines.append(f"**{title_text}**")
                cleaned_lines.append("")  # addempty line
                continue
            
            # if previousrowwas skippedtitle，and currentrowempty，also skip
            if skip_next_empty and stripped == '':
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        # removebeginningempty line
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        
        # removebeginningseparatorline
        while cleaned_lines and cleaned_lines[0].strip() in ['---', '***', '___']:
            cleaned_lines.pop(0)
            # meanwhileremoveseparatorline afterempty line
            while cleaned_lines and cleaned_lines[0].strip() == '':
                cleaned_lines.pop(0)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def update_progress(
        cls, 
        report_id: str, 
        status: str, 
        progress: int, 
        message: str,
        current_section: str = None,
        completed_sections: List[str] = None
    ) -> None:
        """
        UpdateReportgenerateProgress
        
        frontend can getReadprogress.jsonGetrealtimeProgress
        """
        cls._ensure_report_folder(report_id)
        
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections or [],
            "updated_at": datetime.now().isoformat()
        }
        
        with open(cls._get_progress_path(report_id), 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def get_progress(cls, report_id: str) -> Optional[Dict[str, Any]]:
        """getreportgenerateprogress"""
        path = cls._get_progress_path(report_id)
        
        if not os.path.exists(path):
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def get_generated_sections(cls, report_id: str) -> List[Dict[str, Any]]:
        """
        GetalreadygenerateSectionlist
        
        ReturnallalreadysaveSectionfileinformation
        """
        folder = cls._get_report_folder(report_id)
        
        if not os.path.exists(folder):
            return []
        
        sections = []
        for filename in sorted(os.listdir(folder)):
            if filename.startswith('section_') and filename.endswith('.md'):
                file_path = os.path.join(folder, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # fromfilename parsingSectionindex
                parts = filename.replace('.md', '').split('_')
                section_index = int(parts[1])

                sections.append({
                    "filename": filename,
                    "section_index": section_index,
                    "content": content
                })

        return sections
    
    @classmethod
    def assemble_full_report(cls, report_id: str, outline: ReportOutline) -> str:
        """
        assembleComplete report
        
        fromsaveSectionfileassembleComplete report，and processrowtitleclean
        """
        folder = cls._get_report_folder(report_id)
        
        # BuildReportheader
        md_content = f"# {outline.title}\n\n"
        md_content += f"> {outline.summary}\n\n"
        md_content += f"---\n\n"
        
        # sequentiallyReadallSectionfile
        sections = cls.get_generated_sections(report_id)
        for section_info in sections:
            md_content += section_info["content"]
        
        # post-processing：clean entireReporttitlequestion
        md_content = cls._post_process_report(md_content, outline)
        
        # saveComplete report
        full_path = cls._get_report_markdown_path(report_id)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"completereporthasassemble: {report_id}")
        return md_content
    
    @classmethod
    def _post_process_report(cls, content: str, outline: ReportOutline) -> str:
        """
        post-processingReportcontent
        
        1. removeduplicatetitle
        2. keepReportmain title(#)andSection Title(##)，removeother levelstitle(###, ####etc)
        3. clean redundantempty lineandseparatorline
        
        Args:
            content: originalReportcontent
            outline: Reportoutline
            
        Returns:
            after processingcontent
        """
        import re
        
        lines = content.split('\n')
        processed_lines = []
        prev_was_heading = False
        
        # collectoutlineinallSection Title
        section_titles = set()
        for section in outline.sections:
            section_titles.add(section.title)
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Checkwhether istitlerow
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
            
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # Checkwhether isduplicatetitle（inconsecutive5rowappear the same withincontenttitle）
                is_duplicate = False
                for j in range(max(0, len(processed_lines) - 5), len(processed_lines)):
                    prev_line = processed_lines[j].strip()
                    prev_match = re.match(r'^(#{1,6})\s+(.+)$', prev_line)
                    if prev_match:
                        prev_title = prev_match.group(2).strip()
                        if prev_title == title:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    # skipduplicatetitleand subsequentempty line
                    i += 1
                    while i < len(lines) and lines[i].strip() == '':
                        i += 1
                    continue
                
                # titlelevel handling：
                # - # (level=1) onlykeepReportmain title
                # - ## (level=2) keepSection Title
                # - ### and below (level>=3) convert toboldtext
                
                if level == 1:
                    if title == outline.title:
                        # keepReportmain title
                        processed_lines.append(line)
                        prev_was_heading = True
                    elif title in section_titles:
                        # Section Titleerrorusing#，corrected to##
                        processed_lines.append(f"## {title}")
                        prev_was_heading = True
                    else:
                        # other first-leveltitleconvert tobold
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                elif level == 2:
                    if title in section_titles or title == outline.title:
                        # keepSection Title
                        processed_lines.append(line)
                        prev_was_heading = True
                    else:
                        # nonSectionsecond-leveltitleconvert tobold
                        processed_lines.append(f"**{title}**")
                        processed_lines.append("")
                        prev_was_heading = False
                else:
                    # ### and below levelstitleconvert toboldtext
                    processed_lines.append(f"**{title}**")
                    processed_lines.append("")
                    prev_was_heading = False
                
                i += 1
                continue
            
            elif stripped == '---' and prev_was_heading:
                # skiptitlefollowed immediately byseparatorline
                i += 1
                continue
            
            elif stripped == '' and prev_was_heading:
                # titleafter onlykeeponeempty line
                if processed_lines and processed_lines[-1].strip() != '':
                    processed_lines.append(line)
                prev_was_heading = False
            
            else:
                processed_lines.append(line)
                prev_was_heading = False
            
            i += 1
        
        # cleanconsecutivemultipleempty line（keepat most2)
        result_lines = []
        empty_count = 0
        for line in processed_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    @classmethod
    def save_report(cls, report: Report) -> None:
        """SavereportmetainformationandcompleteReport"""
        cls._ensure_report_folder(report.report_id)
        
        # savemetainformationJSON
        with open(cls._get_report_path(report.report_id), 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # saveoutline
        if report.outline:
            cls.save_outline(report.report_id, report.outline)
        
        # saveCompleteMarkdownReport
        if report.markdown_content:
            with open(cls._get_report_markdown_path(report.report_id), 'w', encoding='utf-8') as f:
                f.write(report.markdown_content)
        
        logger.info(f"reportsaved: {report.report_id}")
    
    @classmethod
    def get_report(cls, report_id: str) -> Optional[Report]:
        """getreport"""
        path = cls._get_report_path(report_id)
        
        if not os.path.exists(path):
            # backward compatibleformat：Checkdirectlystored inreportsunder directoryfile
            old_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
            if os.path.exists(old_path):
                path = old_path
            else:
                return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # rebuildReportobject
        outline = None
        if data.get('outline'):
            outline_data = data['outline']
            sections = []
            for s in outline_data.get('sections', []):
                sections.append(ReportSection(
                    title=s['title'],
                    content=s.get('content', '')
                ))
            outline = ReportOutline(
                title=outline_data['title'],
                summary=outline_data['summary'],
                sections=sections
            )
        
        # ifmarkdown_contentempty，attempt tofromfull_report.mdRead
        markdown_content = data.get('markdown_content', '')
        if not markdown_content:
            full_report_path = cls._get_report_markdown_path(report_id)
            if os.path.exists(full_report_path):
                with open(full_report_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
        
        return Report(
            report_id=data['report_id'],
            simulation_id=data['simulation_id'],
            graph_id=data['graph_id'],
            simulation_requirement=data['simulation_requirement'],
            status=ReportStatus(data['status']),
            outline=outline,
            markdown_content=markdown_content,
            created_at=data.get('created_at', ''),
            completed_at=data.get('completed_at', ''),
            error=data.get('error')
        )
    
    @classmethod
    def get_report_by_simulation(cls, simulation_id: str) -> Optional[Report]:
        """based onsimulationIDgetreport"""
        cls._ensure_reports_dir()
        
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # newformat：filefolder
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report and report.simulation_id == simulation_id:
                    return report
            # backward compatibleformat：JSONfile
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report and report.simulation_id == simulation_id:
                    return report
        
        return None
    
    @classmethod
    def list_reports(cls, simulation_id: Optional[str] = None, limit: int = 50) -> List[Report]:
        """columnappearreport"""
        cls._ensure_reports_dir()
        
        reports = []
        for item in os.listdir(cls.REPORTS_DIR):
            item_path = os.path.join(cls.REPORTS_DIR, item)
            # newformat：filefolder
            if os.path.isdir(item_path):
                report = cls.get_report(item)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
            # backward compatibleformat：JSONfile
            elif item.endswith('.json'):
                report_id = item[:-5]
                report = cls.get_report(report_id)
                if report:
                    if simulation_id is None or report.simulation_id == simulation_id:
                        reports.append(report)
        
        # sorted by creation time descending
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    @classmethod
    def delete_report(cls, report_id: str) -> bool:
        """Deletereport（entirefolder）"""
        import shutil
        
        folder_path = cls._get_report_folder(report_id)
        
        # newformat：Deleteentirefilefolder
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"reportfolderhasDelete: {report_id}")
            return True
        
        # backward compatibleformat：Deleteseparatefile
        deleted = False
        old_json_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.json")
        old_md_path = os.path.join(cls.REPORTS_DIR, f"{report_id}.md")
        
        if os.path.exists(old_json_path):
            os.remove(old_json_path)
            deleted = True
        if os.path.exists(old_md_path):
            os.remove(old_md_path)
            deleted = True
        
        return deleted
