const state = {
  history: [],
  lastPrompt: "",
  lastTrace: null,
  busy: false,
};

const elements = {
  form: document.querySelector("#chat-form"),
  input: document.querySelector("#message-input"),
  send: document.querySelector("#send-button"),
  messages: document.querySelector("#messages"),
  username: document.querySelector("#username"),
  password: document.querySelector("#password"),
  clear: document.querySelector("#clear-chat"),
  empty: document.querySelector("#empty-inspector"),
  traceContent: document.querySelector("#trace-content"),
  traceStatus: document.querySelector("#trace-status"),
  contextStep: document.querySelector("#context-step"),
  pipelinePolicy: document.querySelector("#pipeline-policy"),
  pipelineContext: document.querySelector("#pipeline-context"),
  boundaryCallout: document.querySelector("#boundary-callout"),
  boundaryTitle: document.querySelector("#boundary-title"),
  boundaryCopy: document.querySelector("#boundary-copy"),
  metricTotal: document.querySelector("#metric-total"),
  metricOther: document.querySelector("#metric-other"),
  metricTime: document.querySelector("#metric-time"),
  recordList: document.querySelector("#record-list"),
  jsonPayload: document.querySelector("#json-payload"),
  copyJson: document.querySelector("#copy-json"),
  replay: document.querySelector("#replay-button"),
};

function selectedVersion() {
  return document.querySelector('input[name="version"]:checked').value;
}

async function checkServices() {
  try {
    const response = await fetch("/api/health");
    const health = await response.json();
    Object.entries(health.services || {}).forEach(([name, online]) => {
      const service = document.querySelector(`[data-service="${name}"]`);
      if (!service) return;
      service.classList.toggle("online", online);
      service.classList.toggle("offline", !online);
      service.title = online ? `${name} is reachable` : `${name} is offline`;
    });
  } catch (_) {
    document.querySelectorAll("[data-service]").forEach((service) => service.classList.add("offline"));
  }
}

function addMessage(role, content, options = {}) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}-message${options.typing ? " typing" : ""}`;

  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? elements.username.value.slice(0, 2).toUpperCase() : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (options.typing) {
    bubble.innerHTML = "<i></i><i></i><i></i>";
  } else {
    const paragraph = document.createElement("p");
    paragraph.textContent = content;
    bubble.appendChild(paragraph);
  }

  wrapper.append(avatar, bubble);
  elements.messages.appendChild(wrapper);
  elements.messages.scrollTop = elements.messages.scrollHeight;
  return wrapper;
}

function setBusy(busy) {
  state.busy = busy;
  elements.send.disabled = busy;
  elements.input.disabled = busy;
  elements.send.querySelector("span").textContent = busy ? "Running" : "Send";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderTrace(trace) {
  state.lastTrace = trace;
  const breached = trace.boundary_status === "breached";

  elements.empty.hidden = true;
  elements.traceContent.hidden = false;
  elements.traceStatus.className = `status-pill ${trace.boundary_status}`;
  elements.traceStatus.textContent = breached ? "Boundary breached" : "Boundary enforced";
  elements.contextStep.className = `pipeline-step ${breached ? "danger" : "safe"}`;
  elements.pipelinePolicy.textContent = trace.version === "vulnerable" ? "SELECT *" : "WHERE owner_id";
  elements.pipelineContext.textContent = `${trace.record_count} rows received`;

  elements.boundaryCallout.className = `boundary-callout${breached ? "" : " safe"}`;
  elements.boundaryTitle.textContent = breached
    ? "Authorization boundary breached"
    : "Authorization enforced before inference";
  elements.boundaryCopy.textContent = breached
    ? `${trace.other_user_count} row(s) owned by ${trace.other_owners.join(", ")} entered ${trace.authenticated_as}'s model context.`
    : `Only ${trace.authenticated_as}'s rows left SQLite. The model never received another user's data.`;

  elements.metricTotal.textContent = trace.record_count;
  elements.metricOther.textContent = trace.other_user_count;
  elements.metricTime.textContent = `${trace.elapsed_ms} ms`;
  elements.jsonPayload.textContent = JSON.stringify(trace.records, null, 2);

  elements.recordList.innerHTML = trace.records.map((record) => {
    const foreign = record.owner !== trace.authenticated_as;
    return `
      <article class="record${foreign ? " foreign" : ""}">
        <div class="record-top">
          <span class="record-owner">${escapeHtml(record.owner)} · #${escapeHtml(record.report_id)}</span>
          <span class="record-amount">$${escapeHtml(record.amount)}</span>
        </div>
        <p>${escapeHtml(record.merchant)} · •••• ${escapeHtml(record.card_last_four)}</p>
        <small>${escapeHtml(record.purpose)}</small>
        ${foreign ? '<span class="foreign-badge">OTHER USER</span>' : ""}
      </article>`;
  }).join("");

  elements.replay.hidden = trace.version === "fixed";
  elements.traceContent.scrollTop = 0;
}

async function submitMessage(message, options = {}) {
  if (!message.trim() || state.busy) return;

  const version = selectedVersion();
  state.lastPrompt = message.trim();
  if (!options.replay) {
    addMessage("user", state.lastPrompt);
  } else {
    addMessage("user", `[Replayed against fixed server] ${state.lastPrompt}`);
  }

  const historyForRequest = [...state.history];
  state.history.push({ role: "user", content: state.lastPrompt });
  elements.input.value = "";
  setBusy(true);
  const typing = addMessage("assistant", "", { typing: true });

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        version,
        username: elements.username.value,
        password: elements.password.value,
        message: state.lastPrompt,
        history: historyForRequest,
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || result.error || "Request failed");

    typing.remove();
    addMessage("assistant", result.answer);
    state.history.push({ role: "assistant", content: result.answer });
    renderTrace(result.trace);
  } catch (error) {
    typing.remove();
    addMessage("assistant", `Demo error: ${error.message}`);
    state.history.pop();
  } finally {
    setBusy(false);
    elements.input.focus();
  }
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitMessage(elements.input.value);
});

elements.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    elements.input.value = button.dataset.prompt;
    elements.input.focus();
  });
});

document.querySelectorAll('input[name="version"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    state.history = [];
    const version = selectedVersion();
    elements.pipelinePolicy.textContent = version === "vulnerable" ? "SELECT * on next turn" : "Token filter on next turn";
  });
});

elements.clear.addEventListener("click", () => {
  state.history = [];
  elements.messages.innerHTML = "";
  addMessage("assistant", "Conversation cleared. Ask me about your expense reports.");
});

elements.copyJson.addEventListener("click", async () => {
  await navigator.clipboard.writeText(elements.jsonPayload.textContent);
  elements.copyJson.textContent = "Copied";
  setTimeout(() => { elements.copyJson.textContent = "Copy JSON"; }, 1200);
});

elements.replay.addEventListener("click", () => {
  document.querySelector('input[name="version"][value="fixed"]').checked = true;
  state.history = [];
  submitMessage(state.lastPrompt, { replay: true });
});

checkServices();
