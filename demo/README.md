# Demo video

The 40-second film follows an invented completion claim into its source record and graph.
The message text and timestamps are invented. Example record IDs remain visible.
No real agent incident is claimed.
Background particles illustrate activity. They do not count real agents.

Carter Yoo's Ethogram video informed the pacing. The scenes and animation code are original.
The film uses a paused GSAP timeline and deterministic Canvas drawing.
HyperFrames renders that timeline into a video. Browser playback uses separate controls.

## Build and render

From the repository root, run:

```powershell
cd demo
npm ci
node build.mjs
npx hyperframes telemetry disable
npx hyperframes lint
npx hyperframes snapshot . --at 3,8,14,25,31,37 --output ../artifacts/hyperframes --describe false
npx hyperframes render . --output ../docs/media/swarm-evidence-demo.mp4 --quality delivery --fps 30 --workers 2 --strict
```

`scene.html.in`, `demo.css`, and `demo.js` contain the authored scene.
`build.mjs` creates the renderer entry and browser files.
`static/demo-player.js` provides pause, replay, and seeking at `/demo.html`.
The renderer uses local GSAP. No model API or paid cloud render is required.

The exported MP4 is 1920x1080 at 30 fps, with a 40-second duration.
`docs/media/swarm-evidence-demo.webp` supplies the README animation.
Dependency and source credits appear in [THIRD_PARTY.md](THIRD_PARTY.md).
