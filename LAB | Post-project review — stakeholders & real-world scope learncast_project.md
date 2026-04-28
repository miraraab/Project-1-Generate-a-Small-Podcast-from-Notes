# Learncast – Project Snapshot

## Overview

Learncast addresses a common learning bottleneck: students miss class, re-reading dense notes is slow and passive, and traditional study formats don't fit modern schedules.

The tool targets anyone who learns on the go — commuters, gym-goers, busy professionals — and benefits auditory learners who retain information better through listening than reading.

Built as an MVP at the Ironhack AI Bootcamp, Learncast takes any PDF, `.txt` file, or pasted transcript and runs it through a **three-stage Python pipeline**:
1. Data cleaning
2. GPT-4o mini summarisation (Feynman method + story arc structure)
3. OpenAI TTS audio generation

The output is a personalised MP3 podcast recap — selectable voice, adjustable tone — delivered in minutes instead of hours of re-reading.

**Known MVP limitations:**
- Processing time for dense documents (~10 min)
- Voice naturalness degrades at longer lengths
- URL scraping needs further iteration

---

## Stakeholder Impact

| # | Role / Relationship | Need | Risk if Ignored | Influence | Interest |
|---|---|---|---|---|---|
| 1 | **End Users** – Students & active learners consuming podcasts while multitasking | Accurate, engaging audio recaps that fit into a busy schedule | Tool built for ideal conditions, never adopted; core value prop fails | Low | High |
| 2 | **Founding Team** – Entrepreneurs investing time and money | Viable PMF, scalable architecture, clear path to monetisation | Scope creep, technical debt, demo that never becomes production-ready | High | High |
| 3 | **IT/DevOps** – Deployment and infrastructure | Stable, documented, deployable app with clear dependency management, no hardcoded secrets | App runs on one developer's laptop and nowhere else | High | Low |
| 4 | **Legal/Compliance** – Data handling, API usage, IP | Clarity on data sent to third-party APIs, storage policies, ToS coverage | User transcripts with confidential content sent to external APIs without disclosure | High | Low |
| 5 | **Finance** – API cost tracking and pricing | Predictable cost per user interaction enabling viable pricing structure | No rate limiting → single large PDF triggers disproportionate API costs; unit economics unviable | High | Low |
| 6 | **Customer Support** – First-line response | Clear error messages, internal docs, ability to diagnose failures without dev escalation | Cryptic errors, inefficient ticket handling, increased churn | Low | Medium |
| 7 | **B2B Customers (L&D programs)** – Indirect high-value stakeholder | Data privacy guarantees, data leak prevention, quality commitment | Enterprise deals blocked at security review; locked out of highest-revenue segment | High | High |

---

## From Demo to "Real Project"

### Operations: Monitoring & Incident Response
Currently the app has basic Python logging to the terminal and no alerting. If the OpenAI API goes down or a TTS call fails, the user sees a UI error — nothing is logged persistently.

**Production requirements:**
- Structured logging (Datadog or Sentry)
- Uptime monitoring on the Hugging Face Space URL
- Defined uptime and reliability SLAs
- On-call rotation for peak study hours

---

### Security & Secrets Handling
Development used `.env` files locally and Hugging Face repository secrets for deployment — reasonable for a prototype.

**Production requirements:**
- Secrets manager (AWS Secrets Manager or HashiCorp Vault)
- Automatic secret rotation
- Pre-commit hook scanning for accidentally committed credentials

---

### Data Lifecycle: PII, Retention & Training Data
Learncast currently processes transcript content entirely in memory and passes it to the OpenAI API. No data is stored server-side; no policy exists on post-processing data handling.

**Production requirements:**
- Clear data retention policy (duration, training data opt-out)
- GDPR / FERPA compliance for educational institution use
- Explicit consent flows
- Right-to-deletion capability

---

### Error Handling & Edge Cases
The current pipeline handles the **happy path** well. Edge cases (scanned PDFs, corrupted files, non-English transcripts, very short inputs) receive basic error messages with no recovery path.

**Production requirements:**
- OCR fallback for scanned documents
- Clear user-facing error messages with recovery guidance
- Input validation before API calls
- Retry logic for transient API failures
- Graceful degradation:
  - Stage 2 fails → display raw cleaned transcript
  - Stage 3 fails → display generated script for manual review

---

### API Budget & Cost Management
Currently no rate limiting, cost tracking, or user quota system. A single user can trigger many expensive calls without controls.

**Production requirements:**
- Per-user usage quotas
- Cost monitoring via OpenAI usage dashboard
- Alerts for unexpected spend
- Evaluation of gpt-4o-mini cost-quality tradeoff at scale
- Result caching for repeated or similar inputs

---

### Handoff & Client Documentation
The project has a README for local setup, but assumes comfort with conda environments, API keys, and CLI tools. No user-facing documentation exists.

**Production requirements:**
- Deployment guide with screenshots
- Troubleshooting FAQ
- One-click install script
- Training sessions for client staff
- Defined support process (contact, response time, bug tracking)
- Upfront-agreed definition of done

---

### Scope Beyond the Demo: Multilingual Support & Accessibility
The interface is functional but not optimised for end-user experience and is implicitly English-only.

**Production requirements:**
- Formal UX design process (user testing, accessible design patterns, error states, progress indicators)
- Language detection and multilingual TTS support
- Audio accessibility features (transcripts of generated audio for hearing-impaired users)

---

## Revision Brief

### Before
At project start, success meant getting the pipeline to work — upload a transcript, get audio out. No formal scope document, no defined user, no risk assessment.

**Assumed:** clean PDFs, English content, one user at a time, unlimited API budget. If it ran locally and produced a podcast, it was considered done.

### After
Success is now framed around three pillars:
1. **Who the tool is actually for**
2. **What it needs to handle reliably**
3. **What "done" really means**

**Key changes:**
- **Narrow the MVP scope** to a specific user (e.g. Ironhack students reviewing bootcamp material in English) rather than building for everyone at once
- **Expand to instructors** as a second user type — natural extension with different needs around content control and accuracy
- **Non-functional requirements upfront** — the API call volume vs. response time tradeoff (~10 min wait) is a client decision, not a build surprise
- **Security review gate** before any external deployment
- **Cost ceiling** per user session
- **Broader definition of done** — includes edge case handling and performance benchmarks, not just the happy path
