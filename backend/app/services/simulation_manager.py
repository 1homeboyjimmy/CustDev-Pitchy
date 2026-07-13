"""
OASIS Simulation Manager
Manage Twitter and Reddit dual-platform parallel simulations
Use preset scripts + LLM intelligent generation of config parameters
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.logger import get_logger
from .entity_reader import EntityReader, FilteredEntities
from .oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
from .simulation_config_generator import SimulationConfigGenerator, SimulationParameters
from .rag_service import RagService

logger = get_logger('pitchy.simulation')


class SimulationStatus(str, Enum):
    """Simulation status"""
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"      # Simulation manually stopped
    COMPLETED = "completed"  # Simulation completed naturally
    FAILED = "failed"


class PlatformType(str, Enum):
    """Platform type"""
    TWITTER = "twitter"
    REDDIT = "reddit"


@dataclass
class SimulationState:
    """Simulation status"""
    simulation_id: str
    project_id: str
    graph_id: str

    # Владелец прогона (user_id главного сайта, `sub` из JWT). None — legacy-прогоны
    # до введения персональной истории (видны только администраторам).
    user_id: Optional[str] = None

    # Platform enabled state
    enable_twitter: bool = True
    enable_reddit: bool = True
    
    # Status
    status: SimulationStatus = SimulationStatus.CREATED
    
    # Preparation phase data
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    
    # Config generation information
    config_generated: bool = False
    config_reasoning: str = ""
    
    # Runtime data
    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Error message
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Complete status dict (internal use)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "user_id": self.user_id,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """Simplified status dict (API return use)"""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "error": self.error,
        }


class SimulationManager:
    """
    Simulation Manager
    
    Core Functions:
    1. Read entities from graph and filter
    2. Generate OASIS Agent Profile
    3. Use LLM intelligent generation of simulation config parameters
    4. Prepare all files required by preset scripts
    """
    
    # Simulation data storage directory
    SIMULATION_DATA_DIR = os.path.join(
        os.path.dirname(__file__), 
        '../../uploads/simulations'
    )
    
    def __init__(self):
        # Ensure directory exists
        os.makedirs(self.SIMULATION_DATA_DIR, exist_ok=True)
        
        # In-memory simulation state cache
        self._simulations: Dict[str, SimulationState] = {}
    
    def _get_simulation_dir(self, simulation_id: str) -> str:
        """Get simulation data directory"""
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir
    
    def _save_simulation_state(self, state: SimulationState):
        """Save simulation state to file"""
        sim_dir = self._get_simulation_dir(state.simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        
        state.updated_at = datetime.now().isoformat()
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        
        self._simulations[state.simulation_id] = state
    
    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        """Load simulation state from file"""
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]
        
        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        
        if not os.path.exists(state_file):
            return None
        
        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            user_id=data.get("user_id"),
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
            status=SimulationStatus(data.get("status", "created")),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            current_round=data.get("current_round", 0),
            twitter_status=data.get("twitter_status", "not_started"),
            reddit_status=data.get("reddit_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
        )
        
        self._simulations[simulation_id] = state
        return state
    
    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        user_id: Optional[str] = None,
    ) -> SimulationState:
        """
        Create new simulation
        
        Args:
            project_id: Project ID
            graph_id: Graph ID
            enable_twitter: Whether to enable Twitter simulation
            enable_reddit: Whether to enable Reddit simulation
            
        Returns:
            SimulationState
        """
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            user_id=user_id,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )
        
        self._save_simulation_state(state)
        logger.info(f"Create simulation: {simulation_id}, project={project_id}, graph={graph_id}")
        
        return state
    
    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3,
        storage: 'GraphStorage' = None,
        ontology: Optional[Dict[str, Any]] = None,
    ) -> SimulationState:
        """
        Prepare simulation environment (fully automated)
        
        Steps:
        1. Read and filter entities from graph
        2. Generate OASIS Agent Profile for each entity (optional LLM enhancement, parallel support)
        3. Use LLM intelligent generation of simulation config parameters (time, activity, speaking frequency, etc.)
        4. Save config files and Profile files
        5. Copy preset scripts to simulation directory
        
        Args:
            simulation_id: Simulation ID
            simulation_requirement: Simulation requirement description (for LLM config generation)
            document_text: Original document content (for LLM background understanding)
            defined_entity_types: Predefined entity types (optional)
            use_llm_for_profiles: Whether to use LLM to generate detailed profiles
            progress_callback: Progress callback function (stage, progress, message)
            parallel_profile_count: Number of parallel profile generations, default 3
            
        Returns:
            SimulationState
        """
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")
        
        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)
            
            sim_dir = self._get_simulation_dir(simulation_id)
            
            # ========== Phase 0: Get Market Context from RAG ==========
            # We pull structured chunks (with source + score metadata) and
            # format them into a single string that the profile generator
            # injects into each persona's system prompt. Including sources
            # gives the LLM something concrete to cite when justifying a
            # persona's pain point or scepticism, instead of inventing facts.
            if progress_callback:
                progress_callback("reading", 5, "Получение контекста рынка через RAG...")

            import asyncio
            market_context = ""
            try:
                rag_result = asyncio.run(
                    RagService.search(query=simulation_requirement, top_k=8)
                )
                if rag_result.chunks:
                    # Format as numbered list with source attribution so the
                    # downstream LLM can cite (and we can verify) which fact
                    # came from where.
                    lines = []
                    for i, ch in enumerate(rag_result.chunks, 1):
                        src = ch.metadata.get("source") or ch.metadata.get("url") or ""
                        cat = ch.metadata.get("collection") or ch.metadata.get("category") or ""
                        label = f"{cat}: {src}" if src and cat else (src or cat or "источник не указан")
                        lines.append(f"[{i}] ({label}, score={ch.score:.2f})\n{ch.text}")
                    market_context = "\n\n".join(lines)
                    logger.info(
                        f"RAG market context: {len(rag_result.chunks)} chunks, "
                        f"{len(market_context)} chars formatted"
                    )
                elif rag_result.context:
                    market_context = rag_result.context
                    logger.info(f"RAG legacy context: {len(market_context)} chars")
                else:
                    logger.warning("RAG returned no context for simulation_requirement")
            except Exception as rag_e:
                logger.warning(f"RAG context lookup failed (non-critical): {rag_e}")
            
            # ========== Phase 1: Read and filter entities ==========
            if progress_callback:
                progress_callback("reading", 0, "Connecting to graph...")

            if not storage:
                raise ValueError("storage (GraphStorage) is required for prepare_simulation")
            reader = EntityReader(storage)
            
            if progress_callback:
                progress_callback("reading", 30, "Анализ архитектуры общества...")
            
            # Build entity_type → agent_role map from ontology so each EntityNode
            # carries its role through the rest of the pipeline.
            entity_type_role_map: Dict[str, str] = {}
            if ontology and isinstance(ontology, dict):
                for et in ontology.get("entity_types", []) or []:
                    et_name = et.get("name")
                    et_role = et.get("default_agent_role")
                    if et_name and et_role:
                        entity_type_role_map[et_name] = et_role
                logger.info(f"Loaded agent roles for {len(entity_type_role_map)} entity types from ontology")

            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True,
                entity_type_role_map=entity_type_role_map or None,
            )

            # Hard filter: internal_team entities (the product itself, its founders,
            # its team) MUST NOT participate as customer-dev agents. Their voice
            # would be the product speaking about itself, which distorts the
            # signal we're trying to capture. We log what's excluded so the user
            # can verify the role classification looked right.
            if entity_type_role_map:
                before_count = len(filtered.entities)
                kept, excluded = [], []
                for ent in filtered.entities:
                    if ent.agent_role == "internal_team":
                        excluded.append(f"{ent.name} ({ent.get_entity_type()})")
                    else:
                        kept.append(ent)
                if excluded:
                    logger.info(
                        f"Excluded {len(excluded)}/{before_count} internal_team entities from simulation: {excluded[:5]}{'…' if len(excluded) > 5 else ''}"
                    )
                filtered.entities = kept
                filtered.filtered_count = len(kept)

            # Intelligent Ranking: prioritize "Human" entities for the "Society of Agents"
            def get_entity_actor_score(entity) -> int:
                etype = (entity.get_entity_type() or "").lower()
                # High priority: Individual human actors
                if etype in ["person", "student", "professor", "alumni", "founder", "expert", "analyst", "investor", "seller", "user"]:
                    return 100
                # Medium priority: Organizations/Institutions (can be represented by humans)
                if etype in ["organization", "university", "government", "governmentagency", "mediaoutlet", "company", "ngo"]:
                    return 50
                # Low priority: Abstract concepts, non-human things
                if etype in ["website", "service", "platform", "market", "product", "concept", "idea", "document"]:
                    return 10
                return 30 # Default for unknown types

            # Sort by actor score (highest first)
            filtered.entities.sort(key=get_entity_actor_score, reverse=True)

            # Strict Limit: keep only top 10 entities for the "Society of Agents"
            if len(filtered.entities) > 10:
                logger.info(f"Limiting simulation entities from {len(filtered.entities)} to 10 (sorted by actor relevance)")
                filtered.entities = filtered.entities[:10]
                filtered.filtered_count = 10
            
            state.entities_count = filtered.filtered_count
            state.entity_types = list(filtered.entity_types)
            
            if progress_callback:
                progress_callback(
                    "reading", 100, 
                    f"Completed, total {filtered.filtered_count} entities",
                    current=filtered.filtered_count,
                    total=filtered.filtered_count
                )
            
            if filtered.filtered_count == 0:
                state.status = SimulationStatus.FAILED
                state.error = "No entities matching criteria found, check if graph is correctly constructed"
                self._save_simulation_state(state)
                return state
            
            # ========== Phase 2: Generate Agent Profile ==========
            total_entities = len(filtered.entities)
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 0, 
                    "Запуск активации агентов...",
                    current=0,
                    total=total_entities
                )
            
            # Pass graph_id to enable graph retrieval functionality, get richer context
            generator = OasisProfileGenerator(storage=storage, graph_id=state.graph_id)
            
            def profile_progress(current, total, msg):
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 
                        int(current / total * 100), 
                        msg,
                        current=current,
                        total=total,
                        item_name=msg
                    )
            
            # Set real-time save file path (prefer Reddit JSON format)
            realtime_output_path = None
            realtime_platform = "reddit"
            if state.enable_reddit:
                realtime_output_path = os.path.join(sim_dir, "reddit_profiles.json")
                realtime_platform = "reddit"
            elif state.enable_twitter:
                realtime_output_path = os.path.join(sim_dir, "twitter_profiles.csv")
                realtime_platform = "twitter"
            
            profiles = generator.generate_profiles_from_entities(
                entities=filtered.entities,
                use_llm=use_llm_for_profiles,
                progress_callback=profile_progress,
                graph_id=state.graph_id,  # Pass graph_id for graph retrieval
                parallel_count=parallel_profile_count,  # Parallel generation count
                realtime_output_path=realtime_output_path,  # Real-time save path
                output_platform=realtime_platform,  # Output format
                market_context=market_context  # Pass market context for persona generation
            )
            
            state.profiles_count = len(profiles)
            
            # Save Profile files (Note: Twitter uses CSV format, Reddit uses JSON format)
            # Reddit has been saved in real-time during generation, save once more here to ensure completeness
            if progress_callback:
                progress_callback(
                    "generating_profiles", 95, 
                    "Сохранение профилей агентов...",
                    current=total_entities,
                    total=total_entities
                )
            
            if state.enable_reddit:
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                    platform="reddit"
                )
            
            if state.enable_twitter:
                # Twitter uses CSV format! This is OASIS requirement
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                    platform="twitter"
                )
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 100, 
                    f"Завершено, активировано {len(profiles)} агентов",
                    current=len(profiles),
                    total=len(profiles)
                )
            
            # ========== Phase 3: LLM intelligent generation of simulation config ==========
            if progress_callback:
                progress_callback(
                    "generating_config", 0, 
                    "Анализ требований симуляции...",
                    current=0,
                    total=3
                )
            
            config_generator = SimulationConfigGenerator()
            
            if progress_callback:
                progress_callback(
                    "generating_config", 30, 
                    "Генерация параметров общества...",
                    current=1,
                    total=3
                )
            
            sim_params = config_generator.generate_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                entities=filtered.entities,
                enable_twitter=state.enable_twitter,
                enable_reddit=state.enable_reddit,
                market_context=market_context  # Pass market context for config generation
            )
            
            if progress_callback:
                progress_callback(
                    "generating_config", 70, 
                    "Сохранение конфигурации...",
                    current=2,
                    total=3
                )
            
            # Save config files
            config_path = os.path.join(sim_dir, "simulation_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(sim_params.to_json())
            
            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning
            
            if progress_callback:
                progress_callback(
                    "generating_config", 100, 
                    "Генерация завершена",
                    current=3,
                    total=3
                )
            
            # Note: Run scripts remain in backend/scripts/ directory, no longer copy to simulation directory
            # When starting simulation, simulation_runner runs scripts from scripts/ directory
            
            # Update status
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)
            
            logger.info(f"Simulation preparation completed: {simulation_id}, "
                       f"entities={state.entities_count}, profiles={state.profiles_count}")
            
            return state
            
        except Exception as e:
            logger.error(f"Simulation preparation failed: {simulation_id}, error={str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise
    
    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        """Get simulation state"""
        return self._load_simulation_state(simulation_id)
    
    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        """List all simulations"""
        simulations = []
        
        if os.path.exists(self.SIMULATION_DATA_DIR):
            for sim_id in os.listdir(self.SIMULATION_DATA_DIR):
                # Skip hidden files (such as .DS_Store) and non-directory files
                sim_path = os.path.join(self.SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith('.') or not os.path.isdir(sim_path):
                    continue
                
                state = self._load_simulation_state(sim_id)
                if state:
                    if project_id is None or state.project_id == project_id:
                        simulations.append(state)
        
        return simulations
    
    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        """Get Agent Profiles for simulation"""
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation does not exist: {simulation_id}")
        
        sim_dir = self._get_simulation_dir(simulation_id)
        profile_path = os.path.join(sim_dir, f"{platform}_profiles.json")
        
        if not os.path.exists(profile_path):
            return []
        
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """Get simulation config"""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        """Get run instructions"""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit": f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
            "instructions": (
                f"1. Activate conda environment: conda activate Pitchy\n"
                f"2. Run simulation (scripts located in {scripts_dir}):\n"
                f"   - Run Twitter alone: python {scripts_dir}/run_twitter_simulation.py --config {config_path}\n"
                f"   - Run Reddit alone: python {scripts_dir}/run_reddit_simulation.py --config {config_path}\n"
                f"   - Run both platforms in parallel: python {scripts_dir}/run_parallel_simulation.py --config {config_path}"
            )
        }
