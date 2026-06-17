const root = document.documentElement;
const courseData = window.SSU_COURSES ?? [];

function syncViewportHeight() {
  const height = window.visualViewport?.height ?? window.innerHeight;
  root.style.setProperty("--app-height", `${height}px`);
}

syncViewportHeight();
window.addEventListener("resize", syncViewportHeight);
window.visualViewport?.addEventListener("resize", syncViewportHeight);
window.visualViewport?.addEventListener("scroll", syncViewportHeight);

const STAGE_TIMING = {
  introShowcase: 5100,
  demoStartDelay: 200,
  course: 2800,
  needs: 4600,
  result: 6200,
};

const timers = new Set();
let searchTimer = null;
let loadingTimer = null;
let loadingImageTimer = null;
let toastTimer = null;
let loadingStepsFinished = false;
let recommendationResult = null;
let recommendationError = null;
let recommendationPending = false;
const selectedCourses = new Map();
const userPreferences = {
  timePreference: "",
  dayOffPreference: "",
  targetCredits: "",
  assignmentLoad: "",
  teamPresentation: "",
  examPreference: "",
  difficultyPreference: "",
  gradePreference: "",
  attendancePreference: "",
  classMood: "",
  liberalChoice: "",
  liberalKeywords: [],
};

const API_BASE_URL =
  window.location.protocol === "file:"
    ? "http://127.0.0.1:8000"
    : `http://${window.location.hostname}:8000`;
const DAY_COLUMNS = {
  "월": 2,
  "화": 3,
  "수": 4,
  "목": 5,
  "금": 6,
};
const COURSE_COLORS = ["#b9e7fb", "#cbd8ff", "#bfe9e5", "#ffd0c9", "#ffe4a8", "#d8ccff", "#c8efd5"];
const LOADING_STEP_RANGES = [
  [0.8, 1.2],
  [2.0, 3.0],
  [2.0, 3.0],
  [1.0, 3.0],
  [2.0, 4.0],
];
const RESULT_START_MINUTES = 9 * 60;
const RESULT_END_MINUTES = 20 * 60;
const RESULT_SLOT_MINUTES = 30;
const RESULT_SLOT_COUNT = (RESULT_END_MINUTES - RESULT_START_MINUTES) / RESULT_SLOT_MINUTES;
const FEATURE_ORDER = [
  "assignment_load",
  "team_presentation",
  "exam_load",
  "difficulty",
  "grade_generosity",
  "attendance_strictness",
  "fun_relaxed",
];
const FEATURE_LABELS = {
  assignment_load: "과제량",
  team_presentation: "팀플/발표",
  exam_load: "시험 부담",
  difficulty: "난이도",
  grade_generosity: "학점 후함",
  attendance_strictness: "출석 엄격",
  fun_relaxed: "분위기",
};
const SCORE_LABELS = {
  lecture: "강의평",
  credit: "목표 학점",
  time: "시간대",
  dayOff: "공강",
  keyword: "교양 키워드",
};
const SCORE_WEIGHTS = {
  lecture: 0.32,
  credit: 0.35,
  time: 0.12,
  dayOff: 0.12,
  keyword: 0.09,
};
const PREFERENCE_VECTOR_TARGETS = {
  assignmentLoad: {
    ok: ["assignment_load", 0.85],
    low: ["assignment_load", 0.1],
  },
  teamPresentation: {
    ok: ["team_presentation", 0.85],
    avoid: ["team_presentation", 0.1],
  },
  examPreference: {
    exam: ["exam_load", 0.85],
    low: ["exam_load", 0.1],
  },
  difficultyPreference: {
    deep: ["difficulty", 0.82],
    easy: ["difficulty", 0.15],
  },
  gradePreference: {
    generous: ["grade_generosity", 0.9],
    content: ["grade_generosity", 0.45],
  },
  attendancePreference: {
    strict: ["attendance_strictness", 0.75],
    loose: ["attendance_strictness", 0.1],
  },
  classMood: {
    fun: ["fun_relaxed", 0.92],
    structured: ["fun_relaxed", 0.45],
  },
};
const PREFERENCE_LABELS = {
  timePreference: {
    title: "선호 시간대",
    morning: "아침형",
    evening: "저녁형",
    unknown: "상관없음",
  },
  dayOffPreference: {
    title: "공강 방식",
    compact: "공강 만들기",
    spread: "골고루 분산",
    unknown: "상관없음",
  },
  assignmentLoad: {
    title: "과제량",
    ok: "과제 괜찮음",
    low: "과제 적게",
    unknown: "상관없음",
  },
  teamPresentation: {
    title: "팀플/발표",
    ok: "있어도 괜찮음",
    avoid: "피하고 싶음",
    unknown: "상관없음",
  },
  examPreference: {
    title: "시험 방식",
    exam: "시험 중심 선호",
    low: "시험 부담 적게",
    unknown: "상관없음",
  },
  difficultyPreference: {
    title: "난이도",
    deep: "깊이 있는 수업",
    easy: "부담 적은 수업",
    unknown: "상관없음",
  },
  gradePreference: {
    title: "학점 기준",
    generous: "학점 후한 수업",
    content: "내용이 중요",
    unknown: "상관없음",
  },
  attendancePreference: {
    title: "출석 기준",
    strict: "엄격해도 괜찮음",
    loose: "부담 적게",
    unknown: "상관없음",
  },
  classMood: {
    title: "수업 분위기",
    fun: "재미있고 편한 수업",
    structured: "체계적인 수업",
    unknown: "상관없음",
  },
  liberalChoice: {
    title: "교양 자동 추천",
    yes: "네",
    no: "아니오",
  },
};
const PREFERENCE_RULES = {
  timePreference: {
    morning: "수업 시작 시간이 빠른 후보에 더 높은 시간대 점수를 줬어요.",
    evening: "오전보다 오후에 배치된 후보에 더 높은 시간대 점수를 줬어요.",
    unknown: "시간대는 추천 우선순위에서 크게 반영하지 않았어요.",
  },
  dayOffPreference: {
    compact: "수업이 적은 요일 수에 모일수록 공강 점수를 높였어요.",
    spread: "요일별로 수업이 고르게 퍼질수록 분산 점수를 높였어요.",
    unknown: "공강 여부는 다른 조건보다 약하게 반영했어요.",
  },
  assignmentLoad: {
    ok: "강의평에서 과제나 과제 피드백이 언급된 수업도 긍정 후보로 유지했어요.",
    low: "과제가 많다는 강의평이 많은 수업은 강의평 적합도를 낮췄어요.",
    unknown: "과제량은 강의평 판단에서 크게 가중하지 않았어요.",
  },
  teamPresentation: {
    ok: "팀플, 조모임, 발표가 있는 수업도 후보에서 제외하지 않았어요.",
    avoid: "팀플이나 발표 언급이 많은 수업은 사용자 니즈와 덜 맞게 봤어요.",
    unknown: "팀플/발표 여부는 추천 판단에서 크게 가중하지 않았어요.",
  },
  examPreference: {
    exam: "시험 중심 수업도 사용자의 선호와 맞는 후보로 봤어요.",
    low: "시험 부담, 중간/기말 언급이 많은 수업은 적합도를 낮췄어요.",
    unknown: "시험 방식은 강의평 판단에서 크게 가중하지 않았어요.",
  },
  difficultyPreference: {
    deep: "어렵거나 깊이 있다는 강의평이 있어도 긍정적으로 볼 수 있게 했어요.",
    easy: "난이도가 높고 빡세다는 강의평이 많은 수업은 덜 추천했어요.",
    unknown: "난이도는 다른 조건보다 약하게 반영했어요.",
  },
  gradePreference: {
    generous: "학점이 후하다는 강의평이 있는 수업을 더 유리하게 평가했어요.",
    content: "학점보다 수업 내용과 강의평 적합도를 더 우선했어요.",
    unknown: "학점 후함은 추천 판단에서 크게 가중하지 않았어요.",
  },
  attendancePreference: {
    strict: "출석이 엄격하다는 언급이 있어도 후보에서 제외하지 않았어요.",
    loose: "출석 부담이 크다는 강의평이 많은 수업은 덜 추천했어요.",
    unknown: "출석 기준은 추천 판단에서 크게 가중하지 않았어요.",
  },
  classMood: {
    fun: "재미있고 편하다는 강의평이 많은 수업을 더 좋게 평가했어요.",
    structured: "재미보다 체계적이고 안정적인 강의평을 더 우선했어요.",
    unknown: "수업 분위기는 다른 조건보다 약하게 반영했어요.",
  },
  liberalChoice: {
    yes: "관심 키워드와 관련된 교양 과목만 자동 후보로 넣었어요.",
    no: "사용자가 직접 선택한 과목만으로 시간표를 구성하고, 교양은 자동 추가하지 않았어요.",
  },
};

function wait(ms, callback) {
  const id = window.setTimeout(() => {
    timers.delete(id);
    callback();
  }, ms);
  timers.add(id);
}

function setStage(stage) {
  root.dataset.stage = stage;
}

function setView() {
  const viewByHash = {
    "#course": "course",
    "#needs": "needs",
    "#personal-needs": "personal-needs",
    "#loading": "loading",
    "#result": "result",
  };

  root.dataset.view = viewByHash[window.location.hash] ?? "start";

  if (root.dataset.view === "course") {
    wait(120, () => {
      document.querySelector(".course-search-input")?.focus();
    });
  }

  if (root.dataset.view === "needs") {
    updateNeedsSummary();
  }

  if (root.dataset.view === "loading") {
    startLoadingSequence();
  } else {
    stopLoadingSequence();
  }

  if (root.dataset.view === "result") {
    renderResultPlans(recommendationResult);
  }
}

function showDemo() {
  root.dataset.demoReady = "true";
}

function runDemoLoop() {
  setStage("course");

  wait(STAGE_TIMING.course, () => {
    setStage("needs");
  });

  wait(STAGE_TIMING.course + STAGE_TIMING.needs, () => {
    setStage("result");
  });

  wait(STAGE_TIMING.course + STAGE_TIMING.needs + STAGE_TIMING.result, () => {
    runDemoLoop();
  });
}

function lockGestures() {
  document.addEventListener("dragstart", (event) => event.preventDefault());
  document.addEventListener("gesturestart", (event) => event.preventDefault());
  document.addEventListener("gesturechange", (event) => event.preventDefault());
  document.addEventListener("gestureend", (event) => event.preventDefault());

  document.addEventListener(
    "wheel",
    (event) => {
      if (event.ctrlKey) {
        event.preventDefault();
      }
    },
    { passive: false },
  );
}

function normalize(value) {
  return value.replace(/\s/g, "").toLowerCase();
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };

    return entities[character];
  });
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function scorePercent(value) {
  return Math.round(Number(value || 0) * 100);
}

function scoreValue(plan, key) {
  return Number(plan?.score?.[key] ?? 0);
}

function getPlanScores(plan) {
  return Object.keys(SCORE_LABELS).map((key) => ({
    key,
    label: SCORE_LABELS[key],
    value: scoreValue(plan, key),
    percent: scorePercent(scoreValue(plan, key)),
    weight: SCORE_WEIGHTS[key],
  }));
}

function getTopScores(plan) {
  return [...getPlanScores(plan)].sort((left, right) => right.value - left.value);
}

function getUserVector() {
  const vectorMap = Object.fromEntries(FEATURE_ORDER.map((feature) => [feature, 0.5]));

  Object.entries(PREFERENCE_VECTOR_TARGETS).forEach(([preferenceKey, options]) => {
    const value = userPreferences[preferenceKey];
    if (!value || value === "unknown" || !options[value]) {
      return;
    }

    const [feature, target] = options[value];
    vectorMap[feature] = target;
  });

  return FEATURE_ORDER.map((feature) => Number(vectorMap[feature].toFixed(2)));
}

function getPlanLectureVector(plan) {
  const courses = plan?.courses ?? [];
  if (!courses.length) {
    return FEATURE_ORDER.map(() => 0.5);
  }

  return FEATURE_ORDER.map((feature) => {
    const sum = courses.reduce((total, course) => {
      return total + Number(course.review?.features?.[feature] ?? 0.5);
    }, 0);

    return Number((sum / courses.length).toFixed(2));
  });
}

function dotProduct(left, right) {
  return left.reduce((sum, value, index) => sum + (value * right[index]), 0);
}

function vectorNorm(vector) {
  return Math.sqrt(vector.reduce((sum, value) => sum + (value * value), 0));
}

function cosineScore(left, right) {
  const denominator = vectorNorm(left) * vectorNorm(right);
  if (!denominator) {
    return 0;
  }

  return dotProduct(left, right) / denominator;
}

function randomDuration(range) {
  const [min, max] = range;
  const seconds = Math.round((min + Math.random() * (max - min)) * 10) / 10;
  return seconds * 1000;
}

function getCourseKey(course) {
  return `${course.course_name}-${course.credits}-${course.completion_type}`;
}

function getCourseMatches(keyword) {
  const normalizedKeyword = normalize(keyword);

  if (!normalizedKeyword) {
    return [];
  }

  const uniqueCourses = new Map();

  for (const course of courseData) {
    if (!normalize(course.course_name).includes(normalizedKeyword)) {
      continue;
    }

    const key = getCourseKey(course);

    if (!uniqueCourses.has(key)) {
      uniqueCourses.set(key, course);
    }

    if (uniqueCourses.size === 5) {
      break;
    }
  }

  return [...uniqueCourses.values()];
}

function renderSuggestions(matches, keyword = "") {
  const suggestions = document.querySelector(".course-suggestions");

  if (!suggestions) {
    return;
  }

  if (!keyword.trim()) {
    suggestions.innerHTML = '<div class="suggestion-empty">과목명을 입력하면 검색 결과가 표시돼요.</div>';
    return;
  }

  if (!matches.length) {
    suggestions.innerHTML = '<div class="suggestion-empty">검색 결과가 없어요.</div>';
    return;
  }

  suggestions.innerHTML = matches
    .map((course) => {
      const key = getCourseKey(course);
      const isSelected = selectedCourses.has(key);

      return `
        <button
          class="suggestion-row${isSelected ? " is-selected" : ""}"
          type="button"
          data-course-key="${escapeHTML(key)}"
        >
          <span>
            <strong class="suggestion-name">${escapeHTML(course.course_name)}</strong>
            <span class="suggestion-meta">${escapeHTML(course.credits)}학점 · ${escapeHTML(course.completion_type)}</span>
          </span>
          <span class="suggestion-action" aria-hidden="true">${isSelected ? "✓" : "+"}</span>
        </button>
      `;
    })
    .join("");
}

function setCartOpen(isOpen) {
  const coursePage = document.querySelector(".course-page");
  const cartButton = document.querySelector(".course-cart-fab");

  if (!coursePage || !cartButton) {
    return;
  }

  coursePage.dataset.cartOpen = isOpen ? "true" : "false";
  cartButton.setAttribute("aria-expanded", String(isOpen));
}

function showToast() {
  const toast = document.querySelector(".app-toast");

  if (!toast) {
    return;
  }

  window.clearTimeout(toastTimer);
  toast.classList.remove("is-visible");
  void toast.offsetWidth;
  toast.classList.add("is-visible");

  toastTimer = window.setTimeout(() => {
    toast.classList.remove("is-visible");
  }, 1700);
}

function updateCart() {
  const count = selectedCourses.size;
  const credits = [...selectedCourses.values()].reduce((sum, course) => sum + Number(course.credits || 0), 0);
  const cartCount = document.querySelector(".cart-count");
  const cartSummary = document.querySelector(".cart-summary");
  const cartList = document.querySelector(".cart-list");
  const nextButton = document.querySelector(".cart-next-button");

  if (cartCount) {
    cartCount.textContent = count;
  }

  if (cartSummary) {
    cartSummary.textContent = count
      ? `${count}과목을 담았어요 (${credits}학점)`
      : "아직 담은 과목이 없어요";
  }

  if (nextButton) {
    nextButton.disabled = count === 0;
  }

  if (!cartList) {
    return;
  }

  if (count === 0) {
    cartList.innerHTML = '<div class="cart-empty">검색해서 듣고 싶은 과목을 담아주세요.</div>';
    return;
  }

  cartList.innerHTML = [...selectedCourses.values()]
    .map(
      (course) => `
        <div class="cart-item">
          <span>
            <strong>${escapeHTML(course.course_name)}</strong>
            <span>${escapeHTML(course.credits)}학점 · ${escapeHTML(course.completion_type)}</span>
          </span>
          <button class="cart-remove-button" type="button" data-course-key="${escapeHTML(getCourseKey(course))}" aria-label="${escapeHTML(course.course_name)} 제거">×</button>
        </div>
      `,
    )
    .join("");
}

function updateNeedsSummary() {
  const summary = document.querySelector(".needs-selected-summary");
  const count = selectedCourses.size;
  const credits = [...selectedCourses.values()].reduce((sum, course) => sum + Number(course.credits || 0), 0);

  if (summary) {
    summary.textContent = `선택 과목 ${count}개 · ${credits}학점`;
  }
}

function resetForCourseRestart() {
  selectedCourses.clear();
  Object.keys(userPreferences).forEach((key) => {
    userPreferences[key] = Array.isArray(userPreferences[key]) ? [] : "";
  });
  recommendationResult = null;
  recommendationError = null;
  recommendationPending = false;
  loadingStepsFinished = false;
  setCartOpen(false);
  updateCart();
  updateNeedsSummary();
  updateBasicSubmitState();
  updatePersonalSubmitState();
  updateLiberalKeywordState();
  updateKeywordPreview();
  document.querySelectorAll("[data-preference].is-selected").forEach((button) => {
    button.classList.remove("is-selected");
  });
  document.querySelectorAll(".target-credit-input, .keyword-input, .course-search-input").forEach((input) => {
    input.value = "";
  });
  renderSuggestions([], "");
  window.localStorage.removeItem("ssu-time:lastRecommendationPayload");
  window.localStorage.removeItem("ssu-time:lastRecommendationResult");
  window.localStorage.removeItem("ssu-time:lastRecommendationError");
}

function hasAnswered(keys) {
  return keys.every((key) => userPreferences[key]);
}

function updateBasicSubmitState() {
  const nextButton = document.querySelector(".basic-next-button");

  if (nextButton) {
    nextButton.disabled = !hasAnswered(["timePreference", "dayOffPreference", "targetCredits"]);
  }
}

function updatePersonalSubmitState() {
  const submitButton = document.querySelector(".needs-submit-button");

  if (submitButton) {
    submitButton.disabled = !hasAnswered([
      "assignmentLoad",
      "teamPresentation",
      "examPreference",
      "difficultyPreference",
      "gradePreference",
      "attendancePreference",
      "classMood",
      "liberalChoice",
    ]);
  }
}

function updateLiberalKeywordState() {
  const keywordCard = document.querySelector(".keyword-card");
  const keywordInput = document.querySelector(".keyword-input");
  const enabled = userPreferences.liberalChoice === "yes";

  if (keywordCard) {
    keywordCard.dataset.keywordEnabled = String(enabled);
  }

  if (keywordInput) {
    keywordInput.disabled = !enabled;
    if (!enabled) {
      keywordInput.value = "";
    }
  }

  if (!enabled) {
    userPreferences.liberalKeywords = [];
    updateKeywordPreview();
  }
}

function updateKeywordPreview() {
  const preview = document.querySelector(".keyword-preview");

  if (!preview) {
    return;
  }

  if (!userPreferences.liberalKeywords.length) {
    preview.innerHTML = "";
    return;
  }

  preview.innerHTML = userPreferences.liberalKeywords
    .map(
      (keyword) => `
        <button class="keyword-chip" type="button" data-keyword="${escapeHTML(keyword)}">
          ${escapeHTML(keyword)}
        </button>
      `,
    )
    .join("");
}

function buildRecommendationPayload() {
  const targetCredits = Number(userPreferences.targetCredits || 18);
  const liberalKeywords = userPreferences.liberalChoice === "yes"
    ? [...userPreferences.liberalKeywords]
    : [];

  return {
    selectedCourses: [...selectedCourses.values()].map((course) => ({
      course_name: course.course_name,
      credits: Number(course.credits || 0),
      completion_type: course.completion_type,
    })),
    preferences: {
      ...userPreferences,
      targetCredits,
      liberalKeywords,
    },
    liberalKeywords,
    targetCredits,
  };
}

async function requestRecommendation() {
  recommendationPending = true;
  recommendationResult = null;
  recommendationError = null;
  const payload = buildRecommendationPayload();
  window.localStorage.setItem("ssu-time:lastRecommendationPayload", JSON.stringify(payload));
  window.localStorage.removeItem("ssu-time:lastRecommendationResult");
  window.localStorage.removeItem("ssu-time:lastRecommendationError");

  try {
    const response = await fetch(`${API_BASE_URL}/recommend`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Recommendation request failed: ${response.status}`);
    }

    recommendationResult = await response.json();
    window.localStorage.setItem("ssu-time:lastRecommendationResult", JSON.stringify(recommendationResult));
    window.localStorage.setItem("ssu-time:lastRecommendationAt", new Date().toISOString());
    renderResultPlans(recommendationResult);
  } catch (error) {
    recommendationError = error;
    window.localStorage.setItem(
      "ssu-time:lastRecommendationError",
      JSON.stringify({
        message: error.message,
        at: new Date().toISOString(),
      }),
    );
  } finally {
    recommendationPending = false;
    completeLoadingWhenReady();
  }
}

function beginRecommendation() {
  loadingStepsFinished = false;
  recommendationResult = null;
  recommendationError = null;
  recommendationPending = true;
  window.location.hash = "#loading";
  requestRecommendation();
}

function bindCourseSearch() {
  const input = document.querySelector(".course-search-input");
  const suggestions = document.querySelector(".course-suggestions");
  const cartButton = document.querySelector(".course-cart-fab");
  const cartBackdrop = document.querySelector(".cart-backdrop");
  const cartList = document.querySelector(".cart-list");
  const nextButton = document.querySelector(".cart-next-button");

  if (!input) {
    return;
  }

  renderSuggestions([], "");
  updateCart();

  input.addEventListener("input", (event) => {
    window.clearTimeout(searchTimer);
    const keyword = event.target.value;

    searchTimer = window.setTimeout(() => {
      renderSuggestions(getCourseMatches(keyword), keyword);
    }, 100);
  });

  suggestions?.addEventListener("click", (event) => {
    const row = event.target.closest(".suggestion-row");

    if (!row) {
      return;
    }

    const course = getCourseMatches(input.value).find((item) => getCourseKey(item) === row.dataset.courseKey);

    if (!course) {
      return;
    }

    const key = getCourseKey(course);

    if (selectedCourses.has(key)) {
      selectedCourses.delete(key);
    } else {
      selectedCourses.set(key, course);
      showToast();
    }

    renderSuggestions(getCourseMatches(input.value), input.value);
    updateCart();
    updateNeedsSummary();
  });

  cartButton?.addEventListener("click", () => {
    setCartOpen(true);
  });

  cartBackdrop?.addEventListener("click", () => {
    setCartOpen(false);
  });

  cartList?.addEventListener("click", (event) => {
    const removeButton = event.target.closest(".cart-remove-button");

    if (!removeButton) {
      return;
    }

    selectedCourses.delete(removeButton.dataset.courseKey);
    renderSuggestions(getCourseMatches(input.value), input.value);
    updateCart();
    updateNeedsSummary();
  });

  nextButton?.addEventListener("click", () => {
    if (!selectedCourses.size) {
      return;
    }

    setCartOpen(false);
    window.location.hash = "#needs";
  });
}

function bindNeedsForm() {
  const forms = document.querySelectorAll(".needs-form");
  const keywordInput = document.querySelector(".keyword-input");
  const targetCreditInput = document.querySelector(".target-credit-input");
  const basicNextButton = document.querySelector(".basic-next-button");
  const submitButton = document.querySelector(".needs-submit-button");

  if (!forms.length) {
    return;
  }

  forms.forEach((form) => {
    form.addEventListener("click", (event) => {
      const option = event.target.closest("[data-preference]");

      if (!option) {
        return;
      }

      const { preference, value } = option.dataset;
      userPreferences[preference] = value;

      form
        .querySelectorAll(`[data-preference="${preference}"]`)
        .forEach((button) => {
          button.classList.toggle("is-selected", button === option);
        });

      if (preference === "targetCredits" && targetCreditInput) {
        targetCreditInput.value = "";
      }

      if (preference === "liberalChoice") {
        updateLiberalKeywordState();
      }

      updateBasicSubmitState();
      updatePersonalSubmitState();
    });
  });

  targetCreditInput?.addEventListener("input", (event) => {
    const value = Number(event.target.value);
    userPreferences.targetCredits = Number.isFinite(value) && value > 0 && value <= 24
      ? String(value)
      : "";

    document
      .querySelectorAll('[data-preference="targetCredits"]')
      .forEach((button) => {
        button.classList.remove("is-selected");
      });

    updateBasicSubmitState();
  });

  keywordInput?.addEventListener("keydown", (event) => {
    if (keywordInput.disabled || userPreferences.liberalChoice !== "yes") {
      return;
    }

    if (event.key !== "Enter") {
      return;
    }

    event.preventDefault();
    const keyword = event.target.value.trim();

    if (!keyword || userPreferences.liberalKeywords.includes(keyword)) {
      event.target.value = "";
      return;
    }

    userPreferences.liberalKeywords = [...userPreferences.liberalKeywords, keyword].slice(0, 5);
    event.target.value = "";
    updateKeywordPreview();
  });

  document.querySelector(".keyword-preview")?.addEventListener("click", (event) => {
    const chip = event.target.closest(".keyword-chip");

    if (!chip) {
      return;
    }

    userPreferences.liberalKeywords = userPreferences.liberalKeywords.filter(
      (keyword) => keyword !== chip.dataset.keyword,
    );
    updateKeywordPreview();
  });

  basicNextButton?.addEventListener("click", () => {
    if (basicNextButton.disabled) {
      return;
    }

    window.location.hash = "#personal-needs";
  });

  submitButton?.addEventListener("click", () => {
    if (submitButton.disabled) {
      return;
    }

    beginRecommendation();
  });

  updateNeedsSummary();
  updateLiberalKeywordState();
  updateBasicSubmitState();
  updatePersonalSubmitState();
}

function getPlanTitle(type) {
  const titles = {
    balanced: "균형형 추천",
    "day-off": "공강형 추천",
    "time-fit": "시간대 맞춤 추천",
  };

  return titles[type] ?? "맞춤 추천";
}

function getPlanDescription(plan) {
  const scores = getTopScores(plan);
  const best = scores[0];
  const weak = scores[scores.length - 1];
  const targetCredits = Number(recommendationResult?.meta?.targetCredits ?? userPreferences.targetCredits ?? 18);
  const creditGap = targetCredits - Number(plan.credits || 0);

  if (creditGap > 0 && scoreValue(plan, "credit") < 0.85) {
    return `${best.label} 점수가 높지만, 시간 충돌을 피하느라 목표보다 ${creditGap}학점 적게 구성했어요.`;
  }

  if (weak.value < 0.4) {
    return `${best.label}을 우선한 시안이에요. 대신 ${weak.label} 점수는 낮아 이 부분은 양보했어요.`;
  }

  return `${best.label}과 ${scores[1].label}이 잘 맞아 전체 적합도가 높은 시안이에요.`;
}

function getReasonItems(plan) {
  const scores = getTopScores(plan);
  const targetCredits = Number(recommendationResult?.meta?.targetCredits ?? userPreferences.targetCredits ?? 18);
  const creditGap = targetCredits - Number(plan.credits || 0);
  const items = [
    {
      title: `${scores[0].label} 점수가 가장 높아요`,
      body: `${scores[0].percent}점으로 이 시안의 가장 강한 추천 근거예요.`,
    },
    {
      title: `${scores[1].label}도 잘 맞아요`,
      body: `${scores[1].percent}점으로 사용자의 조건과 비교적 잘 맞았어요.`,
    },
  ];
  const weak = scores[scores.length - 1];

  if (creditGap > 0) {
    items.push({
      title: `목표보다 ${creditGap}학점 적어요`,
      body: "시간 충돌을 피하고 강의평 적합도를 유지하기 위해 학점을 무리하게 채우지 않았어요.",
    });
  } else if (weak.value < 0.45) {
    items.push({
      title: `${weak.label}은 조금 아쉬워요`,
      body: `${weak.percent}점이라 이 시안에서는 다른 조건을 더 우선했어요.`,
    });
  } else {
    items.push({
      title: "조건이 고르게 맞았어요",
      body: "강의평, 학점, 시간 조건 사이의 균형이 크게 무너지지 않았어요.",
    });
  }

  return items;
}

function getPreferenceAnswer(preferenceKey) {
  const value = userPreferences[preferenceKey] || "unknown";
  return PREFERENCE_LABELS[preferenceKey]?.[value] ?? value;
}

function getPreferenceRule(preferenceKey) {
  const value = userPreferences[preferenceKey] || "unknown";
  return PREFERENCE_RULES[preferenceKey]?.[value] ?? "이 항목은 추천 판단에 보조적으로 반영했어요.";
}

function getDecisionRows(plan) {
  const targetCredits = Number(recommendationResult?.meta?.targetCredits ?? userPreferences.targetCredits ?? 18);
  const keywords = userPreferences.liberalKeywords ?? [];
  const actualCredits = Number(plan?.credits ?? 0);
  const creditGap = targetCredits - actualCredits;
  const liberalCourses = (plan?.courses ?? []).filter((course) => course.courseGroup === "liberal");

  return [
    {
      group: "기본 정보",
      title: "목표 학점",
      answer: `${targetCredits}학점`,
      rule: creditGap > 0
        ? `목표 학점을 넘기지 않도록 제한했고, 시간 충돌 때문에 ${actualCredits}학점까지만 구성했어요.`
        : `목표 학점을 넘기지 않는 범위에서 ${actualCredits}학점으로 구성했어요.`,
    },
    {
      group: "기본 정보",
      title: "선호 시간대",
      answer: getPreferenceAnswer("timePreference"),
      rule: getPreferenceRule("timePreference"),
    },
    {
      group: "기본 정보",
      title: "공강 방식",
      answer: getPreferenceAnswer("dayOffPreference"),
      rule: getPreferenceRule("dayOffPreference"),
    },
    {
      group: "기본 정보",
      title: "교양 자동 추천",
      answer: getPreferenceAnswer("liberalChoice"),
      rule: userPreferences.liberalChoice === "yes"
        ? keywords.length
          ? `키워드(${keywords.join(", ")})와 강의명/강의평이 가까운 교양만 자동 후보로 넣었고, 이 시안에는 교양 ${liberalCourses.length}개가 들어갔어요.`
          : `키워드를 입력하지 않아서 교양선택 과목 후보를 랜덤으로 섞고, 시간 충돌과 목표 학점에 맞는 교양 ${liberalCourses.length}개를 넣었어요.`
        : "교양 자동 추천을 끄기로 했기 때문에 사용자가 직접 선택한 과목만으로 시간표를 구성했어요.",
    },
    ...[
      "assignmentLoad",
      "teamPresentation",
      "examPreference",
      "difficultyPreference",
      "gradePreference",
      "attendancePreference",
      "classMood",
    ].map((key) => ({
      group: "개인 니즈",
      title: PREFERENCE_LABELS[key].title,
      answer: getPreferenceAnswer(key),
      rule: getPreferenceRule(key),
    })),
  ];
}

function renderDecisionRows(plan) {
  const rows = getDecisionRows(plan);
  let currentGroup = "";

  return rows
    .map((row) => {
      const groupTitle = row.group !== currentGroup
        ? `<h4>${escapeHTML(row.group)}</h4>`
        : "";
      currentGroup = row.group;

      return `
        ${groupTitle}
        <article class="decision-row">
          <div>
            <span>${escapeHTML(row.title)}</span>
            <strong>${escapeHTML(row.answer)}</strong>
          </div>
          <p>${escapeHTML(row.rule)}</p>
        </article>
      `;
    })
    .join("");
}

function getTimeTableShell(label) {
  const days = ["월", "화", "수", "목", "금"]
    .map((day) => `<div class="result-day-head">${day}</div>`)
    .join("");
  const times = Array.from({ length: 12 }, (_, index) => 9 + index)
    .map((hour) => {
      const row = 2 + ((hour - 9) * 2);
      return `<div class="result-time" style="grid-row: ${row};">${String(hour).padStart(2, "0")}</div>`;
    })
    .join("");

  return `
    <div class="result-timetable" aria-label="${escapeHTML(label)} 시간표">
      <div class="result-time-head"></div>
      ${days}
      ${times}
      __COURSE_BLOCKS__
    </div>
  `;
}

function getMeetingLocation(course, meeting) {
  const timeRaw = String(course.timeRaw || "");
  const lines = timeRaw.split(/\n+/);
  const targetTime = `${meeting.startText}-${meeting.endText}`;
  const line = lines.find((item) => item.includes(meeting.day) && item.includes(targetTime)) ?? "";
  const location = line.match(/\(([^)]+)\)/)?.[1] ?? "";

  if (!location) {
    return "";
  }

  const parts = location.split("-");
  return parts.length > 1 ? parts.slice(0, -1).join("-") : location;
}

function getCourseBlocks(plan) {
  const occupied = new Map();

  return (plan.courses ?? [])
    .flatMap((course, courseIndex) => {
      const color = COURSE_COLORS[courseIndex % COURSE_COLORS.length];

      return (course.meetings ?? [])
        .filter((meeting) => DAY_COLUMNS[meeting.day])
        .map((meeting) => {
          if (Number(meeting.start || 0) >= RESULT_END_MINUTES || Number(meeting.end || 0) <= RESULT_START_MINUTES) {
            return "";
          }

          const visibleStart = Math.max(Number(meeting.start || 0), RESULT_START_MINUTES);
          const visibleEnd = Math.min(Number(meeting.end || 0), RESULT_END_MINUTES);
          const rowStart = clamp(Math.floor((visibleStart - RESULT_START_MINUTES) / RESULT_SLOT_MINUTES) + 2, 2, RESULT_SLOT_COUNT + 1);
          const rowEnd = clamp(Math.ceil((visibleEnd - RESULT_START_MINUTES) / RESULT_SLOT_MINUTES) + 2, rowStart + 1, RESULT_SLOT_COUNT + 2);
          const dayKey = meeting.day;
          const slots = Array.from({ length: rowEnd - rowStart }, (_, index) => `${dayKey}-${rowStart + index}`);
          const hasOverlap = slots.some((slot) => occupied.has(slot));

          if (hasOverlap) {
            return "";
          }

          slots.forEach((slot) => occupied.set(slot, true));

          const professor = course.professor ? String(course.professor) : "";
          const location = getMeetingLocation(course, meeting);
          const title = [course.courseName, professor, location].filter(Boolean).join(" · ");

          return `
            <div
              class="result-course"
              style="grid-column: ${DAY_COLUMNS[meeting.day]}; grid-row: ${rowStart} / ${rowEnd}; background: ${color};"
              title="${escapeHTML(title)}"
            >
              <strong>${escapeHTML(course.courseName)}</strong>
              ${professor ? `<span>${escapeHTML(professor)}</span>` : ""}
              ${location ? `<small>${escapeHTML(location)}</small>` : ""}
            </div>
          `;
        });
    })
    .join("");
}

function renderResultPlans(data) {
  const tabs = document.querySelector(".result-tabs");
  const plans = document.querySelector(".result-plans");
  const explainButton = document.querySelector(".result-explain-button");

  if (!tabs || !plans) {
    return;
  }

  if (recommendationError) {
    if (explainButton) {
      explainButton.disabled = true;
    }
    tabs.innerHTML = "";
    plans.innerHTML = `
      <div class="result-empty">
        <strong>추천 서버에 연결하지 못했어요.</strong>
        <p>백엔드 서버를 켠 뒤 다시 추천 시간표를 받아보세요.</p>
      </div>
    `;
    return;
  }

  if (!data?.plans?.length) {
    if (explainButton) {
      explainButton.disabled = true;
    }
    tabs.innerHTML = "";
    plans.innerHTML = `
      <div class="result-empty">
        <strong>조건에 맞는 시간표를 찾지 못했어요.</strong>
        <p>선택한 과목이나 목표 학점을 조금 조정해보면 좋아요.</p>
      </div>
    `;
    return;
  }

  if (explainButton) {
    explainButton.disabled = false;
  }

  const planSlots = ["A", "B", "C"];
  const planByLabel = new Map(
    data.plans.map((plan) => [String(plan.label || "").toUpperCase(), plan]),
  );
  const firstAvailableLabel = planSlots.find((label) => planByLabel.has(label)) || "A";
  const missingLabels = planSlots.filter((label) => !planByLabel.has(label));

  tabs.innerHTML = planSlots
    .map((label) => {
      const plan = planByLabel.get(label);
      const isActive = label === firstAvailableLabel && Boolean(plan);
      const isUnavailable = !plan;

      return `
        <button
          class="${isActive ? "is-active" : ""} ${isUnavailable ? "is-unavailable" : ""}"
          type="button"
          role="tab"
          aria-selected="${isActive}"
          data-result-tab="${escapeHTML(label.toLowerCase())}"
          ${isUnavailable ? "disabled" : ""}
        >
          ${escapeHTML(label)}안${isUnavailable ? " 부족" : ""}
        </button>
      `;
    })
    .join("");

  const shortageNote = missingLabels.length
    ? `
      <div class="result-shortage-note">
        <strong>조건에 맞는 다른 시안이 부족해요.</strong>
        <p>${escapeHTML(missingLabels.join(", "))}안은 선택 과목, 목표 학점, 시간 충돌 조건을 지키면 새 조합을 만들기 어려워서 표시하지 않았어요.</p>
      </div>
    `
    : "";

  plans.innerHTML = planSlots
    .map((label) => {
      const plan = planByLabel.get(label);
      const slotTabId = label.toLowerCase();

      if (!plan) {
        return `
          <article class="result-plan result-plan-unavailable" data-result-plan="${escapeHTML(slotTabId)}">
            <div class="result-empty result-empty-compact">
              <strong>조건에 맞는 다른 시안이 부족해요.</strong>
              <p>비슷한 시간표를 억지로 보여주지 않고, 만들 수 있는 시안만 보여드릴게요.</p>
            </div>
          </article>
        `;
      }

      const tabId = plan.label.toLowerCase();
      const timetable = getTimeTableShell(plan.label).replace("__COURSE_BLOCKS__", getCourseBlocks(plan));
      const score = plan.score ?? {};

      return `
        <article class="result-plan ${label === firstAvailableLabel ? "is-active" : ""}" data-result-plan="${escapeHTML(tabId)}">
          <div class="result-plan-summary">
            <span>${escapeHTML(getPlanTitle(plan.type))}</span>
            <strong>${escapeHTML(plan.credits)}학점 · 적합도 ${scorePercent(score.total)}점</strong>
            <p>${escapeHTML(getPlanDescription(plan))}</p>
          </div>

          ${timetable}
          ${label === firstAvailableLabel ? shortageNote : ""}
        </article>
      `;
    })
    .join("");
}

function getCurrentPlan() {
  const activePlan = document.querySelector(".result-plan.is-active");
  const label = activePlan?.dataset.resultPlan;

  if (!label) {
    return recommendationResult?.plans?.[0] ?? null;
  }

  return recommendationResult?.plans?.find((plan) => plan.label.toLowerCase() === label) ?? null;
}

function renderScoreBars(plan) {
  return getPlanScores(plan)
    .map((score) => `
      <div class="explain-score-row">
        <div>
          <strong>${escapeHTML(score.label)}</strong>
          <span>${score.percent}점</span>
        </div>
        <i><b style="width: ${clamp(score.percent, 0, 100)}%;"></b></i>
      </div>
    `)
    .join("");
}

function renderReasonItems(plan) {
  return getReasonItems(plan)
    .map((item) => `
      <li>
        <strong>${escapeHTML(item.title)}</strong>
        <p>${escapeHTML(item.body)}</p>
      </li>
    `)
    .join("");
}

function openExplainSheet() {
  const plan = getCurrentPlan();
  const body = document.querySelector(".explain-sheet-body");

  if (!plan || !body) {
    return;
  }

  body.innerHTML = `
    <div class="explain-summary">
      <span>${escapeHTML(plan.label)}안 · ${escapeHTML(getPlanTitle(plan.type))}</span>
      <h3>${escapeHTML(getPlanDescription(plan))}</h3>
    </div>
    <ol class="explain-reasons">
      ${renderReasonItems(plan)}
    </ol>
    <section class="decision-section">
      <h3>내 답변이 이렇게 반영됐어요</h3>
      ${renderDecisionRows(plan)}
    </section>
    <section class="explain-score-section">
      <h3>계산된 적합도</h3>
      <p>아래 점수는 위 판단 기준을 반영해 백엔드에서 계산한 결과예요.</p>
      <div class="explain-scores">
        ${renderScoreBars(plan)}
      </div>
    </section>
    <button class="detail-open-button" type="button">
      계산 과정 자세히 보기
    </button>
  `;

  root.dataset.explainOpen = "true";
}

function closeExplainSheet() {
  root.dataset.explainOpen = "false";
}

function renderVector(vector) {
  return `
    <div class="vector-row">
      ${vector.map((value) => `<span>${value.toFixed(2)}</span>`).join("")}
    </div>
  `;
}

function renderFeatureLabels() {
  return `
    <div class="vector-label-row">
      ${FEATURE_ORDER.map((feature) => `<span>${escapeHTML(FEATURE_LABELS[feature])}</span>`).join("")}
    </div>
  `;
}

function renderWeightedSum(plan) {
  return getPlanScores(plan)
    .map((score) => {
      const contribution = score.value * score.weight;
      return `
        <div class="formula-line">
          <span>${escapeHTML(score.label)}</span>
          <code>${score.value.toFixed(2)} × ${score.weight.toFixed(2)} = ${contribution.toFixed(3)}</code>
        </div>
      `;
    })
    .join("");
}

function renderCourseReasons(plan) {
  return (plan.courses ?? [])
    .map((course) => {
      const isLiberal = course.courseGroup === "liberal";
      const keywordText = isLiberal && course.keywordFit > 0
        ? `교양 키워드 적합도 ${scorePercent(course.keywordFit)}점`
        : "사용자가 선택한 과목 후보";
      return `
        <li>
          <strong>${escapeHTML(course.courseName)}</strong>
          <span>${escapeHTML(course.professor || "교수 정보 없음")} · ${escapeHTML(course.completionType || "")} · ${course.credits}학점</span>
          <p>강의평 적합도 ${scorePercent(course.lectureFit)}점 · ${escapeHTML(keywordText)}</p>
        </li>
      `;
    })
    .join("");
}

function openDetailModal() {
  const plan = getCurrentPlan();
  const body = document.querySelector(".detail-body");

  if (!plan || !body) {
    return;
  }

  body.innerHTML = `
    <section class="detail-section">
      <span class="detail-kicker">questionnaire matrix</span>
      <h3>질문지 답변 → 추천 판단 기준</h3>
      <div class="decision-matrix">
        ${renderDecisionRows(plan)}
      </div>
    </section>

    <section class="detail-section">
      <span class="detail-kicker">linear algebra</span>
      <h3>강의평 매칭 방식</h3>
      <pre><code>사용자 답변 → 니즈 벡터 U
강의평 분석 → 강의 벡터 L
cos(theta) = (U · L) / (||U|| ||L||)

두 벡터의 방향이 가까울수록
강의평 적합도가 높아져요.</code></pre>
    </section>

    <section class="detail-section">
      <span class="detail-kicker">weighted sum</span>
      <h3>최종 점수 가중합</h3>
      ${renderWeightedSum(plan)}
      <div class="formula-total">총합 = ${scoreValue(plan, "total").toFixed(3)} → ${scorePercent(scoreValue(plan, "total"))}점</div>
    </section>

    <section class="detail-section">
      <span class="detail-kicker">courses</span>
      <h3>과목별 근거</h3>
      <ol class="course-reason-list">
        ${renderCourseReasons(plan)}
      </ol>
    </section>
  `;

  root.dataset.explainOpen = "false";
  root.dataset.detailOpen = "true";
}

function closeDetailModal() {
  root.dataset.detailOpen = "false";
}

function bindResultTabs() {
  document.querySelector(".result-tabs")?.addEventListener("click", (event) => {
    const tab = event.target.closest("[data-result-tab]");

    if (!tab) {
      return;
    }

    if (tab.disabled) {
      return;
    }

    const tabs = document.querySelectorAll("[data-result-tab]");
    const plans = document.querySelectorAll("[data-result-plan]");
    const target = tab.dataset.resultTab;

    tabs.forEach((item) => {
      const isActive = item === tab;
      item.classList.toggle("is-active", isActive);
      item.setAttribute("aria-selected", String(isActive));
    });

    plans.forEach((plan) => {
      plan.classList.toggle("is-active", plan.dataset.resultPlan === target);
    });
  });
}

function bindExplanationUI() {
  document.querySelector(".result-explain-button")?.addEventListener("click", () => {
    openExplainSheet();
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-explain-close]")) {
      closeExplainSheet();
    }

    if (event.target.closest(".detail-open-button")) {
      openDetailModal();
    }

    if (event.target.closest("[data-detail-close]")) {
      closeDetailModal();
    }
  });
}

function bindResultRestart() {
  document.querySelector(".result-restart")?.addEventListener("click", () => {
    resetForCourseRestart();
  });
}

function stopLoadingSequence() {
  if (loadingTimer) {
    window.clearTimeout(loadingTimer);
    loadingTimer = null;
  }

  if (loadingImageTimer) {
    window.clearInterval(loadingImageTimer);
    loadingImageTimer = null;
  }

  root.dataset.loadingComplete = "false";
}

function setLoadingStep(step) {
  root.dataset.loadingStep = String(step);
  document.querySelectorAll("[data-loading-step]").forEach((item) => {
    const itemStep = Number(item.dataset.loadingStep);
    item.classList.toggle("is-done", itemStep < step);
    item.classList.toggle("is-active", itemStep === step);
  });
}

function setLoadingCopy(isComplete) {
  const title = document.querySelector("#loading-title");
  const description = document.querySelector(".loading-copy p:last-child");

  if (recommendationError) {
    if (title) {
      title.textContent = "시간표 생성에 실패했어요";
    }

    if (description) {
      description.textContent = "추천 서버가 켜져 있는지 확인해주세요";
    }

    return;
  }

  if (title) {
    title.textContent = isComplete
      ? "시간표가 준비되었어요"
      : "시간표를 맞춰보는 중이에요";
  }

  if (description) {
    description.textContent = isComplete
      ? "마음에 드는 시간표를 확인해보세요"
      : "강의평과 취향을 함께 펼쳐보고 있어요";
  }
}

function setLoadingImage(imageIndex) {
  root.dataset.loadingImage = String(imageIndex);
}

function completeLoadingWhenReady() {
  if (!loadingStepsFinished || recommendationPending) {
    return;
  }

  root.dataset.loadingComplete = "true";
  setLoadingCopy(true);

  if (loadingImageTimer) {
    window.clearInterval(loadingImageTimer);
    loadingImageTimer = null;
  }
}

function startLoadingSequence() {
  stopLoadingSequence();
  let step = 0;
  let imageIndex = 0;
  const maxStep = 4;
  const maxImageIndex = 3;

  loadingStepsFinished = false;
  setLoadingStep(step);
  setLoadingImage(imageIndex);
  root.dataset.loadingComplete = "false";
  setLoadingCopy(false);

  const advanceStep = () => {
    if (step >= maxStep) {
      loadingTimer = null;
      setLoadingStep(maxStep + 1);
      loadingStepsFinished = true;
      completeLoadingWhenReady();
      return;
    }

    step += 1;
    setLoadingStep(step);
    loadingTimer = window.setTimeout(advanceStep, randomDuration(LOADING_STEP_RANGES[step] ?? [1.2, 1.8]));
  };

  loadingTimer = window.setTimeout(advanceStep, randomDuration(LOADING_STEP_RANGES[0]));

  loadingImageTimer = window.setInterval(() => {
    imageIndex = imageIndex >= maxImageIndex ? 0 : imageIndex + 1;
    setLoadingImage(imageIndex);
  }, 2500);
}

root.dataset.stage = "idle";
root.dataset.demoReady = "false";
setView();
bindCourseSearch();
bindNeedsForm();
bindResultTabs();
bindExplanationUI();
bindResultRestart();
lockGestures();

window.addEventListener("hashchange", setView);

wait(STAGE_TIMING.introShowcase, () => {
  showDemo();
  wait(STAGE_TIMING.demoStartDelay, () => {
    runDemoLoop();
  });
});
