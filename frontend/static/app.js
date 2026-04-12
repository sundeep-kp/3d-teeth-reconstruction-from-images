const tabs = Array.from(document.querySelectorAll(".tab"));
const panels = Array.from(document.querySelectorAll(".model-card"));

function setActiveModel(modelName) {
  tabs.forEach((tab) => {
    const isActive = tab.dataset.model === modelName;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", String(isActive));
  });

  panels.forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === modelName);
  });
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => setActiveModel(tab.dataset.model));
});

if (tabs.length > 0) {
  setActiveModel("knn");
}

const hasRunner = document.getElementById("endpoint") !== null;

if (hasRunner) {
  const fields = {
    endpoint: document.getElementById("endpoint"),
    workspaceRoot: document.getElementById("workspaceRoot"),
    gpu: document.getElementById("gpu"),
    cpu: document.getElementById("cpu"),
    testDir: document.getElementById("testDir"),
    outputDir: document.getElementById("outputDir"),
    reconDir: document.getElementById("reconDir"),
    dreamerCfg: document.getElementById("dreamerCfg"),
    cmdGenerate: document.getElementById("cmdGenerate"),
    cmdUpper: document.getElementById("cmdUpper"),
    cmdLower: document.getElementById("cmdLower"),
    terminal: document.getElementById("terminal"),
    runnerStatus: document.getElementById("runnerStatus"),
    verboseMode: document.getElementById("verboseMode")
  };

  function log(line, className = "") {
    const span = document.createElement("span");
    if (className) span.className = className;
    span.textContent = `${line}\n`;
    fields.terminal.appendChild(span);
    fields.terminal.scrollTop = fields.terminal.scrollHeight;
  }

  function formatTime() {
    const now = new Date();
    return now.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });
  }

  function logVerbose(line, className = "") {
    if (!fields.verboseMode.checked && className === "muted") return;
    const timestamp = `[${formatTime()}]`;
    log(`${timestamp} ${line}`, className);
  }

  function setRunnerStatus(isConnected, message) {
    fields.runnerStatus.textContent = message;
    fields.runnerStatus.classList.toggle("connected", isConnected);
    fields.runnerStatus.classList.toggle("error", !isConnected);
  }

  function buildCommands() {
    const gpu = fields.gpu.value.trim() || "0";
    const cpu = fields.cpu.value.trim() || "4";
    const cfg = fields.dreamerCfg.value.trim() || "configs/TeethDreamer.yaml";
    const out = fields.outputDir.value.trim() || "results";
    const testDir = fields.testDir.value.trim() || "example/teeth";
    const recon = fields.reconDir.value.trim() || "../results/reconstruction";

    fields.cmdGenerate.value = [
      "python3 TeethDreamer.py \\",
      `  -b ${cfg} \\`,
      `  --gpus ${gpu} \\`,
      "  --test ckpt/TeethDreamer.ckpt \\",
      `  --output ${out} \\`,
      `  data.params.test_dir=${testDir}`
    ].join("\n");

    fields.cmdUpper.value = [
      "python3 run.py \\",
      `  --img ../${out}/1832_upper_cond_000_000_000_000.png \\`,
      `  --cpu ${cpu} \\`,
      `  --dir ${recon} \\`,
      "  --normal \\",
      "  --rembg"
    ].join("\n");

    fields.cmdLower.value = [
      "python3 run.py \\",
      `  --img ../${out}/1832_lower_cond_000_000_000_000.png \\`,
      `  --cpu ${cpu} \\`,
      `  --dir ${recon} \\`,
      "  --normal \\",
      "  --rembg"
    ].join("\n");
  }

  async function runViaEndpoint(command, cwd) {
    const endpoint = fields.endpoint.value.trim();
    const root = fields.workspaceRoot.value.trim() || ".";
    const runCwd = cwd === "instant" ? `${root}/instant-nsr-pl` : root;

    log(`$ ${command}`, "warn");
    logVerbose("preparing execution...", "muted");
    logVerbose(`endpoint: ${endpoint}`, "muted");
    logVerbose(`working directory: ${runCwd}`, "muted");

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, cwd: runCwd })
      });

      logVerbose(`response status: ${res.status}`, "muted");

      if (!res.ok) {
        setRunnerStatus(false, "Runner endpoint error");
        logVerbose(`endpoint responded with error: HTTP ${res.status}`, "err");
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();

      setRunnerStatus(true, "Runner endpoint connected");
      logVerbose(`response metadata cwd: ${data.cwd || "unknown"}`, "muted");
      logVerbose(`response metadata code: ${data.code ?? "unknown"}`, "muted");

      if (data.stdout) log(data.stdout, "ok");
      if (data.stderr) log(data.stderr, "err");

      logVerbose(
        `command completed with exit code ${data.code ?? "unknown"}`,
        data.code === 0 ? "ok" : "err"
      );

      return data;
    } catch (err) {
      setRunnerStatus(false, "Runner endpoint not connected");
      log(`Error: Runner unavailable (${err.message}). Copy and run in terminal.`, "err");
      throw err;
    }
  }

  async function copyText(id) {
    const text = fields[id].value;
    try {
      await navigator.clipboard.writeText(text);
      log(`Copied ${id}`, "ok");
    } catch (_) {
      log(`Clipboard blocked. Manually copy from ${id}.`, "warn");
    }
  }

  ["gpu", "cpu", "testDir", "outputDir", "reconDir", "dreamerCfg"].forEach((id) => {
    fields[id].addEventListener("input", buildCommands);
  });

  document.querySelectorAll("button[data-copy]").forEach((btn) => {
    btn.addEventListener("click", () => copyText(btn.dataset.copy));
  });

  document.querySelectorAll("button[data-cmd]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const command = fields[btn.dataset.cmd].value.trim();
      if (!command) return;
      try {
        await runViaEndpoint(command, btn.dataset.cwd);
      } catch (_) {
        // Error is already logged above.
      }
    });
  });

  document.getElementById("runAll").addEventListener("click", async () => {
    const queue = [
      { id: "cmdGenerate", cwd: "workspace" },
      { id: "cmdUpper", cwd: "instant" },
      { id: "cmdLower", cwd: "instant" }
    ];

    for (const item of queue) {
      try {
        await runViaEndpoint(fields[item.id].value.trim(), item.cwd);
      } catch (_) {
        break;
      }
    }
  });

  document.getElementById("clearLog").addEventListener("click", () => {
    fields.terminal.textContent = "";
  });

  buildCommands();
  setRunnerStatus(false, "Runner endpoint not connected");
  log("Ready. Edit paths if needed, then copy or run commands.");
}

const hasPredictor = document.getElementById("predictForm") !== null;

if (hasPredictor) {
  const symptomNames = [
    "bad_breath",
    "black_spots",
    "bleeding_gums",
    "clicking_sound",
    "difficulty_chewing",
    "difficulty_swallowing",
    "fever",
    "gum_irritation",
    "gum_recession",
    "hard_deposits",
    "headache",
    "jaw_pain",
    "loose_teeth",
    "lump",
    "pain_while_chewing",
    "sensitivity",
    "severe_pain",
    "sharp_pain",
    "swelling_face",
    "swelling_gums",
    "swollen_gums",
    "tooth_discoloration",
    "tooth_pain",
    "ulcers",
    "visible_crack",
    "yellow_deposits"
  ];

  const predictForm = document.getElementById("predictForm");
  const symptomGrid = document.getElementById("symptomGrid");
  const clearSymptoms = document.getElementById("clearSymptoms");
  const predictModel = document.getElementById("predictModel");
  const predictEndpoint = document.getElementById("predictEndpoint");
  const predictLoading = document.getElementById("predictLoading");
  const predictError = document.getElementById("predictError");
  const predictResults = document.getElementById("predictResults");
  const topDisease = document.getElementById("topDisease");
  const topConfidenceText = document.getElementById("topConfidenceText");
  const topConfidenceBar = document.getElementById("topConfidenceBar");
  const dangerLabel = document.getElementById("dangerLabel");
  const dangerScoreText = document.getElementById("dangerScoreText");
  const dangerBadge = document.getElementById("dangerBadge");
  const alternativesList = document.getElementById("alternativesList");

  function toDisplayName(value) {
    return value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function setDangerClass(label) {
    dangerBadge.classList.remove("danger-low", "danger-moderate", "danger-high", "danger-critical");
    const normalized = (label || "").toLowerCase();
    if (normalized === "low") dangerBadge.classList.add("danger-low");
    if (normalized === "moderate") dangerBadge.classList.add("danger-moderate");
    if (normalized === "high") dangerBadge.classList.add("danger-high");
    if (normalized === "critical") dangerBadge.classList.add("danger-critical");
  }

  function renderSymptomGrid() {
    symptomGrid.innerHTML = symptomNames
      .map(
        (symptom) => `
          <label class="symptom-item">
            <input type="checkbox" value="${symptom}" />
            <span>${toDisplayName(symptom)}</span>
          </label>
        `,
      )
      .join("");
  }

  function selectedSymptoms() {
    return Array.from(symptomGrid.querySelectorAll("input[type='checkbox']:checked")).map((el) => el.value);
  }

  function clearState() {
    predictLoading.style.display = "none";
    predictError.style.display = "none";
    predictError.textContent = "";
  }

  function showError(message) {
    predictLoading.style.display = "none";
    predictResults.style.display = "none";
    predictError.style.display = "block";
    predictError.textContent = message;
  }

  function renderResults(data) {
    clearState();
    predictResults.style.display = "grid";

    const confidencePct = (Number(data.confidence || 0) * 100).toFixed(2);
    topDisease.textContent = data.top_disease || "Unknown";
    topConfidenceText.textContent = `Confidence: ${confidencePct}% (${(data.model || "dt").toUpperCase()})`;
    topConfidenceBar.style.width = `${confidencePct}%`;

    const danger = data.danger || {};
    dangerLabel.textContent = danger.label || "Unknown";
    dangerScoreText.textContent = `Score: ${danger.score ?? "N/A"} (Severity ${danger.severity ?? "?"})`;
    dangerBadge.textContent = danger.label || "N/A";
    setDangerClass(danger.label || "");

    const alternatives = Array.isArray(data.alternatives) ? data.alternatives : [];
    alternativesList.innerHTML = alternatives.length
      ? alternatives
          .map((item) => {
            const pct = (Number(item.confidence || 0) * 100).toFixed(2);
            return `<li><span>${item.disease}</span><span>${pct}%</span></li>`;
          })
          .join("")
      : "<li><span>No additional alternatives</span><span>-</span></li>";
  }

  renderSymptomGrid();

  clearSymptoms.addEventListener("click", () => {
    symptomGrid.querySelectorAll("input[type='checkbox']").forEach((box) => {
      box.checked = false;
    });
    clearState();
    predictResults.style.display = "none";
  });

  predictForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearState();

    const symptoms = selectedSymptoms();
    if (symptoms.length === 0) {
      showError("Select at least one symptom before predicting.");
      return;
    }

    predictLoading.style.display = "block";
    predictResults.style.display = "none";

    try {
      const response = await fetch(predictEndpoint.value.trim(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symptoms,
          model: predictModel.value,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || `Request failed with HTTP ${response.status}`);
      }

      renderResults(payload);
    } catch (error) {
      showError(error.message || "Prediction failed");
    } finally {
      predictLoading.style.display = "none";
    }
  });
}
