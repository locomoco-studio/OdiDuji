const tabs = document.querySelectorAll(".tab-button");
const panels = document.querySelectorAll(".panel");
const fileInput = document.querySelector("#imageInput");
const fileButton = document.querySelector("#fileButton");
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

  card.append(image, removeButton);
  previewGrid.prepend(card);
  setStatus("success", "upload_job_id 생성됨 · status=received");
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
    showResultState(button.dataset.demo);
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
  showResultState("results");
});
