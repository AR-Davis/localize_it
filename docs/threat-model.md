# Threat Model

## Overview

Localize It operates under a **radical locality** principle: your data should never need to leave your machine. This document analyzes threats and mitigations.

## Threat Actors

### 1. Cloud AI Providers

**Threat:** Claims ownership of training data derived from your interactions.

**Current Reality:** Terms of service grant providers broad rights to use interactions for model improvement.

**Mitigation:**
- Capture happens locally, not via provider APIs
- Data never transmitted to third parties
- You own complete interaction logs

**Residual Risk:** Provider may still claim rights to original cloud interactions.

**Response:** This is accepted as the cost of using cloud AI. Localize It captures value that would otherwise be lost.

---

### 2. Network Adversaries

**Threat:** Interception of data during cloud AI usage.

**Risk:** High for unencrypted traffic, low for HTTPS.

**Mitigation:**
- Cloud AI uses TLS/HTTPS (assumed)
- Local capture has no network component
- Airgap mode completely eliminates network threat

**Residual Risk:** None for local operations.

---

### 3. Local System Compromise

**Threat:** Attacker gains access to your machine.

**Risk:** Training data, interaction logs, and model weights exposed.

**Mitigation:**
- File system permissions (standard Unix model)
- Optional encryption at rest
- No cloud sync of sensitive data

**Residual Risk:** Physical access = game over (standard threat model).

**Enhancement Options:**
- Full disk encryption
- Encrypted volume for `data/` directory
- Hardware security modules for model weights

---

### 4. Training Data Poisoning

**Threat:** Malicious inputs that corrupt your personal model.

**Attack Vector:**
- Compromised cloud AI responses
- Intentionally crafted malicious queries
- Third-party interaction logs

**Mitigation:**
- Source verification (only your interactions)
- Quality filtering before training
- Version control (rollback capability)
- Manual review of training corpus

**Residual Risk:** Low if you control all inputs.

---

### 5. Catastrophic Forgetting

**Threat:** New training overwrites valuable prior knowledge.

**Scenario:**
- Train on Week 1 data → Model learns style A
- Train on Week 2 data → Model forgets style A

**Mitigation:**
- Version control for all adapters
- Incremental training strategies
- EWC (Elastic Weight Consolidation) if implemented
- Regular evaluation against prior benchmarks

**Residual Risk:** Moderate. Mitigated by versioning.

---

### 6. Model Extraction

**Threat:** Someone extracts your personal model from your device.

**Risk:** Loss of competitive advantage, privacy exposure.

**Mitigation:**
- Access controls (file permissions)
- Encryption at rest
- Optional: Split weights across devices

**Residual Risk:** Depends on physical security.

---

## Privacy Guarantees

### What We Promise

✅ **No cloud training data leaves your machine**
- All capture is local
- No telemetry
- No usage analytics

✅ **No external dependencies**
- Core functions offline-capable
- Optional: Cloud sync (opt-in only)

✅ **Complete user control**
- You choose what to capture
- You choose what to train
- You choose what to delete

### What We Cannot Promise

❌ **Provider-side security**
- Cloud AI providers may still have your queries
- We cannot control their data handling

❌ **Perfect extraction**
- Model weights encode patterns
- Sophisticated attacks may extract information

❌ **Forensic recovery**
- Deleted data may be recoverable
- Use encryption if this matters

---

## Attack Scenarios

### Scenario 1: Employer Monitoring

**Situation:** Employer monitors all cloud AI usage.

**Risk:** Queries exposed, but synthesis not captured by employer.

**Mitigation:** Localize It doesn't prevent employer monitoring, but ensures you own the output.

**Recommendation:** Use personal device for Localize It, separate from work monitoring.

---

### Scenario 2: Legal Subpoena

**Situation:** Legal demand for Localize It data.

**Risk:** Forced disclosure of training data, interaction logs, or model weights.

**Mitigation:**
- Encryption at rest (keys under your control)
- Plausible deniability (optional hidden volumes)
- Jurisdiction selection (if using cloud components)

**Recommendation:** Consult legal counsel. This is tool-agnostic.

---

### Scenario 3: Device Theft

**Situation:** Laptop containing Localize It installation stolen.

**Risk:** Attacker gains access to:
- Raw interaction logs
- Training corpora
- Model weights
- Preference databases

**Mitigation:**
- Full disk encryption (BitLocker/FileVault/LUKS)
- BIOS/EFI password
- Remote wipe capability

**Recommendation:** Full disk encryption is essential.

---

## Security Checklist

### Essential

- [ ] Full disk encryption enabled
- [ ] Strong login password
- [ ] Screen lock after inactivity
- [ ] Regular backups (encrypted)

### Recommended

- [ ] Separate encrypted volume for `data/`
- [ ] Hardware security key for critical operations
- [ ] Airgap mode for sensitive work
- [ ] Regular security updates

### Optional

- [ ] Plausible deniability setup
- [ ] Multi-device split (shamir sharing)
- [ ] Tamper-evident logging

---

## Comparison: Cloud vs Local

| Threat | Cloud AI | Localize It |
|:-------|:---------|:------------|
| Provider breach | High risk | No risk |
| Network interception | TLS mitigates | No network |
| Physical theft | N/A | Encryption required |
| Subpoena | Immediate | Encryption helps |
| Insider threat | High | Low |
| Catastrophic loss | Account-dependent | Your backup |

---

## Contributing to Security

Found a vulnerability?

1. Document the threat
2. Propose mitigation
3. Submit via secure channel (not public issue)

**Contact:** security@localize-it.org (when established)

---

## References

- [OWASP Threat Modeling](https://owasp.org/www-community/Threat_Modeling)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [EFF Surveillance Self-Defense](https://ssd.eff.org/)

---

*Security is a process, not a product. Stay vigilant.*
