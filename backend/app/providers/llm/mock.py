"""
Mock LLM Provider for testing and local development without active API keys.
"""

from __future__ import annotations

import logging
from typing import Any

from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM Provider returning structured responses for the reel pipeline."""

    @property
    def provider_name(self) -> str:
        return "Mock LLM"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: str = "text",
    ) -> str:
        # If generate_json is called, it redirects here.
        # But we'll handle standard text prompt requests here if they occur.
        logger.info("[MockLLM] generate text called")
        return "This is a mock text generation response."

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        logger.info(f"[MockLLM] generate_json called. Prompt slice: {prompt[:100]}...")

        # Convert prompt to lowercase for routing
        prompt_lower = prompt.lower()

        # 1. Quality Engine (Module 12)
        if "hook_quality" in prompt_lower or "cta_effectiveness" in prompt_lower or "evaluate this job reel" in prompt_lower:
            logger.info("[MockLLM] Routing to Quality Engine Mock")
            return {
                "hook_quality": {"score": 95, "reasoning": "Strong hook targeting freshers directly."},
                "retention_score": {"score": 92, "reasoning": "Pacing is fast and structured perfectly."},
                "readability": {"score": 90, "reasoning": "Captions are short and centered in safe zone."},
                "cta_effectiveness": {"score": 93, "reasoning": "Urgency and link-in-bio callout is clear."},
                "overall_score": 93,
                "improvement_suggestions": []
            }

        # 2. Scene Planner (Module 7)
        elif "scene_plan" in prompt_lower or "transition" in prompt_lower or "search_query" in prompt_lower or "visual_description" in prompt_lower:
            logger.info("[MockLLM] Routing to Scene Planner Mock")
            return {
                "scenes": [
                    {
                        "scene_number": 1,
                        "start_time": 0,
                        "end_time": 3,
                        "duration": 3,
                        "visual_description": "Animated text: Remote AI Job opportunity, Zooming in",
                        "search_query": "remote worker laptop",
                        "ai_prompt": "cinematic shot of remote developer working on laptop, cozy environment, 4k",
                        "transition": "fade_in",
                        "text_overlay": "Remote AI Job Opportunity!"
                    },
                    {
                        "scene_number": 2,
                        "start_time": 3,
                        "end_time": 8,
                        "duration": 5,
                        "visual_description": "Mock Technologies company logo backdrop with modern office workspace",
                        "search_query": "modern office space workspace",
                        "ai_prompt": "futuristic tech office, neon highlights, cinematic, 4k",
                        "transition": "slide_left",
                        "text_overlay": "Mock Technologies Hiring"
                    },
                    {
                        "scene_number": 3,
                        "start_time": 8,
                        "end_time": 18,
                        "duration": 10,
                        "visual_description": "rupee symbol and graduation cap graphics popping up",
                        "search_query": "indian rupee money graduation cap",
                        "ai_prompt": "graduation cap next to money icons, 3d render, colorful",
                        "transition": "zoom_in",
                        "text_overlay": "B.Tech/MCA • 8.5-12 LPA"
                    },
                    {
                        "scene_number": 4,
                        "start_time": 18,
                        "end_time": 25,
                        "duration": 7,
                        "visual_description": "calendar showing deadline of August 30, warning badge",
                        "search_query": "calendar clock ticking",
                        "ai_prompt": "digital calendar ticking down, high contrast, clean",
                        "transition": "slide_up",
                        "text_overlay": "Apply by August 30!"
                    },
                    {
                        "scene_number": 5,
                        "start_time": 25,
                        "end_time": 30,
                        "duration": 5,
                        "visual_description": "CTA button flashing Link in Bio with arrow pointing",
                        "search_query": "link in bio click button",
                        "ai_prompt": "glowing link button, click gesture, neon arrows",
                        "transition": "scale_up",
                        "text_overlay": "Link in Bio! Apply Now"
                    }
                ]
            }

        # 3. Script Generator (Module 5)
        elif "write a reel script" in prompt_lower or "total_duration_estimate" in prompt_lower or ("script" in prompt_lower and "duration" in prompt_lower):
            logger.info("[MockLLM] Routing to Script Generator Mock")
            return {
                "script": "[HOOK - 0-3s] Stop scrolling if you are a 2025 batch fresher looking for remote jobs! [PAUSE] [INFO - 3-8s] Mock Technologies just announced hiring for AI Software Engineers! [PAUSE] [DETAILS - 8-18s] Anyone with a B.Tech or MCA degree can apply. Salary is 8.5 to 12 LPA. [PAUSE] [URGENCY - 18-25s] The last date is August 30. No prior experience is required. [PAUSE] [CTA - 25-30s] Link in bio. Apply now before it closes!",
                "total_duration_estimate": 30,
                "sections": [
                    {"type": "hook", "text": "Stop scrolling if you are a 2025 batch fresher looking for remote jobs!", "duration_estimate": 3, "start_time": 0, "end_time": 3},
                    {"type": "info", "text": "Mock Technologies just announced hiring for AI Software Engineers!", "duration_estimate": 5, "start_time": 3, "end_time": 8},
                    {"type": "details", "text": "Anyone with a B.Tech or MCA degree can apply. Salary is 8.5 to 12 LPA.", "duration_estimate": 10, "start_time": 8, "end_time": 18},
                    {"type": "urgency", "text": "The last date is August 30. No prior experience is required.", "duration_estimate": 7, "start_time": 18, "end_time": 25},
                    {"type": "cta", "text": "Link in bio. Apply now before it closes!", "duration_estimate": 5, "start_time": 25, "end_time": 30}
                ],
                "word_count": 100,
                "language": "hinglish"
            }

        # 4. Hook Generator (Module 4)
        elif "hook" in prompt_lower or "scroll-stop" in prompt_lower:
            logger.info("[MockLLM] Routing to Hook Generator Mock")
            return {
                "hooks": [
                    {
                        "index": 0,
                        "text": "Stop scrolling if you are a 2025 batch fresher looking for remote jobs!",
                        "score": 95,
                        "reasoning": "Direct callout to target audience with strong hook.",
                        "is_selected": True
                    },
                    {
                        "index": 1,
                        "text": "Mock Technologies is hiring remote AI Engineers at 12 LPA!",
                        "score": 88,
                        "reasoning": "High salary value proposition hook.",
                        "is_selected": False
                    },
                    {
                        "index": 2,
                        "text": "fresher remote job with 12 LPA salary package!",
                        "score": 82,
                        "reasoning": "Urgency and benefits callout.",
                        "is_selected": False
                    }
                ],
                "selected": "Stop scrolling if you are a 2025 batch fresher looking for remote jobs!"
            }

        # 5. Info Extraction (Module 3)
        elif "extract" in prompt_lower or "structured job information" in prompt_lower or "job data" in prompt_lower:
            logger.info("[MockLLM] Routing to Info Extraction Mock")
            return {
                "company_name": "Mock Technologies",
                "job_role": "AI Engineer",
                "salary": "8.5 - 12 LPA",
                "eligibility": "B.Tech/MCA/M.Sc in CSE/IT",
                "degree_requirements": ["B.Tech", "MCA", "M.Sc"],
                "batch": "2024, 2025",
                "experience": "Fresher / 1 Year",
                "location": "Remote (India)",
                "last_date": "2026-08-30",
                "selection_process": ["Online Test", "Technical Interview", "HR Interview"],
                "apply_link": "https://careers.mocktech.com/jobs/ai-engineer",
                "important_notes": ["Good knowledge of FastAPI", "Must be available for remote work"]
            }

        # General Fallback JSON
        logger.info("[MockLLM] Routing to General Fallback Mock")
        return {"status": "success", "data": "mock_response"}
