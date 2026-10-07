# ExamPPT

**PDF试卷无损转PPT 工具**

把 PDF 试卷转换成真正适合课堂讲评的 PPT：**原题不改、顺序不变、整题不跨页、视觉字号一致，并执行自动 QA。**

> 当前状态：Pre-alpha / v0.0.2。自动切题、跨页题合并、固定规则排版与 PowerPoint 实际渲染回归已经跑通；桌面 GUI 骨架和 PDF↔PPT 同题同步链路已进入实现阶段，人工边界调整、WPS 实机 QA、答案逐步揭示和安装包仍在开发。

## 项目定位

ExamPPT 不是通用 PDF 转 PPT，也不负责 AI 解题。它只做一件事：把现有试卷忠实地“编译”为课堂可直接讲评的 PPT。

核心原则：

- 原题内容不改写；
- 题目顺序不改变；
- 一道题不拆到两张幻灯片；
- 同一份试卷保持统一视觉尺度；
- 内容放不下时不偷偷缩小某一道题；
- 只压缩连续纯白区域，不缩放可见文字、公式和图形；
- 生成后必须自动检查；
- 提供原 PDF ↔ 最终 PPT 同题对照；
- 输出以 Microsoft PowerPoint 和 WPS 演示为主要兼容目标。

## 当前已经跑通

- 数字型 PDF 自动识别题号；
- 连续题号序列校验；
- 自动识别跨页题并合并；
- 自动识别题型分区；
- 统一视觉尺度；
- 动态分页；
- 漏题 / 重复 / 乱序 / 越界 / 跨 PPT 页 QA；
- PowerPoint 1600×900 实际渲染检查；
- CLI 工程骨架；
- Codex Skill / WorkBuddy Skill 骨架；
- GitHub + Gitee 双仓发布基础设施。

真实回归试卷中已实现：25/25 题自动识别，自动分页结果与人工认可版均为 15 页，结构 QA 为 PASS。

## CLI（开发版）

在源码环境中：

```bash
exam-ppt doctor
exam-ppt scan "试卷.pdf"
exam-ppt build "试卷.pdf"
```

可选覆盖页眉中的试卷名称：

```bash
exam-ppt build "试卷.pdf" --title "九年级数学月考模拟试卷2"
```

当前仍是开发版，不建议普通教师直接安装源码环境。正式 V0.1 会提供 Windows 安装版和便携版。

## V0.1 计划

- PDF → 课堂讲评 PPT
- 自动切题 + 手动调整兜底
- 普通讲评版
- 答案逐步揭示版
- 左侧原 PDF / 右侧最终 PPT，同题联动
- PowerPoint / WPS 双兼容验证
- Windows 10 / 11 x64
- `ExamPPT-Setup-x64.exe`
- `ExamPPT-Portable-x64.zip`
- CLI
- Codex Skill
- WorkBuddy Skill
- GitHub + Gitee 双发布

## 暂不做

- AI 解题 / AI 解析
- 账号与登录
- 云端同步
- 学生系统 / 班级管理
- 在线网站
- macOS / Linux / Win7

## 文档

- 自动切题设计：`docs/AUTO_SPLIT.md`
- 产品边界：`docs/PRODUCT_SPEC.md`
- 发布约定：`docs/RELEASE.md`
- 桌面 GUI 设计：`docs/GUI.md`

## 开源仓库

- GitHub 主仓库：https://github.com/ni-ke-zhen-niu-a/ExamPPT
- Gitee 国内镜像：https://gitee.com/ni-ke-zhen-niu-a/ExamPPT

正式可用版发布后，Gitee Release 将作为国内普通教师的主要下载入口，同时提供：

- `ExamPPT-Setup-x64.exe`
- `ExamPPT-Portable-x64.zip`
- `SHA256SUMS.txt`

## 开源协议

Apache-2.0
