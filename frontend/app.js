const tabs = document.querySelectorAll(".tab-button");
const panels = document.querySelectorAll(".panel");
const fileInput = document.querySelector("#imageInput");
const fileButton = document.querySelector("#fileButton");
const uploadWebhookUrlInput = document.querySelector("#uploadWebhookUrl");
const questionWebhookUrlInput = document.querySelector("#questionWebhookUrl");
const dropzone = document.querySelector("#dropzone");
const previewGrid = document.querySelector("#previewGrid");
const successStatus = document.querySelector("#successStatus");
const errorStatus = document.querySelector("#errorStatus");
const questionForm = document.querySelector("#questionForm");
const questionInput = document.querySelector("#questionInput");
const quickQuestions = document.querySelectorAll("[data-question]");
const stateButtons = document.querySelectorAll("[data-state]");
const emptyState = document.querySelector("#emptyState");
const results = document.querySelector("#results");
const noAnswerState = document.querySelector("#noAnswerState");
const ambiguousState = document.querySelector("#ambiguousState");
const fallbackState = document.querySelector("#fallbackState");
const evidenceText = document.querySelector("#evidenceText");

const allowedTypes = new Set(["image/jpeg", "image/png"]);
const allowedExtensions = [".jpg", ".jpeg", ".png"];
const maxFileSize = 10 * 1024 * 1024;
const legacyWebhookBaseUrlStorageKey = "odiduji.webhookBaseUrl";
const uploadWebhookUrlStorageKey = "odiduji.uploadWebhookUrl";
const questionWebhookUrlStorageKey = "odiduji.questionWebhookUrl";
const defaultWebhookBaseUrl = "http://127.0.0.1:5678/webhook";
const defaultUploadWebhookUrl = `${defaultWebhookBaseUrl}/image-upload`;
const defaultQuestionWebhookUrl = `${defaultWebhookBaseUrl}/question-submit`;

const stateViews = {
  empty: emptyState,
  results,
  noAnswer: noAnswerState,
  ambiguous: ambiguousState,
  fallback: fallbackState,
};

const evidenceBySource = {
  assignment: "제출 기한은 5월 28일 23:59까지입니다.",
  scholarship: "신청 기간 내 서류를 업로드해야 합니다.",
};

function showTab(tabName) {
  tabs.forEach((tab) => {
    tab.classList.toggle("is-active", tab.dataset.tab === tabName);
  });

  panels.forEach((panel) => {
    panel.classList.toggle("is-active", panel.dataset.panel === tabName);
  });
}

function setStatus(type, message) {
  successStatus.hidden = true;
  errorStatus.hidden = true;

  if (type === "success") {
    successStatus.textContent = message;
    successStatus.hidden = false;
  }

  if (type === "error") {
    errorStatus.textContent = message;
    errorStatus.hidden = false;
  }
}

function normalizeWebhookUrl(value, endpoint) {
  const fallback = endpoint === "image-upload" ? defaultUploadWebhookUrl : defaultQuestionWebhookUrl;
  const otherEndpoint = endpoint === "image-upload" ? "question-submit" : "image-upload";
  const rawUrl = (value || fallback)
    .trim()
    .replace("http://localhost:", "http://127.0.0.1:")
    .replace(/\/+$/, "");

  if (!rawUrl) return fallback;
  if (rawUrl.endsWith(`/${endpoint}`)) return rawUrl;
  if (rawUrl.endsWith(`/${otherEndpoint}`)) {
    return rawUrl.replace(new RegExp(`/${otherEndpoint}$`), `/${endpoint}`);
  }
  if (rawUrl.endsWith("/webhook") || rawUrl.endsWith("/webhook-test")) {
    return `${rawUrl}/${endpoint}`;
  }
  return rawUrl;
}

function getUploadWebhookUrl() {
  return normalizeWebhookUrl(uploadWebhookUrlInput.value, "image-upload");
}

function getQuestionWebhookUrl() {
  return normalizeWebhookUrl(questionWebhookUrlInput.value, "question-submit");
}

function showResultState(stateName) {
  Object.entries(stateViews).forEach(([name, element]) => {
    element.hidden = name !== stateName;
  });

  stateButtons.forEach((button) => {
    button.classList.toggle("is-selected", button.dataset.state === stateName);
  });
}

function hasAllowedExtension(fileName) {
  const lowerName = fileName.toLowerCase();
  return allowedExtensions.some((extension) => lowerName.endsWith(extension));
}

function validateFile(file) {
  if (!allowedTypes.has(file.type) || !hasAllowedExtension(file.name)) {
    return "unsupported_file_type";
  }

  if (file.size > maxFileSize) {
    return "file_too_large";
  }

  return null;
}

function updatePreviewMeta(card, message, type = "info") {
  const meta = card.querySelector(".preview-meta");
  if (!meta) return;
  meta.textContent = message;
  meta.dataset.type = type;
}

async function uploadImage(file, card) {
  const formData = new FormData();
  formData.append("image", file, file.name);

  updatePreviewMeta(card, "webhook 전송 중", "info");
  setStatus("success", "Webhook 전송 중");

  let response;
  try {
    response = await fetch(getUploadWebhookUrl(), {
      method: "POST",
      body: formData,
    });
  } catch (error) {
    updatePreviewMeta(card, "webhook 연결 실패", "error");
    setStatus("error", `webhook_connection_failed: ${getUploadWebhookUrl()}`);
    return;
  }

  const responseText = await response.text();
  let payload = null;
  try {
    payload = responseText ? JSON.parse(responseText) : null;
  } catch (_) {
    payload = null;
  }

  if (!response.ok) {
    updatePreviewMeta(card, `HTTP ${response.status}`, "error");
    setStatus("error", `webhook_http_${response.status}`);
    return;
  }

  if (!payload) {
    updatePreviewMeta(card, "응답 JSON 없음", "error");
    setStatus("error", "invalid_webhook_response");
    return;
  }

  if (payload.status === "rejected" || payload.validation_status === "rejected") {
    const reason = payload.reject_reason || "upload_rejected";
    updatePreviewMeta(card, reason, "error");
    setStatus("error", reason);
    return;
  }

  const captureId = payload.capture_id || "capture_id 없음";
  const cacheLabel = payload.cache_hit ? "cache_hit" : payload.status || "received";
  updatePreviewMeta(card, `${captureId} · ${cacheLabel}`, "success");
  setStatus("success", `${captureId} · ${cacheLabel}`);
}

function createElement(tag, className, textContent) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (textContent !== undefined) element.textContent = textContent;
  return element;
}

function formatConfidence(card) {
  if (card.needs_review) return "확인 필요";
  const confidence = Number(card.confidence);
  return Number.isFinite(confidence) ? confidence.toFixed(2) : "-";
}

function evidenceSummary(card) {
  const evidence = card.evidence_text || {};
  const first = Object.values(evidence).find((value) => value !== null && value !== "");
  return first || "근거 문장 없음";
}

function renderResultCards(payload) {
  if (payload.no_answer) {
    showResultState("noAnswer");
    evidenceText.textContent = payload.no_answer_reason || "no_answer";
    return;
  }

  const cards = payload.cards || [];
  results.innerHTML = "";

  const titleRow = createElement("div", "section-title-row");
  const titleGroup = createElement("div");
  titleGroup.append(
    createElement("span", "eyebrow", "Evidence-bound answer"),
    createElement("h2", null, `${cards.length}건의 결과 카드`),
  );
  titleRow.append(titleGroup, createElement("span", "status-pill success", "no hallucination"));
  results.append(titleRow);

  if (payload.answer) {
    const answer = createElement("article", "surface empty-state");
    answer.append(createElement("strong", null, payload.answer));
    results.append(answer);
  }

  cards.forEach((card) => {
    const article = createElement("article", `result-card${card.needs_review ? " needs-review" : ""}`);
    const thumb = createElement("button", card.needs_review ? "thumb yellow" : "thumb");
    thumb.type = "button";
    thumb.append(createElement("span", null, card.doc_type || "card"));
    thumb.addEventListener("click", () => {
      evidenceText.textContent = evidenceSummary(card);
    });

    const content = createElement("div", "result-content");
    const header = createElement("div", "result-header");
    const heading = createElement("div");
    heading.append(
      createElement("span", "doc-type", card.doc_type || "unknown"),
      createElement("h3", null, card.title || card.capture_id || "Untitled"),
    );
    header.append(heading, createElement("span", card.needs_review ? "confidence review" : "confidence", formatConfidence(card)));

    const dl = document.createElement("dl");
    const fields = card.fields || {};
    Object.entries(fields).forEach(([key, value]) => {
      if (value === null || value === "") return;
      const row = createElement("div");
      row.append(createElement("dt", null, key), createElement("dd", null, String(value)));
      dl.append(row);
    });
    const evidenceRow = createElement("div");
    evidenceRow.append(createElement("dt", null, "근거"), createElement("dd", null, evidenceSummary(card)));
    dl.append(evidenceRow);

    content.append(header, dl);
    article.append(thumb, content);
    results.append(article);
  });

  evidenceText.textContent = cards[0] ? evidenceSummary(cards[0]) : "결과 카드 없음";
  showResultState("results");
}

async function submitQuestion(query) {
  showResultState("empty");
  emptyState.querySelector("strong").textContent = "질문을 전송하는 중입니다.";

  const body = new FormData();
  body.append("raw_query", query);

  let response;
  try {
    response = await fetch(getQuestionWebhookUrl(), {
      method: "POST",
      body,
    });
  } catch (error) {
    emptyState.querySelector("strong").textContent = "질문 웹훅 연결 실패";
    emptyState.querySelector("p").textContent = getQuestionWebhookUrl();
    return;
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok || !payload) {
    emptyState.querySelector("strong").textContent = `질문 응답 오류 ${response.status}`;
    emptyState.querySelector("p").textContent = "n8n Webhook 응답을 확인하세요.";
    return;
  }

  if (payload.status === "failed") {
    emptyState.querySelector("strong").textContent = payload.error_code || "workflow_failed";
    emptyState.querySelector("p").textContent = payload.error_message || "n8n workflow failed";
    return;
  }

  renderResultCards(payload);
}

function addPreview(file) {
  const validationError = validateFile(file);
  if (validationError) {
    setStatus("error", validationError);
    return;
  }

  const card = document.createElement("article");
  card.className = "preview-card";

  const image = document.createElement("img");
  image.alt = file.name;
  image.src = URL.createObjectURL(file);
  image.addEventListener(
    "load",
    () => {
      URL.revokeObjectURL(image.src);
    },
    { once: true },
  );

  const removeButton = document.createElement("button");
  removeButton.className = "remove";
  removeButton.type = "button";
  removeButton.setAttribute("aria-label", `${file.name} 제거`);
  removeButton.textContent = "x";
  removeButton.addEventListener("click", () => {
    card.remove();
    if (!previewGrid.children.length) {
      setStatus("", "");
    }
  });

  const meta = document.createElement("span");
  meta.className = "preview-meta";
  meta.textContent = "업로드 대기";
  meta.dataset.type = "info";

  card.append(image, removeButton, meta);
  previewGrid.prepend(card);
  uploadImage(file, card);
}

function handleFiles(files) {
  Array.from(files).forEach(addPreview);
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => showTab(tab.dataset.tab));
});

fileButton.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", (event) => {
  handleFiles(event.target.files);
  event.target.value = "";
});

const legacyWebhookBaseUrl = localStorage.getItem(legacyWebhookBaseUrlStorageKey);
const savedUploadWebhookUrl = localStorage.getItem(uploadWebhookUrlStorageKey);
const savedQuestionWebhookUrl = localStorage.getItem(questionWebhookUrlStorageKey);

uploadWebhookUrlInput.value = normalizeWebhookUrl(savedUploadWebhookUrl || legacyWebhookBaseUrl || defaultUploadWebhookUrl, "image-upload");
questionWebhookUrlInput.value = normalizeWebhookUrl(savedQuestionWebhookUrl || legacyWebhookBaseUrl || defaultQuestionWebhookUrl, "question-submit");

uploadWebhookUrlInput.addEventListener("change", () => {
  uploadWebhookUrlInput.value = getUploadWebhookUrl();
  localStorage.setItem(uploadWebhookUrlStorageKey, uploadWebhookUrlInput.value);
});

questionWebhookUrlInput.addEventListener("change", () => {
  questionWebhookUrlInput.value = getQuestionWebhookUrl();
  localStorage.setItem(questionWebhookUrlStorageKey, questionWebhookUrlInput.value);
});

["dragenter", "dragover"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("is-dragover");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-dragover");
  });
});

dropzone.addEventListener("drop", (event) => {
  handleFiles(event.dataTransfer.files);
});

quickQuestions.forEach((button) => {
  button.addEventListener("click", () => {
    quickQuestions.forEach((item) => item.classList.remove("is-selected"));
    button.classList.add("is-selected");
    questionInput.value = button.dataset.question;
    submitQuestion(button.dataset.question);
  });
});

stateButtons.forEach((button) => {
  button.addEventListener("click", () => {
    showResultState(button.dataset.state);
  });
});

document.querySelectorAll("[data-source]").forEach((button) => {
  button.addEventListener("click", () => {
    evidenceText.textContent = evidenceBySource[button.dataset.source];
  });
});

questionForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = questionInput.value.trim();

  if (!query) {
    quickQuestions.forEach((item) => item.classList.remove("is-selected"));
    showResultState("empty");
    return;
  }

  quickQuestions.forEach((item) => {
    item.classList.toggle("is-selected", item.dataset.question === query);
  });
  submitQuestion(query);
});
