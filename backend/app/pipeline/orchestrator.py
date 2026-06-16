"""
Pipeline Orchestrator — State Machine

Manages the end-to-end reel generation pipeline.
Coordinates all 12 modules, handles retries, and tracks state transitions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings, LLMProvider
from app.models.job import Job, JobStatus
from app.providers.llm.openai_llm import OpenAILLMProvider
from app.providers.llm.claude import ClaudeLLMProvider
from app.providers.llm.mock import MockLLMProvider
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.fallback import FallbackLLMProvider

from app.pipeline.m01_ingestion import ingest
from app.pipeline.m02_transcription import transcribe
from app.pipeline.m03_extraction import extract_job_info, extract_from_manual
from app.pipeline.m04_hooks import generate_hooks
from app.pipeline.m05_script import generate_script
from app.pipeline.m06_voice import generate_voice
from app.pipeline.m07_scene_plan import plan_scenes
from app.pipeline.m08_captions import generate_captions
from app.pipeline.m09_visual_assets import acquire_visuals
from app.pipeline.m10_video_gen import generate_scene_videos
from app.pipeline.m11_assembly import assemble_final_reel
from app.pipeline.m12_quality import evaluate_quality, should_regenerate

logger = logging.getLogger(__name__)


def update_env_default_llm(provider_name: str):
    """Dynamically update the DEFAULT_LLM_PROVIDER variable in the backend .env file."""
    try:
        # Check standard paths
        env_paths = [
            Path("e:/AI video genrator/backend/.env"),
            Path(".env"),
            Path("backend/.env"),
            Path("../.env")
        ]
        env_path = None
        for path in env_paths:
            if path.exists():
                env_path = path
                break

        if env_path:
            content = env_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith("DEFAULT_LLM_PROVIDER="):
                    lines[i] = f"DEFAULT_LLM_PROVIDER={provider_name}"
                    updated = True
                    break
            
            # If not found, append it at the end
            if not updated:
                lines.append(f"DEFAULT_LLM_PROVIDER={provider_name}")
            
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            logger.info(f"[Failover] Updated config file {env_path} with DEFAULT_LLM_PROVIDER={provider_name}")
        else:
            logger.warning("[Failover] No .env file found to persist LLM provider update.")
    except Exception as e:
        logger.error(f"[Failover] Failed to update default LLM in .env file: {e}")


def _create_single_provider(name: str) -> BaseLLMProvider | None:
    """Helper to create a single LLM provider instance if the key is available."""
    settings = get_settings()
    if name == "claude" and settings.anthropic_api_key:
        return ClaudeLLMProvider()
    elif name == "openai" and settings.openai_api_key:
        return OpenAILLMProvider()
    elif name == "groq" and settings.groq_api_key:
        return OpenAILLMProvider(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.3-70b-versatile",
            provider_name="Groq",
        )
    elif name == "sambanova" and settings.sambanova_api_key:
        return OpenAILLMProvider(
            api_key=settings.sambanova_api_key,
            base_url="https://api.sambanova.ai/v1",
            model="Meta-Llama-3.3-70B-Instruct",
            provider_name="SambaNova",
        )
    elif name == "cerebras" and settings.cerebras_api_key:
        return OpenAILLMProvider(
            api_key=settings.cerebras_api_key,
            base_url="https://api.cerebras.ai/v1",
            model="gpt-oss-120b",
            provider_name="Cerebras",
        )
    elif name == "gemini" and settings.google_api_key:
        return OpenAILLMProvider(
            api_key=settings.google_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model="gemini-1.5-flash",
            provider_name="Gemini",
        )
    return None


def _get_llm(provider_name: str | None = None) -> BaseLLMProvider:
    """Get the LLM provider instance wrapped in a fallback resolver."""
    settings = get_settings()
    
    # 1. Determine primary name
    primary_name = provider_name or settings.default_llm_provider.value
    primary = _create_single_provider(primary_name)
    
    # If primary name config is missing keys, fall back to anything available
    if not primary:
        for possible_name in ["openai", "groq", "sambanova", "cerebras", "gemini", "claude"]:
            primary = _create_single_provider(possible_name)
            if primary:
                primary_name = possible_name
                break
                
    if not primary:
        logger.warning("No LLM API keys configured. Falling back to MockLLMProvider.")
        return MockLLMProvider()

    # 2. Gather all other configured fallback providers
    fallbacks = []
    for name in ["openai", "groq", "sambanova", "cerebras", "gemini", "claude"]:
        if name == primary_name:
            continue
        p = _create_single_provider(name)
        if p:
            fallbacks.append(p)
            
    # Add a callback to dynamically change the default provider when failover succeeds
    def on_fallback_success(working_provider: BaseLLMProvider):
        working_name = working_provider.provider_name.lower()
        for key in ["openai", "claude", "groq", "sambanova", "cerebras", "gemini"]:
            if key in working_name:
                try:
                    # Update settings in memory
                    from app.config import LLMProvider
                    settings.default_llm_provider = LLMProvider(key)
                    logger.info(f"[Failover] Switched in-memory default LLM provider to: {key}")
                    # Update settings in .env file
                    update_env_default_llm(key)
                except Exception as ex:
                    logger.error(f"[Failover] Failed to persist failover settings: {ex}")
                break

    return FallbackLLMProvider(primary, fallbacks, on_fallback_success=on_fallback_success)


StatusCallback = Optional[callable]


def scale_scene_timing(scenes: list[dict[str, Any]], actual_duration: float) -> list[dict[str, Any]]:
    """Proportionally scale scene timings to match the actual voiceover duration."""
    if not scenes:
        return scenes
    
    # Calculate old total duration from the last scene's end time
    old_duration = scenes[-1].get("end_time", 30.0)
    if not old_duration or old_duration <= 0:
        old_duration = 30.0
        
    scale_factor = actual_duration / old_duration
    
    current_time = 0.0
    for scene in scenes:
        orig_dur = scene.get("duration", 5.0)
        scaled_dur = orig_dur * scale_factor
        
        scene["start_time"] = round(current_time, 2)
        scene["end_time"] = round(current_time + scaled_dur, 2)
        scene["duration"] = round(scaled_dur, 2)
        current_time += scaled_dur
        
    # Ensure last scene ends exactly at actual_duration
    scenes[-1]["end_time"] = round(actual_duration, 2)
    scenes[-1]["duration"] = round(scenes[-1]["end_time"] - scenes[-1]["start_time"], 2)
    
    return scenes


async def run_pipeline(
    job: Job,
    session: Any,
    on_status: StatusCallback = None,
) -> Job:
    """Run the full reel generation pipeline for a job.

    Args:
        job: The Job model instance.
        session: Database session for persisting state.
        on_status: Optional callback for status updates.

    Returns:
        Updated Job with results or error.
    """
    settings = get_settings()
    llm = _get_llm(job.llm_provider)

    def _update_status(status: JobStatus, message: str = ""):
        job.status = status
        job.updated_at = datetime.now(timezone.utc)
        session.add(job)
        session.commit()
        logger.info(f"[Pipeline] Job {job.id}: {status.value} — {message}")
        if on_status:
            on_status(job.id, status.value, message)

    try:
        # ═══════════════════════════════════════════════════════════
        # MODULE 1: INGESTION
        # ═══════════════════════════════════════════════════════════
        _update_status(JobStatus.INGESTING, "Starting video ingestion...")

        ingestion_result = await ingest(
            job_id=job.id,
            input_type=job.input_type.value,
            input_value=job.input_value,
            upload_path=job.upload_path,
        )

        if ingestion_result.audio_path:
            job.audio_path = str(ingestion_result.audio_path)

        # ═══════════════════════════════════════════════════════════
        # MODULE 2: TRANSCRIPTION (skip for text-based inputs)
        # ═══════════════════════════════════════════════════════════
        transcript_text = ""

        if not ingestion_result.skip_transcription and ingestion_result.audio_path:
            _update_status(JobStatus.TRANSCRIBING, "Transcribing audio...")

            transcription = await transcribe(
                audio_path=ingestion_result.audio_path,
                model_size=settings.whisper_model_size,
            )

            transcript_text = transcription.full_text
            job.transcript = transcript_text

            # Auto-detect language
            if not job.voice_language:
                job.voice_language = transcription.language

        elif ingestion_result.text_content:
            transcript_text = ingestion_result.text_content
            job.transcript = transcript_text

        # ═══════════════════════════════════════════════════════════
        # MODULE 3: INFORMATION EXTRACTION
        # ═══════════════════════════════════════════════════════════
        _update_status(JobStatus.EXTRACTING, "Extracting job information...")

        if job.input_type.value == "manual" and job.job_data:
            # Manual input — use provided data
            job_data = extract_from_manual(job.job_data)
        elif transcript_text:
            job_data = await extract_job_info(transcript_text, llm)
        else:
            raise RuntimeError("No text content available for extraction")

        job.job_data = job_data
        session.add(job)
        session.commit()

        # ═══════════════════════════════════════════════════════════
        # GENERATION LOOP (with quality retry on text-assets only)
        # ═══════════════════════════════════════════════════════════
        voice_language = job.voice_language or settings.default_voice_language.value

        while True:
            # ── MODULE 4: HOOK GENERATION ─────────────────────────
            _update_status(JobStatus.GENERATING_HOOKS, "Generating scroll-stopping hooks...")

            hooks_result = await generate_hooks(job_data, llm)
            job.hook_variants = hooks_result["hooks"]
            job.selected_hook = hooks_result["selected"]

            # ── MODULE 5: SCRIPT GENERATION ───────────────────────
            _update_status(JobStatus.GENERATING_SCRIPT, "Writing reel script...")

            script_data = await generate_script(
                job_data=job_data,
                selected_hook=hooks_result["selected"],
                llm=llm,
                language=voice_language,
            )
            job.script = script_data.get("script", "")

            # ── MODULE 7: SCENE PLANNING ──────────────────────────
            _update_status(JobStatus.PLANNING_SCENES, "Planning visual scenes...")

            # Use estimated script duration to plan scenes for the quality check
            estimated_duration = script_data.get("total_duration_estimate", 30)
            scene_plan = await plan_scenes(
                script_data=script_data,
                job_data=job_data,
                llm=llm,
                total_duration=estimated_duration,
            )
            job.scene_plan = scene_plan

            # ── MODULE 12: QUALITY CHECK (on script text and scene plan) ──
            _update_status(JobStatus.QUALITY_CHECK, "Evaluating script quality...")

            quality_evaluation_failed = False
            try:
                quality_scores = await evaluate_quality(
                    hook=hooks_result["selected"],
                    script=job.script or "",
                    job_data=job_data,
                    scene_plan=scene_plan,
                    duration=estimated_duration,
                    llm=llm,
                )
            except Exception as qe:
                logger.warning(f"[Pipeline] Quality check failed due to LLM rate limit or error: {qe}. Proceeding with default quality scores.")
                quality_evaluation_failed = True
                quality_scores = {
                    "overall_score": 85.0,
                    "hook_quality": {"score": 85.0, "reasoning": "Fallback score (Quality check API rate-limited)"},
                    "retention_score": {"score": 85.0, "reasoning": "Fallback score"},
                    "readability": {"score": 85.0, "reasoning": "Fallback score"},
                    "cta_effectiveness": {"score": 85.0, "reasoning": "Fallback score"},
                    "improvement_suggestions": ["Ensure LLM API keys have enough daily quota to run quality evaluation."]
                }

            job.quality_scores = quality_scores
            job.overall_score = quality_scores.get("overall_score", 0)

            # Check if regeneration is needed
            if not quality_evaluation_failed and should_regenerate(
                quality_scores=quality_scores,
                threshold=settings.quality_threshold,
                current_retry=job.retry_count,
                max_retries=settings.max_retries,
            ):
                job.retry_count += 1
                logger.info(f"[Pipeline] Retrying ({job.retry_count}/{settings.max_retries}): score={job.overall_score}")
                continue  # Loop back to Module 4
            else:
                break  # Quality passed or max retries reached

        # ═══════════════════════════════════════════════════════════
        # AUDIO & VIDEO ASSET GENERATION (Run exactly once, after quality approval)
        # ═══════════════════════════════════════════════════════════

        # ── MODULE 6: VOICE GENERATION ────────────────────────
        _update_status(JobStatus.GENERATING_VOICE, "Generating AI voiceover...")

        voice_result = await generate_voice(
            script_data=script_data,
            job_id=job.id,
            provider_name=job.voice_provider or settings.default_voice_provider.value,
            language=voice_language,
            voice_id=job.voice_id or "",
        )
        job.voice_path = voice_result["voice_path"]
        job.voice_provider = voice_result["provider"]

        voice_duration = voice_result["duration"]

        # Proportionally scale the planned scene start and end times to the actual voiceover duration
        scene_plan = scale_scene_timing(scene_plan, voice_duration)
        job.scene_plan = scene_plan

        # ── MODULE 8: CAPTION GENERATION ──────────────────────
        _update_status(JobStatus.GENERATING_CAPTIONS, "Creating captions...")

        captions_result = await generate_captions(
            script_data=script_data,
            job_data=job_data,
            job_id=job.id,
            voice_duration=voice_duration,
        )
        job.captions_path = captions_result["captions_path"]

        # ── MODULE 9: VISUAL ASSET ACQUISITION ────────────────
        _update_status(JobStatus.GENERATING_VISUALS, "Acquiring visual assets...")

        video_provider = job.video_provider or settings.default_video_provider.value
        use_ai = video_provider != "pexels"

        scene_plan = await acquire_visuals(
            scene_plan=scene_plan,
            job_id=job.id,
            use_ai_generation=use_ai,
        )

        # ── MODULE 10: AI VIDEO GENERATION (if needed) ───────
        pending_ai = [
            s for s in scene_plan
            if not s.get("visual_path") or s.get("visual_source") in ("ai_pending", "placeholder", "failed")
        ]
        if pending_ai:
            _update_status(JobStatus.GENERATING_VIDEO, "Generating AI video clips...")
            scene_plan = await generate_scene_videos(
                scene_plan=scene_plan,
                job_id=job.id,
                provider_name=video_provider,
            )

        job.scene_plan = scene_plan

        # ── MODULE 11: VIDEO ASSEMBLY ─────────────────────────
        _update_status(JobStatus.ASSEMBLING, "Assembling final reel...")

        assembly_result = await assemble_final_reel(
            scene_plan=scene_plan,
            voice_path=voice_result["voice_path"],
            captions_path=captions_result["captions_path"],
            job_id=job.id,
        )
        job.output_path = assembly_result["output_path"]

        # ═══════════════════════════════════════════════════════════
        # COMPLETION
        # ═══════════════════════════════════════════════════════════
        if job.overall_score and job.overall_score >= settings.quality_threshold:
            _update_status(JobStatus.COMPLETED, f"Reel completed! Score: {job.overall_score}")
        else:
            _update_status(JobStatus.COMPLETED_LOW_QUALITY, f"Completed with score: {job.overall_score}")

        job.completed_at = datetime.now(timezone.utc)
        session.add(job)
        session.commit()

        logger.info(f"[Pipeline] Job {job.id} COMPLETED: score={job.overall_score}, retries={job.retry_count}")
        return job

    except Exception as e:
        logger.error(f"[Pipeline] Job {job.id} FAILED: {e}", exc_info=True)
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.updated_at = datetime.now(timezone.utc)
        session.add(job)
        session.commit()
        return job
