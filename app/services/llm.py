import logging
from typing import List, Optional, Type, TypeVar

from app.config import settings

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app import models

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAI Client Management
# ---------------------------------------------------------------------------
_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """Initializes and caches a singleton OpenAI client configured for Azure AI Foundry."""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
        )
    return _client


# ---------------------------------------------------------------------------
# Structured Output Schemas
# ---------------------------------------------------------------------------
class MediaEvaluationResult(BaseModel):
    """
    Schema for Azure OpenAI structured output.
    Note: 'justification' must precede 'decision' to enforce Chain-of-Thought
    reasoning prior to the classification token emission.
    """
    justification: str = Field(
        description="1 to 3 concise sentences explaining whether the content aligns semantically with the WASP-HS scope."
    )
    decision: models.AIRecommendation = Field(
        description="Classification decision: 'relevant', 'irrelevant', or 'uncertain'."
    )


class AcademicEvaluationResult(BaseModel):
    """
    Schema for Academic Publication structured output.
    Note: 'justification' must precede 'decision' to enforce Chain-of-Thought
    reasoning prior to the classification token emission.
    """
    justification: str = Field(
        description="1 to 3 concise sentences explaining whether the scientific abstract or paper aligns semantically with the WASP-HS scope."
    )
    decision: models.AIRecommendation = Field(
        description="Classification decision: 'relevant', 'irrelevant', or 'uncertain'."
    )


# ---------------------------------------------------------------------------
# System Prompts & Rubrics
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an expert research analyst evaluating media publications for "WASP-HS" (The Wallenberg AI, Autonomous Systems and Software Program – Humanities and Society).

WASP-HS SCOPE AND OBJECTIVE:
WASP-HS investigates the challenges and impacts of Artificial Intelligence (AI), autonomous systems, and emerging software technologies on the humanities, culture, governance, labor, ethics, psychology, philosophy, and society at large.

EVALUATION RUBRIC:
1. RELEVANT ("relevant"):
   - The article discusses AI, machine learning, or autonomous systems specifically through a societal, humanistic, ethical, psychological, legal, cultural, or policy lens.
   - The article explicitly mentions the WASP-HS program, its leadership, funded research projects, conferences, or affiliated members discussing their WASP-HS research.

2. IRRELEVANT ("irrelevant"):
   - The article only mentions an affiliated researcher in an unrelated context (e.g., general university budget cuts, standard campus administration, unrelated historical linguistics, or non-AI disciplinary work).
   - The article discusses purely technical software/hardware engineering with no humanistic or societal context.
   - The article discusses non-AI topics entirely.

3. UNCERTAIN ("uncertain"):
   - The provided text (e.g., truncated text or title only) is too ambiguous to determine whether the article concerns AI's impact on society or an unrelated subject.

INSTRUCTIONS:
- First, write a 1-3 sentence justification explaining your reasoning based on the rubric above.
- Second, output the final decision ('relevant', 'irrelevant', or 'uncertain')."""

ACADEMIC_SYSTEM_PROMPT = """You are an expert bibliometrician and research evaluator for "WASP-HS" (The Wallenberg AI, Autonomous Systems and Software Program – Humanities and Society).

WASP-HS SCOPE AND OBJECTIVE:
WASP-HS investigates the challenges and impacts of Artificial Intelligence (AI), autonomous systems, and emerging software technologies on the humanities, culture, governance, labor, ethics, psychology, philosophy, and society at large.

EVALUATION RUBRIC:
1. RELEVANT ("relevant"):
   - The abstract explicitly acknowledges "WASP-HS" funding or affiliation.
   - OR, the research clearly intersects AI, machine learning, or autonomous systems with a societal, humanistic, psychological, legal, cultural, or ethical domain.

2. IRRELEVANT ("irrelevant"):
   - The paper is purely technical/algorithmic (e.g., improving a neural network architecture, computer vision hardware) with no humanistic or societal analysis.
   - The paper is purely humanities/social science (e.g., historical linguistics, standard sociology) with absolutely no connection to AI or autonomous systems.

3. UNCERTAIN ("uncertain"):
   - The abstract is missing and the title is too ambiguous to classify securely.

INSTRUCTIONS:
- First, write a 1-3 sentence justification explaining your reasoning based on the rubric above.
- Second, output the final decision ('relevant', 'irrelevant', or 'uncertain')."""

# ---------------------------------------------------------------------------
# API Invocation with Exponential Backoff
# ---------------------------------------------------------------------------
T = TypeVar('T', bound=BaseModel)


@retry(
    retry=retry_if_exception_type((
            RateLimitError,
            APITimeoutError,
            InternalServerError,
            APIConnectionError,
    )),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _call_structured_evaluation(
        client: OpenAI,
        deployment_name: str,
        system_prompt: str,
        user_payload: str,
        response_model: Type[T]
) -> T:
    """Calls Azure AI Foundry with structured output and handles transient failures via tenacity."""
    completion = client.beta.chat.completions.parse(
        model=deployment_name,
        messages=[  # type: ignore
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
        response_format=response_model,
    )

    message = completion.choices[0].message
    if message.refusal:
        raise ValueError(f"Azure model refused to respond: {message.refusal}")

    if not message.parsed:
        raise ValueError("Model completed response without valid structured output.")

    return message.parsed


# ---------------------------------------------------------------------------
# Core Service Functions
# ---------------------------------------------------------------------------
def evaluate_media(db: Session, items_to_eval: List[models.MediaPublication]) -> int:
    """
    Evaluates a batch of media publications sequentially against the WASP-HS scope.

    Updates each item's ai_recommendation, is_relevant, has_processing_error,
    and processing_error_msg columns with per-item database commits.
    Returns the number of successfully evaluated publications.
    """
    if not items_to_eval:
        return 0

    client = get_openai_client()
    deployment_name = settings.azure_openai_deployment_name
    success_count = 0

    for item in items_to_eval:
        try:
            # 1. Defensive Sanitization and Truncation
            clean_title = (item.title or "Untitled").strip()[:500]
            clean_source = (item.source_name or "Unknown Source").strip()[:200]
            pub_date = item.published_date.isoformat() if item.published_date else "Unknown Date"
            content_url = (item.content_url or "None provided").strip()[:500]

            raw_body = (item.article_body or "").strip()
            if not raw_body:
                clean_body = "[Article body not available - evaluate based solely on title and metadata]"
            else:
                clean_body = raw_body[:15000]

            user_payload = (
                f"Title: {clean_title}\n"
                f"Source/Outlet: {clean_source}\n"
                f"Published Date: {pub_date}\n"
                f"URL: {content_url}\n\n"
                f"Article Body Content:\n{clean_body}"
            )

            # 2. Invoke Model via Structured Outputs
            result = _call_structured_evaluation(
                client=client,
                deployment_name=deployment_name,
                system_prompt=SYSTEM_PROMPT,
                user_payload=user_payload,
                response_model=MediaEvaluationResult,
            )

            # 3. Log Justification
            logger.info(
                "MediaPublication [ID %s] evaluated as '%s'. Justification: %s",
                item.id,
                result.decision.value,
                result.justification,
            )

            # 4. Map States to SQLAlchemy Model
            item.ai_recommendation = result.decision

            if result.decision == models.AIRecommendation.RELEVANT:
                item.is_relevant = True
            elif result.decision == models.AIRecommendation.IRRELEVANT:
                item.is_relevant = False
            else:  # UNCERTAIN
                item.is_relevant = None

            # Reset error quarantine flags on success
            item.has_processing_error = False
            item.processing_error_msg = None

            db.commit()
            success_count += 1

        except Exception as e:
            logger.exception("Failed evaluation for MediaPublication [ID %s]: %s", getattr(item, "id", "Unknown"),
                             str(e))
            try:
                db.rollback()
                item.has_processing_error = True
                item.processing_error_msg = str(e)[:1000]
                db.commit()
            except Exception as quarantine_err:
                logger.critical(
                    "Database failure while saving quarantine state for MediaPublication [ID %s]: %s",
                    getattr(item, "id", "Unknown"),
                    str(quarantine_err),
                )
                db.rollback()

    return success_count


def evaluate_academic(db: Session, items_to_eval: List[models.AcademicPublication]) -> int:
    """
    Evaluates a batch of academic publications sequentially against the WASP-HS scope.

    Updates each item's ai_recommendation, is_relevant, has_processing_error,
    and processing_error_msg columns with per-item database commits.
    Returns the number of successfully evaluated publications.
    """
    if not items_to_eval:
        return 0

    client = get_openai_client()
    deployment_name = settings.azure_openai_deployment_name
    success_count = 0

    for item in items_to_eval:
        try:
            # 1. Defensive Sanitization and Truncation
            clean_title = (item.title or "Untitled").strip()[:500]
            clean_journal = (item.journal_name or "Unknown Journal").strip()[:200]
            clean_authors = (item.authors_raw or "Unknown Authors").strip()[:500]
            clean_funding = (item.funding_info or "No funding info provided").strip()[:500]

            raw_abstract = (item.abstract or "").strip()
            if not raw_abstract:
                clean_abstract = "[Abstract not available - evaluate based on title and metadata]"
            else:
                clean_abstract = raw_abstract[:15000]

            user_payload = (
                f"Title: {clean_title}\n"
                f"Journal: {clean_journal}\n"
                f"Authors: {clean_authors}\n"
                f"Funding Info: {clean_funding}\n\n"
                f"Abstract:\n{clean_abstract}"
            )

            # 2. Invoke Model via Structured Outputs
            result = _call_structured_evaluation(
                client=client,
                deployment_name=deployment_name,
                system_prompt=ACADEMIC_SYSTEM_PROMPT,
                user_payload=user_payload,
                response_model=AcademicEvaluationResult,
            )

            # 3. Log Justification
            logger.info(
                "AcademicPublication [ID %s] evaluated as '%s'. Justification: %s",
                item.id,
                result.decision.value,
                result.justification,
            )

            # 4. Map States to SQLAlchemy Model
            item.ai_recommendation = result.decision

            if result.decision == models.AIRecommendation.RELEVANT:
                item.is_relevant = True
            elif result.decision == models.AIRecommendation.IRRELEVANT:
                item.is_relevant = False
            else:  # UNCERTAIN
                item.is_relevant = None

            # Reset error quarantine flags on success
            item.has_processing_error = False
            item.processing_error_msg = None

            db.commit()
            success_count += 1

        except Exception as e:
            logger.exception("Failed evaluation for AcademicPublication [ID %s]: %s", getattr(item, "id", "Unknown"),
                             str(e))
            try:
                db.rollback()
                item.has_processing_error = True
                item.processing_error_msg = str(e)[:1000]
                db.commit()
            except Exception as quarantine_err:
                logger.critical(
                    "Database failure while saving quarantine state for AcademicPublication [ID %s]: %s",
                    getattr(item, "id", "Unknown"),
                    str(quarantine_err),
                )
                db.rollback()

    return success_count
