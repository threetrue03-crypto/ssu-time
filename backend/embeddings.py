from __future__ import annotations

import math
import os
from typing import Any

import numpy as np


DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

FEATURE_ANCHORS: dict[str, dict[str, list[str]]] = {
    "assignment_load": {
        "positive": [
            "과제가 매우 많고 매주 제출해야 하는 수업이다.",
            "숙제와 보고서 때문에 학업 부담이 큰 강의다.",
            "과제에 많은 시간과 노력이 필요한 수업이다.",
        ],
        "negative": [
            "과제가 거의 없어서 부담이 적은 수업이다.",
            "숙제나 보고서를 제출하지 않아도 되는 강의다.",
            "과제 부담이 매우 적고 편하게 들을 수 있다.",
        ],
    },
    "team_presentation": {
        "positive": [
            "팀 프로젝트와 조별 활동이 많은 수업이다.",
            "발표와 협업을 자주 해야 하는 강의다.",
            "팀플과 프레젠테이션이 성적에서 중요하다.",
        ],
        "negative": [
            "팀플과 발표가 전혀 없는 수업이다.",
            "조별 활동 없이 개인적으로 공부하는 강의다.",
            "발표나 프로젝트 부담이 거의 없다.",
        ],
    },
    "exam_load": {
        "positive": [
            "중간고사와 기말고사의 시험 부담이 큰 수업이다.",
            "시험 범위가 넓고 암기할 내용이 많다.",
            "시험 성적이 중요하고 시험 준비가 힘든 강의다.",
        ],
        "negative": [
            "시험이 없거나 시험 부담이 매우 적은 수업이다.",
            "중간고사와 기말고사를 보지 않는 강의다.",
            "시험 준비에 많은 시간을 들이지 않아도 된다.",
        ],
    },
    "difficulty": {
        "positive": [
            "내용이 어렵고 깊이 있는 공부가 필요한 수업이다.",
            "개념과 문제가 복잡해서 이해하기 어려운 강의다.",
            "학습량이 많고 난이도가 높은 수업이다.",
        ],
        "negative": [
            "내용이 쉽고 이해하기 편한 수업이다.",
            "초보자도 부담 없이 따라갈 수 있는 강의다.",
            "난이도가 낮고 공부하기 수월한 수업이다.",
        ],
    },
    "grade_generosity": {
        "positive": [
            "교수님이 학점을 후하게 주는 수업이다.",
            "노력한 만큼 좋은 성적을 받기 쉬운 강의다.",
            "A 학점을 비교적 잘 받을 수 있는 수업이다.",
        ],
        "negative": [
            "교수님이 학점을 매우 엄격하게 주는 수업이다.",
            "열심히 해도 좋은 성적을 받기 어려운 강의다.",
            "성적 기준이 까다롭고 학점을 짜게 준다.",
        ],
    },
    "attendance_strictness": {
        "positive": [
            "출석과 지각을 매우 엄격하게 관리하는 수업이다.",
            "결석하면 성적에서 큰 불이익을 받는 강의다.",
            "매시간 출석을 확인하고 출결 기준이 엄격하다.",
        ],
        "negative": [
            "출석과 지각을 크게 신경 쓰지 않는 수업이다.",
            "출결 관리가 느슨하고 결석 부담이 적은 강의다.",
            "출석 점수의 비중이 낮은 수업이다.",
        ],
    },
    "fun_relaxed": {
        "positive": [
            "교수님 설명이 재미있고 수업 분위기가 편안하다.",
            "흥미롭고 즐겁게 들을 수 있는 강의다.",
            "지루하지 않고 학생들과 소통이 잘 되는 수업이다.",
        ],
        "negative": [
            "수업이 지루하고 분위기가 딱딱하다.",
            "설명이 재미없고 듣는 동안 졸린 강의다.",
            "분위기가 불편하고 수업에 흥미를 느끼기 어렵다.",
        ],
    },
}


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class SentenceEmbeddingFeatureExtractor:
    """Map Korean review sentences to the seven SSU-TIME feature scores."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv(
            "SSU_TIME_EMBEDDING_MODEL",
            DEFAULT_MODEL_NAME,
        )
        self.enabled = os.getenv("SSU_TIME_USE_EMBEDDINGS", "1") != "0"
        self._model: Any = None
        self._positive_prototypes: np.ndarray | None = None
        self._negative_prototypes: np.ndarray | None = None
        self.error: str | None = None

    @property
    def dependency_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            return False
        return True

    @property
    def ready(self) -> bool:
        return self._model is not None and self._positive_prototypes is not None

    def load(self) -> bool:
        if self.ready:
            return True
        if not self.enabled:
            self.error = "disabled by SSU_TIME_USE_EMBEDDINGS=0"
            return False
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._build_prototypes()
            self.error = None
            return True
        except Exception as exc:  # Model download and runtime errors must not stop the API.
            self.error = f"{type(exc).__name__}: {exc}"
            self._model = None
            return False

    def _encode(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        encoded = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return np.asarray(encoded, dtype=np.float32)

    def _build_prototypes(self) -> None:
        positive_texts = [
            sentence
            for feature in FEATURE_ANCHORS.values()
            for sentence in feature["positive"]
        ]
        negative_texts = [
            sentence
            for feature in FEATURE_ANCHORS.values()
            for sentence in feature["negative"]
        ]
        anchor_count = len(next(iter(FEATURE_ANCHORS.values()))["positive"])
        positive = self._encode(positive_texts)
        negative = self._encode(negative_texts)
        dimension = positive.shape[1]
        positive = positive.reshape(len(FEATURE_ANCHORS), anchor_count, dimension).mean(axis=1)
        negative = negative.reshape(len(FEATURE_ANCHORS), anchor_count, dimension).mean(axis=1)
        self._positive_prototypes = _normalize_rows(positive)
        self._negative_prototypes = _normalize_rows(negative)

    def transform(self, texts: list[str], batch_size: int = 64) -> list[dict[str, float]]:
        if not texts:
            return []
        if not self.load():
            raise RuntimeError(self.error or "sentence embedding model is unavailable")

        review_vectors = self._encode(
            [text.strip() or "내용이 없는 강의평" for text in texts],
            batch_size=batch_size,
        )
        positive_similarity = review_vectors @ self._positive_prototypes.T
        negative_similarity = review_vectors @ self._negative_prototypes.T
        feature_names = list(FEATURE_ANCHORS)
        results: list[dict[str, float]] = []

        for row_index in range(len(texts)):
            vector: dict[str, float] = {}
            for feature_index, feature_name in enumerate(feature_names):
                positive = float(positive_similarity[row_index, feature_index])
                negative = float(negative_similarity[row_index, feature_index])
                margin = positive - negative
                raw_score = _sigmoid(margin * 10.0)

                # Weakly related reviews stay close to neutral instead of forcing a label.
                relevance = max(0.0, min(1.0, (max(positive, negative) - 0.15) / 0.45))
                score = 0.5 + ((raw_score - 0.5) * relevance)
                vector[feature_name] = round(max(0.0, min(1.0, score)), 6)
            results.append(vector)
        return results
