#!/usr/bin/env bash
# Create GCE firewall + static IP + e2-standard-4 VM for GrahaRekha.
# Run on a machine with gcloud authenticated (laptop or Cloud Shell).
#
#   export GCP_PROJECT=your-project-id
#   bash deploy/gcp-create-vm.sh
set -euo pipefail

PROJECT="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GCP_REGION:-asia-south1}"
ZONE="${GCP_ZONE:-asia-south1-a}"
NAME="${GCP_VM_NAME:-graharekha-api}"
ADDR_NAME="${GCP_ADDR_NAME:-graharekha-api-ip}"
FW_NAME="${GCP_FW_NAME:-graharekha-http-https}"
TAG="${GCP_TAG:-graharekha-web}"

if [[ -z "$PROJECT" || "$PROJECT" == "(unset)" ]]; then
  echo "Set GCP_PROJECT or: gcloud config set project YOUR_PROJECT_ID" >&2
  exit 1
fi

echo "==> Project=$PROJECT region=$REGION zone=$ZONE"
gcloud config set project "$PROJECT"
gcloud config set compute/region "$REGION"
gcloud config set compute/zone "$ZONE"

echo "==> Enable Compute Engine API"
gcloud services enable compute.googleapis.com

if ! gcloud compute firewall-rules describe "$FW_NAME" >/dev/null 2>&1; then
  echo "==> Firewall $FW_NAME (tcp:80,443 → tag $TAG)"
  gcloud compute firewall-rules create "$FW_NAME" \
    --allow=tcp:80,tcp:443 \
    --target-tags="$TAG" \
    --description="HTTP/HTTPS for GrahaRekha Caddy"
else
  echo "==> Firewall $FW_NAME already exists"
fi

if ! gcloud compute addresses describe "$ADDR_NAME" --region="$REGION" >/dev/null 2>&1; then
  echo "==> Reserve static IP $ADDR_NAME"
  gcloud compute addresses create "$ADDR_NAME" --region="$REGION"
else
  echo "==> Static IP $ADDR_NAME already exists"
fi

IP=$(gcloud compute addresses describe "$ADDR_NAME" --region="$REGION" --format='get(address)')
echo "==> Static IP: $IP"

if ! gcloud compute instances describe "$NAME" --zone="$ZONE" >/dev/null 2>&1; then
  echo "==> Create VM $NAME (e2-standard-4, 80GB)"
  gcloud compute instances create "$NAME" \
    --zone="$ZONE" \
    --machine-type=e2-standard-4 \
    --boot-disk-size=80GB \
    --boot-disk-type=pd-balanced \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags="$TAG" \
    --scopes=cloud-platform \
    --address="$ADDR_NAME"
else
  echo "==> VM $NAME already exists"
fi

EXT=$(gcloud compute instances describe "$NAME" --zone="$ZONE" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

cat <<EOF

==> Done.

1. DNS A record:  gcp.graharekha.com  →  $EXT
2. OAuth origin:  https://gcp.graharekha.com
3. SSH and bootstrap:
     gcloud compute ssh $NAME --zone=$ZONE
     curl -fsSL https://raw.githubusercontent.com/ritesh1sinha-cyber/astro-palmistry/main/deploy/gcp-setup-vm.sh | sudo bash
     nano ~/astro-palmistry/deploy/.env   # DOMAIN / Razorpay / LLM
     cd ~/astro-palmistry
     sudo docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env up -d --build

4. Wait for DNS, then:  curl -sS https://gcp.graharekha.com/health

Do NOT open 5432/6379. Do NOT change live Razorpay webhook yet.
EOF
