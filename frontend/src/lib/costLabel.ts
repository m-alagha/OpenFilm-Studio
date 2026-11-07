/**
 * Cost display rules from docs/UX_SPEC.md: mock estimates and unknown prices are
 * always labelled, never shown as a bare number, and the provider account balance
 * is "unavailable" unless the provider actually exposes it.
 */

export interface CostEstimate {
  /** null means the price is unknown. */
  amountUsd: number | null;
  isMock: boolean;
}

export function formatEstimate(estimate: CostEstimate): string {
  if (estimate.amountUsd === null) {
    return "Price unknown: verify before generating";
  }
  const amount = `$${estimate.amountUsd.toFixed(2)}`;
  return estimate.isMock ? `${amount} (mock, no charge)` : `${amount} (estimate)`;
}

export function formatProviderBalance(balanceUsd: number | null | undefined): string {
  return balanceUsd == null ? "Provider balance: unavailable" : `Provider balance: $${balanceUsd.toFixed(2)}`;
}
