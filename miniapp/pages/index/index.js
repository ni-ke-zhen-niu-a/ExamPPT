const app = getApp();

Page({
  data: {
    filePath: "",
    fileName: "",
    fileSize: "",
    jobId: "",
    percent: 0,
    stage: "等待处理",
    busy: false,
    done: false,
    downloadReady: false,
    questionCount: 0,
    slideCount: 0,
    error: ""
  },

  pollTimer: null,

  onUnload() {
    if (this.pollTimer) {
      clearTimeout(this.pollTimer);
      this.pollTimer = null;
    }
  },

  choosePdf() {
    wx.chooseMessageFile({
      count: 1,
      type: "file",
      extension: ["pdf"],
      success: (res) => {
        const file = res.tempFiles[0];
        if (!file.name.toLowerCase().endsWith(".pdf")) {
          wx.showToast({ title: "请选择PDF文件", icon: "none" });
          return;
        }

        this.setData({
          filePath: file.path,
          fileName: file.name,
          fileSize: this.formatSize(file.size),
          jobId: "",
          percent: 0,
          stage: "等待处理",
          done: false,
          downloadReady: false,
          questionCount: 0,
          slideCount: 0,
          error: ""
        });
      }
    });
  },

  startJob() {
    if (!this.data.filePath || this.data.busy) return;

    this.setData({
      busy: true,
      done: false,
      downloadReady: false,
      percent: 1,
      stage: "正在上传PDF",
      error: ""
    });

    wx.uploadFile({
      url: `${app.globalData.apiBase}/api/jobs`,
      filePath: this.data.filePath,
      name: "file",
      formData: {
        original_name: this.data.fileName
      },
      success: (res) => {
        if (res.statusCode < 200 || res.statusCode >= 300) {
          this.fail(`上传失败（${res.statusCode}）`);
          return;
        }

        try {
          const job = JSON.parse(res.data);
          this.applyJob(job);
          this.schedulePoll();
        } catch (error) {
          this.fail("服务器返回的数据无法解析");
        }
      },
      fail: (error) => {
        this.fail(error.errMsg || "上传失败");
      }
    });
  },

  schedulePoll() {
    if (!this.data.jobId) return;

    if (this.pollTimer) clearTimeout(this.pollTimer);
    this.pollTimer = setTimeout(() => {
      wx.request({
        url: `${app.globalData.apiBase}/api/jobs/${this.data.jobId}`,
        method: "GET",
        success: (res) => {
          if (res.statusCode !== 200) {
            this.fail(`查询任务失败（${res.statusCode}）`);
            return;
          }

          this.applyJob(res.data);
          if (!["completed", "needs_review", "failed"].includes(res.data.status)) {
            this.schedulePoll();
          }
        },
        fail: (error) => {
          this.fail(error.errMsg || "无法连接服务器");
        }
      });
    }, 900);
  },

  applyJob(job) {
    const terminal = ["completed", "needs_review", "failed"].includes(job.status);
    const failed = job.status === "failed";

    this.setData({
      jobId: job.id || this.data.jobId,
      percent: Number(job.percent || 0),
      stage: job.stage || "正在处理",
      busy: !terminal,
      done: terminal && !failed,
      downloadReady: Boolean(job.download_ready),
      questionCount: Number(job.question_count || 0),
      slideCount: Number(job.slide_count || 0),
      error: failed ? (job.error || "生成失败") : ""
    });
  },

  downloadPpt() {
    if (!this.data.jobId || !this.data.downloadReady) return;

    wx.showLoading({ title: "正在下载" });
    wx.downloadFile({
      url: `${app.globalData.apiBase}/api/jobs/${this.data.jobId}/download`,
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode !== 200) {
          wx.showToast({ title: "下载失败", icon: "none" });
          return;
        }

        wx.openDocument({
          filePath: res.tempFilePath,
          fileType: "pptx",
          showMenu: true,
          fail: () => {
            wx.showToast({ title: "PPT已下载，请从文件中打开", icon: "none" });
          }
        });
      },
      fail: (error) => {
        wx.hideLoading();
        wx.showToast({ title: error.errMsg || "下载失败", icon: "none" });
      }
    });
  },

  fail(message) {
    if (this.pollTimer) {
      clearTimeout(this.pollTimer);
      this.pollTimer = null;
    }
    this.setData({
      busy: false,
      stage: "处理失败",
      error: message
    });
  },

  formatSize(bytes) {
    if (!bytes) return "";
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
});
