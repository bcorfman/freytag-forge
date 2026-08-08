# Hosted-demo E2E and alpha-readiness plan

This is an operator-owned release gate, not a request for players to smoke-test
the product. Do not invite alpha or beta players until the automated gate and a
maintainer review are green.

## Automated gate — every main deployment

The `Hosted demo post-deploy E2E` workflow uses the same API base URL as the
GitHub Pages client and performs the browser's real startup sequence only after
Railway reports that its deployment has completed:

1. `GET /api/v1/health` must return `200` and `{"status":"ok"}`.
2. `POST /api/v1/session` must create a session and allow the Pages origin.
3. `POST /api/v1/turn` with `look` must return an opening, a turn-zero state,
   and the same session id.
4. A deterministic journey must commit and expose facts through snapshots:
   `front_steps → foyer → market_lane`, then `take route key` must put the key
   in inventory.
5. `save`, a move away, and `load` must restore both the saved location and
   inventory. This proves durable fact authority rather than a one-response
   demo.

The diagnostic workflow is manually dispatchable after a Railway success. The
normal promotion gate is chained directly from the `tests` workflow's verified
Railway deployment rather than a repository-dispatch event. The diagnostic job
requires a deployed API URL;
a service that is healthy at Railway but cannot narrate or preserve state fails
this gate.

## Maintainer review — before an invitation

After the automated gate passes, a maintainer reviews one captured hosted-demo
transcript. Confirm that the opening is Cloudflare-authored, grounded in the
committed scene, and free of secrets or implementation text. Record any
failure as a release bug; do not ask a player to diagnose it.

## Alpha feedback — only after the gate

Players are then invited to explore, not to verify uptime. Ask open-ended
questions about agency, clarity, tension, and delight; retain the transcript
only as product feedback. Any availability, continuity, secrecy, or save/load
failure returns the build to the operator gate before further invitations.
