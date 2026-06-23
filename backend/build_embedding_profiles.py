from __future__ import annotations

from backend.recommender import RecommendationEngine


def main() -> None:
    print("[SSU-TIME] 문장 임베딩 모델을 불러오고 강의평 프로필을 생성합니다.")
    engine = RecommendationEngine(force_embedding_rebuild=True)
    if engine.embedding_mode != "embedding":
        raise RuntimeError(
            "임베딩 프로필을 만들지 못했습니다: "
            + (engine.embedding_error or engine.embedding_mode),
        )
    print(f"[완료] 분석 방식: {engine.embedding_mode}")
    print(f"[완료] 강의 프로필: {len(engine.profiles)}개")
    print(f"[완료] 캐시 파일: {engine.embedding_cache_path}")


if __name__ == "__main__":
    main()
