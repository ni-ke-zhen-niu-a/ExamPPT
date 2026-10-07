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
          <div class="pager">
            <button id="prevPage" disabled>‹</button>
            <span id="pageInfo">— / —</span>
            <button id="nextPage" disabled>›</button>
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

let pdfDoc: Awaited<ReturnType<typeof pdfjsLib.getDocument>["promise"]> | null = null;

function baseName(path: string) {
  return path.split(/[\\/]/).pop() || path;
}

function formatSize(bytes: number | null) {
  if (bytes === null) return "";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function openPdfBytes(bytes: Uint8Array, name: string, sourcePath: string | null = null) {
  state.sourcePath = sourcePath;
  state.fileName = name;
  state.currentPage = 1;
  state.summary = null;
  state.manifest = null;
  state.currentQuestion = null;
  resetResult();

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
  footerNote.textContent = pass
    ? "QA 通过：点击题号可同步核对原 PDF 与 PPT"
    : "存在需要人工确认的项目，请逐题核对";
}

async function buildPpt() {
  if (!nativeTauri || !state.sourcePath) return;

  const oldText = buildBtn.textContent;
  buildBtn.disabled = true;
  buildBtn.textContent = "正在生成…";
  qaStatus.textContent = "处理中";
  qaStatus.className = "status-pill working";
  footerNote.textContent = "正在自动切题、合并跨页题、排版并执行 QA…";

  try {
    const command = Command.sidecar("binaries/examppt-core", [
      "build",
      state.sourcePath,
    ]);
    const output = await command.execute();

    const stdout = output.stdout.trim();
    if (!stdout) throw new Error(output.stderr || "ExamPPT Core 未返回结果");

    const summary = JSON.parse(stdout) as BuildSummary;
    state.summary = summary;

    const manifestText = await invoke<string>("read_text_file", { path: summary.manifest });
    state.manifest = JSON.parse(manifestText) as Manifest;

    renderBuildResult();
    if (summary.question_count > 0) await setCurrentQuestion(1);
  } catch (error) {
    showError(`生成失败：${String(error)}`);
  } finally {
    buildBtn.disabled = false;
    buildBtn.textContent = oldText || "生成讲题 PPT";
  }
}

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
