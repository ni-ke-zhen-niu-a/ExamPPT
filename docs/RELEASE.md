# ExamPPT 发布约定

ExamPPT 使用 GitHub + Gitee 双发布：

- GitHub：源代码主仓库与开发协作。
- Gitee：国内镜像与普通教师下载入口。

## Release 文件名

正式 Windows 版本固定发布：

- `ExamPPT-Setup-x64.exe`
- `ExamPPT-Portable-x64.zip`
- `SHA256SUMS.txt`

文件名保持稳定，方便教程、公众号和小红书长期引用。

## 版本 Release

每个正式版本建立语义化 Release，例如：

- `v0.1.0`
- `v0.1.1`
- `v0.2.0`

版本下载地址形式：

`https://gitee.com/ni-ke-zhen-niu-a/ExamPPT/releases/download/v0.1.0/ExamPPT-Setup-x64.exe`

## 固定“最新版”下载入口

正式发布后额外维护一个 `latest` Release，并始终上传相同文件名：

`https://gitee.com/ni-ke-zhen-niu-a/ExamPPT/releases/download/latest/ExamPPT-Setup-x64.exe`

这样面向国内普通教师的教程只需要长期保留一个安装包链接。

## 发布前硬门槛

只有满足以下条件才上传面向普通教师的安装包：

1. PDF → PPT 主流程可独立完成；
2. 题目顺序、整题不跨页、视觉尺度 QA 通过；
3. PowerPoint 放映检查通过；
4. WPS 打开与放映检查通过；
5. Setup 与 Portable 在干净 Windows 10/11 环境验证；
6. SHA-256 校验文件已生成。

Pre-alpha 阶段不发布误导普通教师的安装包。
