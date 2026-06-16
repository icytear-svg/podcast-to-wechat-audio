# Claude Code 说明 / Claude Code Instructions

把这个仓库当作一个 Agent Skills 包，以及一组可独立运行的脚本。

Use this repository as an Agent Skills package plus standalone scripts.

如果要在 Claude Code 中以 skill 方式使用，请把 `podcast-to-wechat-audio/` 文件夹安装或复制到 Claude skills 目录，然后在播客 RSS 到视频号音频迁移任务中调用它。

For Claude Code skill-style usage, install or copy the `podcast-to-wechat-audio/` folder into a Claude skills location, then invoke it for podcast RSS to WeChat Channels audio migration tasks.

修改本仓库时 / When modifying this repository:

- 遵循 `AGENTS.md`。
- Follow `AGENTS.md`.
- 不要把真实 RSS、媒体、截图、日志或浏览器 profile 放进 Git。
- Keep real feed URLs, media, screenshots, logs, and browser profiles out of Git.
- 除非用户明确批准真实发布，否则测试时使用 `--submit-mode pause`。
- Use `--submit-mode pause` for tests unless the user explicitly approves live publishing.
- 修改浏览器自动化前，先阅读 `podcast-to-wechat-audio/references/wechat-channels-audio.md`。
- Read `podcast-to-wechat-audio/references/wechat-channels-audio.md` before changing browser automation.
