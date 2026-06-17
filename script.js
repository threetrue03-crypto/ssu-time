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
const selectedCourses = new Map();
const userPreferences = {
  evaluation: "",
  timePreference: "",
  dayOffPreference: "",
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

    const key = `${course.course_name}-${course.credits}-${course.completion_type}`;

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
    .map(
      (course) => {
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
      },
    )
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
    cartSummary.textContent = `${count}개 · ${credits}학점`;
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
  return ["evaluation", "timePreference", "dayOffPreference"].filter((key) => userPreferences[key]).length;
}

function updateNeedsSubmitState() {
  const submitButton = document.querySelector(".needs-submit-button");

  if (submitButton) {
    submitButton.disabled = getAnsweredPreferenceCount() < 3;
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
    .map((keyword) => `<span>${escapeHTML(keyword)}</span>`)
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

    updateNeedsSubmitState();
  });

  keywordInput?.addEventListener("input", (event) => {
    userPreferences.liberalKeywords = event.target.value
      .split(/[,，\s]+/)
      .map((keyword) => keyword.trim())
      .filter(Boolean)
      .slice(0, 5);

    updateKeywordPreview();
  });

  updateNeedsSummary();
  updateNeedsSubmitState();
}

root.dataset.stage = "idle";
root.dataset.demoReady = "false";
setView();
bindCourseSearch();
bindNeedsForm();
lockGestures();

window.addEventListener("hashchange", setView);

wait(STAGE_TIMING.introShowcase, () => {
  showDemo();
  wait(STAGE_TIMING.demoStartDelay, () => {
    runDemoLoop();
  });
});
