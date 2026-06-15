# Privacy And Open Source Checklist

Use this checklist before publishing code or artifacts from a podcast-to-WeChat migration.

## Never Publish

- Real RSS feed URLs unless the owner explicitly wants them public.
- Generated queue files in `data/`.
- Downloaded covers, source audio, transcoded MP3 files, or any `downloads/` contents.
- Browser login state in `.wechat-profile/`.
- Screenshots, debug JSON, traces, or logs in `logs/`.
- Account names, personal contact details, cookies, tokens, or platform identifiers.

## Safe To Publish

- Generic scripts with no default feed URL.
- `requirements.txt`.
- Example commands that use placeholders such as `<RSS_URL>`.
- Documentation about observed page behavior, as long as it contains no private account data.
- `.gitignore` rules that exclude generated data and login state.

## Recommended `.gitignore`

```gitignore
data/
downloads/
logs/
.wechat-profile/
__pycache__/
*.pyc
*.part
```

## Release Defaults

- Default to dry-run or pause behavior.
- Make public publishing require an explicit flag or command.
- Mention that users are responsible for complying with platform terms and copyright obligations for the audio they publish.
