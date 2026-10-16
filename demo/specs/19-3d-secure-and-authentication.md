# 3D Secure and Strong Customer Authentication

## Overview

3D Secure (3DS) is a protocol that adds an authentication step to card payments, reducing
chargebacks for the issuing bank and shifting fraud liability away from you. 3DS2 is the
current version; 3DS1 is deprecated and rejected by most European issuers.

Strong Customer Authentication (SCA) is an EU PSD2 regulatory requirement mandating 3DS2
on most consumer card payments where both the merchant and cardholder bank are in the
European Economic Area (EEA). Violations can result in declined payments and regulatory fines.

## How 3DS2 Works

1. **Risk data collection**: The SDK collects browser/device fingerprint data.
2. **Frictionless flow**: The issuer performs background authentication using risk signals.
   ~85% of transactions pass frictionlessly with no customer interaction.
3. **Challenge flow**: For higher-risk transactions, the customer completes an additional
   challenge (OTP, biometric, bank app push notification).
4. **Authentication result**: An `authentication_value` (cryptogram) and `eci` indicator
   are returned. These are included in the authorisation to claim the liability shift.

## Triggering 3DS

### Automatic (Recommended)

Set `authentication: "auto"` in the payment create request:

```python
payment = client.payments.create(
    amount=4900,
    currency="EUR",
    source="card_tok_XXXX",
    authentication="auto",
    return_url="https://yoursite.com/payment/complete",
)
```

The SDK handles the entire 3DS flow client-side. If a challenge is required, the payment
status becomes `requires_action` and `next_action.redirect_url` is populated:

```json
{
  "id": "pay_01J8X3K",
  "status": "requires_action",
  "next_action": {
    "type": "redirect_to_url",
    "redirect_url": "https://3ds.example.com/challenge?token=..."
  }
}
```

Redirect the customer to `redirect_url`. After the challenge, the customer is redirected
back to `return_url?payment_id=pay_01J8X3K`. Retrieve the payment to confirm its final status.

### Manual 3DS (Advanced)

For server-rendered flows or native mobile apps, trigger 3DS manually:

1. Create a `PaymentIntent` object.
2. Collect device fingerprint data on the client.
3. Call `POST /v2/payment-intents/{id}/authenticate` with fingerprint data.
4. Check `authentication.status`: `success` (frictionless), `challenge_required`, or `failed`.
5. If challenge required, render the challenge iframe using `challenge_url`.
6. Confirm the payment intent after authentication.

## SCA Exemptions

Under PSD2, certain transactions are exempt from SCA:

| Exemption | Criteria |
|-----------|---------|
| Low value | Below €30 (resets every 5 transactions or €100 cumulative) |
| Low risk | Merchant's fraud rate < 0.01% for Amex/Mastercard, < 0.06% for Visa |
| Trusted beneficiary | Customer has added merchant to their trusted list |
| Recurring (subsequent) | After the first SCA-authenticated payment in a series |
| MIT (Merchant-initiated) | No cardholder present; pre-agreed mandate |

Request an exemption by setting `sca_exemption`:

```python
payment = client.payments.create(
    amount=2000,
    currency="EUR",
    source="pm_CARD123",
    sca_exemption="recurring",
    previous_payment_id="pay_FIRST_PAYMENT",
)
```

The platform claims the exemption in the authorisation request. If the issuer declines
the exemption, the payment returns `requires_action` and must complete a full 3DS challenge.

## Liability Shift

When 3DS authentication succeeds (with or without challenge), liability for fraudulent
chargebacks shifts from you to the issuing bank. You still bear liability for
non-fraud disputes (e.g. "item not received").

When 3DS is not performed (or the exemption is declined), you bear full chargeback liability.

## Testing 3DS

In the sandbox, use the following test cards:

| Card | Outcome |
|------|---------|
| 4000 0027 6000 3184 | Frictionless success |
| 4000 0025 0000 3155 | Challenge required → authentication succeeds |
| 4000 0000 0000 3220 | Challenge required → customer fails |
| 4000 0000 0000 3063 | 3DS2 not supported; falls back to 3DS1 |

On the sandbox challenge page, enter code `000000` to simulate success or `111111`
to simulate failure.
