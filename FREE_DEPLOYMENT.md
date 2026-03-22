# Free Deployment (No Monthly Hosting Bill)

This project can be made public for free by running it on your own machine and exposing it through Cloudflare Tunnel.

## Option A - Fast temporary public link

1. Start from project root
2. Run:
   - `./run_public_free.ps1`
3. Copy the `https://...trycloudflare.com` URL shown by cloudflared
4. Share and test in browser

Notes:
- URL changes each time tunnel restarts
- App is only online while your machine and script are running

## Option B - Stable custom domain for free

Prereqs:
- Domain managed in Cloudflare (free plan)
- cloudflared installed on host machine

Steps:

1. Login:
   - `cloudflared tunnel login`
2. Create tunnel:
   - `cloudflared tunnel create videoforge`
3. Map DNS:
   - `cloudflared tunnel route dns videoforge videoforge.knightlogics.com`
4. Start local app:
   - `./run_prod.ps1`
5. Start hostname tunnel:
   - `cloudflared tunnel --url http://127.0.0.1:5050 --hostname videoforge.knightlogics.com`

When running, the app is reachable at:
- `https://videoforge.knightlogics.com`

## Tradeoffs vs paid host

Pros:
- $0 monthly hosting bill
- Keep full backend app features

Cons:
- Host machine must stay online
- Reliability and uptime depend on your local PC and network
- Not ideal for high traffic or large public usage
