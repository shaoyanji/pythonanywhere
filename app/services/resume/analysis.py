"""Deterministic job-description analysis.

No language model, no third-party library: tokenising, synonym groups, a light
stemmer, and TF-IDF weighted cosine similarity. The point is a result you can
explain line by line — every proposal names the phrase it matched and the clause
it came from, so a wrong proposal is a wrong phrase in a visible table, not an
opaque score.

Known limits, deliberately not solved here (v1): implication ("led the team that
ran Kubernetes" is not a mention of Kubernetes), negation ("no Kubernetes
experience required"), proof versus mere mention, seniority and years, and JD
header/fluff lines being treated as requirements. Those need judgement, and the
human gate exists because of them.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

#: Cosine floor for a proposal. Deliberately fixed: a matcher that misses should
#: be fixed by adding a phrase to its group, never by sliding this number.
THRESHOLD = 0.15

#: concept -> surface forms found in job descriptions. Multi-word phrases are
#: matched with flexible separators, so "cloud native orchestration",
#: "cloud-native orchestration" and "cloud_native orchestration" are one entry.
SYNONYM_GROUPS: dict[str, tuple[str, ...]] = {
    "go": ("golang", "go lang", "go"),
    "kubernetes": (
        "cloud-native orchestration",
        "cloud native orchestration",
        "container orchestration",
        "orchestration platform",
        "kubernetes",
        "k8s",
        "helm",
        "eks",
        "gke",
    ),
    "telemetry": (
        "observability",
        "distributed tracing",
        "telemetry",
        "monitoring",
        "prometheus",
        "grafana",
        "opentelemetry",
        "metrics",
        "tracing",
    ),
    "nixos": (
        "declarative infrastructure",
        "declarative system configuration",
        "infrastructure as code",
        "configuration as code",
        "nixos",
        "nix",
        "iac",
    ),
    "python": ("python3", "python"),
    "flask": ("flask", "wsgi"),
    "mysql": ("mysql", "mariadb", "relational database", "sql"),
    "linux": ("linux", "unix", "systemd", "freebsd"),
    "ci": (
        "continuous integration",
        "continuous delivery",
        "ci/cd",
        "github actions",
        "gitlab ci",
        "jenkins",
    ),
    "containers": ("container images", "oci images", "docker", "containers"),
    "terraform": ("terraform", "pulumi", "cloudformation"),
    "aws": ("amazon web services", "aws", "ec2", "s3", "lambda", "iam"),
    "gcp": ("google cloud", "gcp", "bigquery"),
    "networking": (
        "load balancing",
        "tcp/ip",
        "networking",
        "wireguard",
        "tailscale",
        "nginx",
        "dns",
        "vpn",
    ),
    "security": (
        "secrets management",
        "authentication",
        "authorization",
        "hardening",
        "security",
        "oauth",
        "sops",
    ),
    "testing": ("integration tests", "unit tests", "test automation", "pytest", "testing"),
    "typescript": ("typescript", "javascript", "nodejs", "node"),
    "react": ("frontend", "front-end", "react"),
    "postgres": ("postgresql", "postgres"),
    "mentoring": ("technical leadership", "code review", "mentorship", "mentoring", "coaching"),
    "agile": ("sprint planning", "agile", "scrum", "kanban"),
    "documentation": ("technical writing", "runbooks", "documentation"),
}

#: Longest surface forms first, so "cloud-native orchestration" wins over "go"
#: inside "Golang" and over bare "kubernetes" where both could match.
_PHRASES = sorted(
    ((phrase, concept) for concept, phrases in SYNONYM_GROUPS.items() for phrase in phrases),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

_SEPARATOR = r"[\s\-_]+"
_CLAUSE_SPLIT = re.compile(r"[.;:,!\n]+")
_LEADING_CONJUNCTION = re.compile(r"^(?:and|or|with|plus)\s+", re.IGNORECASE)
_WORD = re.compile(r"[a-z0-9+#]+")
_SUFFIXES = (
    "ational",
    "ations",
    "ingly",
    "ation",
    "ments",
    "ment",
    "edly",
    "ing",
    "ies",
    "ed",
    "es",
    "ly",
    "s",
)


@dataclass(frozen=True)
class Hit:
    concept: str
    phrase: str
    start: int
    end: int


@dataclass(frozen=True)
class ResumeItem:
    key: str
    label: str
    text: str


def normalize(text: str) -> str:
    """Lowercase, treat hyphens and underscores as spaces, collapse runs."""
    return re.sub(r"\s+", " ", text.lower().replace("-", " ").replace("_", " ")).strip()


def stem(word: str) -> str:
    """Strip one common English suffix. Crude on purpose and symmetric: the same
    function runs over JD and resume text, so consistency matters more than
    linguistic accuracy. "kubernetes" and "kubernetess" still collide, "nixos"
    and "nix" do not."""
    for suffix in _SUFFIXES:
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    """Every alphanumeric token, however short. No stopword list and no length
    filter: "go", "c" and "r" are technologies, and dropping them to tidy the
    vector would silently delete real requirements."""
    return [stem(token) for token in _WORD.findall(normalize(text))]


def concept_hits(text: str) -> list[Hit]:
    """Every synonym-group phrase present in ``text``, longest match first, with
    overlapping shorter matches discarded."""
    found: list[Hit] = []
    for phrase, concept in _PHRASES:
        pattern = r"\b" + _SEPARATOR.join(re.escape(part) for part in phrase.split()) + r"\b"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            found.append(Hit(concept, phrase, match.start(), match.end()))

    kept: list[Hit] = []
    for hit in sorted(found, key=lambda item: (item.start, -(item.end - item.start))):
        overlaps = any(
            hit.start < other.end and other.start < hit.end and other.start != hit.start
            for other in kept
        )
        if not overlaps:
            kept.append(hit)
    return kept


def clause_for(text: str, start: int, end: int) -> str:
    """The clause containing ``[start, end)``, as evidence a human can check."""
    bounds = [(match.start(), match.end()) for match in _CLAUSE_SPLIT.finditer(text)]
    left = 0
    right = len(text)
    for boundary_start, boundary_end in bounds:
        if boundary_end <= start:
            left = boundary_end
        elif boundary_start >= end:
            right = boundary_start
            break
    clause = text[left:right].strip()
    clause = _LEADING_CONJUNCTION.sub("", clause)
    return re.sub(r"\s+", " ", clause).strip(" ,.;:")


def resume_items(resume: dict) -> list[ResumeItem]:
    """Flatten a resume into addressable units. The key is what a proposal points
    at and what an approval writes back to, so it is stable across edits."""
    items: list[ResumeItem] = []
    sections = resume.get("sections", {}) or {}

    for index, skill in enumerate(sections.get("skills", []) or []):
        name = str(skill.get("name", "")).strip()
        if not name:
            continue
        detail = str(skill.get("detail", "")).strip()
        items.append(ResumeItem(f"skills/{name}", name, f"{name} {detail}".strip()))

    for job_index, job in enumerate(sections.get("experience", []) or []):
        heading = " ".join(
            str(job.get(field, "")).strip() for field in ("role", "company", "period")
        ).strip()
        items.append(ResumeItem(f"experience/{job_index}", heading, heading))
        for bullet_index, bullet in enumerate(job.get("bullets", []) or []):
            text = str(bullet).strip()
            if text:
                key = f"experience/{job_index}/bullets/{bullet_index}"
                items.append(ResumeItem(key, f"{heading} — bullet {bullet_index + 1}", text))

    for index, project in enumerate(sections.get("projects", []) or []):
        name = str(project.get("name", "")).strip()
        summary = str(project.get("summary", "")).strip()
        if name or summary:
            items.append(ResumeItem(f"projects/{index}", name or f"project {index + 1}", f"{name} {summary}".strip()))

    for index, school in enumerate(sections.get("education", []) or []):
        heading = " ".join(
            str(school.get(field, "")).strip() for field in ("degree", "school", "period")
        ).strip()
        if heading:
            items.append(ResumeItem(f"education/{index}", heading, heading))

    summary = str(resume.get("summary", "")).strip()
    if summary:
        items.append(ResumeItem("summary", "Professional summary", summary))

    return items


def _tfidf_vectors(documents: list[list[str]]) -> list[dict[str, float]]:
    """TF-IDF vectors over a corpus of token lists: tf is the raw count, idf is
    smoothed so a term in every document still carries a little weight."""
    total = len(documents) or 1
    document_frequency: dict[str, int] = {}
    for tokens in documents:
        for token in set(tokens):
            document_frequency[token] = document_frequency.get(token, 0) + 1

    vectors: list[dict[str, float]] = []
    for tokens in documents:
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        vectors.append(
            {
                token: count * (math.log((total + 1) / (document_frequency[token] + 1)) + 1.0)
                for token, count in counts.items()
            }
        )
    return vectors


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(weight * right.get(token, 0.0) for token, weight in left.items())
    norm_left = math.sqrt(sum(weight * weight for weight in left.values()))
    norm_right = math.sqrt(sum(weight * weight for weight in right.values()))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def _concept_tokens(concepts: list[str]) -> list[str]:
    """A synonym group is a shared vocabulary, so the concept joins the vector
    twice: once as its canonical name and once as a marker. Without this,
    "observability" in a JD and "telemetry" in a resume are lexically disjoint and
    cosine similarity is zero however right the mapping. The marker is what lets a
    resume item declare a concept it never spells out ("Flake-based host fleets"
    is NixOS without saying so)."""
    tokens: list[str] = []
    for concept in concepts:
        tokens.append(concept)
        tokens.append(f"#concept:{concept}")
    return tokens


def _item_concepts(item: ResumeItem) -> list[str]:
    return [hit.concept for hit in concept_hits(item.text)]


def analyze_job(jd_text: str, resume: dict) -> dict:
    """Return proposals and gaps for one job description against one resume."""
    items = resume_items(resume)
    hits = concept_hits(jd_text)

    clauses: list[str] = []
    clause_of_hit: list[str] = []
    for hit in hits:
        clause = clause_for(jd_text, hit.start, hit.end)
        clauses.append(clause)
        clause_of_hit.append(clause)

    jd_tokens = tokenize(jd_text)
    jd_concepts = sorted({hit.concept for hit in hits})

    corpus: list[list[str]] = []
    for index, clause in enumerate(clauses):
        corpus.append(tokenize(clause) + _concept_tokens([hits[index].concept]))
    for item in items:
        corpus.append(tokenize(item.text) + _concept_tokens(sorted(set(_item_concepts(item)))))

    vectors = _tfidf_vectors(corpus)
    clause_vectors = vectors[: len(clauses)]
    item_vectors = vectors[len(clauses) :]

    resume_concepts = sorted({concept for item in items for concept in _item_concepts(item)})
    proposals: list[dict] = []
    seen: set[tuple[str, str]] = set()

    # Candidates are restricted to items that carry the same concept. Cosine over
    # the whole resume let a long heading win on a stray shared word ("declarative
    # infrastructure" landed on "Infrastructure Engineer"), which is a proposal
    # pointing at text that has nothing to do with the requirement.
    item_concept_sets = [set(_item_concepts(item)) for item in items]

    for index, hit in enumerate(hits):
        best_item: ResumeItem | None = None
        best_score = 0.0
        for position, item in enumerate(items):
            if hit.concept not in item_concept_sets[position]:
                continue
            score = _cosine(clause_vectors[index], item_vectors[position])
            if score > best_score:
                best_score, best_item = score, item
        if best_item is None or best_score < THRESHOLD:
            continue
        if (hit.concept, best_item.key) in seen:
            continue
        seen.add((hit.concept, best_item.key))
        proposals.append(
            {
                "concept": hit.concept,
                "requirement": hit.phrase,
                "resume_key": best_item.key,
                "label": best_item.label,
                "evidence": clause_of_hit[index],
                "score": round(best_score, 4),
                "suggested_change": None,
            }
        )

    gaps = [
        {
            "concept": hit.concept,
            "requirement": hit.phrase,
            "evidence": clause_of_hit[index],
            "resume_key": None,
        }
        for index, hit in enumerate(hits)
        if hit.concept not in resume_concepts
    ]

    proposals.sort(key=lambda proposal: (-proposal["score"], proposal["resume_key"]))

    return {
        "threshold": THRESHOLD,
        "proposals": proposals,
        "gaps": gaps,
        "jd_concepts": jd_concepts,
        "resume_concepts": resume_concepts,
        "jd_tokens": len(jd_tokens),
        "resume_items": len(items),
    }
