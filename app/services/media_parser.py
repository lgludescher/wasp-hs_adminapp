"""
media_parser.py
Service for parsing media monitoring exports (Retriever and Factiva).
Extracts articles into standardized Pydantic models.
"""

from datetime import datetime
import re
import logging
from typing import List, Dict, Any, Optional

import dateparser
from striprtf.striprtf import rtf_to_text
from pydantic import ValidationError

# Import existing models and schemas from your app
from app.models import MediaPlatform
from app.schemas import MediaPublicationCreate


logger = logging.getLogger(__name__)


class ParseException(Exception):
    """Custom exception for unrecoverable parsing errors (e.g., wrong file type)."""
    pass


# --- Public API ---

def parse_uploaded_file(file_content: bytes, filename: str) -> List[MediaPublicationCreate]:
    """
    Main orchestrator to parse an uploaded file from Retriever or Factiva.
    Safely decodes bytes, sniffs the platform, routes to the correct parser, and validates.
    """
    # 1. Safe Decoding
    try:
        # Try UTF-8 first (standard for most modern web exports)
        # 'utf-8-sig' safely removes Windows Byte Order Marks (BOM) if present
        text = file_content.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            # Fallback 1: UTF-16 (common for Windows-generated RTF/TXT files)
            text = file_content.decode('utf-16')
        except UnicodeDecodeError:
            # Fallback 2: cp1252 replacing broken characters to prevent a hard crash
            text = file_content.decode('cp1252', errors='replace')

    # 2. Content Sniffing
    platform = _sniff_platform(text, filename)

    # 3. Route to Sub-Parsers
    if platform == MediaPlatform.RETRIEVER:
        raw_articles = _parse_retriever(text)
    elif platform == MediaPlatform.FACTIVA:
        raw_articles = _parse_factiva(text)
    else:
        raise ParseException("Unsupported platform detected.")

    # 4. Validate & Build Models
    validated_articles = []
    for raw_data in raw_articles:
        model = _validate_and_build_model(raw_data)
        if model:
            validated_articles.append(model)

    if not validated_articles:
        logger.warning(f"File {filename} was parsed but yielded 0 valid articles.")

    return validated_articles


# --- Private Helper Functions ---

def _sniff_platform(text: str, filename: str) -> MediaPlatform:
    """Inspects the file content/extension to determine the platform."""

    # 1. Check Retriever specific markers (using the first 50k chars)
    sample_head = text[:50000].lower()
    if "ret.nu" in sample_head or "===========" in sample_head:
        return MediaPlatform.RETRIEVER

    # 2. Check Factiva specific markers
    factiva_id_pattern = r'[a-z]{4,8}\d{1,4}20\d{6}[a-z0-9]{7,12}'

    # Search in the LAST 50,000 characters to bypass the header images
    # and hit the Accession Numbers at the bottom of the articles.
    sample_tail = text[-50000:].lower()

    if re.search(factiva_id_pattern, sample_tail):
        return MediaPlatform.FACTIVA

    # 3. Strict Fallback
    # Check the very beginning for the RTF signature
    if filename.lower().endswith('.rtf') and text.lstrip().startswith(r"{\rtf"):
        return MediaPlatform.FACTIVA

    if filename.lower().endswith('.txt'):
        return MediaPlatform.RETRIEVER

    raise ParseException(
        "Could not determine the platform from the file content. Ensure it is a valid Retriever or Factiva export."
    )


def _parse_retriever(text: str) -> List[Dict[str, Any]]:
    """State-machine based parser for Retriever TXT files."""
    articles = []

    # Strip the global file header before splitting.
    # Added localized terms to protect against different UI export languages.
    text = re.sub(
        r'^.*?(?:News Articles|Nyhetsartiklar|Artikler|Uutiset)[:\s]*',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    chunks = re.split(r'={10,}', text)

    for chunk in chunks:
        lines = [line.strip() for line in chunk.split('\n') if line.strip()]
        if len(lines) < 3:
            continue

        raw_data = {
            "platform": MediaPlatform.RETRIEVER,
            "title": lines[0],  # Safely the actual title again!
            "source_name": None,
            "published_date": None,
            "content_url": None,
            "external_id": None,
            "article_body": None
        }

        # 1. Dynamic Anchoring
        meta_idx = -1
        for i, line in enumerate(lines):
            # Matches: [Source Name], YYYY-MM-DD [HH:MM]
            if re.search(r',\s*\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?$', line):
                meta_idx = i
                break

        if meta_idx == -1:
            logger.warning(
                f"Skipping a Retriever chunk: Could not locate Source/Date anchor. Title: {raw_data['title'][:30]}"
            )
            continue

        # 2. Extract Source and Date from the anchor line
        source_date_line = lines[meta_idx]
        parts = source_date_line.rsplit(',', 1)
        raw_data["source_name"] = parts[0].strip()
        raw_data["published_date"] = dateparser.parse(parts[1].strip())

        # 3. URL and External ID extraction
        url_match = re.search(r'https://ret\.nu/\w+', chunk)
        if url_match:
            raw_data["content_url"] = url_match.group(0)
            raw_data["external_id"] = raw_data["content_url"].split('/')[-1]

        # 4. Robust Body Extraction (Saving the Lead Paragraph)
        body_lines = []

        # If there are lines between the title and the anchor, it's a lead paragraph!
        if meta_idx > 1:
            body_lines.extend(lines[1:meta_idx])

        # Extract the rest of the body
        for line in lines[meta_idx + 1:]:
            # Skip the medium/page lines immediately following the anchor
            if re.match(r'^(Publicerat|Published|Sida|Page)\b', line, re.IGNORECASE):
                continue

            # Stop triggers (Copyrights, Captions, or the URL section)
            if line.startswith('©') or line.startswith('Copyright') or line.startswith('Bildtext:'):
                break
            if 'ret.nu' in line or 'webartikeln' in line:
                break

            # Strip stray HTML tags (e.g., <br>) and append
            clean_line = re.sub(r'<[^>]+>', '', line)
            body_lines.append(clean_line)

        body_text = '\n'.join(body_lines).strip()
        raw_data["article_body"] = body_text if body_text else None

        articles.append(raw_data)

    return articles


def _parse_factiva(text: str) -> List[Dict[str, Any]]:
    """State-machine based parser for Factiva RTF files."""
    articles = []

    # Strip RTF formatting securely
    try:
        clean_text = rtf_to_text(text)
    except Exception as e:
        logger.error(f"Failed to strip RTF tags: {str(e)}")
        clean_text = text

    # Primary ID & Date pattern (matches the Accession Number and extracts the 8-digit date)
    id_pattern = r'(?i)document[a-z]*\s+([A-Z]{4,8}\d{1,4}(20\d{6})[A-Za-z0-9]{7,12})'
    matches = list(re.finditer(id_pattern, clean_text))

    start_idx = 0
    for match in matches:
        chunk = clean_text[start_idx:match.start()]
        external_id = match.group(1)
        date_str = match.group(2)
        start_idx = match.end()

        # 1. Prepare raw lines (keeping empty lines) to rebuild natural paragraphs
        raw_lines = chunk.split('\n')

        # 2. Prepare dense lines (dropping empty lines) for reliable metadata anchoring
        dense_lines = [line.strip() for line in raw_lines if line.strip()]

        if not dense_lines:
            continue

        raw_data = {
            "platform": MediaPlatform.FACTIVA,
            "external_id": external_id,
            "title": None,
            "source_name": None,
            "published_date": None,
            "content_url": None,
            "article_body": None
        }

        # --- BULLETPROOF DATE EXTRACTION ---
        try:
            raw_data["published_date"] = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            pass

        # --- METADATA ANCHORING (Using dense_lines) ---
        anchor_idx = -1
        for i, line in enumerate(dense_lines):
            # Look for the Source Code (e.g., PUBTSDA)
            if re.match(r'^[A-Z]{4,8}$', line):
                if i < 15:
                    anchor_idx = i
                    break

        if anchor_idx != -1:
            if anchor_idx >= 1:
                raw_data["source_name"] = dense_lines[anchor_idx - 1]

            # Fallback date scanning
            if not raw_data.get("published_date"):
                if anchor_idx >= 2:
                    parsed_date = dateparser.parse(dense_lines[anchor_idx - 2])
                    if parsed_date:
                        raw_data["published_date"] = parsed_date
                    elif anchor_idx >= 3:
                        raw_data["published_date"] = dateparser.parse(dense_lines[anchor_idx - 3])

        # --- PARAGRAPH-BASED TITLE EXTRACTION ---
        paragraphs = []
        current_para = []
        for line in raw_lines:
            stripped = line.strip()
            if stripped:
                current_para.append(stripped)
            else:
                if current_para:
                    paragraphs.append(" ".join(current_para))
                    current_para = []
        if current_para:
            paragraphs.append(" ".join(current_para))

        # Filter out PR wire boilerplate paragraphs
        blacklist_phrases = ["published this content", "solely responsible", "distributed via"]
        valid_paras = [p for p in paragraphs if not any(phrase in p.lower() for phrase in blacklist_phrases)]

        # The title is simply the very first valid paragraph
        raw_data["title"] = valid_paras[0] if valid_paras else "Unknown Title"

        # --- BODY EXTRACTION (Using dense_lines) ---
        body_start_idx = -1
        for i, line in enumerate(dense_lines):
            if re.match(r'^(©|copyright)', line, re.IGNORECASE):
                body_start_idx = i + 1
                break

        # Fallback if no copyright symbol is found
        if body_start_idx == -1 and anchor_idx != -1:
            body_start_idx = anchor_idx + 2

        body_lines = []
        if body_start_idx != -1 and body_start_idx < len(dense_lines):
            for line in dense_lines[body_start_idx:]:
                # Only skip actual junk artifacts, allowing repeated titles to safely pass into the body
                if line.lower() in ["access the original document here"] or \
                        re.match(r'^(published|publicerad|publicerat):\s*', line, re.IGNORECASE):
                    continue
                body_lines.append(line)

        body_text = '\n'.join(body_lines).strip()
        raw_data["article_body"] = body_text if body_text else None

        # --- SANITIZED URL EXTRACTION ---
        # Explicitly excludes trailing brackets, quotes, and commas
        url_match = re.search(r'https?://[^\s)\]"\',(*]+', chunk)
        if url_match:
            raw_data["content_url"] = url_match.group(0)

        articles.append(raw_data)

    return articles


def _validate_and_build_model(raw_data: Dict[str, Any]) -> Optional[MediaPublicationCreate]:
    """
    Final checkpoint. Checks business rules, cleans data, and maps to Pydantic.
    Returns None and logs a warning if the article is invalid.
    """
    # Safely clean values
    body = (raw_data.get("article_body") or "").strip()
    url = (raw_data.get("content_url") or "").strip()

    # We only use this variable for safe logging, letting Pydantic validate the real title
    title_for_log = str(raw_data.get("title") or "Unknown Title").strip()

    # Update raw_data to ensure we don't pass trailing spaces or whitespace-only strings to the DB
    raw_data["article_body"] = body if body else None
    raw_data["content_url"] = url if url else None

    if raw_data.get("title"):
        raw_data["title"] = raw_data["title"].strip()
    if raw_data.get("source_name"):
        raw_data["source_name"] = raw_data["source_name"].strip()

    # Business Rule: Must have either valid text body or a valid URL
    if not body and not url:
        logger.warning(
            f"Skipped Article [{raw_data.get('platform')}]: Missing both body and URL. "
            f"Title preview: {title_for_log[:30]}"
        )
        return None

    try:
        # Pydantic will catch missing mandatory fields (Title, Source, Date)
        model = MediaPublicationCreate(**raw_data)
        return model
    except ValidationError as e:
        logger.warning(
            f"Skipped Article [{raw_data.get('platform')}]: Missing required fields. "
            f"Title preview: {title_for_log[:30]}. Errors: {e.errors()}"
        )
        return None
