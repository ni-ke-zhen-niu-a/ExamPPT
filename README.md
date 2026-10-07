# ExamPPT

**PDF试卷无损转PPT 工具**

把 PDF 试卷转换成真正适合课堂讲评的 PPT：**原题不改、顺序不变、整题不跨页、视觉字号一致，并执行自动 QA。**

> 当前状态：Pre-alpha。核心排版与 QA 规则已经通过真实九年级数学试卷回归测试，GUI、自动切题、安装包与 WPS/PowerPoint 双渲染正在开发中。

## 目标

ExamPPT 不是通用 PDF 转 PPT，也不负责 AI 解题。它只做一件事：把现有试卷忠实地“编译”为课堂可直接讲评的 PPT。

核心原则：

- 原题内容不改写；
- 题目顺序不改变；
- 一道题不拆到两张幻灯片；
- 同一份试卷保持统一视觉尺度；
- 内容放不下时不偷偷缩小字号；
- 生成后必须自动检查并提供 PDF ↔ PPT 对照；
- 输出兼容 Microsoft PowerPoint 与 WPS 演示。

## 计划中的 V0.1

- PDF → 课堂讲评 PPT
- 自动切题 + 手动调整兜底
- 普通讲评版
- 答案逐步揭示版
- 左侧原 PDF / 右侧最终 PPT，同题联动
- 漏题、重复、乱序、跨页、越界、视觉尺度 QA
- PowerPoint / WPS 放映兼容
- Windows 10 / 11 x64
- 安装版 + 便携版
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

## 开源与下载

- GitHub：源代码主仓库
- Gitee：中国镜像与国内下载
- 正式版将同时提供 Setup.exe 与 Portable.zip

项目采用 Apache-2.0 许可证。
