# 微信视频号音频笔记 / WeChat Channels Audio Notes

自动化视频号助手音频发布时，请使用这些笔记。

Use these notes when automating WeChat Channels Assistant audio publishing.

## 已知页面行为 / Known Page Behavior

- 音频管理页面位于视频号助手的内容管理 -> 音频。
- The audio management UI is available from WeChat Channels Assistant under content management -> audio.
- 发布按钮可能显示为 `发表音频` 或 `发布音频`，自动化时要同时匹配。
- The publish button may be labeled either `发表音频` or `发布音频`; match both.
- 新建音频表单可以直接打开：`https://channels.weixin.qq.com/platform/post/createAudio`。
- The create form can be opened directly at `https://channels.weixin.qq.com/platform/post/createAudio`.
- 重要内容经常在 iframe 内。查找和交互时要同时检查主页面和所有 frame。
- Important page content is often inside iframes. Search and interact across the main page and every frame.
- 上传封面会打开“编辑音频封面”的裁剪/确认弹窗。确认上传的是目标封面后，可以点击“确认”。
- Uploading a cover opens an `编辑音频封面` crop/confirmation dialog. It is safe to click `确认` after uploading the intended cover.
- 不要只因为封面进度条还显示百分比就阻塞。表单有时在百分比仍可见时已经可以提交。
- Do not block solely on visible cover progress percentages. The form may be submittable while a percentage is still shown.
- 优先检查提交按钮是否可见且可用。
- Prefer checking that the submit button is visible and enabled.
- 音频文件卡片可见，不代表平台已经接受音频。如果表单仍显示 `请上传音频` 或 `音频信息不符合要求`，继续等待或在点击发布前失败退出。
- A visible audio file card is not enough to prove the audio is accepted. If the form still shows `请上传音频` or `音频信息不符合要求`, keep waiting or fail before clicking publish.
- 音频上传进度显示 `100%` 后也不要立刻点击发布。继续等待，直到百分比进度元素从页面上消失。
- Do not publish immediately when audio upload progress reaches `100%`. Keep waiting until the visible percentage/progress element disappears.

## 媒体限制观察 / Media Constraints Observed

- 音频接受 WAV 和 MP3。播客 RSS 常见 M4A，上传前建议转码。
- Audio accepts WAV and MP3. Podcast RSS sources often provide M4A, which should be transcoded before upload.
- MP3 128 kbps 是一个实用默认值。保留原始音频文件，不要覆盖源文件。
- Use MP3 at 128 kbps as a practical default. Keep the source audio unchanged.
- 封面应尽量接近正方形，并低于页面大小限制。
- Cover images should be square enough for the crop dialog and under the page's size limit.

## 自动化护栏 / Automation Guardrails

- 使用项目本地的持久化浏览器 profile，例如 `.wechat-profile/`，不要放在 skill 文件夹里。
- Use a persistent browser profile directory such as `.wechat-profile/` in the project folder, not in the skill folder.
- 默认使用 `pause` 模式。公开发布前必须得到用户明确确认。
- Keep `pause` as the default mode. Require explicit user confirmation before using `publish`.
- 为已填写表单和错误状态截图，保存到项目本地 `logs/screenshots/`。
- Take screenshots for filled forms and errors. Store them in project-local `logs/screenshots/`.
- 点击发布后不要立刻把队列写成 `uploaded`。必须重新打开音频管理页，并用标题片段或期号确认新条目存在。
- Do not mark a queue row as `uploaded` immediately after clicking publish. Re-open the audio manager and verify the new row by title fragment or episode number first.
- 每条提交后，下一条直接导航到新建音频 URL，不依赖列表页状态。
- After each submitted item, navigate directly to the create-audio URL for the next item instead of relying on list-page state.
- 需要重试时，只把受影响的队列行从 `error` 改回 `pending`。
- When retries are needed, reset only the affected queue rows from `error` to `pending`.
