# Hosted-demo E2E and alpha-readiness plan

This is an operator-owned release gate, not a request for players to smoke-test
the product. Do not invite alpha or beta players until the automated gate and a
maintainer review are green.

## Automated gate — every main deployment

The `Hosted demo E2E` CI job uses the same API base URL as the GitHub Pages
client and performs the browser's real startup sequence:

1. `GET /api/v1/health` must return `200` and `{"status":"ok"}`.
2. `POST /api/v1/session` must create a session and allow the Pages origin.
3. `POST /api/v1/turn` with `look` must return `200`, `status: ok`, the same
   session id, opening lines, and a turn-zero state.

The job is required to have `VITE_API_BASE_URL` configured. A deployment that
is healthy at Railway but cannot narrate an opening fails this gate.

## Maintainer review — before an invitation

After the automated gate passes, a maintainer reviews one captured hosted-demo
transcript. Confirm that the opening is Cloudflare-authored, grounded in the
committed scene, free of secrets or implementation text, and followed by one
ordinary action with a coherent result. Record any failure as a release bug;
do not ask a player to diagnose it.

## Alpha feedback — only after the gate

Players are then invited to explore, not to verify uptime. Ask open-ended
questions about agency, clarity, tension, and delight; retain the transcript
only as product feedback. Any availability, continuity, secrecy, or save/load
failure returns the build to the operator gate before further invitations.
