from __future__ import annotations

import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Any, Callable

import openpyxl

from backend.embeddings import SentenceEmbeddingFeatureExtractor


BASE_DIR = Path(__file__).resolve().parents[1]
COURSE_PATH = BASE_DIR / "outputs" / "course-data-cleaned" / "ssu_time_courses_clean.json"
REVIEW_PATH = BASE_DIR / "scraper" / "data" / "api_reviews.xlsx"
EMBEDDING_CACHE_PATH = BASE_DIR / "backend" / "data" / "review_embedding_profiles.json"

DAYS = ["월", "화", "수", "목", "금"]
DAY_INDEX = {day: index for index, day in enumerate(DAYS)}
FEATURES = [
    "assignment_load",
    "team_presentation",
    "exam_load",
    "difficulty",
    "grade_generosity",
    "attendance_strictness",
    "fun_relaxed",
]

FEATURE_KEYWORDS = {
    "assignment_load": {
        "positive": ["과제", "레포트", "보고서", "자소서", "매주", "숙제", "감상문"],
        "negative": ["과제 없음", "과제는 없음", "과제 거의", "부담 없음", "부담이 적"],
    },
    "team_presentation": {
        "positive": ["팀플", "조별", "조모임", "발표", "프로젝트", "ppt", "피피티"],
        "negative": ["팀플 없음", "발표 없음", "개인 과제"],
    },
    "exam_load": {
        "positive": ["시험", "중간", "기말", "퀴즈", "쪽지시험", "암기", "오픈북"],
        "negative": ["시험 없음", "중간 없음", "기말 없음", "시험은 없음"],
    },
    "difficulty": {
        "positive": ["어렵", "난이도", "빡세", "힘들", "헬", "많이 외", "분량", "막막"],
        "negative": ["쉽", "꿀", "널널", "부담 적", "어렵지", "편하게"],
    },
    "grade_generosity": {
        "positive": ["학점", "성적", "A+", "에이쁠", "후하", "잘 주", "만점", "너그러"],
        "negative": ["짜다", "깐깐", "F", "폭격", "성적 받기 힘"],
    },
    "attendance_strictness": {
        "positive": ["출석", "출결", "지각", "결석", "출첵", "대리출석"],
        "negative": ["출석 안", "출석은 안", "출결 안", "지각 안"],
    },
    "fun_relaxed": {
        "positive": ["재밌", "재미", "편하", "좋", "추천", "유익", "친절", "최고"],
        "negative": ["노잼", "지루", "별로", "최악", "비추", "불편"],
    },
}

PREFERENCE_TARGETS = {
    "assignmentLoad": {
        "ok": ("assignment_load", 0.85),
        "low": ("assignment_load", 0.1),
    },
    "teamPresentation": {
        "ok": ("team_presentation", 0.85),
        "avoid": ("team_presentation", 0.1),
    },
    "examPreference": {
        "exam": ("exam_load", 0.85),
        "low": ("exam_load", 0.1),
    },
    "difficultyPreference": {
        "deep": ("difficulty", 0.82),
        "easy": ("difficulty", 0.15),
    },
    "gradePreference": {
        "generous": ("grade_generosity", 0.9),
        "content": ("grade_generosity", 0.45),
    },
    "attendancePreference": {
        "strict": ("attendance_strictness", 0.75),
        "loose": ("attendance_strictness", 0.1),
    },
    "classMood": {
        "fun": ("fun_relaxed", 0.92),
        "structured": ("fun_relaxed", 0.45),
    },
}


@dataclass(frozen=True)
class Meeting:
    day: str
    start: int
    end: int


@dataclass
class LectureProfile:
    course_name: str
    professor: str
    review_count: int = 0
    rating_avg: float = 0.0
    feature_vector: dict[str, float] = field(default_factory=dict)
    text: str = ""
    feature_source: str = "keyword"


@dataclass
class Candidate:
    course: dict[str, Any]
    meetings: list[Meeting]
    profile: LectureProfile
    lecture_fit: float
    keyword_fit: float = 0.0

    @property
    def credits(self) -> int:
        return int(self.course.get("credits") or 0)

    @property
    def id(self) -> str:
        return str(self.course.get("id") or "")

    @property
    def course_name(self) -> str:
        return str(self.course.get("course_name") or "")

    @property
    def professor(self) -> str:
        return str(self.course.get("professor") or "")

    @property
    def group(self) -> str:
        return str(self.course.get("course_group") or "")


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def parse_meetings(time_raw: str) -> list[Meeting]:
    meetings: list[Meeting] = []
    for line in str(time_raw or "").splitlines():
        match = re.search(r"([월화수목금토일\s]+)\s+(\d{1,2}:\d{2})-(\d{1,2}:\d{2})", line)
        if not match:
            continue
        day_text, start_text, end_text = match.groups()
        for day in DAYS:
            if day in day_text:
                meetings.append(Meeting(day=day, start=minutes(start_text), end=minutes(end_text)))
    return meetings


def has_conflict(items: list[Candidate]) -> bool:
    by_day: dict[str, list[Meeting]] = defaultdict(list)
    for item in items:
        for meeting in item.meetings:
            by_day[meeting.day].append(meeting)

    for meetings in by_day.values():
        sorted_meetings = sorted(meetings, key=lambda meeting: meeting.start)
        for before, after in zip(sorted_meetings, sorted_meetings[1:]):
            if before.end > after.start:
                return True
    return False


def is_liberal_course(course: dict[str, Any]) -> bool:
    return (
        str(course.get("course_group") or "") == "liberal"
        and str(course.get("completion_type") or "") == "교선"
    )


def format_vector(vector: dict[str, float]) -> str:
    return ", ".join(f"{feature}={vector.get(feature, 0.5):.3f}" for feature in FEATURES)


def format_candidate(candidate: Candidate) -> str:
    meetings = ", ".join(
        f"{meeting.day} {meeting.start // 60:02d}:{meeting.start % 60:02d}-{meeting.end // 60:02d}:{meeting.end % 60:02d}"
        for meeting in candidate.meetings
    )
    return (
        f"{candidate.course_name} / {candidate.professor} / {candidate.credits}학점 / "
        f"{candidate.course.get('completion_type')} / lecture_fit={candidate.lecture_fit:.4f} / "
        f"keyword_fit={candidate.keyword_fit:.4f} / reviews={candidate.profile.review_count} / {meetings}"
    )


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))


def keyword_score(text: str, positive: list[str], negative: list[str]) -> float:
    lowered = text.lower()
    pos = sum(lowered.count(word.lower()) for word in positive)
    neg = sum(lowered.count(word.lower()) for word in negative)
    if pos == 0 and neg == 0:
        return 0.5
    return max(0.0, min(1.0, sigmoid((pos - neg) / 2)))


def review_features(
    text: str,
    rating: float | None,
    semantic_features: dict[str, float] | None = None,
) -> dict[str, float]:
    keyword_features = {
        name: keyword_score(text, words["positive"], words["negative"])
        for name, words in FEATURE_KEYWORDS.items()
    }
    if semantic_features:
        features = {
            name: (semantic_features.get(name, 0.5) * 0.75) + (keyword_features[name] * 0.25)
            for name in FEATURES
        }
    else:
        features = keyword_features
    if rating is not None:
        rating_score = max(0.0, min(1.0, rating / 5))
        features["fun_relaxed"] = (features["fun_relaxed"] * 0.72) + (rating_score * 0.28)
        features["grade_generosity"] = (features["grade_generosity"] * 0.85) + (rating_score * 0.15)
    return features


def average_vectors(vectors: list[dict[str, float]]) -> dict[str, float]:
    if not vectors:
        return {feature: 0.5 for feature in FEATURES}
    return {
        feature: sum(vector.get(feature, 0.5) for vector in vectors) / len(vectors)
        for feature in FEATURES
    }


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def cosine(left: list[float], right: list[float]) -> float:
    left_norm = norm(left)
    right_norm = norm(right)
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot(left, right) / (left_norm * right_norm)


def user_vector(preferences: dict[str, Any]) -> tuple[list[float], list[float]]:
    target = [0.5] * len(FEATURES)
    weights = [0.0] * len(FEATURES)
    index = {feature: idx for idx, feature in enumerate(FEATURES)}

    for pref_key, options in PREFERENCE_TARGETS.items():
        value = str(preferences.get(pref_key) or "")
        if value == "unknown":
            continue
        if value not in options:
            continue
        feature, target_value = options[value]
        target[index[feature]] = target_value
        weights[index[feature]] = 1.0

    if not any(weights):
        weights = [1.0] * len(FEATURES)
    return target, weights


def lecture_fit(profile: LectureProfile, preferences: dict[str, Any]) -> float:
    target, weights = user_vector(preferences)
    lecture = [profile.feature_vector.get(feature, 0.5) for feature in FEATURES]
    weighted_target = [value * weight for value, weight in zip(target, weights)]
    weighted_lecture = [value * weight for value, weight in zip(lecture, weights)]
    direction = (cosine(weighted_target, weighted_lecture) + 1) / 2
    distance = sum(
        (1 - abs(target_value - lecture_value)) * weight
        for target_value, lecture_value, weight in zip(target, lecture, weights)
    ) / max(sum(weights), 1)
    return round((direction * 0.55) + (distance * 0.45), 4)


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[가-힣A-Za-z0-9+]{2,}", text)
        if len(token) <= 20
    ]


class TfidfIndex:
    def __init__(self, documents: dict[str, str]) -> None:
        self.documents = documents
        self.doc_count = len(documents)
        self.df: Counter[str] = Counter()
        self.vectors: dict[str, dict[str, float]] = {}
        self._build()

    def _build(self) -> None:
        tokenized = {doc_id: tokenize(text) for doc_id, text in self.documents.items()}
        for tokens in tokenized.values():
            self.df.update(set(tokens))
        self.vectors = {
            doc_id: self.vectorize_tokens(tokens)
            for doc_id, tokens in tokenized.items()
        }

    def idf(self, token: str) -> float:
        return math.log((1 + self.doc_count) / (1 + self.df.get(token, 0))) + 1

    def vectorize_tokens(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        if not counts:
            return {}
        max_count = max(counts.values())
        return {
            token: (count / max_count) * self.idf(token)
            for token, count in counts.items()
        }

    def vectorize(self, text: str) -> dict[str, float]:
        return self.vectorize_tokens(tokenize(text))

    @staticmethod
    def sparse_cosine(left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        common = set(left) & set(right)
        numerator = sum(left[token] * right[token] for token in common)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)

    def similarity(self, text: str, doc_id: str) -> float:
        return self.sparse_cosine(self.vectorize(text), self.vectors.get(doc_id, {}))


class RecommendationEngine:
    def __init__(
        self,
        course_path: Path = COURSE_PATH,
        review_path: Path = REVIEW_PATH,
        force_embedding_rebuild: bool = False,
    ) -> None:
        self.course_path = course_path
        self.review_path = review_path
        self.embedding_cache_path = EMBEDDING_CACHE_PATH
        self.embedding_extractor = SentenceEmbeddingFeatureExtractor()
        self.embedding_mode = "keyword"
        self.embedding_error: str | None = None
        self.force_embedding_rebuild = force_embedding_rebuild
        self.courses: list[dict[str, Any]] = []
        self.profiles: dict[tuple[str, str], LectureProfile] = {}
        self.fallback_profile = LectureProfile(
            course_name="",
            professor="",
            review_count=0,
            rating_avg=3.0,
            feature_vector={feature: 0.5 for feature in FEATURES},
        )
        self.keyword_index = TfidfIndex({})
        self.load()

    def load(self) -> None:
        self.courses = json.loads(self.course_path.read_text(encoding="utf-8"))
        self.profiles = self._load_profiles()
        documents = {}
        for course in self.courses:
            doc_id = str(course.get("id"))
            profile = self.profile_for(course)
            documents[doc_id] = " ".join(
                [
                    str(course.get("course_name") or ""),
                    str(course.get("liberal_area") or ""),
                    str(course.get("source_area") or ""),
                    profile.text,
                ],
            )
        self.keyword_index = TfidfIndex(documents)

    def _load_profiles(self) -> dict[tuple[str, str], LectureProfile]:
        if not self.review_path.exists():
            return {}

        workbook = openpyxl.load_workbook(self.review_path, read_only=True, data_only=True)
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        headers = [str(value) if value is not None else "" for value in next(rows)]
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for row in rows:
            record = {headers[index]: row[index] if index < len(row) else None for index in range(len(headers))}
            course_name = str(record.get("course_name") or "")
            professor = str(record.get("professor") or "")
            if not course_name or not professor:
                continue
            grouped[(normalize_key(course_name), normalize_key(professor))].append(record)

        if not self.force_embedding_rebuild:
            cached_profiles = self._load_embedding_cache()
            if cached_profiles is not None:
                self.embedding_mode = "embedding-cache"
                return cached_profiles

        semantic_vectors: list[dict[str, float]] | None = None
        flattened_records = [record for records in grouped.values() for record in records]
        if self.embedding_extractor.dependency_available:
            try:
                semantic_vectors = self.embedding_extractor.transform(
                    [str(record.get("review_text") or "") for record in flattened_records],
                )
                self.embedding_mode = "embedding"
            except Exception as exc:
                self.embedding_error = str(exc)
                self.embedding_mode = "keyword-fallback"
        else:
            self.embedding_error = "sentence-transformers is not installed"
            self.embedding_mode = "keyword-fallback"

        semantic_by_record = (
            {id(record): semantic_vectors[index] for index, record in enumerate(flattened_records)}
            if semantic_vectors is not None
            else {}
        )
        profiles: dict[tuple[str, str], LectureProfile] = {}
        for key, records in grouped.items():
            vectors = []
            ratings = []
            texts = []
            for record in records:
                text = str(record.get("review_text") or "")
                rating = None
                try:
                    rating = float(record.get("rating"))
                    ratings.append(rating)
                except (TypeError, ValueError):
                    pass
                texts.append(text)
                vectors.append(
                    review_features(
                        text,
                        rating,
                        semantic_by_record.get(id(record)),
                    ),
                )

            profiles[key] = LectureProfile(
                course_name=str(records[0].get("course_name") or ""),
                professor=str(records[0].get("professor") or ""),
                review_count=len(records),
                rating_avg=sum(ratings) / len(ratings) if ratings else 0.0,
                feature_vector=average_vectors(vectors),
                text="\n".join(texts[:40]),
                feature_source=self.embedding_mode,
            )
        if semantic_vectors is not None:
            self._save_embedding_cache(profiles)
        return profiles

    def _embedding_cache_metadata(self) -> dict[str, Any]:
        stat = self.review_path.stat()
        return {
            "source_size": stat.st_size,
            "source_mtime_ns": stat.st_mtime_ns,
            "model_name": self.embedding_extractor.model_name,
            "feature_version": 1,
        }

    def _load_embedding_cache(self) -> dict[tuple[str, str], LectureProfile] | None:
        if not self.embedding_cache_path.exists():
            return None
        try:
            payload = json.loads(self.embedding_cache_path.read_text(encoding="utf-8"))
            if payload.get("metadata") != self._embedding_cache_metadata():
                return None
            profiles: dict[tuple[str, str], LectureProfile] = {}
            for item in payload.get("profiles", []):
                key = (
                    normalize_key(str(item.get("course_name") or "")),
                    normalize_key(str(item.get("professor") or "")),
                )
                profiles[key] = LectureProfile(
                    course_name=str(item.get("course_name") or ""),
                    professor=str(item.get("professor") or ""),
                    review_count=int(item.get("review_count") or 0),
                    rating_avg=float(item.get("rating_avg") or 0.0),
                    feature_vector={
                        feature: float((item.get("feature_vector") or {}).get(feature, 0.5))
                        for feature in FEATURES
                    },
                    text=str(item.get("text") or ""),
                    feature_source="embedding-cache",
                )
            return profiles or None
        except (OSError, ValueError, TypeError):
            return None

    def _save_embedding_cache(
        self,
        profiles: dict[tuple[str, str], LectureProfile],
    ) -> None:
        self.embedding_cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": self._embedding_cache_metadata(),
            "profiles": [
                {
                    "course_name": profile.course_name,
                    "professor": profile.professor,
                    "review_count": profile.review_count,
                    "rating_avg": profile.rating_avg,
                    "feature_vector": profile.feature_vector,
                    "text": profile.text,
                }
                for profile in profiles.values()
            ],
        }
        self.embedding_cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def profile_for(self, course: dict[str, Any]) -> LectureProfile:
        course_key = normalize_key(str(course.get("course_name") or ""))
        professor_text = str(course.get("professor") or "")
        professor_names = [name.strip() for name in re.split(r"[\n,/]", professor_text) if name.strip()]

        for professor in professor_names or [professor_text]:
            key = (course_key, normalize_key(professor))
            if key in self.profiles:
                return self.profiles[key]

        return self.fallback_profile

    def candidates_for_course_name(self, course_name: str, preferences: dict[str, Any]) -> list[Candidate]:
        normalized = normalize_key(course_name)
        candidates = []
        for course in self.courses:
            if normalize_key(str(course.get("course_name") or "")) != normalized:
                continue
            meetings = parse_meetings(str(course.get("time_raw") or ""))
            if not meetings:
                continue
            profile = self.profile_for(course)
            candidates.append(
                Candidate(
                    course=course,
                    meetings=meetings,
                    profile=profile,
                    lecture_fit=lecture_fit(profile, preferences),
                ),
            )
        return sorted(candidates, key=lambda item: item.lecture_fit, reverse=True)[:8]

    def candidates_for_selected_course(self, selected_course: dict[str, str], preferences: dict[str, Any]) -> list[Candidate]:
        normalized = normalize_key(selected_course.get("course_name") or selected_course.get("name") or "")
        selected_type = str(selected_course.get("completion_type") or selected_course.get("completionType") or "")
        candidates = []
        for course in self.courses:
            if normalize_key(str(course.get("course_name") or "")) != normalized:
                continue
            if selected_type and str(course.get("completion_type") or "") != selected_type:
                continue
            meetings = parse_meetings(str(course.get("time_raw") or ""))
            if not meetings:
                continue
            profile = self.profile_for(course)
            candidates.append(
                Candidate(
                    course=course,
                    meetings=meetings,
                    profile=profile,
                    lecture_fit=lecture_fit(profile, preferences),
                ),
            )
        return sorted(candidates, key=lambda item: item.lecture_fit, reverse=True)[:8]

    def liberal_candidates(
        self,
        keywords: list[str],
        preferences: dict[str, Any],
        limit: int = 28,
    ) -> list[Candidate]:
        query = " ".join(keywords)
        candidates = []
        for course in self.courses:
            if not is_liberal_course(course):
                continue
            meetings = parse_meetings(str(course.get("time_raw") or ""))
            if not meetings:
                continue
            profile = self.profile_for(course)
            if keywords:
                keyword_fit = self.keyword_index.similarity(query, str(course.get("id")))
                direct_bonus = 0.0
                haystack = normalize_key(
                    " ".join(
                        [
                            str(course.get("course_name") or ""),
                            str(course.get("liberal_area") or ""),
                            str(course.get("source_area") or ""),
                        ],
                    ),
                )
                for keyword in keywords:
                    if normalize_key(keyword) in haystack:
                        direct_bonus += 0.16
                keyword_fit = min(1.0, keyword_fit + direct_bonus)
                if keyword_fit <= 0.02:
                    continue
            else:
                keyword_fit = 0.5
            candidates.append(
                Candidate(
                    course=course,
                    meetings=meetings,
                    profile=profile,
                    lecture_fit=lecture_fit(profile, preferences),
                    keyword_fit=keyword_fit,
                ),
            )
        if not keywords:
            random.shuffle(candidates)
            sampled = candidates[: max(limit * 3, limit)]
            return sorted(
                sampled,
                key=lambda item: (item.lecture_fit * 0.7) + (random.random() * 0.3),
                reverse=True,
            )[:limit]
        return sorted(
            candidates,
            key=lambda item: (item.keyword_fit * 0.55) + (item.lecture_fit * 0.45),
            reverse=True,
        )[:limit]

    @staticmethod
    def time_preference_score(items: list[Candidate], preference: str) -> float:
        if preference == "unknown" or not items:
            return 0.5
        starts = [meeting.start for item in items for meeting in item.meetings]
        if not starts:
            return 0.5
        average_start = sum(starts) / len(starts)
        if preference == "morning":
            return max(0.0, min(1.0, (15 * 60 - average_start) / (6 * 60)))
        if preference == "evening":
            return max(0.0, min(1.0, (average_start - 9 * 60) / (8 * 60)))
        return 0.5

    @staticmethod
    def day_off_score(items: list[Candidate], preference: str) -> float:
        if preference == "unknown" or not items:
            return 0.5
        used_days = {meeting.day for item in items for meeting in item.meetings}
        if preference == "compact":
            return max(0.0, min(1.0, (5 - len(used_days)) / 4))
        if preference == "spread":
            return max(0.0, min(1.0, len(used_days) / 5))
        return 0.5

    @staticmethod
    def credit_score(total_credits: int, target_credits: int) -> float:
        if target_credits <= 0:
            return 0.5
        if total_credits > target_credits:
            return 0.0
        return max(0.0, 1 - ((target_credits - total_credits) / max(target_credits, 1)))

    def score_plan(self, items: list[Candidate], preferences: dict[str, Any], target_credits: int) -> dict[str, float]:
        total_credits = sum(item.credits for item in items)
        lecture_avg = sum(item.lecture_fit for item in items) / max(len(items), 1)
        keyword_values = [item.keyword_fit for item in items if item.keyword_fit > 0]
        wants_liberal = str(preferences.get("liberalChoice") or "") == "yes" or bool(preferences.get("liberalKeywords"))
        has_liberal = any(is_liberal_course(item.course) for item in items)
        if keyword_values:
            keyword_avg = sum(keyword_values) / len(keyword_values)
        elif wants_liberal and not has_liberal:
            keyword_avg = 0.0
        else:
            keyword_avg = 0.5
        time_score = self.time_preference_score(items, str(preferences.get("timePreference") or "unknown"))
        day_score = self.day_off_score(items, str(preferences.get("dayOffPreference") or "unknown"))
        credit = self.credit_score(total_credits, target_credits)
        total = (
            lecture_avg * 0.32
            + time_score * 0.12
            + day_score * 0.12
            + keyword_avg * 0.09
            + credit * 0.35
        )
        return {
            "total": round(total, 4),
            "lecture": round(lecture_avg, 4),
            "time": round(time_score, 4),
            "dayOff": round(day_score, 4),
            "keyword": round(keyword_avg, 4),
            "credit": round(credit, 4),
        }

    def selected_course_names(self, selected_courses: list[Any]) -> list[str]:
        names = []
        for item in selected_courses:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                names.append(str(item.get("course_name") or item.get("name") or ""))
        return [name for name in dict.fromkeys(names) if name]

    def selected_course_specs(self, selected_courses: list[Any]) -> list[dict[str, str]]:
        specs = []
        for item in selected_courses:
            if isinstance(item, str):
                specs.append({"course_name": item})
            elif isinstance(item, dict):
                name = str(item.get("course_name") or item.get("name") or "")
                if not name:
                    continue
                specs.append(
                    {
                        "course_name": name,
                        "completion_type": str(item.get("completion_type") or item.get("completionType") or ""),
                    },
                )
        unique: dict[tuple[str, str], dict[str, str]] = {}
        for spec in specs:
            key = (normalize_key(spec.get("course_name", "")), spec.get("completion_type", ""))
            unique.setdefault(key, spec)
        return list(unique.values())

    def major_combinations(self, selected_specs: list[dict[str, str]], preferences: dict[str, Any]) -> list[list[Candidate]]:
        groups = [self.candidates_for_selected_course(spec, preferences) for spec in selected_specs]
        if any(not group for group in groups):
            return []
        combos = []
        for combo in product(*groups):
            items = list(combo)
            if len({item.course_name for item in items}) != len(items):
                continue
            if not has_conflict(items):
                combos.append(items)
        return combos[:500]

    def liberal_combinations(
        self,
        liberal_pool: list[Candidate],
        max_credits: int,
        base_items: list[Candidate],
    ) -> list[list[Candidate]]:
        if max_credits <= 0 or not liberal_pool:
            return [[]]

        results: list[list[Candidate]] = [[]]

        def backtrack(index: int, picked: list[Candidate], credits: int) -> None:
            if len(results) >= 140:
                return
            for cursor in range(index, len(liberal_pool)):
                candidate = liberal_pool[cursor]
                if credits + candidate.credits > max_credits:
                    continue
                candidate_names = {item.course_name for item in picked}
                if candidate.course_name in candidate_names:
                    continue
                next_items = [*base_items, *picked, candidate]
                if has_conflict(next_items):
                    continue
                new_picked = [*picked, candidate]
                results.append(new_picked)
                backtrack(cursor + 1, new_picked, credits + candidate.credits)

        backtrack(0, [], 0)
        return results

    def log_review_profiles(self, emit: Callable[[str], None]) -> None:
        emit("[3] 강의평 DB 파싱 결과")
        emit(f"    - review file: {self.review_path}")
        emit(f"    - course/professor profiles: {len(self.profiles)}")
        for index, profile in enumerate(self.profiles.values(), start=1):
            emit(
                "    "
                + f"[profile {index:03d}] {profile.course_name} / {profile.professor} "
                + f"reviews={profile.review_count} rating_avg={profile.rating_avg:.2f} "
                + f"source={profile.feature_source} "
                + f"vector=[{format_vector(profile.feature_vector)}]"
            )

    def recommend(self, payload: dict[str, Any], logger: Callable[[str], None] | None = None) -> dict[str, Any]:
        def emit(message: str = "") -> None:
            if logger:
                logger(message)

        preferences = dict(payload.get("preferences") or {})
        selected_courses = payload.get("selectedCourses") or []
        selected_names = self.selected_course_names(selected_courses)
        selected_specs = self.selected_course_specs(selected_courses)
        keywords = [
            str(keyword).strip()
            for keyword in payload.get("liberalKeywords") or preferences.get("liberalKeywords") or []
            if str(keyword).strip()
        ]
        preferences["liberalKeywords"] = keywords
        wants_liberal = str(preferences.get("liberalChoice") or "") == "yes" or bool(keywords)
        try:
            target_credits = int(preferences.get("targetCredits") or payload.get("targetCredits") or 18)
        except (TypeError, ValueError):
            target_credits = 18

        emit("=" * 88)
        emit("[SSU-TIME] POST /recommend 요청 수신")
        emit("[1] 선택 과목 확인")
        if selected_courses:
            for index, course in enumerate(selected_courses, start=1):
                if isinstance(course, dict):
                    emit(
                        "    "
                        + f"{index}. {course.get('course_name') or course.get('name')} / "
                        + f"{course.get('credits')}학점 / {course.get('completion_type')}"
                    )
                else:
                    emit(f"    {index}. {course}")
        else:
            emit("    - 선택 과목 없음")

        emit("[2] 사용자 니즈 확인")
        emit(f"    - 목표 학점: {target_credits}학점")
        emit(f"    - 시간대 선호: {preferences.get('timePreference') or 'unknown'}")
        emit(f"    - 공강 선호: {preferences.get('dayOffPreference') or 'unknown'}")
        if wants_liberal and keywords:
            emit(f"    - 교양 키워드: {', '.join(keywords)}")
        elif wants_liberal:
            emit("    - 교양 키워드: 없음 - 랜덤 교양 후보 사용")
        else:
            emit("    - 교양 키워드: 없음 - 교양 자동 추천 안 함")
        emit(
            "    - 개인 니즈: "
            + ", ".join(
                f"{key}={preferences.get(key)}"
                for key in [
                    "assignmentLoad",
                    "teamPresentation",
                    "examPreference",
                    "difficultyPreference",
                    "gradePreference",
                    "attendancePreference",
                    "classMood",
                ]
            )
        )

        emit("[DATA] 과목 DB 확인")
        emit(f"    - course file: {self.course_path}")
        emit(f"    - total course rows: {len(self.courses)}")
        emit(f"    - liberal auto-pool rows: {sum(1 for course in self.courses if is_liberal_course(course))}")
        self.log_review_profiles(emit)

        target_vector, target_weights = user_vector(preferences)
        emit("[4] 사용자 니즈 벡터 생성")
        emit(f"    - FEATURES: {FEATURES}")
        emit(f"    - U(target): {[round(value, 4) for value in target_vector]}")
        emit(f"    - W(weight): {[round(value, 4) for value in target_weights]}")
        emit("    - cosine(theta) = (U dot L) / (||U|| ||L||)")

        emit("[5] 전공 후보 생성")
        for spec in selected_specs:
            candidates = self.candidates_for_selected_course(spec, preferences)
            spec_label = spec.get("course_name", "")
            if spec.get("completion_type"):
                spec_label += f" / {spec.get('completion_type')}"
            emit(f"    - {spec_label}: {len(candidates)}개 후보")
            for candidate in candidates:
                emit(f"      * {format_candidate(candidate)}")

        major_combos = self.major_combinations(selected_specs, preferences) if selected_specs else [[]]
        emit(f"    - 시간 충돌 없는 전공 조합: {len(major_combos)}개")

        liberal_pool = self.liberal_candidates(keywords, preferences) if wants_liberal else []
        emit("[6] 교양 후보 생성")
        if wants_liberal and keywords:
            emit("    - 자동 추천은 course_group=liberal, completion_type=교선만 허용")
            emit(f"    - keyword query: {' '.join(keywords)}")
            emit(f"    - liberal candidates: {len(liberal_pool)}개")
            for candidate in liberal_pool:
                emit(f"      * {format_candidate(candidate)}")
        elif wants_liberal:
            emit("    - 키워드가 비어 있어 교양선택 후보를 랜덤으로 섞어 생성")
            emit("    - 자동 추천은 course_group=liberal, completion_type=교선만 허용")
            emit(f"    - liberal random candidates: {len(liberal_pool)}개")
            for candidate in liberal_pool:
                emit(f"      * {format_candidate(candidate)}")
        else:
            emit("    - 교양 키워드가 비어 있어 교양 후보를 생성하지 않음")

        plans = []

        emit("[7] 시간표 조합 계산")
        plan_log_count = 0
        for major_items in major_combos:
            major_credits = sum(item.credits for item in major_items)
            if major_credits > target_credits:
                emit(f"    - 전공 조합 제외: {major_credits}학점 > 목표 {target_credits}학점")
                continue
            remaining = target_credits - major_credits
            liberal_combos = self.liberal_combinations(liberal_pool, remaining, major_items)
            emit(
                "    - base major combo: "
                + f"{', '.join(item.course_name + '/' + item.professor for item in major_items) or '없음'} "
                + f"({major_credits}학점), remaining={remaining}학점, liberal_combo_count={len(liberal_combos)}"
            )
            for liberal_items in liberal_combos:
                items = [*major_items, *liberal_items]
                if not items:
                    continue
                if has_conflict(items):
                    emit(
                        "      x conflict 제외: "
                        + ", ".join(item.course_name + "/" + item.professor for item in items)
                    )
                    continue
                total_credits = sum(item.credits for item in items)
                if total_credits > target_credits:
                    emit(f"      x 학점 초과 제외: {total_credits}학점 > {target_credits}학점")
                    continue
                score = self.score_plan(items, preferences, target_credits)
                plans.append({"items": items, "score": score, "credits": total_credits})
                if plan_log_count < 300:
                    emit(
                        "      o 후보 채택: "
                        + f"{total_credits}학점 score={score['total']:.4f} "
                        + f"(lecture={score['lecture']:.4f}, credit={score['credit']:.4f}, "
                        + f"time={score['time']:.4f}, dayOff={score['dayOff']:.4f}, keyword={score['keyword']:.4f})"
                    )
                    for item in items:
                        emit(f"          - {format_candidate(item)}")
                elif plan_log_count == 300:
                    emit("      ... 후보 로그가 많아 이후 채택 후보는 개수만 집계")
                plan_log_count += 1

        unique: dict[str, dict[str, Any]] = {}
        for plan in sorted(plans, key=lambda item: item["score"]["total"], reverse=True):
            key = "|".join(sorted(item.id for item in plan["items"]))
            unique.setdefault(key, plan)
        plans = list(unique.values())
        emit("[8] 중복 제거 및 정렬")
        emit(f"    - accepted candidate plans: {len(plans)}개")

        if not plans:
            emit("[RESULT] 조건에 맞는 시간표 조합 없음")
            emit("=" * 88)
            return {
                "plans": [],
                "meta": {
                    "reason": "조건에 맞는 시간표 조합을 찾지 못했어요.",
                    "selectedCourseNames": selected_names,
                    "targetCredits": target_credits,
                    "liberalKeywords": keywords,
                    "liberalChoice": preferences.get("liberalChoice"),
                },
            }

        balanced = sorted(plans, key=lambda item: item["score"]["total"], reverse=True)
        compact = sorted(plans, key=lambda item: (item["score"]["dayOff"], item["score"]["total"]), reverse=True)
        time_first = sorted(plans, key=lambda item: (item["score"]["time"], item["score"]["total"]), reverse=True)
        picked = []
        for label, plan_type, source in [
            ("A", "balanced", balanced),
            ("B", "day-off", compact),
            ("C", "time-fit", time_first),
        ]:
            for plan in source:
                key = "|".join(sorted(item.id for item in plan["items"]))
                if key not in {entry["key"] for entry in picked}:
                    picked.append({"label": label, "type": plan_type, "key": key, **plan})
                    break

        emit("[9] 최종 A/B/C 시안")
        for plan in picked:
            emit(
                f"    - {plan['label']}안 type={plan['type']} credits={plan['credits']} "
                + f"score={plan['score']['total']:.4f}"
            )
            for item in plan["items"]:
                marker = "교양" if is_liberal_course(item.course) else "사용자 선택/전공"
                emit(f"        [{marker}] {format_candidate(item)}")
        emit("[SSU-TIME] 추천 결과 반환 완료")
        emit("=" * 88)

        return {
            "plans": [self.serialize_plan(plan) for plan in picked],
            "meta": {
                "selectedCourseNames": selected_names,
                "targetCredits": target_credits,
                "liberalKeywords": keywords,
                "liberalChoice": preferences.get("liberalChoice"),
                "candidatePlanCount": len(plans),
                "reviewProfileCount": len(self.profiles),
            },
        }

    def serialize_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        return {
            "label": plan["label"],
            "type": plan["type"],
            "credits": plan["credits"],
            "score": plan["score"],
            "courses": [self.serialize_candidate(item) for item in plan["items"]],
        }

    @staticmethod
    def serialize_candidate(item: Candidate) -> dict[str, Any]:
        return {
            "id": item.id,
            "courseName": item.course_name,
            "professor": item.professor,
            "credits": item.credits,
            "completionType": item.course.get("completion_type"),
            "courseGroup": item.group,
            "timeRaw": item.course.get("time_raw"),
            "meetings": [
                {
                    "day": meeting.day,
                    "start": meeting.start,
                    "end": meeting.end,
                    "startText": f"{meeting.start // 60:02d}:{meeting.start % 60:02d}",
                    "endText": f"{meeting.end // 60:02d}:{meeting.end % 60:02d}",
                }
                for meeting in item.meetings
            ],
            "lectureFit": item.lecture_fit,
            "keywordFit": round(item.keyword_fit, 4),
            "review": {
                "count": item.profile.review_count,
                "ratingAvg": round(item.profile.rating_avg, 2),
                "featureSource": item.profile.feature_source,
                "features": {
                    key: round(value, 4)
                    for key, value in item.profile.feature_vector.items()
                },
            },
        }
