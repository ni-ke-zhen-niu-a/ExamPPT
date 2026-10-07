---
name: exam-ppt
description: 将PDF试卷转换为课堂讲评PPT，并检查漏题、跨页、越界和视觉字号一致性。
---

# ExamPPT

调用已安装的 `exam-ppt` 命令行工具。

## 默认流程
1. 先执行 `exam-ppt doctor`。
2. 用户要求转换试卷时执行 `exam-ppt build "<PDF路径>"`。
3. 读取 QA 结果；如果存在 MANUAL_REQUIRED，明确提示用户检查，不要直接宣称成功。
4. 不修改题目内容和顺序。
