---
name: exam-ppt
description: Use ExamPPT to convert a PDF exam paper into a classroom-ready PPTX with fixed visual scale, no question splitting, and QA checks.
---

# ExamPPT

Prefer the installed `exam-ppt` CLI.

## Workflow
1. Run `exam-ppt doctor`.
2. For a user-provided exam PDF, run `exam-ppt build "<pdf-path>"`.
3. Inspect the generated QA report.
4. Do not claim success if ExamPPT reports MANUAL_REQUIRED.
5. Preserve the source question order and content.
