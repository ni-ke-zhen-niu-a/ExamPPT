# Desktop GUI V0.1

ExamPPT 桌面版采用 **Tauri 2 + Vanilla TypeScript + PDF.js + Python sidecar**。

## 为什么这样拆

- Tauri 只负责桌面窗口、文件选择、安装包与进程调度；
- PDF.js 负责左侧原始 PDF 的本地预览；
- ExamPPT Core 继续作为唯一转换内核；
- Python Core 使用 PyInstaller 打包成 sidecar，普通老师不需要安装 Python；
- GUI 不复制排版算法，因此 CLI、WorkBuddy、Codex 与桌面版输出保持一致。

## 当前界面

三栏结构：

1. 左侧：原始 PDF；
2. 中间：题目导航与 QA 状态；
3. 右侧：PPT 16:9 放映预览。

生成完成后，点击任意题号：

- 左侧自动跳到该题所在的 PDF 页；
- 右侧自动跳到包含该题的 PPT 页；
- 跨页题显示“跨页已合并”；
- QA 状态显示 PASS 或需人工确认。

## 当前技术状态

已完成：

- 桌面界面骨架；
- PDF.js 本地 PDF 预览；
- ExamPPT Core sidecar 打包脚本；
- sidecar 自动切题 / PPT / QA / 预览输出；
- 题号 → PDF 页 → PPT 页的同步数据结构；
- Windows current-user NSIS 安装模式配置。

待完成：

- Tauri Windows 原生编译与安装包；
- 原生拖放 PDF；
- 手动拖动题目边界；
- WPS 实机 QA；
- 答案逐步揭示模式。

## Sidecar

构建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_sidecar.ps1
```

生成的本地构建文件：

`app/desktop/src-tauri/binaries/examppt-core-x86_64-pc-windows-msvc.exe`

该二进制不提交 Git，正式 Release / CI 在构建阶段生成。
