# Create GCE firewall + static IP + e2-standard-4 VM (Windows PowerShell).
# Requires Google Cloud SDK: https://cloud.google.com/sdk/docs/install
#
#   $env:GCP_PROJECT = "your-project-id"
#   .\deploy\gcp-create-vm.ps1
#
# Or open Cloud Shell in the console and run deploy/gcp-create-vm.sh instead.

$ErrorActionPreference = "Stop"

$Project = if ($env:GCP_PROJECT) { $env:GCP_PROJECT } else { (gcloud config get-value project 2>$null) }
$Region  = if ($env:GCP_REGION) { $env:GCP_REGION } else { "asia-south1" }
$Zone    = if ($env:GCP_ZONE) { $env:GCP_ZONE } else { "asia-south1-a" }
$Name    = if ($env:GCP_VM_NAME) { $env:GCP_VM_NAME } else { "graharekha-api" }
$Addr    = if ($env:GCP_ADDR_NAME) { $env:GCP_ADDR_NAME } else { "graharekha-api-ip" }
$Fw      = if ($env:GCP_FW_NAME) { $env:GCP_FW_NAME } else { "graharekha-http-https" }
$Tag     = if ($env:GCP_TAG) { $env:GCP_TAG } else { "graharekha-web" }

if (-not $Project -or $Project -eq "(unset)") {
  Write-Error "Set `$env:GCP_PROJECT or: gcloud config set project YOUR_PROJECT_ID"
}

Write-Host "==> Project=$Project region=$Region zone=$Zone"
gcloud config set project $Project
gcloud config set compute/region $Region
gcloud config set compute/zone $Zone

Write-Host "==> Enable Compute Engine API"
gcloud services enable compute.googleapis.com

$fwExists = gcloud compute firewall-rules describe $Fw 2>$null
if (-not $fwExists) {
  Write-Host "==> Firewall $Fw (tcp:80,443 -> tag $Tag)"
  gcloud compute firewall-rules create $Fw `
    --allow=tcp:80,tcp:443 `
    --target-tags=$Tag `
    --description="HTTP/HTTPS for GrahaRekha Caddy"
} else {
  Write-Host "==> Firewall $Fw already exists"
}

$addrExists = gcloud compute addresses describe $Addr --region=$Region 2>$null
if (-not $addrExists) {
  Write-Host "==> Reserve static IP $Addr"
  gcloud compute addresses create $Addr --region=$Region
} else {
  Write-Host "==> Static IP $Addr already exists"
}

$Ip = gcloud compute addresses describe $Addr --region=$Region --format="get(address)"
Write-Host "==> Static IP: $Ip"

$vmExists = gcloud compute instances describe $Name --zone=$Zone 2>$null
if (-not $vmExists) {
  Write-Host "==> Create VM $Name (e2-standard-4, 80GB)"
  gcloud compute instances create $Name `
    --zone=$Zone `
    --machine-type=e2-standard-4 `
    --boot-disk-size=80GB `
    --boot-disk-type=pd-balanced `
    --image-family=ubuntu-2204-lts `
    --image-project=ubuntu-os-cloud `
    --tags=$Tag `
    --scopes=cloud-platform `
    --address=$Addr
} else {
  Write-Host "==> VM $Name already exists"
}

$Ext = gcloud compute instances describe $Name --zone=$Zone `
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)"

Write-Host @"

==> Done.

1. DNS A record:  gcp.graharekha.com  ->  $Ext
2. OAuth origin:  https://gcp.graharekha.com
3. SSH and bootstrap:
     gcloud compute ssh $Name --zone=$Zone
     curl -fsSL https://raw.githubusercontent.com/ritesh1sinha-cyber/astro-palmistry/main/deploy/gcp-setup-vm.sh | sudo bash
     nano ~/astro-palmistry/deploy/.env
     cd ~/astro-palmistry
     sudo docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env up -d --build

4. Wait for DNS, then:  curl -sS https://gcp.graharekha.com/health

Do NOT open 5432/6379. Do NOT change live Razorpay webhook yet.
See deploy/gcp-migrate-data.sh, deploy/gcp-prove-payments.md, deploy/gcp-cutover.md
"@
