# Prove GCP payments (parallel window — Railway still live)

Run on `https://gcp.graharekha.com` only. Do not change the primary
`www.graharekha.com` Razorpay webhook.

## Checklist

- [ ] `curl -sS https://gcp.graharekha.com/health` returns OK
- [ ] Admin login works
- [ ] Analysis → Payment health: key id, key secret, webhook secret all **set**
- [ ] Free full report generates and opens
- [ ] Paid unlock opens Razorpay **checkout overlay** with ₹298
  (not the blue shared Payment Button fallback)
- [ ] Order response / health shows `hasGatewayOrder: true` for the new order
- [ ] (Optional) Add a **second** Razorpay webhook temporarily:
  - URL: `https://gcp.graharekha.com/api/payment/webhook`
  - Events: `payment.captured`, `order.paid`
  - Secret matches `RAZORPAY_WEBHOOK_SECRET` on the VM
- [ ] (Optional) Pay ₹298, confirm report unlocks, refund in Razorpay dashboard
- [ ] Payment health shows a matched webhook for that order
- [ ] If aborting: delete the temporary GCP webhook; leave www alone

When all required boxes are green, follow [`gcp-cutover.md`](gcp-cutover.md).
