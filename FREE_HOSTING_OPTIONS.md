# Free Hosting Options for VideoForge Studio

This document compares realistic zero-cost deployment paths for this app.

## App Requirements (why this is hard)

VideoForge needs:
- Python backend
- FFmpeg runtime for heavy processing
- Large uploads
- Long-running render jobs
- Writable storage for job/output state

## Option 1 - Vercel (direct backend hosting)

Status: Not recommended for current architecture.

Why:
- Function max duration limits are not ideal for long FFmpeg renders
- Request payload limits are restrictive for video uploads
- Storage is external and paid add-ons become likely

Conclusion:
- Vercel is good for the KnightLogics static site and frontend pages
- Vercel is not a good direct host for this heavy media backend as-is

## Option 2 - Cloudflare Tunnel from your own PC

Status: Free and works now.

Pros:
- $0 hosting bill
- No backend rewrite needed
- Already implemented in this repo

Cons:
- App only online when your machine is on
- Reliability depends on your home network and machine uptime
- Temporary URLs rotate unless using named tunnel + Cloudflare DNS

Best use:
- Immediate free launch, demos, proof-of-function

## Option 3 - Oracle Cloud Always Free VM

Status: Best true free 24/7 hosting candidate.

Pros:
- Always Free compute options
- Can run Docker + FFmpeg backend continuously
- Stable public IP/domain possible

Cons:
- More setup complexity than managed platforms
- Capacity is limited and region availability can vary

Best use:
- Free long-term hosting with stable uptime expectations

## Option 4 - Other managed platforms (Render/Railway/Fly)

Status: Usually not fully free for this workload.

Pros:
- Easiest managed deployment

Cons:
- Billing required for stable backend + disk + usage
- Conflicts with strict zero-cost requirement

## Recommendation under strict $0 requirement

1. Immediate: Use Cloudflare Tunnel free path already implemented.
2. Next step: Move to Oracle Always Free VM for stable 24/7 free hosting.
3. Keep KnightLogics site where it is and link out to the app host.

## Implemented assets in this repo

- FREE_DEPLOYMENT.md (Cloudflare free run path)
- run_public_free.ps1 (one-command local + tunnel launcher)
- render.yaml (kept for optional paid production path)

