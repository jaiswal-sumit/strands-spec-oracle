# Multi-Currency Support

## Supported Currencies

The platform supports 135 currencies. The full list is available at:

**GET** `/v2/currencies`

```json
[
  { "code": "USD", "name": "US Dollar", "symbol": "$", "minor_units": 2 },
  { "code": "JPY", "name": "Japanese Yen", "symbol": "¥", "minor_units": 0 },
  { "code": "KWD", "name": "Kuwaiti Dinar", "symbol": "KD", "minor_units": 3 }
]
```

`minor_units` is the number of decimal places. JPY has 0 (amounts are integers);
KWD has 3; most currencies have 2.

## Amount Representation

All amounts are integers in the smallest currency unit:

| Currency | Amount | Minor Units | API Value |
|----------|--------|-------------|-----------|
| USD | $20.00 | 2 | 2000 |
| JPY | ¥1500 | 0 | 1500 |
| KWD | KD 5.500 | 3 | 5500 |
| BHD | BD 2.012 | 3 | 2012 |

Never pass decimals to the API. The API returns an error if the amount is not a valid
minor-unit integer for the specified currency.

## Presentment vs. Settlement Currency

- **Presentment currency**: what the customer sees and is charged in.
- **Settlement currency**: the currency in which funds land in your account.

These can differ. You can charge a customer in EUR and receive GBP in your account.
The platform performs the FX conversion at the time of capture using live rates, with a
0.5% conversion fee (or as specified in your contract).

To see the exact conversion applied to a settled payment:

```json
{
  "id": "pay_01J8X3K",
  "amount": 2000,
  "currency": "EUR",
  "settlement": {
    "amount": 1712,
    "currency": "GBP",
    "exchange_rate": 0.856,
    "fee_amount": 9
  }
}
```

## Multi-Currency Pricing

For subscription products, define prices in multiple currencies:

**POST** `/v2/prices`

```json
{
  "product_id": "prod_PRO_MONTHLY",
  "billing_interval": "monthly",
  "tiers": [
    { "currency": "USD", "unit_amount": 4900 },
    { "currency": "EUR", "unit_amount": 4500 },
    { "currency": "GBP", "unit_amount": 3900 },
    { "currency": "JPY", "unit_amount": 6800 }
  ]
}
```

When creating a subscription for a customer with a billing address in Germany, the platform
automatically selects the EUR price. Override this with an explicit `currency` in the
subscription create payload.

## Automatic FX (Dynamic Currency Conversion)

For one-off payments where the customer's currency is unknown, set `currency: "auto"`:

```python
payment = client.payments.create(
    amount=100,
    currency="auto",
    customer_currency="EUR",
    source="card_tok_XXXX",
)
```

The platform converts 100 base-currency units to the nearest EUR amount and presents the
EUR total to the customer. The customer's card statement shows the EUR charge.

## FX Rates

Retrieve live exchange rates for display purposes:

**GET** `/v2/fx-rates?base=USD&targets=EUR,GBP,JPY`

```json
{
  "base": "USD",
  "rates": {
    "EUR": 0.9201,
    "GBP": 0.7942,
    "JPY": 148.53
  },
  "fetched_at": "2024-10-01T14:00:00Z"
}
```

Rates are refreshed every 5 minutes from multiple provider feeds. Display a "rate may
vary at checkout" disclaimer; the exact rate locks at payment capture time.

## Currency Restrictions by Payment Method

Not all payment methods support all currencies:

| Method | Supported Currencies |
|--------|---------------------|
| Visa / Mastercard | 135 (all) |
| Amex | 52 major currencies |
| ACH Debit | USD only |
| SEPA Debit | EUR only |
| Klarna | SEK, NOK, DKK, EUR, GBP, USD, CAD, AUD |
| Afterpay | AUD, NZD, CAD, USD, GBP |

Attempting to charge a payment method in an unsupported currency returns a
`currency_not_supported` error.
