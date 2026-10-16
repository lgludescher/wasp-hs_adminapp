import re
import difflib
import logging
from datetime import timedelta
from typing import List, Set, Any
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app import models

logger = logging.getLogger(__name__)

# --- Configuration & Constants ---
PRESTIGE_SOURCES: Set[str] = {
    "dagens nyheter", "dn",
    "svenska dagbladet", "svd",
    "svt", "svt nyheter",
    "sveriges radio", "sr",
    "dagens industri", "di",
    "aftonbladet",
    "expressen",
    "forskning  framsteg",  # normalized string
    "tt"
}


# --- Helper Functions ---

def normalize_text(text: str) -> str:
    """Safely lowercases and strips all non-word characters, preserving Unicode letters."""
    if not text:
        return ""
    # \w matches letters (including Unicode like å,ä,ö), numbers, and underscores.
    return re.sub(r'[^\w]', '', text.lower())


def is_similar(text1: str, text2: str, threshold: float = 0.95) -> bool:
    """Evaluates absolute text similarity using standard library difflib."""
    if not text1 or not text2:
        return False
    return difflib.SequenceMatcher(None, text1, text2).ratio() > threshold


def get_lccs_length(text1: str, text2: str) -> int:
    """Returns the length of the Longest Common Contiguous Substring."""
    if not text1 or not text2:
        return 0
    match = difflib.SequenceMatcher(None, text1, text2, autojunk=False).find_longest_match(0, len(text1), 0, len(text2))
    return match.size


def _get_clusters(graph: dict, item_map: dict) -> List[List[Any]]:
    """Extracts isolated components (clusters) from the pairwise matching graph."""
    visited = set()
    clusters = []

    for node_id in item_map:
        if node_id not in visited:
            cluster = []
            queue = [node_id]
            visited.add(node_id)

            while queue:
                curr = queue.pop(0)
                cluster.append(item_map[curr])
                for neighbor in graph.get(curr, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            if len(cluster) > 1:
                clusters.append(cluster)

    return clusters


def _resolve_cluster(db: Session, model_class, cluster: List[Any], hierarchy_func):
    """Evaluates a single cluster to crown exactly one winner and re-parent losers."""
    incumbents = [i for i in cluster if i.is_duplicate is not None]
    pending = [i for i in cluster if i.is_duplicate is None]

    if not pending:
        return

    # 1. Identify winner
    if incumbents:
        winner = max(incumbents, key=hierarchy_func)
        losers = pending
    else:
        winner = max(pending, key=hierarchy_func)
        winner.is_duplicate = False
        losers = [i for i in pending if i.id != winner.id]

    if not losers:
        return

    # 2. Mark losers and re-parent
    loser_ids = []
    for loser in losers:
        loser.is_duplicate = True
        loser.duplicate_of_id = winner.id
        loser_ids.append(loser.id)

    # 3. Mass Re-parenting for transitive children
    if loser_ids:
        db.query(model_class).filter(
            model_class.duplicate_of_id.in_(loser_ids)
        ).update(
            {model_class.duplicate_of_id: winner.id},
            synchronize_session=False
        )


# --- Media Deduplication ---

def get_media_hierarchy(item: models.MediaPublication):
    norm_source = normalize_text(item.source_name)
    is_prestige = 1 if norm_source in PRESTIGE_SOURCES else 0
    body_len = len(item.article_body) if item.article_body else 0
    date_score = -item.published_date.timestamp() if item.published_date else 0
    return (is_prestige, body_len, date_score)


def flag_media_duplicates(db: Session, items_to_dedup: List[models.MediaPublication]):
    if not items_to_dedup:
        return

    try:
        db.flush()

        dates = [i.published_date for i in items_to_dedup if i.published_date]
        if not dates:
            logger.warning("No published dates found in media batch, aborting deduplication.")
            return

        min_date = min(dates) - timedelta(days=14)
        max_date = max(dates) + timedelta(days=14)
        batch_ids = {i.id for i in items_to_dedup}

        historical_items = db.query(models.MediaPublication).filter(
            models.MediaPublication.published_date >= min_date,
            models.MediaPublication.published_date <= max_date,
            models.MediaPublication.id.notin_(batch_ids),
            models.MediaPublication.article_body.isnot(None)
        ).all()

        # Unified Memory Map & Normalizations
        all_items = items_to_dedup + historical_items
        item_map = {i.id: i for i in all_items}

        norm_titles = {i.id: normalize_text(i.title) for i in all_items}
        norm_bodies = {i.id: normalize_text(i.article_body[:2000]) if i.article_body else "" for i in all_items}

        graph = defaultdict(set)

        # Unified Matching
        for b1 in items_to_dedup:
            for i2 in all_items:
                if b1.id == i2.id: continue
                if i2.id in batch_ids and b1.id > i2.id: continue
                if i2.id in graph[b1.id]: continue

                is_match = False

                # 0. Fastest Track
                if b1.content_url and i2.content_url and b1.content_url == i2.content_url:
                    is_match = True

                if not is_match:
                    b1_title = norm_titles[b1.id]
                    i2_title = norm_titles[i2.id]
                    b1_body = norm_bodies[b1.id]
                    i2_body = norm_bodies[i2.id]

                    if b1_title and b1_title == i2_title:
                        if len(b1_title) < 30:
                            body_lccs = get_lccs_length(b1_body, i2_body)
                            if body_lccs > 100 or is_similar(b1_body[:200], i2_body[:200], 0.95):
                                is_match = True
                        else:
                            is_match = True

                    elif is_similar(b1_title, i2_title, 0.95):
                        if len(b1_title) < 30 or len(i2_title) < 30:
                            body_lccs = get_lccs_length(b1_body, i2_body)
                            if body_lccs > 100 or is_similar(b1_body[:200], i2_body[:200], 0.95):
                                is_match = True
                        else:
                            is_match = True

                    else:
                        title_lccs = get_lccs_length(b1_title, i2_title)
                        shorter_title_len = min(len(b1_title), len(i2_title))

                        if shorter_title_len > 0 and (title_lccs > 35 or title_lccs > 0.70 * shorter_title_len):
                            body_lccs = get_lccs_length(b1_body, i2_body)
                            shorter_body_len = min(len(b1_body), len(i2_body))

                            if body_lccs > 100 or (shorter_body_len > 0 and body_lccs > 0.70 * shorter_body_len):
                                is_match = True

                if is_match:
                    graph[b1.id].add(i2.id)
                    graph[i2.id].add(b1.id)

        clusters = _get_clusters(graph, item_map)
        for cluster in clusters:
            _resolve_cluster(db, models.MediaPublication, cluster, get_media_hierarchy)

        clustered_ids = {item.id for cluster in clusters for item in cluster}
        for b in items_to_dedup:
            if b.id not in clustered_ids and b.is_duplicate is None:
                b.is_duplicate = False

        db.commit()
        logger.info(f"Media deduplication resolved {len(clusters)} clusters.")

    except Exception as e:
        db.rollback()
        logger.error(f"Batch failure during Media deduplication: {e}", exc_info=True)


# --- Academic Deduplication ---

def get_academic_hierarchy(item: models.AcademicPublication):
    has_doi = 1 if item.doi else 0
    has_abstract = 1 if item.abstract else 0
    has_journal = 1 if item.journal_name else 0
    date_score = item.published_date.timestamp() if item.published_date else 0
    return (has_doi, has_abstract, has_journal, date_score)


def flag_academic_duplicates(db: Session, items_to_dedup: List[models.AcademicPublication]):
    if not items_to_dedup:
        return

    try:
        db.flush()
        batch_ids = {i.id for i in items_to_dedup}

        dois = {i.doi for i in items_to_dedup if i.doi}
        swepub_ids = {i.swepub_id for i in items_to_dedup if i.swepub_id}
        titles = {i.title for i in items_to_dedup if i.title}

        historical_items = []
        if dois or swepub_ids or titles:
            historical_items = db.query(models.AcademicPublication).filter(
                or_(
                    models.AcademicPublication.doi.in_(dois) if dois else False,
                    models.AcademicPublication.swepub_id.in_(swepub_ids) if swepub_ids else False,
                    models.AcademicPublication.title.in_(titles) if titles else False
                ),
                models.AcademicPublication.id.notin_(batch_ids)
            ).all()

        all_items = items_to_dedup + historical_items
        item_map = {i.id: i for i in all_items}

        norm_titles = {i.id: normalize_text(i.title) for i in all_items}
        norm_authors = {i.id: normalize_text(i.authors_raw) if i.authors_raw else "" for i in all_items}
        norm_abstracts = {i.id: normalize_text(i.abstract[:2000]) if i.abstract else "" for i in all_items}

        graph = defaultdict(set)

        # Unified Matching
        for b1 in items_to_dedup:
            for i2 in all_items:
                if b1.id == i2.id: continue
                if i2.id in batch_ids and b1.id > i2.id: continue
                if i2.id in graph[b1.id]: continue

                is_match = False

                # 0. Fastest Track
                if (b1.doi and i2.doi and b1.doi == i2.doi) or (
                        b1.swepub_id and i2.swepub_id and b1.swepub_id == i2.swepub_id):
                    is_match = True

                if not is_match:
                    b1_title = norm_titles[b1.id]
                    i2_title = norm_titles[i2.id]

                    # Core similarity logic (Exact, Ratio, or LCCS)
                    title_match_found = False
                    if b1_title and b1_title == i2_title:
                        title_match_found = True
                    elif is_similar(b1_title, i2_title, 0.95):
                        title_match_found = True
                    else:
                        title_lccs = get_lccs_length(b1_title, i2_title)
                        shorter_title_len = min(len(b1_title), len(i2_title))
                        if shorter_title_len > 0 and (title_lccs > 35 or title_lccs > 0.70 * shorter_title_len):
                            title_match_found = True

                    # Entropy Guards for Academic Data
                    if title_match_found:
                        if len(b1_title) >= 30 and len(i2_title) >= 30 and is_similar(b1_title, i2_title, 0.95):
                            # Safe pass for long, highly similar titles
                            is_match = True
                        else:
                            # Entropy Guard required (Title is short OR required LCCS extraction)
                            b1_auth = norm_authors[b1.id]
                            i2_auth = norm_authors[i2.id]

                            auth_lccs = get_lccs_length(b1_auth, i2_auth)
                            shorter_auth_len = min(len(b1_auth), len(i2_auth))

                            # Author Guard: Tolerates initials vs full names
                            if shorter_auth_len > 0 and (auth_lccs > 0.70 * shorter_auth_len):
                                is_match = True
                            else:
                                # Abstract Fallback Guard (if authors are missing/mangled)
                                b1_abs = norm_abstracts[b1.id]
                                i2_abs = norm_abstracts[i2.id]

                                abs_lccs = get_lccs_length(b1_abs, i2_abs)
                                shorter_abs_len = min(len(b1_abs), len(i2_abs))

                                if abs_lccs > 100 or (shorter_abs_len > 0 and abs_lccs > 0.70 * shorter_abs_len):
                                    is_match = True

                if is_match:
                    graph[b1.id].add(i2.id)
                    graph[i2.id].add(b1.id)

        clusters = _get_clusters(graph, item_map)
        for cluster in clusters:
            _resolve_cluster(db, models.AcademicPublication, cluster, get_academic_hierarchy)

        clustered_ids = {item.id for cluster in clusters for item in cluster}
        for b in items_to_dedup:
            if b.id not in clustered_ids and b.is_duplicate is None:
                b.is_duplicate = False

        db.commit()
        logger.info(f"Academic deduplication resolved {len(clusters)} clusters.")

    except Exception as e:
        db.rollback()
        logger.error(f"Batch failure during Academic deduplication: {e}", exc_info=True)
