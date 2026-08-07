# Google Cloud — Compute Engine VM (parallel to Railway)

Use your **$300 free trial credit** for a second production-like stack:
one GCE VM running the same shape as Railway (API + MiniLM inline workers),
plus Postgres, Redis, and Caddy (HTTPS + static site).

Railway can keep serving `www.graharekha.co.in` via Vercel; GCP can serve a
subdomain such as `gcp.graharekha.co.in` until you cut over DNS.

```
Browser ──▶ Caddy (80/443) ──▶ site/ (static)
                    │
                    └── /api/* ──▶ api:3000 (INLINE_WORKER + MiniLM)
                                      ├── Postgres
                                      └── Redis
```

## Cost (ballpark on credit)

| Piece | Suggested | ~burn rate |
|-------|-----------|------------|
| VM | **e2-standard-4** (4 vCPU / 16 GB) | ~$100–130 / month on-demand |
| Disk | 50–80 GB SSD | small |
| Egress | low at first | metered |

Free trial credit lasts ~90 days — enough to validate. **Do not** use free-tier
`e2-micro` for MiniLM; it will OOM again.

## 1. One-time GCP setup (your laptop)

1. Open [Google Cloud Console](https://console.cloud.google.com/) → activate
   the free trial if needed.
2. Create / select a project (e.g. `graharekha-prod`).
3. Enable **Compute Engine API**.
4. Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) 【官方】,
   then:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config set compute/region asia-south1   # Mumbai — low latency for India
gcloud config set compute/zone asia-south1-a
```

## 2. Firewall

```bash
gcloud compute firewall-rules create graharekha-http-https \
  --allow=tcp:80,tcp:443 \
  --target-tags=graharekha-web \
  --description="HTTP/HTTPS for GrahaRekha Caddy"
```

SSH (optional if using IAP): default `default-allow-ssh` is usually fine.

## 3. Create the VM

```bash
gcloud compute instances create graharekha-api \
  --zone=asia-south1-a \
  --machine-type=e2-standard-4 \
  --boot-disk-size=80GB \
  --boot-disk-type=pd-balanced \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=graharekha-web \
  --scopes=cloud-platform
```

Note the **external IP**:

```bash
gcloud compute instances describe graharekha-api \
  --zone=asia-south1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

## 4. DNS

Create an **A record**:

| Host | Type | Value |
|------|------|--------|
| `gcp.graharekha.co.in` | A | *(VM external IP)* |
| `www.gcp.graharekha.co.in` | A | *(same, optional)* |

Wait for DNS before Caddy can get a Let's Encrypt cert.

## 5. Install & start the stack on the VM

```bash
gcloud compute ssh graharekha-api --zone=asia-south1-a
```

On the VM:

```bash
# paste and run, or clone then:
curl -fsSL https://raw.githubusercontent.com/ritesh1sinha-cyber/astro-palmistry/main/deploy/gcp-setup-vm.sh | sudo bash
```

Or manually:

```bash
sudo apt-get update && sudo apt-get install -y git openssl
git clone https://github.com/ritesh1sinha-cyber/astro-palmistry.git
cd astro-palmistry
sudo bash deploy/gcp-setup-vm.sh
```

Edit secrets before (or after first generate):

```bash
nano ~/astro-palmistry/deploy/.env
# set DOMAIN=gcp.graharekha.co.in
# confirm GOOGLE_CLIENT_ID
sudo docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env up -d --build
```

First image build often takes **15–25 minutes** (torch + MiniLM).

## 6. Google Sign-In origins

In [Google Cloud OAuth credentials](https://console.cloud.google.com/apis/credentials),
add Authorized JavaScript origin:

- `https://gcp.graharekha.co.in`

(Keep Railway / `www.graharekha.co.in` origins too.)

## 7. Verify

```bash
curl -sS https://gcp.graharekha.co.in/health
curl -sS https://gcp.graharekha.co.in/api/public-config
# googleClientId should be set
```

Logs:

```bash
cd ~/astro-palmistry
docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env logs -f api
```

## 8. Point Vercel at GCP later (optional)

In `vercel.json`, change the Railway rewrite host to your GCP domain (or keep
Vercel → Railway and use GCP only as backup). Same-origin via Caddy on the VM
means you can also open `https://gcp.graharekha.co.in` directly with no Vercel.

Webhook for Razorpay if you cut over:

`https://gcp.graharekha.co.in/api/payment/webhook`

## Useful ops

```bash
# update app after a git push
cd ~/astro-palmistry && git pull && git lfs pull
docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env up -d --build

# stop billing quickly
gcloud compute instances stop graharekha-api --zone=asia-south1-a
```

## Do not

- Open Postgres (`5432`) or Redis (`6379`) on `0.0.0.0` — keep them Docker-internal.
- Use a shared/guessable `APP_SECRET` / `PG_PASSWORD`.
- Expect free-tier micro VMs to run MiniLM — always **≥16 GB** RAM for this image.

See also: `deploy/docker-compose.gcp.yml`, `deploy/.env.gcp.example`,
`deploy/gcp-setup-vm.sh`, Railway notes in `RAILWAY.md`.
