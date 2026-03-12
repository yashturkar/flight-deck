"""Read-only retrieval and context bundling over notes."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import PurePosixPath

from app.core.config import settings
from app.services import current_view_service, git_service, vault_service

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_FRONTMATTER_BOUNDARY_RE = re.compile(r"^---\s*$", re.MULTILINE)
_SNIPPET_MAX_CHARS = 240


@dataclass(slots=True)
class NoteDocument:
    path: str
    content: str
    title: str
    headings: list[str]
    tags: list[str]
    links: set[str]
    sources: list[str]
    view: str
    search_blob: str
    tokens: set[str]
    backlinks: set[str] = field(default_factory=set)


@dataclass(slots=True)
class RetrievalMatch:
    path: str
    title: str
    score: float
    reasons: list[str]
    excerpt: str
    view: str
    sources: list[str]


@dataclass(slots=True)
class BundleMatch(RetrievalMatch):
    content: str | None
    content_tokens: int
    truncated: bool


@dataclass(slots=True)
class RetrievalIndex:
    docs: dict[str, NoteDocument]


_INDEX_CACHE: dict[tuple[object, ...], RetrievalIndex] = {}


def search_notes(query: str, view: str = "current", limit: int = 10) -> list[RetrievalMatch]:
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return []

    index = _get_index(view)
    query_tokens = _tokenize(normalized_query)
    scored = _score_documents(index, normalized_query, query_tokens)
    ordered = sorted(scored.values(), key=lambda item: (-item.score, item.path))

    return ordered[:limit]


def build_context_bundle(
    query: str,
    view: str = "current",
    limit: int = 10,
    token_budget: int = 4000,
) -> tuple[list[BundleMatch], int]:
    matches = search_notes(query=query, view=view, limit=limit)
    index = _get_index(view)

    used_tokens = 0
    bundle: list[BundleMatch] = []
    for match in matches:
        doc = index.docs[match.path]
        content_tokens = _estimate_tokens(doc.content)
        if used_tokens + content_tokens <= token_budget:
            content = doc.content
            used_tokens += content_tokens
            truncated = False
            included_tokens = content_tokens
        else:
            content = None
            truncated = True
            included_tokens = 0

        bundle.append(
            BundleMatch(
                path=match.path,
                title=match.title,
                score=match.score,
                reasons=match.reasons,
                excerpt=match.excerpt,
                view=match.view,
                sources=match.sources,
                content=content,
                content_tokens=included_tokens,
                truncated=truncated,
            )
        )

    return bundle, used_tokens


def _get_index(view: str) -> RetrievalIndex:
    cache_key, docs = _load_documents(view)
    cached = _INDEX_CACHE.get(cache_key)
    if cached is not None:
        return cached

    index = RetrievalIndex(docs=docs)
    _INDEX_CACHE.clear()
    _INDEX_CACHE[cache_key] = index
    return index


def _load_documents(view: str) -> tuple[tuple[object, ...], dict[str, NoteDocument]]:
    if view == "main":
        items = vault_service.list_notes()
        main_signature = tuple(
            (path, int(modified_at.timestamp() * 1_000_000))
            for path, modified_at in items
        )
        raw_docs = []
        for path, _ in items:
            content, _ = vault_service.read_note(path)
            raw_docs.append((path, content, [settings.git_branch]))
        cache_key = ("main", main_signature)
    elif view == "current":
        pending = current_view_service._pending_branches()
        ref_signature = tuple(
            (branch, git_service.resolve_ref(branch))
            for branch in [settings.git_branch, *pending]
        )
        items = current_view_service.list_notes_current(pending_branches=pending)
        raw_docs = []
        for path, _, sources in items:
            content, _, read_sources = current_view_service.read_note_current(
                path,
                pending_branches=pending,
            )
            raw_docs.append((path, content, read_sources or sources))
        cache_key = ("current", ref_signature)
    else:
        raise ValueError(f"Unsupported view '{view}'")

    docs = {
        doc.path: doc
        for doc in (
            _build_document(path=path, content=content, sources=sources, view=view)
            for path, content, sources in raw_docs
        )
    }

    for doc in docs.values():
        doc.links.intersection_update(docs.keys())
        for target in doc.links:
            docs[target].backlinks.add(doc.path)

    return cache_key, docs


def _build_document(path: str, content: str, sources: list[str], view: str) -> NoteDocument:
    frontmatter, body = _split_frontmatter(content)
    title = _extract_title(path, frontmatter, body)
    headings = _extract_headings(body)
    tags = _extract_tags(frontmatter)
    links = _extract_links(path, body)
    search_parts = [path, title, *headings, *tags, body]
    search_blob = "\n".join(part for part in search_parts if part).lower()
    tokens = set(_tokenize(search_blob))

    return NoteDocument(
        path=path,
        content=content,
        title=title,
        headings=headings,
        tags=tags,
        links=links,
        sources=sources,
        view=view,
        search_blob=search_blob,
        tokens=tokens,
    )


def _score_documents(
    index: RetrievalIndex,
    normalized_query: str,
    query_tokens: list[str],
) -> dict[str, RetrievalMatch]:
    interim: dict[str, tuple[float, list[str]]] = {}

    for doc in index.docs.values():
        score = 0.0
        reasons: list[str] = []
        title_lower = doc.title.lower()
        path_lower = doc.path.lower()

        if normalized_query in title_lower:
            score += 8.0
            reasons.append("title matches query")
        if normalized_query in path_lower:
            score += 6.0
            reasons.append("path matches query")
        if normalized_query in doc.search_blob:
            score += 4.0
            reasons.append("content matches query")

        for token in query_tokens:
            if token in path_lower:
                score += 2.5
                _append_reason(reasons, f"path contains '{token}'")
            if token in title_lower:
                score += 3.5
                _append_reason(reasons, f"title contains '{token}'")
            if any(token in heading.lower() for heading in doc.headings):
                score += 2.0
                _append_reason(reasons, f"heading contains '{token}'")
            if any(token == tag.lower() for tag in doc.tags):
                score += 2.5
                _append_reason(reasons, f"tag matches '{token}'")
            elif token in doc.tokens:
                score += 1.0
                _append_reason(reasons, f"body contains '{token}'")

        if score > 0:
            interim[doc.path] = (score, reasons[:4])

    seeds = sorted(interim.items(), key=lambda item: (-item[1][0], item[0]))[:5]
    for seed_path, (seed_score, _) in seeds:
        if seed_score < 3:
            continue
        seed_doc = index.docs[seed_path]
        for neighbor_path in seed_doc.links:
            if neighbor_path == seed_path:
                continue
            score, reasons = interim.get(neighbor_path, (0.0, []))
            score += 1.0
            _append_reason(reasons, f"linked from {seed_path}")
            interim[neighbor_path] = (score, reasons[:4])
        for backlink_path in seed_doc.backlinks:
            if backlink_path == seed_path:
                continue
            score, reasons = interim.get(backlink_path, (0.0, []))
            score += 0.75
            _append_reason(reasons, f"links to {seed_path}")
            interim[backlink_path] = (score, reasons[:4])

    return {
        path: RetrievalMatch(
            path=path,
            title=index.docs[path].title,
            score=round(score, 2),
            reasons=reasons[:4],
            excerpt=_build_excerpt(index.docs[path], normalized_query, query_tokens),
            view=index.docs[path].view,
            sources=index.docs[path].sources,
        )
        for path, (score, reasons) in interim.items()
        if score > 0
    }


def _split_frontmatter(content: str) -> tuple[str, str]:
    if not content.startswith("---\n"):
        return "", content

    matches = list(_FRONTMATTER_BOUNDARY_RE.finditer(content))
    if len(matches) < 2 or matches[0].start() != 0:
        return "", content

    frontmatter = content[matches[0].end():matches[1].start()].strip()
    body = content[matches[1].end():].lstrip("\n")
    return frontmatter, body


def _extract_title(path: str, frontmatter: str, body: str) -> str:
    fields = _parse_frontmatter(frontmatter)
    if title := fields.get("title"):
        return title[0]

    headings = _extract_headings(body)
    if headings:
        return headings[0]

    stem = PurePosixPath(path).stem.replace("-", " ").replace("_", " ")
    return stem.strip().title() or path


def _extract_headings(body: str) -> list[str]:
    return [match.strip() for match in _HEADING_RE.findall(body)]


def _extract_tags(frontmatter: str) -> list[str]:
    fields = _parse_frontmatter(frontmatter)
    return fields.get("tags", [])


def _parse_frontmatter(frontmatter: str) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {}
    current_key: str | None = None

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key and line.strip().startswith("-"):
            value = line.strip()[1:].strip().strip("'\"")
            if value:
                parsed.setdefault(current_key, []).append(value)
            continue
        current_key = None
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip().lower()
        value = raw_value.strip()
        if not value:
            current_key = key
            parsed.setdefault(key, [])
            continue
        if key == "tags":
            parsed[key] = _split_tag_values(value)
        else:
            parsed[key] = [value.strip().strip("'\"")]

    return parsed


def _split_tag_values(value: str) -> list[str]:
    cleaned = value.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return [
        token.strip().strip("'\"")
        for token in cleaned.split(",")
        if token.strip().strip("'\"")
    ]


def _extract_links(path: str, body: str) -> set[str]:
    links: set[str] = set()
    for raw in _WIKILINK_RE.findall(body):
        target = raw.split("|", 1)[0].strip()
        normalized = _normalize_link_target(path, target)
        if normalized:
            links.add(normalized)

    for raw in _MARKDOWN_LINK_RE.findall(body):
        normalized = _normalize_link_target(path, raw)
        if normalized:
            links.add(normalized)
    return links


def _normalize_link_target(source_path: str, raw_target: str) -> str | None:
    target = raw_target.strip().strip("<>").split("#", 1)[0].split("?", 1)[0]
    if not target or "://" in target or target.startswith(("mailto:", "#")):
        return None

    if target.startswith("/"):
        candidate = PurePosixPath(target.lstrip("/"))
    else:
        candidate = PurePosixPath(source_path).parent / target

    try:
        normalized = candidate.as_posix()
    except Exception:
        return None

    if normalized.startswith("../"):
        return None

    path_obj = PurePosixPath(normalized)
    if not path_obj.suffix:
        normalized = f"{normalized}.md"
    if PurePosixPath(normalized).suffix.lower() not in vault_service.ALLOWED_EXTENSIONS:
        return None
    return normalized


def _build_excerpt(doc: NoteDocument, normalized_query: str, query_tokens: list[str]) -> str:
    _, body = _split_frontmatter(doc.content)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    for line in lines:
        lowered = line.lower()
        if normalized_query in lowered or any(token in lowered for token in query_tokens):
            return _trim_snippet(_strip_markdown(line))
    if doc.headings:
        return _trim_snippet(_strip_markdown(doc.headings[0]))
    if lines:
        return _trim_snippet(_strip_markdown(lines[0]))
    return doc.title


def _strip_markdown(text: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", text)
    text = re.sub(r"\[\[([^\]|]+)\|?([^\]]*)\]\]", lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _trim_snippet(text: str) -> str:
    if len(text) <= _SNIPPET_MAX_CHARS:
        return text
    return text[: _SNIPPET_MAX_CHARS - 1].rstrip() + "…"


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _tokenize(text: str) -> list[str]:
    return [
        token
        for token in (match.group(0).lower() for match in _WORD_RE.finditer(text))
        if len(token) > 1
    ]


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)
