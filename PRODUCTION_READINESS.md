# Pata HAO production-readiness tracker

This tracker separates work that can be completed remotely from Kenya-only
payment activation. Live M-Pesa remains disabled until Safaricom onboarding is
complete.

## Remote foundation

- [x] Explicit development, staging, and production runtime modes
- [x] PostgreSQL required outside development
- [x] Development payment simulation disabled outside development
- [x] Live M-Pesa configuration fails closed
- [x] CI validates that production settings can boot safely
- [x] Liveness and database-readiness probes
- [x] Environment-controlled server log level and stdout logging
- [x] Environment-controlled mobile API origin
- [x] HTTPS-only release API configuration
- [x] Android release no longer uses the debug signing key
- [ ] Select permanent Android application ID before Play Console enrollment
- [ ] Provision stable Django hosting and managed PostgreSQL
- [ ] Move public photos/videos to durable object storage and a CDN
- [ ] Put mandate/identity documents in separate private object storage
- [ ] Configure transactional email and verify password recovery delivery
- [ ] Configure crash reporting, uptime alerts, and centralized logs
- [ ] Configure encrypted automated backups and complete a restore drill
- [ ] Implement device registration and Firebase push delivery
- [ ] Complete privacy, terms, refunds, deletion, and staff operating policies
- [ ] Complete a closed beta on low-end phones and weak Kenyan networks

## Kenya activation

- [ ] Open/confirm the dedicated Pata HAO business bank account
- [ ] Obtain the dedicated Safaricom administration number
- [ ] Complete PayBill or Business Till KYC and approval
- [ ] Complete Daraja Go Live and store credentials only in the secret manager
- [ ] Run controlled real-money collection, callback, timeout, duplicate,
      receipt, refund, and settlement tests
- [ ] Start with staff-authorized, reconciled partner payouts
- [ ] Enable wider paid-viewing access only after the controlled pilot is stable
