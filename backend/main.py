from __future__ import annotations

from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.recommender import RecommendationEngine


class RecommendRequest(BaseModel):
    selectedCourses: list[Any] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    liberalKeywords: list[str] = Field(default_factory=list)
    targetCredits: int | None = None


engine = RecommendationEngine()
app = FastAPI(title="SSU-TIME API", version="0.1.0")
last_recommendation: dict[str, Any] = {}


def backend_log(message: str = "") -> None:
    print(message, flush=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "courseCount": len(engine.courses),
        "reviewProfileCount": len(engine.profiles),
        "embeddingMode": engine.embedding_mode,
        "embeddingModel": engine.embedding_extractor.model_name,
        "embeddingError": engine.embedding_error,
    }


@app.get("/courses")
def search_courses(q: str = "", limit: int = 10) -> dict[str, Any]:
    query = q.replace(" ", "").lower()
    results = []
    seen = set()

    for course in engine.courses:
        name = str(course.get("course_name") or "")
        key = (name, course.get("credits"), course.get("completion_type"))
        if key in seen:
            continue
        if query and query not in name.replace(" ", "").lower():
            continue
        seen.add(key)
        results.append(
            {
                "courseName": name,
                "credits": course.get("credits"),
                "completionType": course.get("completion_type"),
                "courseGroup": course.get("course_group"),
            },
        )
        if len(results) >= limit:
            break

    return {"courses": results}


@app.post("/recommend")
def recommend(request: RecommendRequest) -> dict[str, Any]:
    payload = request.model_dump()
    backend_log()
    backend_log(f"[REQUEST TIME] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    result = engine.recommend(payload, logger=backend_log)
    last_recommendation.clear()
    last_recommendation.update(
        {
            "at": datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
            "result": result,
        },
    )
    return result


@app.get("/debug/last-recommend")
def debug_last_recommend() -> dict[str, Any]:
    return last_recommendation or {"message": "아직 /recommend 요청이 없습니다."}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
