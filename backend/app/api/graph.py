"""
Graph-related API Routes
Uses project context mechanism with server-side state persistence
"""

import os
import traceback
import threading
from flask import request, jsonify, current_app

from . import graph_bp
from ..config import Config
from ..services.ontology_generator import OntologyGenerator
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..utils.auth import login_required, current_user_id, is_admin_user
from ..models.task import TaskManager, TaskStatus
from ..models.project import ProjectManager, ProjectStatus

# Get logger
logger = get_logger('pitchy.api')


def _project_access_error(project):
    if project is None:
        return None
    if project.owner_id is None:
        if is_admin_user():
            return None
        return jsonify({"success": False, "error": "Project access denied"}), 403
    if str(project.owner_id) != str(current_user_id()) and not is_admin_user():
        return jsonify({"success": False, "error": "Project access denied"}), 403
    return None


@graph_bp.before_request
def enforce_project_ownership():
    """Prevent cross-user project reads/writes before route logic runs."""
    project_id = (request.view_args or {}).get('project_id')
    if not project_id and request.is_json:
        project_id = (request.get_json(silent=True) or {}).get('project_id')
    if not project_id:
        return None
    error = _project_access_error(ProjectManager.get_project(project_id))
    return error


def _get_storage():
    """Get Neo4jStorage from Flask app extensions."""
    storage = current_app.extensions.get('neo4j_storage')
    if not storage:
        raise ValueError("GraphStorage not initialized — check Neo4j connection")
    return storage


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# ============== Project Management Interface ==============

@graph_bp.route('/project/<project_id>', methods=['GET'])
@login_required
def get_project(project_id: str):
    """
    Get project details
    """
    project = ProjectManager.get_project(project_id)
    
    if not project:
        return jsonify({
            "success": False,
            "error": f"Project does not exist: {project_id}"
        }), 404
    
    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
@login_required
def list_projects():
    """
    List all projects
    """
    limit = request.args.get('limit', 50, type=int)
    uid = current_user_id()
    projects = [
        p for p in ProjectManager.list_projects(limit=limit * 2)
        if (p.owner_id is not None and str(p.owner_id) == str(uid))
        or (p.owner_id is None and is_admin_user())
    ][:limit]
    
    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id: str):
    """
    Delete project
    """
    success = ProjectManager.delete_project(project_id)

    if not success:
        return jsonify({
            "success": False,
            "error": f"Project does not exist or deletion failed: {project_id}"
        }), 404

    return jsonify({
        "success": True,
        "message": f"Project deleted: {project_id}"
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
@login_required
def reset_project(project_id: str):
    """
    Reset project status (for rebuilding graph)
    """
    project = ProjectManager.get_project(project_id)

    if not project:
        return jsonify({
            "success": False,
            "error": f"Project does not exist: {project_id}"
        }), 404

    # Reset to ontology generated state
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED

    project.graph_id = None
    project.graph_build_task_id = None
    project.ontology_task_id = None
    project.error = None
    ProjectManager.save_project(project)

    return jsonify({
        "success": True,
        "message": f"Project reset: {project_id}",
        "data": project.to_dict()
    })


# ============== Interface 1: Upload Files and Generate Ontology ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
@login_required
def generate_ontology():
    """
    Interface 1: Upload files and analyze to generate ontology definition

    Request method: multipart/form-data

    Parameters:
        files: Uploaded files (PDF/PPTX/MD/TXT), multiple allowed
        simulation_requirement: Simulation requirement description (required)
        project_name: Project name (optional)
        additional_context: Additional notes (optional)

    Response:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "ontology": {
                    "entity_types": [...],
                    "edge_types": [...],
                    "analysis_summary": "..."
                },
                "files": [...],
                "total_text_length": 12345
            }
        }
    """
    try:
        logger.info("=== Starting ontology generation ===")

        # Get parameters
        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')

        logger.debug(f"Project name: {project_name}")
        logger.debug(f"Simulation requirement: {simulation_requirement[:100]}...")

        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "Please provide simulation requirement description (simulation_requirement)"
            }), 400

        # Get uploaded files
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": "Please upload at least one document file"
            }), 400

        # Create project
        project = ProjectManager.create_project(name=project_name, owner_id=current_user_id())
        project.simulation_requirement = simulation_requirement
        logger.info(f"Project created: {project.project_id}")
        
        # Save files and extract text
        document_texts = []
        all_text = ""
        # Track per-file extraction failures so we can surface them to the user
        # with a single 400 instead of a generic 500 traceback.
        extraction_errors: list[str] = []

        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                # Save file to project directory
                file_info = ProjectManager.save_file_to_project(
                    project.project_id,
                    file,
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })

                # Extract text — `extract_text` raises `ValueError` for known
                # user-recoverable cases (scan PDF, unsupported format, etc.)
                try:
                    text = FileParser.extract_text(file_info["path"])
                except ValueError as ve:
                    extraction_errors.append(f"{file_info['original_filename']}: {ve}")
                    continue
                text = TextProcessor.preprocess_text(text)
                if text and text.strip():
                    document_texts.append(text)
                    all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"
                else:
                    extraction_errors.append(
                        f"{file_info['original_filename']}: file contains no extractable text"
                    )

        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            user_msg = (
                "No documents successfully processed. "
                + ("; ".join(extraction_errors) if extraction_errors else "Please check file format")
            )
            return jsonify({
                "success": False,
                "error": user_msg
            }), 400

        # Save extracted text
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"Text extraction completed, total {len(all_text)} characters")

        # Long LLM calls must not occupy the reverse-proxy connection. The
        # frontend opts into this mode and polls the durable TaskManager record.
        if request.headers.get('X-Custdev-Async') == '1':
            task_manager = TaskManager()
            task_id = task_manager.create_task(
                task_type='ontology_generate',
                metadata={'project_id': project.project_id, 'owner_id': current_user_id()},
            )
            project.ontology_task_id = task_id
            ProjectManager.save_project(project)

            def run_ontology_generation():
                try:
                    task_manager.update_task(
                        task_id,
                        status=TaskStatus.PROCESSING,
                        progress=10,
                        message='Анализируем документы и строим онтологию…',
                    )
                    ontology = OntologyGenerator().generate(
                        document_texts=document_texts,
                        simulation_requirement=simulation_requirement,
                        additional_context=additional_context if additional_context else None,
                    )
                    project.ontology = {
                        'entity_types': ontology.get('entity_types', []),
                        'edge_types': ontology.get('edge_types', []),
                    }
                    project.analysis_summary = ontology.get('analysis_summary', '')
                    project.status = ProjectStatus.ONTOLOGY_GENERATED
                    project.ontology_task_id = None
                    ProjectManager.save_project(project)
                    task_manager.complete_task(task_id, {
                        'project_id': project.project_id,
                        'project': project.to_dict(),
                    })
                except Exception as exc:
                    logger.error(f"Ontology generation failed: {exc}")
                    project.status = ProjectStatus.FAILED
                    project.error = str(exc)
                    project.ontology_task_id = None
                    ProjectManager.save_project(project)
                    task_manager.fail_task(task_id, str(exc))

            threading.Thread(target=run_ontology_generation, daemon=True).start()
            return jsonify({
                'success': True,
                'data': {
                    'project_id': project.project_id,
                    'project_name': project.name,
                    'files': project.files,
                    'total_text_length': project.total_text_length,
                    'task_id': task_id,
                    'status': 'processing',
                    'message': 'Ontology generation started. Poll the task status endpoint.',
                },
            })

        # Generate ontology
        logger.info("Calling LLM to generate ontology definition...")
        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement,
            additional_context=additional_context if additional_context else None
        )

        # Save ontology to project
        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info(f"Ontology generation completed: {entity_count} entity types, {edge_count} relation types")
        
        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== Ontology generation completed === Project ID: {project.project_id}")
        
        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })
        
    except Exception as e:
        logger.exception("Ontology generation request failed")
        return jsonify({
            "success": False,
            "error": str(e) or "Ontology generation failed"
        }), 500


@graph_bp.route('/ontology/status/<task_id>', methods=['GET'])
@login_required
def get_ontology_status(task_id: str):
    """Return durable status for asynchronous ontology generation."""
    task = TaskManager().get_task(task_id)
    if not task or task.task_type != 'ontology_generate':
        return jsonify({'success': False, 'error': 'Ontology task does not exist'}), 404
    owner_id = task.metadata.get('owner_id') if task.metadata else None
    if owner_id is not None and str(owner_id) != str(current_user_id()) and not is_admin_user():
        return jsonify({'success': False, 'error': 'Task access denied'}), 403
    return jsonify({'success': True, 'data': task.to_dict()})


# ============== Interface 2: Build Graph ==============

@graph_bp.route('/build', methods=['POST'])
@login_required
def build_graph():
    """
    Interface 2: Build graph based on project_id

    Request (JSON):
        {
            "project_id": "proj_xxxx",  // Required: from interface 1
            "graph_name": "Graph name",    // Optional
            "chunk_size": 500,          // Optional, default 500
            "chunk_overlap": 50         // Optional, default 50
        }

    Response:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "Graph build task started"
            }
        }
    """
    try:
        logger.info("=== Starting graph build ===")

        # Parse request
        data = request.get_json() or {}
        project_id = data.get('project_id')
        logger.debug(f"Request parameters: project_id={project_id}")
        
        if not project_id:
            return jsonify({
                "success": False,
                "error": "Please provide project_id"
            }), 400

        # Get project
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project does not exist: {project_id}"
            }), 404

        # Check project status
        force = data.get('force', False)  # Force rebuild

        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": "Project has not generated ontology yet. Please call /ontology/generate first"
            }), 400

        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": "Graph is being built. Do not submit repeatedly. To force rebuild, add force: true",
                "task_id": project.graph_build_task_id
            }), 400

        # If force rebuild, reset status
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None

        # Get configuration
        graph_name = data.get('graph_name', project.name or 'Pitchy Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)

        # Update project configuration
        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap

        # Get extracted text
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": "Extracted text not found"
            }), 400

        # Get ontology
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": "Ontology definition not found"
            }), 400

        # Get storage in request context (background thread cannot access current_app)
        storage = _get_storage()

        # Create async task
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            f"Build graph: {graph_name}",
            metadata={'project_id': project_id, 'owner_id': current_user_id()},
        )
        logger.info(f"Graph build task created: task_id={task_id}, project_id={project_id}")
        
        # Update project status
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)

        # Start background task
        def build_task():
            build_logger = get_logger('pitchy.build')
            try:
                build_logger.info(f"[{task_id}] Starting graph build...")
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    message="Initializing graph build service..."
                )

                # Create graph builder service (storage passed from outer closure)
                builder = GraphBuilderService(storage=storage)

                # Chunk text
                task_manager.update_task(
                    task_id,
                    message="Chunking text...",
                    progress=5
                )
                chunks = TextProcessor.split_text(
                    text,
                    chunk_size=chunk_size,
                    overlap=chunk_overlap
                )
                total_chunks = len(chunks)

                # Create graph
                task_manager.update_task(
                    task_id,
                    message="Creating Zep graph...",
                    progress=10
                )
                graph_id = builder.create_graph(name=graph_name)

                # Update project graph_id
                project.graph_id = graph_id
                ProjectManager.save_project(project)

                # Set ontology
                task_manager.update_task(
                    task_id,
                    message="Setting ontology definition...",
                    progress=15
                )
                builder.set_ontology(graph_id, ontology)
                
                # Add text (progress_callback signature is (msg, progress_ratio))
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)  # 15% - 55%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )

                task_manager.update_task(
                    task_id,
                    message=f"Starting to add {total_chunks} text chunks...",
                    progress=15
                )

                episode_uuids = builder.add_text_batches(
                    graph_id,
                    chunks,
                    batch_size=3,
                    progress_callback=add_progress_callback
                )

                # Neo4j processing is synchronous, no need to wait
                task_manager.update_task(
                    task_id,
                    message="Text processing completed, generating graph data...",
                    progress=90
                )

                # Deduplicate near-duplicate entities (e.g. "Егор Фигурняк"
                # vs "Егор Сергеевич Фигурняк"). NER produces these often
                # when the same person is mentioned in different forms across
                # chunks. Merging here keeps downstream profile generation
                # from creating two competing personas for one real person.
                try:
                    task_manager.update_task(
                        task_id,
                        message="Объединение дублирующихся сущностей...",
                        progress=92,
                    )
                    dedupe_result = builder.deduplicate_entities(graph_id)
                    if dedupe_result.get("merged"):
                        build_logger.info(
                            f"[{task_id}] Dedupe merged {dedupe_result['merged']} duplicates"
                        )
                except Exception as dedupe_err:
                    # Dedupe is best-effort — never block graph completion on it.
                    build_logger.warning(f"[{task_id}] Dedupe pass failed (non-fatal): {dedupe_err}")

                # Get graph data
                task_manager.update_task(
                    task_id,
                    message="Retrieving graph data...",
                    progress=95
                )
                graph_data = builder.get_graph_data(graph_id)

                # Update project status
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)

                node_count = graph_data.get("node_count", 0)
                edge_count = graph_data.get("edge_count", 0)
                empty_graph = node_count == 0
                build_logger.info(f"[{task_id}] Graph build completed: graph_id={graph_id}, nodes={node_count}, edges={edge_count}")

                # Complete
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message=(
                        "Граф не содержит именованных сущностей; персоны будут созданы из сегментов онтологии"
                        if empty_graph else "Graph build completed"
                    ),
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks,
                        "empty_graph": empty_graph,
                        "fallback": "ontology_archetypes" if empty_graph else None,
                    }
                )

            except Exception as e:
                # Update project status to failed
                build_logger.error(f"[{task_id}] Graph build failed: {str(e)}")
                build_logger.debug(traceback.format_exc())

                project.status = ProjectStatus.FAILED
                project.error = str(e)
                ProjectManager.save_project(project)

                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Build failed: {str(e)}",
                    error=str(e) or "Graph build failed"
                )

        # Start background thread
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": "Graph build task started. Query progress via /task/{task_id}"
            }
        })
        
    except Exception as e:
        logger.exception("Graph build request failed")
        return jsonify({
            "success": False,
            "error": str(e) or "Graph build failed"
        }), 500


# ============== Task Query Interface ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
@login_required
def get_task(task_id: str):
    """
    Query task status
    """
    task = TaskManager().get_task(task_id)

    if not task:
        return jsonify({
            "success": False,
            "error": f"Task does not exist: {task_id}"
        }), 404

    owner_id = (task.metadata or {}).get('owner_id')
    if owner_id is not None and str(owner_id) != str(current_user_id()) and not is_admin_user():
        return jsonify({"success": False, "error": "Task access denied"}), 403

    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
@login_required
def list_tasks():
    """
    List all tasks
    """
    uid = current_user_id()
    admin = is_admin_user()
    tasks = [
        task for task in TaskManager().list_tasks()
        if admin or str((task.get('metadata') or {}).get('owner_id')) == str(uid)
    ]
    
    return jsonify({
        "success": True,
        "data": tasks,
        "count": len(tasks)
    })


# ============== Graph Data Interface ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
@login_required
def get_graph_data(graph_id: str):
    """
    Get graph data (nodes and edges)
    """
    try:
        storage = _get_storage()
        builder = GraphBuilderService(storage=storage)
        graph_data = builder.get_graph_data(graph_id)

        return jsonify({
            "success": True,
            "data": graph_data
        })

    except Exception as e:
        logger.exception("Graph data request failed")
        return jsonify({
            "success": False,
            "error": str(e) or "Unable to load graph data"
        }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
@login_required
def delete_graph(graph_id: str):
    """
    Delete graph
    """
    try:
        storage = _get_storage()
        builder = GraphBuilderService(storage=storage)
        builder.delete_graph(graph_id)

        return jsonify({
            "success": True,
            "message": f"Graph deleted: {graph_id}"
        })

    except Exception as e:
        logger.exception("Graph deletion request failed")
        return jsonify({
            "success": False,
            "error": str(e) or "Unable to delete graph"
        }), 500
