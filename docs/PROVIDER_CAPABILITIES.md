# Provider capabilities — evidence matrix (M0)

**Accessed:** 2026-11-07 · **Method:** official Google documentation, read through a web-fetch tool that summarizes pages · **Live API calls made:** none · **Spend:** $0.00

Nothing on this page has been checked against the live API. Every row comes from documentation only. Before M5 implements an adapter, it must:

1. re-read the raw docs and the official SDK for exact field names (the fetch tool returned summaries, not raw HTML), and
2. run an opt-in live smoke test with the user's own key.

## Confidence legend

- **HIGH**: stated explicitly on an official Google page.
- **MEDIUM**: official, but partial, inconsistent between pages, or only shown in code examples.
- **UNVERIFIED**: not found in official docs, or contradicted by them.
- **UNSUPPORTED**: official docs say it is not supported.

## Sources

| # | URL | Notes |
|---|---|---|
| S1 | https://aistudio.google.com/docs/omni | Gemini Omni guide. `ai.google.dev/gemini-api/docs/*` 301-redirects to `aistudio.google.com/docs/*` |
| S2 | https://aistudio.google.com/docs/models/gemini-omni-flash | Model card |
| S3 | https://aistudio.google.com/docs/pricing | Pricing page |
| S4 | https://aistudio.google.com/docs/rate-limits | Rate limits |
| S5 | https://aistudio.google.com/docs/billing | Prepay/Postpay, spend caps, balance |
| S6 | https://aistudio.google.com/docs/api-key | Key handling |
| S7 | https://aistudio.google.com/docs/video | Video generation landing page (Veo deprecation notice) |
| S8 | https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-omni/ | Launch blog post (consumer product framing) |
| S9 | https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/omni-flash-preview | Enterprise platform (formerly Vertex AI) preview page |

## Model identity

| Fact | Value | Source | Confidence |
|---|---|---|---|
| Does "Gemini Omni 1.2 Flash" exist? | **Yes.** Model code `gemini-omni-1.2-flash` | S1, S2, S3 | HIGH |
| Stability | Labelled **Stable** on the model card; latest update November 2026 | S2 | HIGH |
| Older version | `gemini-omni-1.1-flash` is Stable. **From 2026-12-03 it routes to 1.2** and bills at 1.2 rates | S1, S2, S3 | HIGH |
| Preview version | `gemini-omni-flash-preview` is shut down on the Gemini API (S2). On the Enterprise platform it was deprecated 2026-11-06 (S9) | S2, S9 | HIGH |
| Veo 3.1 previews | `veo-3.1-generate-preview`, `-fast-`, and `-lite-` were **shut down 2026-10-22**. Google points users to Omni or to GA models on the Enterprise platform | S7 | HIGH |
| Veo GA models on the Enterprise platform | Not researched; IDs not verified | — | UNVERIFIED |
| Omni 1.2 on the Enterprise platform (Vertex) | Named only as a migration target. No model page, region, or pricing found | S9 | UNVERIFIED |

**Proposed M5 target:** `gemini-omni-1.2-flash` through the Gemini Developer API (AI Studio API key). **This needs user approval.**

## API contract (Gemini Developer API)

Field names below come from summarized docs. M5 must recheck them against the raw docs and the SDK.

| Fact | Value | Source | Confidence |
|---|---|---|---|
| API surface | Interactions API. SDK method `interactions.create` | S1 | HIGH |
| Endpoint | `POST https://generativelanguage.googleapis.com/v1beta/interactions` (a **v1beta** path) | S1 | HIGH |
| Auth | Header `x-goog-api-key`. Most Omni examples instead use a `?key=` query parameter. **The app must use the header** so keys never appear in URLs or logs | S1, S6 | MEDIUM (examples disagree) |
| Unrestricted standard keys | Rejected. Key must be restricted to the Gemini API | S6 | HIGH |
| Request shape | `model`; `input` (a string, or a list of `{type: text\|image\|video, data\|uri, mime_type}`); `response_format {type:"video", aspect_ratio, resolution, duration, delivery}`; `generation_config.video_config.task` (optional fallback: `text_to_video`, `image_to_video`, `reference_to_video`, `edit`, `extend`); `previous_interaction_id`; optional `background`, `store`, `stream` | S1 | MEDIUM |
| Generation mode | **Synchronous** create call. Generation time depends on duration, resolution, and load. Long HTTP timeouts are needed. There is no long-running-operation ID | S1 | MEDIUM |
| Response | Interaction `{id, status:"completed", model, object:"interaction", steps[...]}`. The `model_output` step holds video content: base64 `data` (`video/mp4`), or a `uri` when `delivery:"uri"` | S1 | MEDIUM |
| Large outputs | Use `delivery:"uri"` for outputs over 4 MB. Poll `GET /v1beta/files/{id}` until `state` is `ACTIVE` (or `FAILED`). Download with `GET /v1beta/files/{id}:download?alt=media`. The `uri` is guaranteed only in the create response or stream | S1 | MEDIUM |
| `store=false` | Faster, but the result cannot be edited or extended in later turns | S1 | MEDIUM |
| Output retention | Not found | — | UNVERIFIED |
| Cancel | No cancel operation found | — | UNVERIFIED (treat as unsupported) |

## Generation capabilities

| Capability | Value | Source | Confidence |
|---|---|---|---|
| Text-to-video | Yes | S1, S2 | HIGH |
| Image-to-video and first/last-frame interpolation | Yes. Interpolation is 3–10 s | S1, S2 | HIGH |
| Duration | 3–15 s in whole seconds, sent as a string like `"10s"` (default 10 s). Above 15 s returns invalid-argument | S1, S2 | HIGH |
| Resolution | `360p`, `720p` (default), `1080p`, `4k`. 1080p and 4k are **upscaled**. 24 FPS | S1, S2 | HIGH |
| Aspect ratio | `16:9` (default) and `9:16` only | S1 | HIGH |
| Native audio in output | Yes. Spoken dialogue is supported when extending *generated* videos | S1, S2 | HIGH |
| Reference images (character consistency) | Up to 6 total; up to 3 per character; up to 2 characters. Consistency is a model behavior, **not a guarantee** | S1 | HIGH |
| **Reference video input** | Yes, for new generations only (not edit or extend). Each clip is ≤ 3 s. A 3–10 s output allows up to 3 clips; an 11–15 s output allows 1. Audio in reference videos is ignored | S1 | HIGH |
| Edit a video | Yes, via `previous_interaction_id`, or an uploaded input video ≤ 15 s | S1, S2 | HIGH |
| Extend a video | 3–10 s per turn, up to 30 s total. Uses the last 10 s of input as context. Appends to the end only | S1, S2 | HIGH |
| **Audio input or voice reference** | **Not supported in the API**. Voice editing is not supported either. S8 describes voice references in the consumer Gemini app; that does not apply to the API | S1 vs S8 | HIGH (unsupported in API) |
| **Voice locking across shots** | No API mechanism. **Do not claim it.** | S1 | UNSUPPORTED |
| Negative prompt, temperature, top_p, system instructions, stop sequences | Not supported | S1 | UNSUPPORTED |
| YouTube URLs as media input | Not supported | S1 | UNSUPPORTED |
| Input formats | `image/jpeg`, `image/png`, and `video/mp4` appear in examples. No full list | S1 | MEDIUM |
| Languages | English fully supported; other languages untested | S1 | HIGH |
| Watermark | SynthID on all outputs | S1, S8 | HIGH |

## Policy and regional restrictions

| Restriction | Source | Confidence |
|---|---|---|
| Editing or extending **uploaded** videos is unavailable in the EEA, Switzerland, and the UK. Editing generated videos works in all available regions | S1 | HIGH |
| Uploading or editing images of minors is not supported in the EEA, Switzerland, or the UK | S1 | HIGH |
| Uploading or editing images of certain recognizable people is not supported | S1 | HIGH |
| Dialogue cannot be added by extending an *uploaded* video of someone talking | S1 | HIGH |
| Safety filters apply to prompts and outputs, vary by region, and block violating prompts | S1 | HIGH |

The app must surface these as `POLICY` errors and must not try to work around them.

## Pricing (dated rate card, 2026-11-07)

Video billing is **per output token**. The per-second figures are Google's own approximations from footnotes on S3.

| Model | Input | Output | Approx. per second | Free tier | Confidence |
|---|---|---|---|---|---|
| `gemini-omni-1.2-flash` | $1.50 / 1M tokens (text, image, video) | $9.00 / 1M (text); **$12.00 / 1M (video)** | 360p ≈ $0.023/s (1,931 tok/s); 720p ≈ $0.07/s; 1080p ≈ $0.104/s (8,688 tok/s); 4K ≈ $0.209/s (17,376 tok/s) | **No** | HIGH (footnotes are approximate) |
| `gemini-omni-1.1-flash` | $1.50 / 1M | $9.00 (text); $17.50 / 1M (video) | ≈ $0.10/s, no resolution breakdown | No | HIGH |

Notes:

- **Audio:** no separate audio price is listed. Whether native audio is included in the video rate is not stated (**UNVERIFIED**).
- **Enterprise platform:** prices may differ there (S3).
- **Example:** a 10 s 720p clip is about $0.70. Treat this as an estimate. The actual charge depends on token usage reported by the API.

M8 must store this rate card with its date and source, and must flag pricing as stale once it is older than a set age.

## Billing, quota, balance

| Fact | Value | Source | Confidence |
|---|---|---|---|
| Paid access required | Yes. The free tier is "Not supported" for `gemini-omni-1.2-flash` | S3, S4 | HIGH |
| Billing model | Prepay is the default for new accounts: credits are bought in AI Studio ($10–$5,000) and expire after 12 months. Postpay also exists | S5 | HIGH |
| **Programmatic balance or credit API** | **None documented.** Balance is managed only in the AI Studio Billing tab. The app must show "provider balance: unavailable" | S5 | HIGH (absence documented) |
| Zero prepay balance | All keys on the billing account fail with **HTTP 402**. The app maps this to `BILLING` | S5 | HIGH |
| Spend caps | Project caps are experimental. Account-tier caps exist. **Caps are not hard:** overages can occur during about 10 minutes of billing latency, and balances can go negative. The in-app budget (M8) is the user's real guardrail | S5 | HIGH |
| Tier caps | Tier 1 $250; Tier 2 $2,000; Tier 3 $20k–$100k+ per month | S5 | HIGH |
| Rate limits (`gemini-omni-1.2-flash`) | Tier 1: 8 RPM / 40 RPD. Tier 2: 16 RPM / 200 RPD. Tier 3: 40 RPM / 2,000 RPD. Limits are per project; daily limits reset at midnight Pacific | S4 | HIGH |

## Blocked or unverified items, and what they mean for later milestones

1. **No live verification.** M5 must stay mock-only until the user runs an opt-in live test with their own paid key.
2. **Exact request and response field names** are MEDIUM confidence. Re-verify them against the raw docs and the official SDK at M5.
3. **Auth:** the docs disagree (query parameter vs. header). Use the header.
4. **Voice locking and audio references are not available in the API.** M7 must use a separate TTS provider or uploaded audio, and must not claim voice identity.
5. **Provider balance is not retrievable.** M8 shows "unavailable".
6. **Cancel is not documented.** M4 and M5 must treat a submitted generation as non-cancellable and potentially billed.
7. **Output retention is unknown.** M5 must download and store results locally right away.
8. **Synchronous generation with long latency** means M4 needs timeouts, idempotency keys, and duplicate-submit protection, so a frontend retry never double-charges.
9. **Model routing on 2026-12-03** (1.1 → 1.2): pin `gemini-omni-1.2-flash`, and re-check docs before M5.
10. **Regional and policy limits** (EEA, Switzerland, UK; minors; recognizable people) must surface as clear `POLICY` errors.
