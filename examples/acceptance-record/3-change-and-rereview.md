# Change and re-review conditions

**Document ID:** CR-2026-001 · **Linked acceptance:** AR-2026-001 · **Date:** 2026-09-23

> ILLUSTRATIVE. Falsify OÜ plays both the supplier and the client role. Not a client engagement. Signatures are made with demo keys.

This is a commercial agreement between the supplier and the client, recorded at acceptance. It covers the system version named in AR-2026-001.

## Changes that do not need a new acceptance round

| Change | Limits agreed | Who decides it stays within the limits |
|---|---|---|
| Retraining on refreshed data from the same pipeline, same features and model configuration | C1 and C2 must still pass on the sealed test split (criteria records unchanged) | Supplier, who notifies the client within 10 working days with the new results |

## Changes that need a new acceptance round

- A new data source or new input features
- A change of model family or configuration
- Use of the system in a new business process or for a new applicant population

A new acceptance round is tested against the same sealed criteria (C1 https://registry.falsify.dev/5ce3c9c3484d8db1ffbc67dc4f3958c9a88009a0ae92ce51e045ea6b70258bc3 and C2) unless both sides sign a new plan version.

## Conditions that trigger a re-review of the acceptance

| Condition | Who watches for it | What happens |
|---|---|---|
| Impact ratio (sex) measured on monthly production decisions falls below 0.80 for two consecutive months | Client credit risk team | Re-review within 30 days |
| Share of recommendations overridden by credit officers rises above 25% in a month | Client operations | Re-review within 30 days |

Falsify records these conditions. Falsify does not monitor them.

## Relation to the AI Act

This agreement does not by itself make any change a "pre-determined change" under Article 43(4) of the AI Act. That provision applies to high-risk systems that continue to learn after being placed on the market, and to changes pre-determined by the provider at the initial conformity assessment and recorded in the technical documentation (Annex IV, point 2(f)). Whether it applies is for the provider to determine.

## Signatures

| Side | Signer | Role | Signature |
|---|---|---|---|
| Client decision owner | demo-client@acceptance-record.example | Head of Credit Risk (illustrative) | `3-change-and-rereview.md.client.sig` |
| Supplier responsible person | demo-supplier@acceptance-record.example | Delivery lead (illustrative) | `3-change-and-rereview.md.supplier.sig` |
