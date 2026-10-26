# Approved 3D lecture presentation

This renderer applies the reviewed 3D professor and navy, ivory and gold boards to all seven lessons. Each published lecture remains a standalone 1920×1080 MP4 containing exactly 30,000 frames at 25 fps (20:00).

The published voice D audio is stream-copied, then checked by hashing the encoded audio packets before and after composition. The transcript, SRT, VTT and chapter sidecars are preserved byte for byte. The scientific material and existing scene definitions remain the source of every board.

The professor appears for 18 seconds in the introduction, seven seconds in each of two transitions, and ten seconds in the conclusion. The remaining time presents the lesson boards and planned reflection pauses. Mouth shapes are prepared from the corresponding original audio segments; body, hand, head and blink motion are rendered from the real rig before publication. Students play ordinary video files and do not run a model or generate speech.

The character and motion files are the exact Microsoft Rocketbox assets used in the approved sample, pinned to commit `0943055db6ec570bcef9f2c8b41c9e5467c808f9`. Their MIT notice is retained beside each video and in MP4 metadata. Browser rendering uses Three.js 0.180.0 and Playwright 1.62.1; phonetic mouth timing uses Rhubarb 1.14.0.

The production workflow runs on `avatar3d-production-20261027`. It retains each output on its own release branch so all seven completed files can be reviewed together before the live branch changes. Reports include the input commit, source text and audio preservation checks, rig evidence, measured duration, full decode result, file hash and final video contact sheet. Browser checks exercise all seven files, Arabic captions, chapter seeking, source links, the complete 1,920-paragraph reader, and desktop and mobile layouts. The published-site smoke check separately verifies the deployed release.
