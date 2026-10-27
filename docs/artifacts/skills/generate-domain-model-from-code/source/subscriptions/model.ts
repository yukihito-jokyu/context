export type Plan = "monthly" | "annual";

export class Customer {
  constructor(public readonly customerId: string, public displayName: string) {}
}

export class Subscription {
  constructor(
    public readonly subscriptionId: string,
    public readonly customer: Customer,
    public readonly plan: Plan,
  ) {}
}
