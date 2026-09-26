export const DEFAULT_MODEL_PRICES = {
  // The exact fast model is not listed on Cloudflare's price page. Use the
  // dearest 8b variant's prices so the count errs high.
  "@cf/meta/llama-3.1-8b-instruct-fast": { input: 0.282, output: 0.827 }
};

function utf8ByteLength(text) {
  return new TextEncoder().encode(text).byteLength;
}

export function estimateInputTokens(text) {
  return Math.ceil(utf8ByteLength(text) / 3);
}

export function callCostMicroUsd(prices, model, inputTokens, outputTokens) {
  const price = prices[model];
  if (!price) return null;
  return Math.ceil(inputTokens * price.input + outputTokens * price.output);
}

export function utcDay(date) {
  return date.toISOString().slice(0, 10);
}

export class BudgetLedger {
  constructor(storage) {
    this.storage = storage;
    this.operation = Promise.resolve();
  }

  run(operation) {
    const result = this.operation.then(operation, operation);
    this.operation = result.catch(() => {});
    return result;
  }

  async reserve(amount, limit) {
    return this.run(async () => {
      const spent = (await this.storage.get("spent")) || 0;
      const reservations = (await this.storage.get("reservations")) || {};
      const open = Object.values(reservations).reduce((total, value) => total + value, 0);
      if (spent + open + amount > limit) return { ok: false };
      const id = crypto.randomUUID();
      await this.storage.put("reservations", { ...reservations, [id]: amount });
      return { ok: true, id };
    });
  }

  async settle(id, amount) {
    return this.run(async () => {
      const spent = (await this.storage.get("spent")) || 0;
      const reservations = (await this.storage.get("reservations")) || {};
      if (!(id in reservations)) return;
      const nextReservations = { ...reservations };
      delete nextReservations[id];
      await this.storage.put("reservations", nextReservations);
      await this.storage.put("spent", spent + amount);
    });
  }
}
