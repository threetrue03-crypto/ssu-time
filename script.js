const root = document.documentElement;
const courseData = window.SSU_COURSES ?? [];

const STAGE_TIMING = {
  introShowcase: 3650,
  demoStartDelay: 200,
  course: 2800,
  needs: 4600,
  result: 6200,
};

const timers = new Set();
let searchTimer = null;
let loadingTimer = null;
let loadingImageTimer = null;
const selectedCourses = new Map();
const userPreferences = {
  evaluation: "",
  timePreference: "",
  dayOffPreference: "",
  targetCredits: "",
  liberalKeywords: [],
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

function getAnsweredPreferenceCount() {
  return ["evaluation", "timePreference", "dayOffPreference", "targetCredits"].filter((key) => userPreferences[key]).length;
}

function updateNeedsSubmitState() {
  const submitButton = document.querySelector(".needs-submit-button");

  if (submitButton) {
    submitButton.disabled = getAnsweredPreferenceCount() < 4;
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
  const form = document.querySelector(".needs-form");
  const keywordInput = document.querySelector(".keyword-input");
  const targetCreditInput = document.querySelector(".target-credit-input");
  const submitButton = document.querySelector(".needs-submit-button");

  if (!form) {
    return;
  }

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

    updateNeedsSubmitState();
  });

  targetCreditInput?.addEventListener("input", (event) => {
    const value = Number(event.target.value);
    userPreferences.targetCredits = Number.isFinite(value) && value > 0 && value <= 24
      ? String(value)
      : "";

    form
      .querySelectorAll('[data-preference="targetCredits"]')
      .forEach((button) => {
        button.classList.remove("is-selected");
      });

    updateNeedsSubmitState();
  });

  keywordInput?.addEventListener("keydown", (event) => {
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

  submitButton?.addEventListener("click", () => {
    if (submitButton.disabled) {
      return;
    }

    window.location.hash = "#loading";
  });

  updateNeedsSummary();
  updateNeedsSubmitState();
}

function bindResultTabs() {
  const tabs = document.querySelectorAll("[data-result-tab]");
  const plans = document.querySelectorAll("[data-result-plan]");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
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
  });
}

function stopLoadingSequence() {
  if (loadingTimer) {
    window.clearInterval(loadingTimer);
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

function startLoadingSequence() {
  stopLoadingSequence();
  let step = 0;
  let imageIndex = 0;
  const maxStep = 4;
  const maxImageIndex = 3;

  setLoadingStep(step);
  setLoadingImage(imageIndex);
  root.dataset.loadingComplete = "false";
  setLoadingCopy(false);

  loadingTimer = window.setInterval(() => {
    if (step >= maxStep) {
      window.clearInterval(loadingTimer);
      loadingTimer = null;
      setLoadingStep(maxStep + 1);
      root.dataset.loadingComplete = "true";
      setLoadingCopy(true);
      if (loadingImageTimer) {
        window.clearInterval(loadingImageTimer);
        loadingImageTimer = null;
      }
      return;
    }

    step += 1;
    setLoadingStep(step);
  }, 1350);

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
lockGestures();

window.addEventListener("hashchange", setView);

wait(STAGE_TIMING.introShowcase, () => {
  showDemo();
  wait(STAGE_TIMING.demoStartDelay, () => {
    runDemoLoop();
  });
});
