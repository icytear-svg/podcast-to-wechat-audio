# 隐私与开源清单 / Privacy And Open Source Checklist

从播客同步到视频号的迁移项目中发布代码或产物前，请使用这份清单。

Use this checklist before publishing code or artifacts from a podcast-to-WeChat migration.

## 永远不要发布 / Never Publish

- 真实 RSS feed URL，除非所有者明确希望公开。
- Real RSS feed URLs unless the owner explicitly wants them public.
- `data/` 中生成的队列文件。
- Generated queue files in `data/`.
- 下载的封面、源音频、转码后的 MP3 或任何 `downloads/` 内容。
- Downloaded covers, source audio, transcoded MP3 files, or any `downloads/` contents.
- `.wechat-profile/` 中的浏览器登录态。
- Browser login state in `.wechat-profile/`.
- `logs/` 中的截图、debug JSON、trace 或日志。
- Screenshots, debug JSON, traces, or logs in `logs/`.
- 账号名称、个人联系方式、cookies、tokens 或平台标识符。
- Account names, personal contact details, cookies, tokens, or platform identifiers.

## 可以安全发布 / Safe To Publish

- 不包含默认真实 feed URL 的通用脚本。
- Generic scripts with no default feed URL.
- `requirements.txt`。
- `requirements.txt`.
- 使用 `<RSS_URL>` 等占位符的示例命令。
- Example commands that use placeholders such as `<RSS_URL>`.
- 关于页面行为的通用文档，前提是不包含私人账号数据。
- Documentation about observed page behavior, as long as it contains no private account data.
- 排除生成数据和登录态的 `.gitignore` 规则。
- `.gitignore` rules that exclude generated data and login state.

## 推荐 `.gitignore` / Recommended `.gitignore`

```gitignore
data/
downloads/
logs/
.wechat-profile/
__pycache__/
*.pyc
*.part
```

## 发布默认值 / Release Defaults

- 默认使用 dry-run 或 pause 行为。
- Default to dry-run or pause behavior.
- 公开发布必须要求显式参数或命令。
- Make public publishing require an explicit flag or command.
- 提醒用户：他们需要自行遵守平台条款，并确认对发布音频拥有版权或授权。
- Mention that users are responsible for complying with platform terms and copyright obligations for the audio they publish.
