# Provider integration contract

**Verification gate:** The previously mentioned "Gemini Omni 1.2 Flash" and its pricing/capabilities are **unverified in this blueprint**. Before implementation, inspect official Google AI / Google Cloud documentation. Save verified model ID, endpoint, authentication, access requirements, supported inputs, limits, response/polling behavior, pricing and billing metadata with links and date. Do not extrapolate from marketing descriptions.

Interface: `capabilities()`, `validate_credentials()`, `estimate_cost(request)`, `submit(request)`, `poll(job)`, `download(result)`, `cancel(job)` where supported. Use normalized errors: AUTH, BILLING, QUOTA, UNSUPPORTED_FEATURE, POLICY, TIMEOUT, PROVIDER, NETWORK. Never assume image/video reference or voice controls exist. Capability-aware UI hides unsupported actions.

Use local mock provider with deterministic sample output and no paid calls. Separate image, video and TTS providers if needed. Never claim exact provider balance unless supported; app budget != account credit. Maintain dated rate card and flag unknown pricing before paid request. Log redacted request IDs and usage, never secrets or sensitive uploaded media.
