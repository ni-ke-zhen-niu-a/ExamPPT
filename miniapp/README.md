# ExamPPT 微信小程序

当前 V0.1 开发目标：

1. 选择 PDF
2. 上传到 ExamPPT Server
3. 查看真实生成进度
4. 显示题目数 / PPT 页数
5. 下载生成的 PPT

## 本地联调

默认 API：

```
http://127.0.0.1:8765
```

开发者工具本地调试时可使用该地址，并关闭合法域名校验。

真机和正式版必须改成已备案、配置到微信公众平台的 HTTPS 服务域名。

`project.config.json` 当前使用 `touristappid`，导入你自己的微信小程序项目后应替换成真实 AppID。
