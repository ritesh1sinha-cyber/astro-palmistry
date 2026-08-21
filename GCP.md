# Google Cloud — Compute Engine VM (parallel to Railway)

Use your **$300 free trial credit** for a second production-like stack:
one GCE VM running the same shape as Railway (API + MiniLM inline workers),
plus Postgres, Redis, and Caddy (HTTPS + static site).

Railway keeps serving `www.graharekha.com` via Vercel until you cut over.
GCP serves a parallel subdomain `gcp.graharekha.com` for proving the stack.

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
Do **not** open Postgres `5432` or Redis `6379` to the internet.

## 3. Create the VM + static IP

One-shot (Linux / Cloud Shell):

```bash
export GCP_PROJECT=YOUR_PROJECT_ID
bash deploy/gcp-create-vm.sh
```

On Windows (after installing the [Cloud SDK](https://cloud.google.com/sdk/docs/install) 【官方】):

```powershell
$env:GCP_PROJECT = "YOUR_PROJECT_ID"
.\deploy\gcp-create-vm.ps1
```

Or manually — reserve a static IP first so DNS does not drift after a restart:

```bash
gcloud compute addresses create graharekha-api-ip \
  --region=asia-south1

gcloud compute addresses describe graharekha-api-ip \
  --region=asia-south1 --format='get(address)'
```

Create the instance attached to that address:

```bash
gcloud compute instances create graharekha-api \
  --zone=asia-south1-a \
  --machine-type=e2-standard-4 \
  --boot-disk-size=80GB \
  --boot-disk-type=pd-balanced \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=graharekha-web \
  --scopes=cloud-platform \
  --address=graharekha-api-ip
```

Confirm the external IP:

```bash
gcloud compute instances describe graharekha-api \
  --zone=asia-south1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

## 4. DNS and OAuth

Create an **A record**:

| Host | Type | Value |
|------|------|--------|
| `gcp.graharekha.com` | A | *(static IP from step 3)* |
| `www.gcp.graharekha.com` | A | *(same, optional)* |

Wait for DNS before Caddy can get a Let's Encrypt cert.

In [Google Cloud OAuth credentials](https://console.cloud.google.com/apis/credentials),
add Authorized JavaScript origin:

- `https://gcp.graharekha.com`

Keep `https://www.graharekha.com` (and Railway) origins too.

Do **not** change the live Razorpay webhook yet — payments stay on Railway
during the parallel window.

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
# set DOMAIN=gcp.graharekha.com
# set ACME_EMAIL=admin@graharekha.com
# paste RAZORPAY_* and LLM_* from Railway
# confirm GOOGLE_CLIENT_ID
sudo docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env up -d --build
```

First image build often takes **15–25 minutes** (torch + MiniLM).

## 6. Verify the empty stack

```bash
curl -sS https://gcp.graharekha.com/health
curl -sS https://gcp.graharekha.com/api/public-config
# googleClientId should be set
```

Logs:

```bash
cd ~/astro-palmistry
docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env logs -f api
```

Admin login on `https://gcp.graharekha.com` → Analysis → Payment health:
key id, key secret, and webhook secret should all read as set.

## 7. Copy Railway data (once GCP is healthy)

Two stores matter. Redis is a job queue — do **not** copy it.

### Postgres

From a machine that can reach Railway Postgres (Railway dashboard → Postgres →
Connect → copy the public URL, or use `railway connect`):

```bash
# on your laptop — dump Railway
pg_dump --no-owner --no-acl "$RAILWAY_DATABASE_URL" -Fc -f railway.dump

# copy dump to the VM
gcloud compute scp railway.dump graharekha-api:~/railway.dump --zone=asia-south1-a
```

On the VM (GCP subdomain only — Railway stays live):

```bash
cd ~/astro-palmistry
# restore into the compose Postgres (container name may be project_postgres_1)
docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env \
  exec -T postgres pg_restore --clean --if-exists --no-owner --no-acl -U astro -d astro \
  < ~/railway.dump
# if pg_restore complains about roles, drop/recreate the DB once then retry:
# docker compose … exec postgres psql -U astro -c "DROP DATABASE IF EXISTS astro; CREATE DATABASE astro OWNER astro;"
```

Or use the helper: [`deploy/gcp-migrate-data.sh`](deploy/gcp-migrate-data.sh).

### Report HTML (`LOCAL_STORE`)

Railway volume is `/data/storage`. Without these files, DB rows exist but reports
404.

```bash
# From Railway shell / volume download, or:
# railway run tar czf - -C /data storage > railway-storage.tgz
gcloud compute scp railway-storage.tgz graharekha-api:~/ --zone=asia-south1-a
```

On the VM:

```bash
cd ~/astro-palmistry
VOL=$(docker volume ls -q | grep reportstore | head -1)
# find the mount path
docker run --rm -v "$VOL":/data -v "$HOME":/backup alpine \
  sh -c 'mkdir -p /data/storage && tar xzf /backup/railway-storage.tgz -C /data'
docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env restart api
```

## 8. Prove payments before cutting over

On `https://gcp.graharekha.com` (not www):

1. Admin login → Payment health: all three Razorpay secrets set.
2. Generate a free report.
3. Start a paid unlock — confirm Razorpay checkout shows `gatewayOrderId`
   (overlay with ₹298, not the blue shared-button fallback).
4. Optional ₹298 test payment; refund from the Razorpay dashboard.

For the test payment only, add a **second** Razorpay webhook:

- URL: `https://gcp.graharekha.com/api/payment/webhook`
- Events: `payment.captured`, `order.paid` (and optionally `payment.failed`)
- Same signing secret as `RAZORPAY_WEBHOOK_SECRET`

Leave the live `https://www.graharekha.com/api/payment/webhook` webhook alone.
Remove the GCP test webhook if you abort the migration.

## 9. Cut over (later, after you confirm GCP)

Reversible — keep Railway running 24–48 h:

1. Re-dump Postgres + reports if Railway accepted new orders during the test
   window (repeat step 7).
2. Change [`vercel.json`](vercel.json) rewrites from
   `astro-api-production-af42.up.railway.app` to `https://gcp.graharekha.com`
   (or serve www from Caddy and skip the Vercel API proxy).
3. Point the **primary** Razorpay webhook at whichever host owns `/api`
   (`https://www.graharekha.com/api/payment/webhook` if Vercel still proxies,
   or `https://gcp.graharekha.com/api/payment/webhook` if Caddy is apex).
4. Rollback: restore `vercel.json` to Railway and redeploy Vercel.

Do **not** delete the Railway project until rollback is no longer needed.

## Useful ops

```bash
# update app after a git push
cd ~/astro-palmistry && git pull && git lfs pull
docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env up -d --build

# stop billing quickly (trial credit)
gcloud compute instances stop graharekha-api --zone=asia-south1-a
```

## Do not

- Open Postgres (`5432`) or Redis (`6379`) on `0.0.0.0` — keep them Docker-internal.
- Use a shared/guessable `APP_SECRET` / `PG_PASSWORD`.
- Expect free-tier micro VMs to run MiniLM — always **≥16 GB** RAM for this image.
- Change live Razorpay / Vercel until step 9.

See also: `deploy/docker-compose.gcp.yml`, `deploy/.env.gcp.example`,
`deploy/gcp-create-vm.sh`, `deploy/gcp-create-vm.ps1`, `deploy/gcp-setup-vm.sh`,
`deploy/gcp-migrate-data.sh`, `deploy/gcp-prove-payments.md`,
`deploy/gcp-cutover.md`, Railway notes in `RAILWAY.md`.
