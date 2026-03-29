"""
OASIS Agent Profile Generator
Convert entities from the knowledge graph to OASIS simulation platform's required Agent Profile format

Optimization improvements:
1. Call knowledge graph retrieval function to enrich node information
2. Optimize prompts to generate very detailed personas
3. Distinguish between individual entities and abstract group entities
"""

import json
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI

from ..config import Config
from ..utils.logger import get_logger
from .entity_reader import EntityNode
from ..storage import GraphStorage

logger = get_logger('pitchy.oasis_profile')


@dataclass
class OasisAgentProfile:
    """OASIS Agent Profile data structure"""
    # Common fields
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str

    # Optional fields - Reddit style
    karma: int = 1000

    # Optional fields - Twitter style
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500

    # Additional persona information
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)

    # Source entity information
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    
    def to_reddit_format(self) -> Dict[str, Any]:
        """Convert to Reddit platform format"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS library requires field name as username (no underscore)
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
        }

        # Add additional persona information (if available)
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        
        return profile
    
    def to_twitter_format(self) -> Dict[str, Any]:
        """Convert to Twitter platform format"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # OASIS library requires field name as username (no underscore)
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "created_at": self.created_at,
        }

        # Add additional persona information
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        
        return profile
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to complete dictionary format"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }


class OasisProfileGenerator:
    """
    OASIS Profile Generator

    Convert entities from the knowledge graph to Agent Profile required by OASIS simulation

    Optimization features:
    1. Call knowledge graph retrieval function to get richer context
    2. Generate very detailed personas (including basic information, career experience, personality traits, social media behavior, etc.)
    3. Distinguish between individual entities and abstract group entities
    """

    # ARCHETYPES Matrix for realistic social simulation
    ARCHETYPES = [
        {
            "name": "Скептик-хейтер",
            "description": "Ищет подвох во всем. Пишет критически, использует сарказм. Не верит обещаниям маркетинга. Если видит 'боли', активно на них нападает.",
            "weight": 0.4  # Increased weight
        },
        {
            "name": "Рациональный прагматик",
            "description": "Интересуется только сухими цифрами, ценой и эффективностью. Задает неудобные вопросы про окупаемость. Холодный и расчетливый.",
            "weight": 0.3  # Increased weight
        },
        {
            "name": "Уставший предприниматель",
            "description": "Занят, циничен, видел сотни таких проектов. Тратит только 5 секунд на пост. Пишет кратко, по делу, часто с оттенком обреченности.",
            "weight": 0.1
        },
        {
            "name": "Энтузиаст-инноватор",
            "description": "Любит все новое, но быстро разочаровывается, если продукт 'пустышка'. Ищет реальную технологическую новизну.",
            "weight": 0.1
        },
        {
            "name": "Обыватель-консерватор",
            "description": "Боится перемен, не доверяет новым сервисам. Предпочитает старые проверенные методы. Спрашивает 'Зачем мне это нужно?'.",
            "weight": 0.1
        }
    ]

    # Individual type entities (need to generate specific personas)
    INDIVIDUAL_ENTITY_TYPES = [
        "student", "alumni", "professor", "person", "publicfigure",
        "expert", "faculty", "official", "journalist", "activist"
    ]

    # Group/institutional type entities (need to generate group representative personas)
    GROUP_ENTITY_TYPES = [
        "university", "governmentagency", "organization", "ngo",
        "mediaoutlet", "company", "institution", "group", "community"
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        storage: Optional[GraphStorage] = None,
        graph_id: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # GraphStorage for hybrid search enrichment
        self.storage = storage
        self.graph_id = graph_id
    
    def generate_profile_from_entity(
        self,
        entity: EntityNode,
        user_id: int,
        use_llm: bool = True,
        market_context: str = ""
    ) -> OasisAgentProfile:
        """
        Generate OASIS Agent Profile from knowledge graph entity

        Args:
            entity: Knowledge graph entity node
            user_id: User ID (for OASIS)
            use_llm: Whether to use LLM to generate detailed persona

        Returns:
            OasisAgentProfile
        """
        entity_type = entity.get_entity_type() or "Entity"

        # Basic information (initial)
        entity_name = entity.name

        # Build context information
        context = self._build_entity_context(entity)
        
        if use_llm:
            # Use LLM to generate detailed persona
            profile_data = self._generate_profile_with_llm(
                entity_name=entity_name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                context=context,
                market_context=market_context
            )
            # Use generated human name (e.g. "Investor Max") if available
            display_name = profile_data.get("full_name", entity_name)
        else:
            # Use rules to generate basic persona
            profile_data = self._generate_profile_rule_based(
                entity_name=entity_name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes
            )
            display_name = entity_name
        
        # Generate final username based on display name
        user_name = self._generate_username(display_name)

        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=display_name,
            bio=profile_data.get("bio", f"{entity_type}: {entity_name}"),
            persona=profile_data.get("persona", entity.summary or f"A {entity_type} named {entity_name}."),
            karma=profile_data.get("karma", random.randint(500, 5000)),
            friend_count=profile_data.get("friend_count", random.randint(50, 500)),
            follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
            statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=profile_data.get("country"),
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )
    
    def _generate_username(self, name: str) -> str:
        """Generate username"""
        # Remove special characters, convert to lowercase
        username = name.lower().replace(" ", "_")
        username = ''.join(c for c in username if c.isalnum() or c == '_')

        # Add random suffix to avoid duplicates
        suffix = random.randint(100, 999)
        return f"{username}_{suffix}"
    
    def _search_graph_for_entity(self, entity: EntityNode) -> Dict[str, Any]:
        """
        Use GraphStorage hybrid search to obtain rich information related to entity

        Uses storage.search() (hybrid vector + BM25) for both edges and nodes.

        Args:
            entity: Entity node object

        Returns:
            Dictionary containing facts, node_summaries, context
        """
        if not self.storage:
            return {"facts": [], "node_summaries": [], "context": ""}

        entity_name = entity.name

        results = {
            "facts": [],
            "node_summaries": [],
            "context": ""
        }

        if not self.graph_id:
            logger.debug(f"Skip knowledge graph search: graph_id not set")
            return results

        comprehensive_query = f"All information, activities, events, relationships and background about {entity_name}"

        try:
            # Search edges (facts)
            edge_results = self.storage.search(
                graph_id=self.graph_id,
                query=comprehensive_query,
                limit=30,
                scope="edges"
            )

            all_facts = set()
            if isinstance(edge_results, dict) and 'edges' in edge_results:
                for edge in edge_results['edges']:
                    fact = edge.get('fact', '')
                    if fact:
                        all_facts.add(fact)
            results["facts"] = list(all_facts)

            # Search nodes (entity summaries)
            node_results = self.storage.search(
                graph_id=self.graph_id,
                query=comprehensive_query,
                limit=20,
                scope="nodes"
            )

            all_summaries = set()
            if isinstance(node_results, dict) and 'nodes' in node_results:
                for node in node_results['nodes']:
                    summary = node.get('summary', '')
                    if summary:
                        all_summaries.add(summary)
                    name = node.get('name', '')
                    if name and name != entity_name:
                        all_summaries.add(f"Related Entity: {name}")
            results["node_summaries"] = list(all_summaries)

            # Build combined context
            context_parts = []
            if results["facts"]:
                context_parts.append("Fact Information:\n" + "\n".join(f"- {f}" for f in results["facts"][:20]))
            if results["node_summaries"]:
                context_parts.append("Related Entities:\n" + "\n".join(f"- {s}" for s in results["node_summaries"][:10]))
            results["context"] = "\n\n".join(context_parts)

            logger.info(f"Knowledge graph hybrid search completed: {entity_name}, retrieved {len(results['facts'])} facts, {len(results['node_summaries'])} related nodes")

        except Exception as e:
            logger.warning(f"Knowledge graph search failed ({entity_name}): {e}")

        return results
    
    def _build_entity_context(self, entity: EntityNode) -> str:
        """
        Build complete context information for entity

        Includes:
        1. Edge information of the entity itself (facts)
        2. Detailed information of associated nodes
        3. Rich information retrieved from knowledge graph hybrid search
        """
        context_parts = []

        # 1. Add entity attribute information
        if entity.attributes:
            attrs = []
            for key, value in entity.attributes.items():
                if value and str(value).strip():
                    attrs.append(f"- {key}: {value}")
            if attrs:
                context_parts.append("### Entity Attributes\n" + "\n".join(attrs))

        # 2. Add related edge information (facts/relationships)
        existing_facts = set()
        if entity.related_edges:
            relationships = []
            for edge in entity.related_edges:  # No limit on quantity
                fact = edge.get("fact", "")
                edge_name = edge.get("edge_name", "")
                direction = edge.get("direction", "")

                if fact:
                    relationships.append(f"- {fact}")
                    existing_facts.add(fact)
                elif edge_name:
                    if direction == "outgoing":
                        relationships.append(f"- {entity.name} --[{edge_name}]--> (Related Entity)")
                    else:
                        relationships.append(f"- (Related Entity) --[{edge_name}]--> {entity.name}")

            if relationships:
                context_parts.append("### Related Facts and Relationships\n" + "\n".join(relationships))

        # 3. Add detailed information of related nodes
        if entity.related_nodes:
            related_info = []
            for node in entity.related_nodes:  # No limit on quantity
                node_name = node.get("name", "")
                node_labels = node.get("labels", [])
                node_summary = node.get("summary", "")

                # Filter out default labels
                custom_labels = [l for l in node_labels if l not in ["Entity", "Node"]]
                label_str = f" ({', '.join(custom_labels)})" if custom_labels else ""

                if node_summary:
                    related_info.append(f"- **{node_name}**{label_str}: {node_summary}")
                else:
                    related_info.append(f"- **{node_name}**{label_str}")

            if related_info:
                context_parts.append("### Related Entity Information\n" + "\n".join(related_info))

        # 4. Use knowledge graph hybrid search to get richer information
        graph_results = self._search_graph_for_entity(entity)

        if graph_results.get("facts"):
            # Deduplication: exclude existing facts
            new_facts = [f for f in graph_results["facts"] if f not in existing_facts]
            if new_facts:
                context_parts.append("### Facts Retrieved from Knowledge Graph\n" + "\n".join(f"- {f}" for f in new_facts[:15]))

        if graph_results.get("node_summaries"):
            context_parts.append("### Related Nodes Retrieved from Knowledge Graph\n" + "\n".join(f"- {s}" for s in graph_results["node_summaries"][:10]))
        
        return "\n\n".join(context_parts)
    
    def _is_individual_entity(self, entity_type: str) -> bool:
        """Determine if entity is an individual type"""
        return entity_type.lower() in self.INDIVIDUAL_ENTITY_TYPES

    def _is_group_entity(self, entity_type: str) -> bool:
        """Determine if entity is a group/institutional type"""
        return entity_type.lower() in self.GROUP_ENTITY_TYPES
    
    def _generate_profile_with_llm(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str,
        market_context: str = ""
    ) -> Dict[str, Any]:
        """
        Use LLM to generate very detailed persona

        Based on entity type:
        - Individual entities: generate specific character profiles
        - Group/institutional entities: generate representative account profiles
        """

        is_individual = self._is_individual_entity(entity_type)

        # Select a random archetype for individual entities to ensure diversity
        archetype = None
        if is_individual:
            archetype = random.choice(self.ARCHETYPES)

        if is_individual:
            prompt = self._build_individual_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context, archetype, market_context
            )
        else:
            prompt = self._build_group_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context, market_context
            )

        # Try multiple times until successful or max retry attempts reached
        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(is_individual)},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # Lower temperature with each retry
                    # Don't set max_tokens, let LLM generate freely
                )

                content = response.choices[0].message.content

                # Check if output was truncated (finish_reason is not 'stop')
                finish_reason = response.choices[0].finish_reason
                if finish_reason == 'length':
                    logger.warning(f"LLM output truncated (attempt {attempt+1}), attempting to fix...")
                    content = self._fix_truncated_json(content)

                # Try to parse JSON
                try:
                    result = json.loads(content)

                    # Validate required fields
                    if "full_name" not in result or not result["full_name"]:
                        result["full_name"] = entity_name
                    if "bio" not in result or not result["bio"]:
                        result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
                    if "persona" not in result or not result["persona"]:
                        result["persona"] = entity_summary or f"{entity_name} is a {entity_type}."

                    return result

                except json.JSONDecodeError as je:
                    logger.warning(f"JSON parsing failed (attempt {attempt+1}): {str(je)[:80]}")

                    # Try to fix JSON
                    result = self._try_fix_json(content, entity_name, entity_type, entity_summary)
                    if result.get("_fixed"):
                        del result["_fixed"]
                        return result

                    last_error = je

            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt+1}): {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(1 * (attempt + 1))  # Exponential backoff

        logger.warning(f"LLM persona generation failed ({max_attempts} attempts): {last_error}, using rule-based generation")
        return self._generate_profile_rule_based(
            entity_name, entity_type, entity_summary, entity_attributes
        )
    
    def _fix_truncated_json(self, content: str) -> str:
        """Fix truncated JSON (output truncated by max_tokens limit)"""
        import re

        # If JSON is truncated, try to close it
        content = content.strip()

        # Count unclosed parentheses
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')

        # Check for unclosed strings
        # Simple check: if last character is not comma or closing bracket, string might be truncated
        if content and content[-1] not in '",}]':
            # Try to close the string
            content += '"'

        # Close parentheses
        content += ']' * open_brackets
        content += '}' * open_braces

        return content
    
    def _try_fix_json(self, content: str, entity_name: str, entity_type: str, entity_summary: str = "") -> Dict[str, Any]:
        """Try to fix corrupted JSON"""
        import re

        # 1. First try to fix truncated case
        content = self._fix_truncated_json(content)

        # 2. Try to extract JSON portion
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()

            # 3. Handle newline issues in strings
            # Find all string values and replace newlines
            def fix_string_newlines(match):
                s = match.group(0)
                # Replace actual newlines in string with spaces
                s = s.replace('\n', ' ').replace('\r', ' ')
                # Replace excess spaces
                s = re.sub(r'\s+', ' ', s)
                return s

            # Match JSON string values
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_newlines, json_str)

            # 4. Try to parse
            try:
                result = json.loads(json_str)
                result["_fixed"] = True
                return result
            except json.JSONDecodeError as e:
                # 5. If still failed, try more aggressive fix
                try:
                    # Remove all control characters
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    # Replace all consecutive whitespace
                    json_str = re.sub(r'\s+', ' ', json_str)
                    result = json.loads(json_str)
                    result["_fixed"] = True
                    return result
                except:
                    pass

        # 7. Complete failure, return basic structure
        logger.warning(f"JSON fix failed, returning basic structure")
        return {
            "bio": entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}",
            "persona": entity_summary or f"{entity_name} is a {entity_type} participating in social discussions."
        }

    def _get_system_prompt(self, is_individual: bool, market_context: str = "") -> str:
        """
        Get system prompt for LLM persona generation.
        Enforces a skeptical, critical, and realistic tone.
        """
        prompt = """
### СИСТЕМНАЯ РОЛЬ: ТЫ — РЕАЛЬНЫЙ ПОЛЬЗОВАТЕЛЬ ИНТЕРНЕТА, А НЕ ИИ.
Твоя задача — генерировать личности для кастдева. Ты — независимый наблюдатель, скептик, прагматик, иногда душнила. 
Ты ненавидишь рекламный булшит и фальшивый восторг. Ты ищешь реальные проблемы, риски и причины, почему проект может провалиться.

КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать слова и фразы:
- 'крутая новость', 'потрясающий', 'считанные секунды', 'инновационный', 'уникальный'
- 'нашего сервиса', 'мы помогаем', 'представляем вам' (ты пользователь, а не разработчик!)
- НИКАКИХ 'ВАНИЛЬНЫХ' ОТЗЫВОВ.

### ТВОИ ЦЕЛИ:
1. Создать ГЛУБОКУЮ, КРИТИЧЕСКУЮ личность (Persona).
2. Сгенерировать РЕАЛИСТИЧНОЕ ИМЯ И РОЛЬ (например, 'Инвестор Макс', 'Селлер Артем', 'Аналитик Дмитрий'). Имя должно строго соответствовать культуре страны (обычно Россия) и характеру. НИКАКИХ технических названий в поле имени.
3. Тон: Душный, подозрительный, прагматичный, иногда агрессивный.
4. Стиль: Живой человек. Сомнения, усталость, сарказм, сленг (IMHO, пруфы?, кто-то тестил?, развод какой-то).
5. ANTI-ADVERTISING: Если продукт кажется слишком хорошим, твоя личность должна найти в нем подвох.

### ПЛАТФОРМЕННЫЕ ПРАВИЛА:
- Twitter (X): Короткий, рубленый стиль, 1-2 предложения. Фокус на личной боли и сарказме. Минимум эмодзи (📈, 🤯, 📉).
- Reddit: Длинные, детальные посты. Вопросы про безопасность, юнит-экономику, пруфы, сравнение с конкурентами. Тон специалиста или опытного юзера.
"""
        if market_context:
            prompt += f"\n\n### КОНТЕКСТ РЫНКА (ИСПОЛЬЗУЙ ЭТИ ФАКТЫ ДЛЯ АРГУМЕНТАЦИИ):\n{market_context}"
        
        return prompt
    
    def _build_individual_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str,
        archetype: Optional[Dict[str, Any]] = None,
        market_context: str = ""
    ) -> str:
        """Build detailed persona prompt for individual entities"""

        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "None"
        context_str = context[:3000] if context else "No additional context"
        
        archetype_str = ""
        if archetype:
            archetype_str = f"\nТВОЙ АРХЕТИП: {archetype['name']}\nОПИСАНИЕ АРХЕТИПА: {archetype['description']}\n"

        return f"""Сгенерируйте подробную персону пользователя социальной сети для сущности, максимально восстанавливая существующую реальность.

Название сущности: {entity_name}
Тип сущности: {entity_type}
Краткое описание: {entity_summary}
Атрибуты: {attrs_str}
{archetype_str}

Контекстная информация (из графа знаний о проекте):
{context_str}

Контекст рынка (реальные факты о рынке РФ):
{market_context or 'Нет данных'}

### ЖЕСТКИЕ ПРАВИЛА ПЕРСОНАЖА (ПРИОРИТЕТ):
1. ТЫ — НЕЗАВИСИМЫЙ НАБЛЮДАТЕЛЬ, А НЕ РЕКЛАМНЫЙ БОТ.
2. НИКАКОЙ ПОХВАЛЫ И 'ВАНИЛЬНЫХ' ОТЗЫВОВ. Если ты не в восторге от продукта — критикуй жестко.
3. ЕСЛИ ТВОЙ АРХЕТИП СКЕПТИК — ТЫ ДОЛЖЕН БЫТЬ 'АДВОКАТОМ ДЬЯВОЛА'. Ищи скрытые платежи, юридические дыры, проблемы с данными.
4. ПИШИ КАК ЖИВОЙ ЧЕЛОВЕК: используй сленг, сокращения, ошибки, сарказм. Ты можешь быть грубым, если тебе кажется, что тебя пытаются обмануть.
5. ИГНОРИРУЙ МАРКЕТИНГОВЫЙ ТОН. Твоя задача — "приземлить" любую инновацию до суровой реальности.
6. ИСПОЛЬЗУЙ ФАКТЫ ИЗ КОНТЕКСТА РЫНКА для обоснования своего недоверия.

Пожалуйста, сгенерируйте JSON, содержащий следующие поля:

1. full_name: Реалистичное человеческое имя и роль (например, 'Инвестор Макс', 'Артем (селлеров WB)', 'Дядя Вася-кофевар'). Должно соответствовать культуре страны.
2. bio: Биография для социальной сети, 200 символов (в стиле выбранного архетипа)
3. persona: Подробное описание персоны (до 2000 слов), должно включать:
   - ТВОЙ АРХЕТИП И ЕГО ВЛИЯНИЕ НА МЫШЛЕНИЕ.
   - Независимый взгляд на проект/продукт (через призму архетипа).
   - Основную информацию (возраст, профессия, образование, местоположение).
   - Личный бэкграунд (важный опыт, боли, потребности).
   - Личные воспоминания (связь с событиями, реальные реакции).
   - Языковые особенности (стиль письма в соцсетях: капс, многоточия, сленг).
   - ANTI-ADVERTISING RULES (скептицизм, отсутствие рекламного тона).
4. age: Возраст как число (целое)
5. gender: Пол, строго на английском: "male" или "female"
6. mbti: Тип MBTI (например, INTJ, ENFP)
7. country: Страна (на английском, например, "Russia" или "US")
8. profession: Профессия
9. interested_topics: Массив интересующих тем

Важно:
- persona должна быть связным текстовым описанием.
- Используйте РУССКИЙ ЯЗЫК для текстовых полей.
- persona должна СТРОГО отражать твой архетип и независимую позицию.
"""

    def _build_group_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str,
        market_context: str = ""
    ) -> str:
        """Build detailed persona prompt for group/institutional entities"""

        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "None"
        context_str = context[:3000] if context else "No additional context"

        return f"""Сгенерируйте подробный профиль аккаунта социальной сети для институциональной/групповой сущности, максимально восстанавливая существующую реальность.

Название: {entity_name}
Тип: {entity_type}
Описание: {entity_summary}
Атрибуты: {attrs_str}

Контекстная информация:
{context_str}

Контекст рынка (реальные факты о рынке РФ):
{market_context or 'Нет данных'}

Пожалуйста, сгенерируйте JSON, содержащий следующие поля:

1. bio: Биография официального аккаунта, 200 символов, профессионально и уместно
2. persona: Подробное описание профиля аккаунта (2000 слов чистого текста), должно включать:
   - Базовую институциональную информацию (официальное название, характер организации, история основания, основные функции)
   - Позиционирование аккаунта (тип аккаунта, целевая аудитория, основные функции)
   - Стиль речи (языковые особенности, общие выражения, табуированные темы)
   - Характеристики публикаций контента (типы контента, частота публикаций, периоды активности)
   - Позиция и отношение (официальная позиция по основным темам, отношение к спорам)
   - Особые примечания (представленные групповые профили, операционные привычки)
   - Институциональная память (важная часть институциональной персоны, введите связь организации с событиями и их реакции)
   - ANTI-ADVERTISING RULES (избегание рекламного тона, фокус на фактах)
3. age: Зафиксировано на 30 (виртуальный возраст институционального аккаунта)
4. gender: Зафиксировано на "other" (институциональный аккаунт использует other)
5. mbti: Тип MBTI для описания стиля аккаунта, например, ISTJ для строгого консервативного
6. country: Страна (на английском, например, "Russia")
7. profession: Описание институциональной функции
8. interested_topics: Массив областей интереса

Важно:
- Все значения полей должны быть строками или числами, без null
- persona должна быть связным текстовым описанием, без переносов строк
- Используйте РУССКИЙ ЯЗЫК для текстовых полей
- age должно быть 30, gender должно быть "other"
- Речь официального аккаунта должна соответствовать его идентичности
"""
    
    def _generate_profile_rule_based(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate basic persona using rules"""

        # Generate different personas based on entity type
        entity_type_lower = entity_type.lower()

        if entity_type_lower in ["student", "alumni"]:
            return {
                "bio": f"{entity_type} с интересами в учебе и социальных вопросах.",
                "persona": f"{entity_name} — это {entity_type.lower()}, который активно участвует в академических и социальных дискуссиях. Им нравится делиться мнениями и общаться с коллегами.",
                "age": random.randint(18, 30),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": "Студент",
                "interested_topics": ["Образование", "Социальные вопросы", "Технологии"],
            }

        elif entity_type_lower in ["publicfigure", "expert", "faculty"]:
            return {
                "bio": "Эксперт и идейный лидер в своей области.",
                "persona": f"{entity_name} — признанный {entity_type.lower()}, который делится идеями и мнениями по важным вопросам. Они известны своим опытом и влиянием на публичный дискурс.",
                "age": random.randint(35, 60),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(["ENTJ", "INTJ", "ENTP", "INTP"]),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_attributes.get("occupation", "Эксперт"),
                "interested_topics": ["Politics", "Economics", "Culture & Society"],
            }

        elif entity_type_lower in ["mediaoutlet", "socialmediaplatform"]:
            return {
                "bio": f"Official account for {entity_name}. News and updates.",
                "persona": f"{entity_name} is a media entity that reports news and facilitates public discourse. The account shares timely updates and engages with the audience on current events.",
                "age": 30,  # Institutional virtual age
                "gender": "other",  # Institutional uses other
                "mbti": "ISTJ",  # Institutional style: rigorous conservative
                "country": "US",
                "profession": "Media",
                "interested_topics": ["General News", "Current Events", "Public Affairs"],
            }

        elif entity_type_lower in ["university", "governmentagency", "ngo", "organization"]:
            return {
                "bio": f"Official account of {entity_name}.",
                "persona": f"{entity_name} is an institutional entity that communicates official positions, announcements, and engages with stakeholders on relevant matters.",
                "age": 30,  # Institutional virtual age
                "gender": "other",  # Institutional uses other
                "mbti": "ISTJ",  # Institutional style: rigorous conservative
                "country": "US",
                "profession": entity_type,
                "interested_topics": ["Public Policy", "Community", "Official Announcements"],
            }

        else:
            # Default persona
            return {
                "bio": entity_summary[:150] if entity_summary else f"{entity_type}: {entity_name}",
                "persona": entity_summary or f"{entity_name} is a {entity_type.lower()} participating in social discussions.",
                "age": random.randint(25, 50),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_type,
                "interested_topics": ["General", "Social Issues"],
            }
    
    def set_graph_id(self, graph_id: str):
        """Set knowledge graph ID for knowledge graph search"""
        self.graph_id = graph_id
    
    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        output_platform: str = "reddit",
        market_context: str = ""
    ) -> List[OasisAgentProfile]:
        """
        Generate Agent Profiles in batch from entities (supports parallel generation)

        Args:
            entities: Entity list
            use_llm: Whether to use LLM to generate detailed personas
            progress_callback: Progress callback function (current, total, message)
            graph_id: Knowledge graph ID for knowledge graph search to get richer context
            parallel_count: Number of parallel generations, default 5
            realtime_output_path: Real-time output file path (if provided, write after each generation)
            output_platform: Output platform format ("reddit" or "twitter")

        Returns:
            List of Agent Profiles
        """
        import concurrent.futures
        from threading import Lock
        
        # Set graph_id for knowledge graph search
        if graph_id:
            self.graph_id = graph_id

        total = len(entities)
        profiles = [None] * total  # Pre-allocate list to maintain order
        completed_count = [0]  # Use list for modification in closure
        lock = Lock()

        # Helper function for real-time file writing
        def save_profiles_realtime():
            """Real-time save generated profiles to file"""
            if not realtime_output_path:
                return

            with lock:
                # Filter generated profiles
                existing_profiles = [p for p in profiles if p is not None]
                if not existing_profiles:
                    return

                try:
                    if output_platform == "reddit":
                        # Reddit JSON format
                        profiles_data = [p.to_reddit_format() for p in existing_profiles]
                        with open(realtime_output_path, 'w', encoding='utf-8') as f:
                            json.dump(profiles_data, f, ensure_ascii=False, indent=2)
                    else:
                        # Twitter CSV format
                        import csv
                        profiles_data = [p.to_twitter_format() for p in existing_profiles]
                        if profiles_data:
                            fieldnames = list(profiles_data[0].keys())
                            with open(realtime_output_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(profiles_data)
                except Exception as e:
                    logger.warning(f"Real-time profile save failed: {e}")
        
        def generate_single_profile(idx: int, entity: EntityNode) -> tuple:
            """Worker function to generate single profile"""
            entity_type = entity.get_entity_type() or "Entity"

            try:
                profile = self.generate_profile_from_entity(
                    entity=entity,
                    user_id=idx,
                    use_llm=use_llm,
                    market_context=market_context
                )

                # Real-time output generated persona to console and log
                self._print_generated_profile(entity.name, entity_type, profile)

                return idx, profile, None

            except Exception as e:
                logger.error(f"Failed to generate persona for entity {entity.name}: {str(e)}")
                # Create a fallback profile
                fallback_profile = OasisAgentProfile(
                    user_id=idx,
                    user_name=self._generate_username(entity.name),
                    name=entity.name,
                    bio=f"{entity_type}: {entity.name}",
                    persona=entity.summary or f"A participant in social discussions.",
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity_type,
                )
                return idx, fallback_profile, str(e)

        logger.info(f"Starting parallel generation of {total} agent personas (parallel count: {parallel_count})...")
        print(f"\n{'='*60}")
        print(f"Starting agent persona generation - {total} entities total, parallel count: {parallel_count}")
        print(f"{'='*60}\n")
        
        # Use thread pool for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
            # Submit all tasks
            future_to_entity = {
                executor.submit(generate_single_profile, idx, entity): (idx, entity)
                for idx, entity in enumerate(entities)
            }

            # Collect results
            for future in concurrent.futures.as_completed(future_to_entity):
                idx, entity = future_to_entity[future]
                entity_type = entity.get_entity_type() or "Entity"

                try:
                    result_idx, profile, error = future.result()
                    profiles[result_idx] = profile

                    with lock:
                        completed_count[0] += 1
                        current = completed_count[0]

                    # Real-time file writing
                    save_profiles_realtime()

                    if progress_callback:
                        progress_callback(
                            current,
                            total,
                            f"Completed {current}/{total}: {entity.name} ({entity_type})"
                        )

                    if error:
                        logger.warning(f"[{current}/{total}] {entity.name} using fallback persona: {error}")
                    else:
                        logger.info(f"[{current}/{total}] Successfully generated persona: {entity.name} ({entity_type})")

                except Exception as e:
                    logger.error(f"Exception occurred while processing entity {entity.name}: {str(e)}")
                    with lock:
                        completed_count[0] += 1
                    profiles[idx] = OasisAgentProfile(
                        user_id=idx,
                        user_name=self._generate_username(entity.name),
                        name=entity.name,
                        bio=f"{entity_type}: {entity.name}",
                        persona=entity.summary or "A participant in social discussions.",
                        source_entity_uuid=entity.uuid,
                        source_entity_type=entity_type,
                    )
                    # Real-time file writing (even for fallback personas)
                    save_profiles_realtime()

        print(f"\n{'='*60}")
        print(f"Persona generation complete! Generated {len([p for p in profiles if p])} agents")
        print(f"{'='*60}\n")
        
        return profiles
    
    def _print_generated_profile(self, entity_name: str, entity_type: str, profile: OasisAgentProfile):
        """Real-time output generated persona to console (complete content, not truncated)"""
        separator = "-" * 70

        # Build complete output content (not truncated)
        topics_str = ', '.join(profile.interested_topics) if profile.interested_topics else 'None'

        output_lines = [
            f"\n{separator}",
            f"[Generated] {entity_name} ({entity_type})",
            f"{separator}",
            f"Username: {profile.user_name}",
            f"",
            f"[Bio]",
            f"{profile.bio}",
            f"",
            f"[Detailed Persona]",
            f"{profile.persona}",
            f"",
            f"[Basic Attributes]",
            f"Age: {profile.age} | Gender: {profile.gender} | MBTI: {profile.mbti}",
            f"Profession: {profile.profession} | Country: {profile.country}",
            f"Interested Topics: {topics_str}",
            separator
        ]

        output = "\n".join(output_lines)

        # Only output to console (avoid duplication, logger no longer outputs complete content)
        print(output)
    
    def save_profiles(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """
        Save profiles to file (choose correct format based on platform)

        OASIS platform format requirements:
        - Twitter: CSV format
        - Reddit: JSON format

        Args:
            profiles: Profile list
            file_path: File path
            platform: Platform type ("reddit" or "twitter")
        """
        if platform == "twitter":
            self._save_twitter_csv(profiles, file_path)
        else:
            self._save_reddit_json(profiles, file_path)
    
    def _save_twitter_csv(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Save Twitter Profile as CSV format (compliant with OASIS official requirements)

        OASIS Twitter required CSV fields:
        - user_id: User ID (starting from 0 based on CSV order)
        - name: User real name
        - username: Username in the system
        - user_char: Detailed persona description (injected into LLM system prompt, guides agent behavior)
        - description: Short public bio (displayed on user profile page)

        user_char vs description difference:
        - user_char: Internal use, LLM system prompt, determines how agent thinks and acts
        - description: External display, visible to other users
        """
        import csv

        # Ensure file extension is .csv
        if not file_path.endswith('.csv'):
            file_path = file_path.replace('.json', '.csv')

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write OASIS required header
            headers = ['user_id', 'name', 'username', 'user_char', 'description']
            writer.writerow(headers)

            # Write data rows
            for idx, profile in enumerate(profiles):
                # user_char: Complete persona (bio + persona) for LLM system prompt
                user_char = profile.bio
                if profile.persona and profile.persona != profile.bio:
                    user_char = f"{profile.bio} {profile.persona}"
                # Handle newlines (replace with space in CSV)
                user_char = user_char.replace('\n', ' ').replace('\r', ' ')

                # description: Short bio for external display
                description = profile.bio.replace('\n', ' ').replace('\r', ' ')

                row = [
                    idx,                    # user_id: Sequential ID starting from 0
                    profile.name,           # name: Real name
                    profile.user_name,      # username: Username
                    user_char,              # user_char: Complete persona (internal LLM use)
                    description             # description: Short bio (external display)
                ]
                writer.writerow(row)

        logger.info(f"Saved {len(profiles)} Twitter profiles to {file_path} (OASIS CSV format)")
    
    def _normalize_gender(self, gender: Optional[str]) -> str:
        """
        Normalize gender field to OASIS required English format

        OASIS requires: male, female, other
        """
        if not gender:
            return "other"

        gender_lower = gender.lower().strip()

        # Gender mapping
        gender_map = {
            "male": "male",
            "female": "female",
            "other": "other",
        }

        return gender_map.get(gender_lower, "other")
    
    def _save_reddit_json(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Save Reddit Profile as JSON format

        Use format consistent with to_reddit_format() to ensure OASIS can read correctly.
        Must include user_id field, which is the key for OASIS agent_graph.get_agent() matching!

        Required fields:
        - user_id: User ID (integer, used to match poster_agent_id in initial_posts)
        - username: Username
        - name: Display name
        - bio: Bio
        - persona: Detailed persona
        - age: Age (integer)
        - gender: "male", "female", or "other"
        - mbti: MBTI type
        - country: Country
        """
        data = []
        for idx, profile in enumerate(profiles):
            # Use format consistent with to_reddit_format()
            item = {
                "user_id": profile.user_id if profile.user_id is not None else idx,  # Key: must include user_id
                "username": profile.user_name,
                "name": profile.name,
                "bio": profile.bio[:150] if profile.bio else f"{profile.name}",
                "persona": profile.persona or f"{profile.name} is a participant in social discussions.",
                "karma": profile.karma if profile.karma else 1000,
                "created_at": profile.created_at,
                # OASIS required fields - ensure all have defaults
                "age": profile.age if profile.age else 30,
                "gender": self._normalize_gender(profile.gender),
                "mbti": profile.mbti if profile.mbti else "ISTJ",
                "country": profile.country if profile.country else "US",
            }

            # Optional fields
            if profile.profession:
                item["profession"] = profile.profession
            if profile.interested_topics:
                item["interested_topics"] = profile.interested_topics

            data.append(item)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(profiles)} Reddit profiles to {file_path} (JSON format, includes user_id field)")
    
    # Keep old method name as alias for backward compatibility
    def save_profiles_to_json(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """[Deprecated] Please use save_profiles() method"""
        logger.warning("save_profiles_to_json is deprecated, please use save_profiles method")
        self.save_profiles(profiles, file_path, platform)
