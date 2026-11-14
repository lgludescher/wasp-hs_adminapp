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
# class MediaEvaluationResult(BaseModel):
#     """
#     Schema for Azure OpenAI structured output.
#     Note: 'justification' must precede 'decision' to enforce Chain-of-Thought
#     reasoning prior to the classification token emission.
#     """
#     justification: str = Field(
#         description="1 to 3 concise sentences explaining whether the content aligns semantically with the WASP-HS scope."
#     )
#     decision: models.AIRecommendation = Field(
#         description="Classification decision: 'relevant', 'irrelevant', or 'uncertain'."
#     )
#
#
# class AcademicEvaluationResult(BaseModel):
#     """
#     Schema for Academic Publication structured output.
#     Note: 'justification' must precede 'decision' to enforce Chain-of-Thought
#     reasoning prior to the classification token emission.
#     """
#     justification: str = Field(
#         description="1 to 3 concise sentences explaining whether the scientific abstract or paper aligns semantically with the WASP-HS scope."
#     )
#     decision: models.AIRecommendation = Field(
#         description="Classification decision: 'relevant', 'irrelevant', or 'uncertain'."
#     )


class MediaEvaluationResult(BaseModel):
    """
    Schema for Azure OpenAI structured output on media publications.
    Field order enforces English Chain-of-Thought reasoning and entity grounding
    prior to emitting the classification token.
    """
    justification: str = Field(
        description=(
            "1 to 3 concise sentences written strictly in English: first summarizing "
            "the article's core topic and any explicit program/researcher attribution, "
            "then explaining how the content aligns with the WASP-HS evaluation rubric."
        )
    )
    cited_members_parsed: Optional[str] = Field(
        default=None,
        description=(
            "Semicolon-separated list ('First Middle Last; First Last') of academic "
            "researchers/scholars (Professors, Lecturers, Docents, Postdocs, PhD students, "
            "Researchers) cited or featured in the article who are either explicitly linked "
            "to WASP-HS in the text OR actively contribute a societal/humanistic/legal/ethical "
            "perspective on AI/autonomous systems. Strip all academic titles and use only name "
            "parts present in the text. Return null (never an empty string or the word 'None') "
            "if no qualifying scholar can be identified with certainty."
        )
    )
    decision: models.AIRecommendation = Field(
        description="Final classification decision: 'relevant', 'irrelevant', or 'uncertain'."
    )


class AcademicEvaluationResult(BaseModel):
    """
    Schema for Academic Publication structured output.
    Field order enforces English Chain-of-Thought reasoning prior to emitting
    the classification token.
    """
    justification: str = Field(
        description=(
            "1 to 3 concise sentences written strictly in English: first summarizing "
            "the paper's core research inquiry and noting whether an abstract or explicit "
            "WASP-HS funding/attribution is present, then explaining how it aligns with "
            "the WASP-HS evaluation rubric."
        )
    )
    decision: models.AIRecommendation = Field(
        description="Final classification decision: 'relevant', 'irrelevant', or 'uncertain'."
    )


# ---------------------------------------------------------------------------
# System Prompts & Rubrics
# ---------------------------------------------------------------------------
# SYSTEM_PROMPT = """You are an expert research analyst evaluating media publications for "WASP-HS" (The Wallenberg AI, Autonomous Systems and Software Program – Humanities and Society).
#
# WASP-HS SCOPE AND OBJECTIVE:
# WASP-HS investigates the challenges and impacts of Artificial Intelligence (AI), autonomous systems, and emerging software technologies on the humanities, culture, governance, labor, ethics, psychology, philosophy, and society at large.
#
# EVALUATION RUBRIC:
# 1. RELEVANT ("relevant"):
#    - The article discusses AI, machine learning, or autonomous systems specifically through a societal, humanistic, ethical, psychological, legal, cultural, or policy lens.
#    - The article explicitly mentions the WASP-HS program, its leadership, funded research projects, conferences, or affiliated members discussing their WASP-HS research.
#
# 2. IRRELEVANT ("irrelevant"):
#    - The article only mentions an affiliated researcher in an unrelated context (e.g., general university budget cuts, standard campus administration, unrelated historical linguistics, or non-AI disciplinary work).
#    - The article discusses purely technical software/hardware engineering with no humanistic or societal context.
#    - The article discusses non-AI topics entirely.
#
# 3. UNCERTAIN ("uncertain"):
#    - The provided text (e.g., truncated text or title only) is too ambiguous to determine whether the article concerns AI's impact on society or an unrelated subject.
#
# INSTRUCTIONS:
# - First, write a 1-3 sentence justification explaining your reasoning based on the rubric above.
# - Second, output the final decision ('relevant', 'irrelevant', or 'uncertain')."""

SYSTEM_PROMPT = """You are an expert research analyst evaluating media publications for "WASP-HS" (The Wallenberg AI, Autonomous Systems and Software Program – Humanity and Society / Humanities and Society).

WASP-HS SCOPE AND CALIBRATION:
- Core Scope: WASP-HS investigates the interplay, opportunities, challenges, and consequences of Artificial Intelligence (AI), autonomous systems, and data-driven software in relation to humanity and society. This spans ethics, law, governance, policy, labor, economy, culture, media, psychology, philosophy, education, healthcare organization, and democratic values.
- Interdisciplinary Research: WASP-HS includes computational and technical research when the inquiry genuinely addresses human or societal interaction (such as human-AI/robot interaction, explainable or trustworthy AI, algorithmic fairness, or socially aware systems).
- Sibling Program Distinction: Distinguish WASP-HS from "WASP" (without "-HS"). Both share the prefix "Wallenberg AI, Autonomous Systems and Software Program", but WASP focuses on pure engineering, core algorithms, and hardware without a human or societal focus.
- Missing Program Mentions: Relevant media articles frequently omit the "WASP-HS" acronym and only cite a researcher by their university role. Absence of "WASP-HS" is neutral; evaluate relevance based on thematic substance and context.

EVALUATION RUBRIC:
1. RELEVANT ("relevant"):
- Substantive Thematic Fit: The article—or a meaningful portion of it, such as an interview segment, op-ed, or expert commentary—examines AI, autonomous systems, or data-driven technology through a societal, humanistic, ethical, legal, cultural, organizational, economic, or policy lens.
- Direct Program Coverage: The article directly reports on the WASP-HS program, its funded projects, events, or leadership in a substantive context.

2. IRRELEVANT ("irrelevant"):
- Purely Technical or Non-AI: The article focuses exclusively on technical hardware/software engineering (including standard WASP research) with no substantive human or societal analysis, OR covers non-AI topics entirely.
- Incidental / Biographical Noise: A researcher's WASP-HS affiliation is mentioned only in passing (e.g., in a byline, fact box / "faktaruta", or boilerplate bio) while the article's actual subject and the researcher's commentary concern an unrelated topic.
- Unrelated Acronym Match: The character sequence "WASP" or "WASP-HS" refers to something unrelated to the Wallenberg research program.

3. UNCERTAIN ("uncertain"):
- Insufficient Information: The provided text (e.g., a heavily truncated snippet or ambiguous title) lacks enough context to determine whether the piece addresses AI and society.
- Conflicting Signals: The article contains contradictory evidence requiring human review—such as an explicit claim of WASP-HS funding/focus paired with content that appears completely unrelated or purely technical, or a borderline topic where the societal angle is ambiguous.

CITED MEMBERS EXTRACTION (cited_members_parsed):
Identify academic scholars (e.g., Professors, Lecturers / Lektorer, Docents, Postdocs, PhD students / Doktorander, Researchers / Forskare) named, quoted, interviewed, or authoring the article who meet EITHER criterion:
(a) Explicit Link: They are explicitly connected to WASP-HS in the article text (extract them even if the article's overall decision is "irrelevant").
(b) Thematic Academic Contributor: When "WASP-HS" is not explicitly linked to them, they are actively featured, interviewed, quoted, or authoring the piece as an academic scholar (typically affiliated with a Swedish university or research institute, or directly collaborating with one) discussing AI or autonomous systems from a societal, humanistic, legal, or ethical perspective.
Exclusions:
- Do NOT include journalists, politicians, union/industry representatives, non-academic commentators, or researchers explicitly linked only to technical WASP.
- Do NOT include global tech figures or foreign academics casually name-dropped in passing who are not directly featured in the piece.
- Do NOT include academics discussing unrelated non-AI topics unless they are explicitly linked to WASP-HS in the text.
Formatting:
- Strip all academic and professional titles (e.g., Prof., Dr., Docent, Doktorand).
- Present each name in standard order ("First Middle Last" or "First Last", or a single surname if that is all the text provides), using ONLY name parts present in the text. Never guess or invent missing first or last names.
- Separate multiple names with "; " (e.g., "Firstname Lastname; Firstname Middle Lastname").
- If no qualifying scholar can be determined with certainty from the text, return null.

LANGUAGE AND OUTPUT INSTRUCTIONS:
- Publications may be in Swedish, English, or occasionally other languages. Interpret the text within its original linguistic and journalistic context (accounting for Swedish concepts such as "humaniora och samhällsvetenskap", "tillit", "offentlig förvaltning", "arbetsmarknad", "rättsvetenskap", and fact boxes / "faktarutor"), but ALWAYS write your justification in English.
- Step 1 (justification): Write 1 to 3 concise sentences in English. First, state what the article is concretely about and note any explicit program or researcher attribution; second, explain how the content aligns with the rubric (checking for consistency between attribution and theme).
- Step 2 (cited_members_parsed): Extract qualifying WASP-HS / academic scholars separated by "; ", or return null.
- Step 3 (decision): Output the final classification ('relevant', 'irrelevant', or 'uncertain')."""

# ACADEMIC_SYSTEM_PROMPT = """You are an expert bibliometrician and research evaluator for "WASP-HS" (The Wallenberg AI, Autonomous Systems and Software Program – Humanities and Society).
#
# WASP-HS SCOPE AND OBJECTIVE:
# WASP-HS investigates the challenges and impacts of Artificial Intelligence (AI), autonomous systems, and emerging software technologies on the humanities, culture, governance, labor, ethics, psychology, philosophy, and society at large.
#
# EVALUATION RUBRIC:
# 1. RELEVANT ("relevant"):
#    - The abstract explicitly acknowledges "WASP-HS" funding or affiliation.
#    - OR, the research clearly intersects AI, machine learning, or autonomous systems with a societal, humanistic, psychological, legal, cultural, or ethical domain.
#
# 2. IRRELEVANT ("irrelevant"):
#    - The paper is purely technical/algorithmic (e.g., improving a neural network architecture, computer vision hardware) with no humanistic or societal analysis.
#    - The paper is purely humanities/social science (e.g., historical linguistics, standard sociology) with absolutely no connection to AI or autonomous systems.
#
# 3. UNCERTAIN ("uncertain"):
#    - The abstract is missing and the title is too ambiguous to classify securely.
#
# INSTRUCTIONS:
# - First, write a 1-3 sentence justification explaining your reasoning based on the rubric above.
# - Second, output the final decision ('relevant', 'irrelevant', or 'uncertain')."""

ACADEMIC_SYSTEM_PROMPT = """You are an expert bibliometrician and research evaluator for "WASP-HS" (The Wallenberg AI, Autonomous Systems and Software Program – Humanity and Society / Humanities and Society).

WASP-HS SCOPE AND CALIBRATION:
- Core Scope: WASP-HS investigates the interplay, opportunities, challenges, and consequences of Artificial Intelligence (AI), autonomous systems, and data-driven software in relation to humanity and society. This spans ethics, law, governance, policy, labor, economy, culture, media, psychology, philosophy, education, healthcare organization, and democratic values.
- Interdisciplinary Research: WASP-HS includes computational, statistical, and technical research when the core inquiry genuinely addresses human or societal dimensions (such as human-AI/robot interaction, explainable or trustworthy AI, algorithmic fairness, socially aware dialogue systems, or machine learning methods developed for social/humanistic analysis).
- Sibling Program & Boilerplate Distinction: Distinguish WASP-HS from "WASP" (without "-HS"), which shares the "Wallenberg AI, Autonomous Systems and Software Program" prefix but focuses on pure engineering, core algorithms, and hardware. Be careful with purely technical papers that merely include a generic one-sentence societal motivation hook in the introduction or conclusion while the actual research inquiry and contribution remain strictly algorithmic or hardware-focused.
- Incomplete Metadata: SwePub records frequently lack funding acknowledgments or abstracts even for core WASP-HS publications. Absence of "WASP-HS" in the metadata is neutral when evaluating thematic relevance.

EVALUATION RUBRIC:
1. RELEVANT ("relevant"):
- Substantive Thematic Fit: The research substantively investigates the intersection of AI, machine learning, autonomous systems, or data-driven technologies with human, societal, ethical, legal, cultural, psychological, organizational, economic, or philosophical questions.
- Explicit Program Funding: The funding metadata or abstract explicitly credits "WASP-HS" (not merely "WASP") as funding or supporting the work, and the paper's content is consistent with academic research in the program's broad domain.

2. IRRELEVANT ("irrelevant"):
- Purely Technical Engineering: The research is strictly algorithmic, mathematical, or hardware-focused (including standard WASP research) where societal impact is absent or mentioned only as superficial background motivation.
- Purely Non-AI / Unrelated: The work lies entirely within the humanities, social sciences, or other disciplines with no connection to AI, autonomous systems, or emerging data-driven technologies.
- Incidental Affiliation Noise: An author's biographical note mentions WASP-HS in passing, while the paper itself clearly investigates an unrelated non-AI topic or purely technical engineering without WASP-HS funding for the work.

3. UNCERTAIN ("uncertain"):
- Insufficient Metadata: Both the abstract and explicit WASP-HS funding info are missing, and the title alone is too broad or ambiguous to confidently verify that the work connects AI/autonomous systems with a human or societal inquiry.
- Conflicting Signals: The record contains contradictory evidence requiring human review—such as explicit WASP-HS funding attribution paired with an abstract that appears strictly unrelated or purely technical, or a borderline interdisciplinary topic where the human/societal dimension cannot be confirmed from the available text.

LANGUAGE AND OUTPUT INSTRUCTIONS:
- Records may be in English, Swedish, or occasionally other languages. Evaluate the record within its original academic context (including Swedish terminology such as "humaniora och samhällsvetenskap", "tillit", "offentlig förvaltning", "arbetsmarknad", and "rättsvetenskap"), but ALWAYS write your justification in English.
- Step 1 (justification): Write 1 to 3 concise sentences in English. First, summarize the paper's core research focus and state whether an abstract or explicit WASP-HS funding/attribution is present; second, explain your classification based on the rubric.
- Step 2 (decision): Output the final classification ('relevant', 'irrelevant', or 'uncertain')."""

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
            item.ai_justification = result.justification
            item.cited_members_parsed = result.cited_members_parsed

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
            item.ai_justification = result.justification

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
