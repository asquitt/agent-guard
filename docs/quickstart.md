# Archived quick start

AgentGuard is mothballed as a standalone product. There is no supported quick
start, hosted service, registration flow, or provider-backed evaluation in the
preserved application.

Do not start the standalone stack, enable registration, connect credentials,
send provider requests, or incur runtime/provider spend. Those actions require
an explicit reactivation decision satisfying every gate in
[`PROJECT_STATUS.json`](../PROJECT_STATUS.json).

## Current archive boundaries

- The public and authenticated onboarding routes are read-only archive pages.
- The registration page is intentionally unavailable even if a backend
  operator changes the dormant registration flags.
- Backend registration defaults off and requires a separate enrollment gate in
  any production-like environment.
- Provider credentials are not accepted in proxy-endpoint configuration.
- Repository SDKs are unpublished source previews and require an explicit
  deployment origin.
- Local tests, builds, fixtures, and containers are repository evidence only;
  they do not prove a hosted or customer-ready service.

The registration UI, deployment authorization, provider/spend controls, and a
full customer journey would all need new implementation and exact-commit review
after a portfolio reactivation decision. Turning on a backend flag alone is not
a supported enrollment path.

## Preserved reference

- [Archive and asset map](./ARCHIVE_AND_ASSET_MAP.md)
- [Archived API reference](./api-reference.md)
- [Archived integration reference](./integration-guide.md)
- [Historical standalone README](./historical/STANDALONE_PRODUCT_README.md)

These references describe source artifacts and historical intent. They are not
instructions or authorization to run the product.
