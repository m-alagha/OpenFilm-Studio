import { describe, expect, it } from "vitest";

import { formatEstimate, formatProviderBalance } from "./costLabel";

describe("formatEstimate", () => {
  it("labels mock estimates", () => {
    expect(formatEstimate({ amountUsd: 0, isMock: true })).toBe("$0.00 (mock, no charge)");
  });

  it("labels real estimates as estimates", () => {
    expect(formatEstimate({ amountUsd: 0.7, isMock: false })).toBe("$0.70 (estimate)");
  });

  it("never shows a number for unknown prices", () => {
    expect(formatEstimate({ amountUsd: null, isMock: false })).toMatch(/unknown/i);
  });
});

describe("formatProviderBalance", () => {
  it("reports unavailable when the provider has no balance API", () => {
    expect(formatProviderBalance(null)).toBe("Provider balance: unavailable");
    expect(formatProviderBalance(undefined)).toBe("Provider balance: unavailable");
  });

  it("shows a balance only when one is provided", () => {
    expect(formatProviderBalance(12.5)).toBe("Provider balance: $12.50");
  });
});
