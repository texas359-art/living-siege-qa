# Living Siege — real 3D visual QA

Dedicated QA repository for the published Bastion scene. No game source, private account data or credentials are stored here. No other project is changed.

Target: https://living-siege.starmedved.chatgpt.site/bastion-test?v=6

## Checks and evidence

- An actual WebGL2 context backed by ANGLE / SwiftShader.
- Browser command-line audit: sandbox enabled, no unsafe SwiftShader, no web-security/TLS bypass.
- Real GLB and embedded texture decoding, 41 bones and actual animation clips.
- GPU pixels with/without the 3D actors; empty canvas/background alone must fail.
- Canvas-only screenshots: Idle, Walk, Attack, Hit, Death.
- Close-up captures use the real interactive camera; the battle uses a side view.
- Independent foot/hand bone movement, camera orbit and zoom.
- Continuous real-time battle recording: movement, attacks, HP reduction and death.
- `battle.mp4` is cropped from the original recording, with no speed-up or frame interpolation; the full `.webm` source is retained.
- JavaScript, render and network errors; responsive 390×844 layout.

This does not certify commercial art quality or real iPhone performance. A human must inspect the screenshots/video; physical iPhone Safari remains a separate check.

## Execution

Standard public-repository Ubuntu 22.04 runner, pinned Playwright 1.55.0 matching the provided `texas359-art/-anomaly-lab` reference. Chromium is installed by official `npx playwright install --with-deps chromium` on the runner, never in ChatGPT Work. No sandbox policy changes or paid services.

The workflow runs on changes to the QA files or manual dispatch. It stops if the repository becomes private. All results, including exact failure logs, are saved as Actions Artifacts for 7 days.

Locally, use a non-root account in an environment that permits the browser sandbox:

```sh
npm install --ignore-scripts
npx playwright install --with-deps chromium
npm test
```

If sandboxing or WebGL is unavailable, report the failure; do not add security-disabling flags.
