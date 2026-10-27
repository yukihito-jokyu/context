import { Subscription } from "../subscriptions/model";

export class Invoice {
  constructor(
    public readonly invoiceId: string,
    public readonly subscription: Subscription,
    public readonly amountYen: number,
  ) {}
}
