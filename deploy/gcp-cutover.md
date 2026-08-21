# Cut over: www.graharekha.com → GCE (no Vercel)

Do this only after `https://gcp.graharekha.com` passed free report + paid checkout.
Keep Railway running 24–48 h for rollback. Vercel is unused after DNS moves.

Static IP: `8.231.107.171` (`graharekha-api`, zone `asia-south1-c`).

## 1. Prep the VM (Caddy hosts www + gcp + apex)

```bash
cd ~/astro-palmistry
sudo git pull
# edit deploy/.env:
#   DOMAIN=www.graharekha.com
#   ALLOWED_ORIGINS=https://www.graharekha.com,https://graharekha.com,https://gcp.graharekha.com
sudo docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env up -d --force-recreate api caddy
```

## 2. Google OAuth (Authorized JavaScript origins)

Add (keep existing gcp / railway if you want):

- `https://www.graharekha.com`
- `https://graharekha.com`

## 3. DNS (GoDaddy) — this removes Vercel from the path

Point both at the VM (replace any Vercel CNAME):

| Host | Type | Value |
|------|------|--------|
| `@` (apex `graharekha.com`) | A | `8.231.107.171` |
| `www` | A | `8.231.107.171` |

Leave `gcp` A → `8.231.107.171` as the parallel test host.

Wait for DNS (often minutes; can be up to ~1 h). Check:

```bash
nslookup www.graharekha.com
curl -sS https://www.graharekha.com/health
curl -sS https://www.graharekha.com/api/public-config
```

Caddy will mint Let's Encrypt certs for `www` and apex once DNS hits the VM.

## 4. Razorpay webhook

Primary webhook URL (same path, now served by Caddy on the VM):

- `https://www.graharekha.com/api/payment/webhook`
- Events: `payment.captured`, `order.paid`

Remove any temporary `gcp.graharekha.com` test webhook once www is live on GCP.

## 5. Smoke test

1. Sign in on `https://www.graharekha.com`
2. Free report + paid unlock (`gatewayOrderId` overlay)
3. Admin → Payment health

## 6. Optional cleanup

- Pause / remove the Vercel project (DNS no longer uses it)
- Do **not** delete Railway until you no longer need rollback

## Rollback

1. GoDaddy: restore `www` (and apex) to previous Vercel targets
2. Razorpay: ensure webhook still hits a live host
3. Railway remains the old API behind Vercel if you restore that path
