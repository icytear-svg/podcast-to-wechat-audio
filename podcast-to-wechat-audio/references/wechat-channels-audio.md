# WeChat Channels Audio Notes

Use these notes when automating WeChat Channels Assistant audio publishing.

## Known Page Behavior

- The audio management UI is available from WeChat Channels Assistant under content management -> audio.
- The publish button may be labeled either `发表音频` or `发布音频`; match both.
- The create form can be opened directly at `https://channels.weixin.qq.com/platform/post/createAudio`.
- Important page content is often inside iframes. Search and interact across the main page and every frame.
- Uploading a cover opens an `编辑音频封面` crop/confirmation dialog. It is safe to click `确认` after uploading the intended cover.
- Do not block solely on visible cover progress percentages. The form may be submittable while a percentage is still shown.
- Prefer checking that the submit button is visible and enabled.
- A visible audio file card is not enough to prove the audio is accepted. If the form still shows `请上传音频` or `音频信息不符合要求`, keep waiting or fail before clicking publish.

## Media Constraints Observed

- Audio accepts WAV and MP3. Podcast RSS sources often provide M4A, which should be transcoded before upload.
- Use MP3 at 128 kbps as a practical default. Keep the source audio unchanged.
- Cover images should be square enough for the crop dialog and under the page's size limit.

## Automation Guardrails

- Use a persistent browser profile directory such as `.wechat-profile/` in the project folder, not in the skill folder.
- Keep `pause` as the default mode. Require explicit user confirmation before using `publish`.
- Take screenshots for filled forms and errors. Store them in project-local `logs/screenshots/`.
- Do not mark a queue row as `uploaded` immediately after clicking publish. Re-open the audio manager and verify the new row by title fragment or episode number first.
- After each submitted item, navigate directly to the create-audio URL for the next item instead of relying on list-page state.
- When retries are needed, reset only the affected queue rows from `error` to `pending`.
