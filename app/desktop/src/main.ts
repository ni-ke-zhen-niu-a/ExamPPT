import "./style.css";
import * as pdfjsLib from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { invoke } from "@tauri-apps/api/core";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { Command } from "@tauri-apps/plugin-shell";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

type SlideEntry = {
  q: number;
  top: number;
  bottom: number;
  height: number;
};

type SlideInfo = {
  slide: number;
  questions: number[];
  bottom_margin: number;
  entries: SlideEntry[];
};

type BuildSummary = {
  status: "PASS" | "MANUAL_REQUIRED" | string;
  title?: string;
  scan_status: string;
  layout_status: string;
  question_count: number;
  cross_page_questions: number[];
  pptx: string;
  manifest: string;
  qa: string;
  preview_dir: string;
  preview_files: string[];
  slides: SlideInfo[];
  warnings: string[];
  violations: string[];
};

type ManifestQuestion = {
  number: number;
  anchor: {
    page: number;
    top: number;
    bottom: number;
  };
  cross_page: boolean;
  image?: string;
};

type Manifest = {
  source_pdf: string;
  name: string;
  questions: ManifestQuestion[];
};

type BoundaryOverride = {
  page: number;
  top: number;
};

type AppState = {
  sourcePath: string | null;
  fileName: string | null;
  fileSize: number | null;
  pageCount: number;
  currentPage: number;
  zoom: number;
  summary: BuildSummary | null;
  manifest: Manifest | null;
  currentQuestion: number | null;
  currentPreviewUrl: string | null;
  boundaryEditMode: boolean;
  boundaryOverrides: Record<number, BoundaryOverride>;
  boundaryDirty: boolean;
};

const state: AppState = {
  sourcePath: null,
  fileName: null,
  fileSize: null,
  pageCount: 0,
  currentPage: 1,
  zoom: 1.15,
  summary: null,
  manifest: null,
  currentQuestion: null,
  currentPreviewUrl: null,
  boundaryEditMode: false,
  boundaryOverrides: {},
  boundaryDirty: false,
};

const nativeTauri = Boolean((window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__);

document.querySelector<HTMLDivElement>("#app")!.innerHTML = `
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">E</div>
        <div>
          <div class="brand-title">ExamPPT</div>
          <div class="brand-subtitle">PDF试卷无损转PPT 工具</div>
        </div>
      </div>
      <div class="top-actions">
        <span class="local-badge">本地离线</span>
        <button class="ghost-btn" id="openFileTop">选择 PDF</button>
        <button class="primary-btn" id="buildBtn" disabled>生成讲题 PPT</button>
      </div>
    </header>

    <main class="workspace">
      <section class="panel pdf-panel">
        <div class="panel-head">
          <div>
            <div class="panel-kicker">原始文件</div>
            <h2>PDF 试卷</h2>
          </div>
          <div class="pdf-head-actions">
            <button class="ghost-btn compact" id="boundaryToggle" disabled>调整边界</button>
            <button class="primary-btn compact" id="applyBoundaries" disabled hidden>应用并重新生成</button>
            <div class="pager">
              <button id="prevPage" disabled>‹</button>
              <span id="pageInfo">— / —</span>
              <button id="nextPage" disabled>›</button>
            </div>
          </div>
        </div>
        <div class="viewer" id="pdfViewer">
          <div class="empty-state" id="dropZone">
            <div class="drop-icon">PDF</div>
            <h3>选择一份 PDF 试卷</h3>
            <p>文件只在本机处理，不上传。浏览器预览支持拖入；桌面版点击选择即可。</p>
            <button class="secondary-btn" id="openFile">选择 PDF</button>
          </div>
          <canvas id="pdfCanvas" hidden></canvas>
          <div id="boundaryLine" class="boundary-line" hidden>
            <span id="boundaryLabel">题目起始线</span>
          </div>
        </div>
      </section>

      <aside class="rail">
        <div class="rail-head">
          <div>
            <div class="panel-kicker">检查</div>
            <h2>题目导航</h2>
          </div>
          <span class="status-pill neutral" id="qaStatus">待处理</span>
        </div>

        <div class="summary-card">
          <div class="build-progress" id="buildProgress" hidden>
            <div class="progress-head">
              <span id="progressStage">准备生成</span>
              <strong id="progressPercent">0%</strong>
            </div>
            <div class="progress-track">
              <div class="progress-bar" id="progressBar"></div>
            </div>
            <div class="progress-meta">
              <span id="progressDetail">正在准备转换引擎…</span>
              <span id="progressElapsed">0 秒</span>
            </div>
          </div>
          <div class="summary-row"><span>识别题目</span><strong id="questionCount">—</strong></div>
          <div class="summary-row"><span>跨页题</span><strong id="crossPageCount">—</strong></div>
          <div class="summary-row"><span>PPT 页数</span><strong id="slideCount">—</strong></div>
        </div>

        <div class="question-list" id="questionList">
          <div class="rail-empty">生成后可按题号同步查看 PDF 与 PPT。</div>
        </div>
      </aside>

      <section class="panel ppt-panel">
        <div class="panel-head">
          <div>
            <div class="panel-kicker">生成结果</div>
            <h2>PPT 放映预览</h2>
          </div>
          <div class="view-actions">
            <span class="slide-info" id="slideInfo">—</span>
            <button class="ghost-btn compact" id="openOutput" disabled>打开输出</button>
          </div>
        </div>
        <div class="viewer ppt-viewer" id="pptViewer">
          <div class="ppt-placeholder" id="pptPlaceholder">
            <div class="ppt-sheet">
              <div class="sheet-line wide"></div>
              <div class="sheet-line"></div>
              <div class="sheet-box"></div>
              <div class="sheet-line medium"></div>
              <div class="sheet-line short"></div>
            </div>
            <h3>这里会显示最终 PPT</h3>
            <p>左侧原 PDF，右侧最终放映画面；点击中间题号即可自动对齐。</p>
          </div>
        </div>
      </section>
    </main>

    <footer class="statusbar">
      <div class="file-status">
        <span class="dot"></span>
        <span id="fileStatus">尚未选择文件</span>
      </div>
      <div class="footer-note" id="footerNote">原题不改 · 整题不跨页 · 视觉字号一致 · 自动 QA</div>
    </footer>
  </div>
  <input id="fileInput" type="file" accept="application/pdf,.pdf" hidden />
`;

const fileInput = document.querySelector<HTMLInputElement>("#fileInput")!;
const canvas = document.querySelector<HTMLCanvasElement>("#pdfCanvas")!;
const dropZone = document.querySelector<HTMLDivElement>("#dropZone")!;
const viewer = document.querySelector<HTMLDivElement>("#pdfViewer")!;
const buildBtn = document.querySelector<HTMLButtonElement>("#buildBtn")!;
const prevPage = document.querySelector<HTMLButtonElement>("#prevPage")!;
const nextPage = document.querySelector<HTMLButtonElement>("#nextPage")!;
const pageInfo = document.querySelector<HTMLSpanElement>("#pageInfo")!;
const fileStatus = document.querySelector<HTMLSpanElement>("#fileStatus")!;
const qaStatus = document.querySelector<HTMLSpanElement>("#qaStatus")!;
const questionList = document.querySelector<HTMLDivElement>("#questionList")!;
const questionCount = document.querySelector<HTMLElement>("#questionCount")!;
const crossPageCount = document.querySelector<HTMLElement>("#crossPageCount")!;
const slideCount = document.querySelector<HTMLElement>("#slideCount")!;
let pptPreview: HTMLImageElement | null = null;
const pptPlaceholder = document.querySelector<HTMLDivElement>("#pptPlaceholder")!;
const slideInfo = document.querySelector<HTMLSpanElement>("#slideInfo")!;
const openOutput = document.querySelector<HTMLButtonElement>("#openOutput")!;
const footerNote = document.querySelector<HTMLDivElement>("#footerNote")!;
const boundaryToggle = document.querySelector<HTMLButtonElement>("#boundaryToggle")!;
const applyBoundaries = document.querySelector<HTMLButtonElement>("#applyBoundaries")!;
const boundaryLine = document.querySelector<HTMLDivElement>("#boundaryLine")!;
const boundaryLabel = document.querySelector<HTMLSpanElement>("#boundaryLabel")!;
const buildProgress = document.querySelector<HTMLDivElement>("#buildProgress")!;
const progressStage = document.querySelector<HTMLSpanElement>("#progressStage")!;
const progressPercent = document.querySelector<HTMLElement>("#progressPercent")!;
const progressBar = document.querySelector<HTMLDivElement>("#progressBar")!;
const progressDetail = document.querySelector<HTMLSpanElement>("#progressDetail")!;
const progressElapsed = document.querySelector<HTMLSpanElement>("#progressElapsed")!;

let progressStartedAt = 0;
let progressTimer: number | null = null;

let pdfDoc: Awaited<ReturnType<typeof pdfjsLib.getDocument>["promise"]> | null = null;

function baseName(path: string) {
  return path.split(/[\\/]/).pop() || path;
}

function formatSize(bytes: number | null) {
  if (bytes === null) return "";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

type BuildProgressPayload = {
  percent: number;
  stage: string;
  detail?: string;
};

function updateElapsedTime() {
  if (!progressStartedAt) return;
  const seconds = Math.max(0, Math.floor((Date.now() - progressStartedAt) / 1000));
  progressElapsed.textContent = `${seconds} 秒`;
}

function beginBuildProgress() {
  if (progressTimer !== null) window.clearInterval(progressTimer);
  progressStartedAt = Date.now();
  buildProgress.hidden = false;
  buildProgress.classList.remove("complete", "error");
  progressTimer = window.setInterval(updateElapsedTime, 1000);
  setBuildProgress({ percent: 3, stage: "正在启动转换引擎", detail: "首次启动可能需要几秒，请稍候…" });
  updateElapsedTime();
}

function setBuildProgress(payload: BuildProgressPayload) {
  const percent = Math.max(0, Math.min(100, Math.round(payload.percent)));
  progressStage.textContent = payload.stage;
  progressPercent.textContent = `${percent}%`;
  progressBar.style.width = `${percent}%`;
  progressDetail.textContent = payload.detail || "正在处理…";
  if (percent < 100) buildBtn.textContent = `正在生成 ${percent}%`;
}

function finishBuildProgress(success: boolean, detail?: string) {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
  updateElapsedTime();
  buildProgress.classList.toggle("complete", success);
  buildProgress.classList.toggle("error", !success);
  setBuildProgress({
    percent: success ? 100 : Math.max(3, Number.parseInt(progressPercent.textContent || "0", 10) || 3),
    stage: success ? "生成完成" : "生成失败",
    detail: detail || (success ? "PPT 与预览已生成" : "请查看下方错误提示"),
  });
}

function handleProgressLine(line: string) {
  const prefix = "EXAMPPT_PROGRESS:";
  if (!line.startsWith(prefix)) return false;
  try {
    const payload = JSON.parse(line.slice(prefix.length)) as BuildProgressPayload;
    setBuildProgress(payload);
  } catch {
    // Ignore malformed progress lines without affecting the final build result.
  }
  return true;
}

function boundaryFilePath() {
  if (!state.sourcePath) return null;
  const withoutPdf = state.sourcePath.replace(/\.pdf$/i, "");
  return `${withoutPdf}_ExamPPT\\boundaries.json`;
}

function effectiveBoundary(question: ManifestQuestion) {
  return state.boundaryOverrides[question.number] || {
    page: question.anchor.page,
    top: question.anchor.top,
  };
}

function updateBoundaryControls() {
  const ready = nativeTauri && Boolean(state.manifest && state.currentQuestion);
  boundaryToggle.disabled = !ready;
  boundaryToggle.classList.toggle("active", state.boundaryEditMode);
  boundaryToggle.textContent = state.boundaryEditMode ? "完成调整" : "调整边界";
  applyBoundaries.hidden = !state.boundaryEditMode;
  applyBoundaries.disabled = !state.boundaryDirty;
}

function updateBoundaryLine() {
  if (!state.boundaryEditMode || !state.manifest || !state.currentQuestion || canvas.hidden) {
    boundaryLine.hidden = true;
    return;
  }

  const question = state.manifest.questions.find((q) => q.number === state.currentQuestion);
  if (!question) {
    boundaryLine.hidden = true;
    return;
  }
  const boundary = effectiveBoundary(question);
  if (boundary.page !== state.currentPage || canvas.clientHeight <= 0 || canvas.height <= 0) {
    boundaryLine.hidden = true;
    return;
  }

  const displayScale = canvas.clientHeight / canvas.height;
  const y = boundary.top * state.zoom * displayScale;
  boundaryLine.style.left = `${canvas.offsetLeft}px`;
  boundaryLine.style.width = `${canvas.clientWidth}px`;
  boundaryLine.style.top = `${canvas.offsetTop + y}px`;
  boundaryLabel.textContent = `第 ${question.number} 题起始线 · 拖动调整`;
  boundaryLine.hidden = false;
}

async function loadBoundaryDraft() {
  state.boundaryOverrides = {};
  state.boundaryDirty = false;
  const path = boundaryFilePath();
  if (!nativeTauri || !path) return;
  try {
    const raw = await invoke<string>("read_text_file", { path });
    const parsed = JSON.parse(raw) as { question_starts?: Record<string, BoundaryOverride> };
    for (const [number, value] of Object.entries(parsed.question_starts || {})) {
      state.boundaryOverrides[Number(number)] = value;
    }
  } catch {
    // No saved manual adjustments for this PDF yet.
  }
}

async function saveBoundaryDraft() {
  const path = boundaryFilePath();
  if (!nativeTauri || !path) throw new Error("当前文件无法保存人工边界。");
  const question_starts = Object.fromEntries(
    Object.entries(state.boundaryOverrides).map(([number, value]) => [number, {
      page: value.page,
      top: Number(value.top.toFixed(3)),
    }]),
  );
  const content = JSON.stringify({ question_starts }, null, 2);
  await invoke("write_text_file", { path, content });
  state.boundaryDirty = false;
  updateBoundaryControls();
  return path;
}

async function openPdfBytes(bytes: Uint8Array, name: string, sourcePath: string | null = null) {
  state.sourcePath = sourcePath;
  state.fileName = name;
  state.currentPage = 1;
  state.summary = null;
  state.manifest = null;
  state.currentQuestion = null;
  state.boundaryEditMode = false;
  state.boundaryOverrides = {};
  state.boundaryDirty = false;
  resetResult();
  await loadBoundaryDraft();

  fileStatus.textContent = state.fileSize
    ? `${name} · ${formatSize(state.fileSize)}`
    : name;

  pdfDoc = await pdfjsLib.getDocument({ data: bytes }).promise;
  state.pageCount = pdfDoc.numPages;

  dropZone.hidden = true;
  canvas.hidden = false;
  prevPage.disabled = true;
  nextPage.disabled = state.pageCount <= 1;
  buildBtn.disabled = !nativeTauri || !sourcePath;
  buildBtn.textContent = nativeTauri ? "生成讲题 PPT" : "桌面版可生成";

  await renderPage();
}

async function openNativePdf(path: string) {
  const raw = await invoke<number[]>("read_file_bytes", { path });
  state.fileSize = raw.length;
  await openPdfBytes(new Uint8Array(raw), baseName(path), path);
}

async function openBrowserPdf(file: File) {
  state.fileSize = file.size;
  await openPdfBytes(new Uint8Array(await file.arrayBuffer()), file.name, null);
}

async function renderPage() {
  if (!pdfDoc) return;
  const page = await pdfDoc.getPage(state.currentPage);
  const viewport = page.getViewport({ scale: state.zoom });
  const ctx = canvas.getContext("2d")!;
  canvas.width = Math.ceil(viewport.width);
  canvas.height = Math.ceil(viewport.height);
  canvas.style.width = "min(100%, " + viewport.width + "px)";
  canvas.style.height = "auto";
  await page.render({ canvasContext: ctx, viewport, canvas }).promise;
  requestAnimationFrame(updateBoundaryLine);

  pageInfo.textContent = `${state.currentPage} / ${state.pageCount}`;
  prevPage.disabled = state.currentPage <= 1;
  nextPage.disabled = state.currentPage >= state.pageCount;
}

async function chooseFile() {
  if (nativeTauri) {
    const selected = await openDialog({
      multiple: false,
      directory: false,
      filters: [{ name: "PDF 试卷", extensions: ["pdf"] }],
    });
    if (typeof selected === "string") {
      try {
        footerNote.textContent = "正在读取 PDF…";
        await openNativePdf(selected);
        footerNote.textContent = "PDF 已载入，可以生成讲题 PPT";
      } catch (error) {
        showError(`无法读取 PDF：${String(error)}`);
      }
    }
    return;
  }
  fileInput.click();
}

function resetResult() {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
  progressStartedAt = 0;
  buildProgress.hidden = true;
  buildProgress.classList.remove("complete", "error");
  qaStatus.textContent = "待处理";
  qaStatus.className = "status-pill neutral";
  questionCount.textContent = "—";
  crossPageCount.textContent = "—";
  slideCount.textContent = "—";
  questionList.innerHTML = '<div class="rail-empty">生成后可按题号同步查看 PDF 与 PPT。</div>';
  pptPlaceholder.hidden = false;
  if (pptPreview) {
    pptPreview.remove();
    pptPreview = null;
  }
  slideInfo.textContent = "—";
  openOutput.disabled = true;
  boundaryLine.hidden = true;
  updateBoundaryControls();
  if (state.currentPreviewUrl) {
    URL.revokeObjectURL(state.currentPreviewUrl);
    state.currentPreviewUrl = null;
  }
}

function showError(message: string) {
  qaStatus.textContent = "错误";
  qaStatus.className = "status-pill danger";
  footerNote.textContent = message;
}

function questionPageMap() {
  const map = new Map<number, number>();
  for (const q of state.manifest?.questions || []) {
    map.set(q.number, q.anchor.page);
  }
  return map;
}

function slideForQuestion(q: number) {
  return state.summary?.slides.find((slide) => slide.questions.includes(q)) || null;
}

async function showPreviewSlide(slideNumber: number) {
  const path = state.summary?.preview_files[slideNumber - 1];
  if (!path || !nativeTauri) return;

  const raw = await invoke<number[]>("read_file_bytes", { path });
  const blob = new Blob([new Uint8Array(raw)], { type: "image/png" });

  if (state.currentPreviewUrl) URL.revokeObjectURL(state.currentPreviewUrl);
  state.currentPreviewUrl = URL.createObjectURL(blob);

  if (!pptPreview) {
    pptPreview = document.createElement("img");
    pptPreview.className = "ppt-preview-image";
    pptPreview.alt = "PPT preview";
    document.querySelector("#pptViewer")?.appendChild(pptPreview);
  }
  pptPreview.src = state.currentPreviewUrl;
  pptPlaceholder.hidden = true;
  slideInfo.textContent = `第 ${slideNumber} / ${state.summary?.preview_files.length || 0} 页`;
}

async function setCurrentQuestion(q: number) {
  state.currentQuestion = q;
  updateBoundaryControls();

  for (const button of questionList.querySelectorAll<HTMLButtonElement>(".question-item")) {
    button.classList.toggle("active", Number(button.dataset.q) === q);
  }

  const page = questionPageMap().get(q);
  if (page) {
    state.currentPage = page;
    await renderPage();
  }

  const slide = slideForQuestion(q);
  if (slide) await showPreviewSlide(slide.slide);
  requestAnimationFrame(updateBoundaryLine);
}

function renderBuildResult() {
  if (!state.summary) return;

  const pass = state.summary.status === "PASS";
  qaStatus.textContent = pass ? "检查通过" : "需确认";
  qaStatus.className = pass ? "status-pill pass" : "status-pill warning";

  questionCount.textContent = String(state.summary.question_count);
  crossPageCount.textContent = state.summary.cross_page_questions.length
    ? state.summary.cross_page_questions.join("、")
    : "0";
  slideCount.textContent = String(state.summary.slides.length);

  questionList.innerHTML = "";
  const cross = new Set(state.summary.cross_page_questions);
  for (let q = 1; q <= state.summary.question_count; q += 1) {
    const button = document.createElement("button");
    button.className = "question-item";
    button.dataset.q = String(q);
    button.innerHTML = `
      <span class="q-number">${q}</span>
      <span class="q-label">第 ${q} 题</span>
      ${cross.has(q) ? '<span class="q-tag">跨页已合并</span>' : '<span class="q-ok">✓</span>'}
    `;
    button.addEventListener("click", () => void setCurrentQuestion(q));
    questionList.appendChild(button);
  }

  openOutput.disabled = false;
  const title = state.summary.title || state.manifest?.name || "试卷";
  footerNote.textContent = pass
    ? `《${title}》生成完成 · QA 通过 · 点击题号可同步核对 PDF 与 PPT`
    : `《${title}》已生成，但存在需要人工确认的项目`;
}

async function buildPpt() {
  if (!nativeTauri || !state.sourcePath) return;
  if (state.boundaryDirty) {
    footerNote.textContent = "边界调整尚未应用，请点击“应用并重新生成”。";
    return;
  }

  const oldText = buildBtn.textContent;
  buildBtn.disabled = true;
  qaStatus.textContent = "处理中";
  qaStatus.className = "status-pill working";
  footerNote.textContent = "正在生成，请查看中间进度；界面会持续显示已用时间。";
  beginBuildProgress();

  try {
    const args = ["build", state.sourcePath];
    const boundaries = boundaryFilePath();
    if (boundaries && Object.keys(state.boundaryOverrides).length > 0) {
      args.push("--boundaries", boundaries);
    }

    const command = Command.sidecar("binaries/examppt-core", args);
    const stdoutLines: string[] = [];
    const stderrLines: string[] = [];

    command.stdout.on("data", (line) => {
      stdoutLines.push(line);
    });
    command.stderr.on("data", (line) => {
      const text = line.trim();
      if (!handleProgressLine(text) && text) stderrLines.push(text);
    });

    const completed = new Promise<void>((resolve, reject) => {
      command.on("close", () => resolve());
      command.on("error", (error) => reject(new Error(error)));
    });

    await command.spawn();
    await completed;

    const stdout = stdoutLines.join("\n").trim();
    if (!stdout) {
      throw new Error(stderrLines.join("\n") || "ExamPPT Core 未返回结果");
    }

    const summary = JSON.parse(stdout) as BuildSummary;
    state.summary = summary;

    const manifestText = await invoke<string>("read_text_file", { path: summary.manifest });
    state.manifest = JSON.parse(manifestText) as Manifest;

    renderBuildResult();
    if (summary.question_count > 0) await setCurrentQuestion(1);
    finishBuildProgress(
      true,
      `${summary.title || state.manifest.name} · ${summary.question_count} 道题 · ${summary.slides.length} 页`,
    );
  } catch (error) {
    const message = String(error);
    finishBuildProgress(false, "生成未完成，请查看错误原因");
    if (/PermissionError|permission denied|being used by another process/i.test(message)) {
      showError("生成失败：输出 PPT 正被 PowerPoint/WPS 占用，请关闭旧文件后重试。");
    } else {
      showError(`生成失败：${message}`);
    }
  } finally {
    buildBtn.disabled = false;
    buildBtn.textContent = oldText || "生成讲题 PPT";
  }
}

let draggingBoundary = false;

function boundaryTopFromPointer(event: PointerEvent) {
  const rect = canvas.getBoundingClientRect();
  if (rect.height <= 0) return null;
  const displayY = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
  const canvasY = displayY * (canvas.height / rect.height);
  return canvasY / state.zoom;
}

function updateBoundaryFromPointer(event: PointerEvent) {
  if (!draggingBoundary || !state.currentQuestion || !state.manifest) return;
  const question = state.manifest.questions.find((q) => q.number === state.currentQuestion);
  const top = boundaryTopFromPointer(event);
  if (!question || top === null) return;

  const previous = state.manifest.questions.find((q) => q.number === question.number - 1);
  const next = state.manifest.questions.find((q) => q.number === question.number + 1);
  let minTop = 1;
  let maxTop = canvas.height / state.zoom - 1;

  if (previous) {
    const prevBoundary = effectiveBoundary(previous);
    if (prevBoundary.page === state.currentPage) minTop = Math.max(minTop, prevBoundary.top + 2);
  }
  if (next) {
    const nextBoundary = effectiveBoundary(next);
    if (nextBoundary.page === state.currentPage) maxTop = Math.min(maxTop, nextBoundary.top - 2);
  }

  state.boundaryOverrides[question.number] = {
    page: state.currentPage,
    top: Math.max(minTop, Math.min(maxTop, top)),
  };
  state.boundaryDirty = true;
  updateBoundaryControls();
  updateBoundaryLine();
  footerNote.textContent = `已调整第 ${question.number} 题起始线，点击“应用并重新生成”后生效。`;
}

boundaryToggle.addEventListener("click", () => {
  if (!state.manifest || !state.currentQuestion) return;
  if (state.boundaryEditMode && state.boundaryDirty) {
    footerNote.textContent = "当前有未应用的边界调整，请先点击“应用并重新生成”。";
    return;
  }
  state.boundaryEditMode = !state.boundaryEditMode;
  updateBoundaryControls();
  updateBoundaryLine();
  footerNote.textContent = state.boundaryEditMode
    ? "拖动左侧红色起始线调整当前题边界；调整后需点击“应用并重新生成”。"
    : "已退出边界调整模式。";
});

applyBoundaries.addEventListener("click", async () => {
  if (!state.boundaryDirty) return;
  try {
    applyBoundaries.disabled = true;
    footerNote.textContent = "正在保存人工边界并重新生成…";
    await saveBoundaryDraft();
    await buildPpt();
  } catch (error) {
    showError(`应用边界失败：${String(error)}`);
  }
});

boundaryLine.addEventListener("pointerdown", (event) => {
  if (!state.boundaryEditMode) return;
  draggingBoundary = true;
  boundaryLine.setPointerCapture(event.pointerId);
  boundaryLine.classList.add("dragging");
  event.preventDefault();
});

boundaryLine.addEventListener("pointermove", (event) => {
  updateBoundaryFromPointer(event);
});

boundaryLine.addEventListener("pointerup", (event) => {
  if (!draggingBoundary) return;
  updateBoundaryFromPointer(event);
  draggingBoundary = false;
  boundaryLine.releasePointerCapture(event.pointerId);
  boundaryLine.classList.remove("dragging");
});

boundaryLine.addEventListener("pointercancel", () => {
  draggingBoundary = false;
  boundaryLine.classList.remove("dragging");
});

window.addEventListener("resize", () => requestAnimationFrame(updateBoundaryLine));

fileInput.addEventListener("change", async () => {
  const file = fileInput.files?.[0];
  if (file) await openBrowserPdf(file);
});

document.querySelector("#openFile")?.addEventListener("click", () => void chooseFile());
document.querySelector("#openFileTop")?.addEventListener("click", () => void chooseFile());
buildBtn.addEventListener("click", () => void buildPpt());

prevPage.addEventListener("click", async () => {
  if (state.currentPage > 1) {
    state.currentPage -= 1;
    await renderPage();
  }
});

nextPage.addEventListener("click", async () => {
  if (state.currentPage < state.pageCount) {
    state.currentPage += 1;
    await renderPage();
  }
});

openOutput.addEventListener("click", async () => {
  if (nativeTauri && state.summary?.pptx) {
    try {
      await invoke("reveal_path", { path: state.summary.pptx });
    } catch (error) {
      showError(`无法打开输出位置：${String(error)}`);
    }
  }
});

viewer.addEventListener("dragover", (event) => {
  event.preventDefault();
  viewer.classList.add("dragging");
});

viewer.addEventListener("dragleave", () => viewer.classList.remove("dragging"));

viewer.addEventListener("drop", async (event) => {
  event.preventDefault();
  viewer.classList.remove("dragging");
  if (nativeTauri) {
    footerNote.textContent = "桌面版拖入支持将在下一步接入；当前请点击“选择 PDF”。";
    return;
  }
  const file = event.dataTransfer?.files?.[0];
  if (file?.type === "application/pdf" || file?.name.toLowerCase().endsWith(".pdf")) {
    await openBrowserPdf(file);
  }
});


async function bootstrapSmokeTest() {
  if (!nativeTauri) return;
  try {
    const pdf = await invoke<string | null>("smoke_test_pdf");
    if (!pdf) return;
    footerNote.textContent = "自动化验收：正在载入测试 PDF…";
    await openNativePdf(pdf);
    const autoBuild = await invoke<boolean>("smoke_test_auto_build");
    if (autoBuild) {
      footerNote.textContent = "自动化验收：正在生成 PPT…";
      await buildPpt();
    }
  } catch (error) {
    showError(`自动化验收失败：${String(error)}`);
  }
}

void bootstrapSmokeTest();
