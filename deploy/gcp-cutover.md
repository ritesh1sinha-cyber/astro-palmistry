# Cut over from Railway → GCP (after parallel proof)

Do this only when `https://gcp.graharekha.com` has passed free report + paid
checkout + optional test payment. Keep Railway running 24–48 h for rollback.

## 1. Final data sync

If Railway accepted any new accounts/orders since the last dump, repeat
[`gcp-migrate-data.sh`](gcp-migrate-data.sh) (or manual `pg_dump` + storage
tarball) during a short maintenance window on **www** (optional banner).

## 2. Point Vercel API proxy at GCP

In [`vercel.json`](../vercel.json), change both rewrite destinations:

```json
"destination": "https://gcp.graharekha.com/api/:path*"
```

and

```json
"destination": "https://gcp.graharekha.com/health"
```

Commit, push, wait for the Vercel deploy. Confirm:

```bash
curl -sS https://www.graharekha.com/health
curl -sS https://www.graharekha.com/api/public-config
```

## 3. Razorpay webhook

Edit the **primary** webhook (the one currently on `www.graharekha.com`):

- Keep URL as `https://www.graharekha.com/api/payment/webhook` if Vercel still
  proxies `/api` to GCP (preferred — no customer-facing URL change).
- Or move it to `https://gcp.graharekha.com/api/payment/webhook` if Caddy becomes
  the public API host.

Events must include `payment.captured` and `order.paid`.

Remove any temporary GCP-only test webhook once the primary one reaches GCP.

## 4. Smoke test on www

1. Sign in on `https://www.graharekha.com`
2. Create a paid order — must get Razorpay overlay with `gatewayOrderId`
3. Optional small payment; confirm unlock
4. Admin → Payment health → latest webhook matched an order

## 5. Rollback

1. Restore `vercel.json` destinations to
   `https://astro-api-production-af42.up.railway.app/...`
2. Redeploy Vercel
3. Ensure Razorpay primary webhook still hits a live host

Do not delete the Railway project until you no longer need this path.
