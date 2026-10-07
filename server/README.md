# ExamPPT Server

微信小程序/网页端共用的 ExamPPT 后端服务。

## 本地启动

在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8765
```

接口：

- `GET /api/health`
- `POST /api/jobs`：multipart/form-data，字段名 `file`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/download`

当前限制：PDF 最大 30 MB，可用环境变量 `EXAMPPT_MAX_UPLOAD_BYTES` 调整。
