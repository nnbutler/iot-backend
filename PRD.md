# Product Requirements Document (PRD)
## Device Manager: Centralized Management Platform for Field Equipment

**Document Version:** 1.0  
**Last Updated:** June 2026  
**Status:** Approved for Development  
**Product Owner:** Nathan Butler  
**Lead Developer:** Nathan Butler

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Goals & Objectives](#goals--objectives)
4. [Success Metrics](#success-metrics)
5. [User Personas](#user-personas)
6. [Feature Overview](#feature-overview)
7. [Use Cases](#use-cases)
8. [Feature Specifications](#feature-specifications)
9. [User Experience](#user-experience)
10. [Phased Rollout](#phased-rollout)
11. [Constraints & Assumptions](#constraints--assumptions)
12. [Success Criteria](#success-criteria)
13. [Out of Scope](#out-of-scope)

---

## Executive Summary

**Product Name:** Device Manager  
**Type:** B2B SaaS Backend + Dashboard  
**Target Users:** Support staff, sales team, operations team  
**Problem Solved:** Currently, when customers experience equipment downtime, support staff have no visibility and must escalate to developers for troubleshooting—wasting developer time and delaying customer resolution.

**Solution:** Device Manager is a centralized monitoring and troubleshooting platform that empowers support staff to diagnose and resolve customer equipment issues independently through:

1. **Real-time monitoring** — See which devices are online, offline, or in error states
2. **Smart troubleshooting** — System suggests most-effective solutions based on past repairs (85%+ success rates)
3. **Knowledge capture** — Support team learns and improves troubleshooting actions as they resolve issues
4. **Audit trail** — Complete history of what happened and when for each device

**Business Impact:**
- **Reduce customer downtime** → Customers lose less revenue
- **Free up developers** → Can focus on product instead of support
- **Empower support team** → Support resolves 95% of issues without escalation
- **Scale to 250+ devices** → System designed for growth without VPN bottlenecks

**Timeline:** Phase 1A (weeks 1-8), Phase 2 Trial (weeks 9-16), Phase 3 Full Rollout (weeks 17-20)

---

## Problem Statement

### Current State (As-Is)

**The Workflow:**
```
Customer calls
    ↓
Sales answers (no visibility)
    ↓
Sales calls Developer
    ↓
Developer manually investigates
    ↓
Developer fixes it
    ↓
Knowledge lost, process repeats for next customer
```

**Pain Points:**
1. **Developers are bottleneck** — Every support issue blocks a developer
2. **Slow resolution** — Takes hours to resolve what could take minutes
3. **No visibility** — Sales/support can't see device state without developer
4. **Knowledge silos** — Each developer solves same problems independently
5. **Customer impact** — Downtime costs customer money while we investigate

### Metrics (Current)

- **Average time to resolution:** 2-4 hours
- **Developer hours/month on support:** ~10 hours (should be 0)
- **Device downtime cost to customers:** $200-750 per incident
- **Support team empowerment:** 0% (complete dependency on devs)

### Desired State (To-Be)

**The Workflow:**
```
Customer calls
    ↓
Support/Sales opens dashboard
    ↓
System shows error + suggested fixes (85%+ success)
    ↓
Support follows steps
    ↓
Issue resolved in 5-15 minutes
    ↓
Knowledge captured for next time
```

**Target Metrics (Phase 1 End):**
- **Average time to resolution:** 5-15 minutes
- **Developer hours/month on support:** ~2 hours (95% reduction)
- **Support team resolution rate:** 90% without escalation
- **System learning:** Each fix improves success rate for next person

---

## Goals & Objectives

### Primary Goals

**G1: Empower Support Team**
- Support staff can diagnose issues without developer involvement
- Clear troubleshooting guides for common issues
- Knowledge base improves as team solves problems

**G2: Reduce Developer Support Burden**
- Reduce developer troubleshooting time from 40 hrs/month to <2 hrs/month
- Free developers for product work, not firefighting
- Only escalate truly novel issues

**G3: Improve Customer Experience**
- Reduce average downtime from 2-4 hours to 5-15 minutes
- Increase resolution rate (90%+ first contact)
- Transparent communication: customer sees what we're doing

**G4: Scale Without Infrastructure Complexity**
- Support 20 devices today, 220 devices in 18 months
- No VPN bottleneck or IP conflict scaling issues
- Each new device adds minimal operational overhead

### Secondary Goals

**G5: Capture Institutional Knowledge**
- Document what works (and what doesn't) for each error
- New hires can use system immediately
- Continuous improvement as team learns

**G6: Build Foundation for Customer Self-Service (Phase 2)**
- Architecture supports customer-facing portal later
- Customers can monitor their own devices
- Reduces support burden further

---

## Success Metrics

### Phase 1 Success (Week 20, after 8-week trial)

| Metric | Current | Target | Success? |
|--------|---------|--------|----------|
| **Time to Resolution** | 120-240 min | 5-15 min | <15 min average |
| **Support Resolution Rate** | 0% (all escalate) | 95%+ | 95%+ without dev help |
| **Developer Support Hours** | 40 hrs/month | <2 hrs/month | 95% reduction |
| **System Uptime** | N/A | 99%+ | No outages >1 hr |
| **Error Knowledge Base** | 0 entries | 20+ entries | 20+ documented errors |
| **Device Monitoring** | 0 monitored | 20 devices | 20 devices live |
| **Support Team Satisfaction** | N/A | 8/10+ | Self-reported satisfaction |
| **Device Uptime Improvement** | Baseline | +15-20% | Customers report less downtime |

### Phase 2 Success (Week 16, after trial period)

- PLC systems running stably
- Support team performing without training wheels
- Repair action success rates optimized (90%+)
- Ready to expand to remaining devices with confidence

### Phase 3 Success (Week 20+, after full rollout)

- All 20 devices managed through system
- Scaling proven (no issues at 20 devices)
- Ready for Phase 1.5 enhancements

### Financial Success Metrics

| Metric | Value |
|--------|-------|
| **Year 1 Developer Hours Saved** | 450+ hours |
| **Year 1 Cost Savings** | $185K+ (support team freed up) |
| **Customer Revenue Protected** | $54K/year (reduced downtime) |
| **Year 1 ROI** | 146% ($87K net benefit on $51K investment) |

---

## User Personas

### Persona 1: Leroy (Sales / Customer Success Manager)

**Demographics:**
- Age: 41
- Experience: 8 years in sales and account management
- Technical skill: Low (no engineering background, comfortable with standard web tools and CRMs)
- Goals: Keep customers happy, answer their calls with confidence, protect the relationship

**Needs:**
- Quick, plain-English status on a customer's device when they call in
- Enough context to explain what happened and what is being done about it
- No need to escalate to a developer for basic "why is it down" questions
- Works entirely from a browser at his desk or laptop

**Pain Points:**
- Customers call frustrated and he has no information to give them
- Has to put customers on hold and chase down a developer for answers
- Technical dashboards and raw data mean nothing to him
- Looks bad in front of customers when he can't explain a simple outage

**Quote:** *"My customer is on the phone right now — I just need to know what to tell them."*

---

### Persona 2: Joe (Field Maintenance Technician)

**Demographics:**
- Age: 54
- Experience: 20+ years in field equipment maintenance
- Technical skill: Low-Intermediate (comfortable with tools, not software systems)
- Goals: Diagnose and fix the unit in front of him, get the customer back up and running

**Needs:**
- Know immediately why a specific device is not working
- See recent fault history and error codes for the unit on-site
- Clear, plain-language explanations — not raw data or developer jargon
- Access from a phone or tablet while standing next to the equipment

**Pain Points:**
- Arrives on-site with no context on what the device has been doing
- Can't tell if a fault is hardware failure, config issue, or connectivity problem
- Has to call the office to ask questions that should be answerable on the spot
- Unfamiliar with newer software tools; steep learning curves slow him down

**Quote:** *"I'm standing right in front of this thing — just tell me what's wrong with it."*

---

### Persona 3: Megan (Developer/Tech Lead)

**Demographics:**
- Age: 35
- Experience: 10 years software engineering
- Technical skill: Advanced
- Goals: Build product, not fix support issues

**Needs:**
- Support can handle 95% of issues without my help
- Clear escalation path for novel issues
- Data on common problems for future product improvements
- Audit trail for debugging

**Pain Points:**
- Spending 15+ hours/month on support instead of product
- Interruptions derail focus
- Same issues repeat monthly
- No institutional knowledge of patterns

**Quote:** *"I want support to be independent. Give them tools to fix it."*

---

## Feature Overview

### Phase 1A: Core Management System (Weeks 1-8)

**F1: Device Registration & Status**
- Devices auto-register when powered on
- Real-time online/offline status
- Last error display
- Metrics (throughput, cycle time, error rate)

**F2: Real-Time Monitoring Dashboard**
- List all devices (20 in Phase 1)
- Filter by status (online, offline, error)
- See customer name and location
- At-a-glance health summary

**F3: Intelligent Troubleshooting System**
- Common errors pre-populated (4-5 most common)
- Repair actions for each error
- Sorted by success rate
- Support staff can add new actions

**F4: Knowledge Base**
- Error type → Suggested fixes mapping
- Success rate tracking (95% means try this first)
- Capture what worked (support records outcome)
- System learns (success rate auto-updates)

**F5: Command Execution**
- Send commands remotely (restart, reset state machine, etc.)
- No SSH access needed
- Audit trail of who sent what
- Results logged

**F6: Error & Log Tracking**
- Recent errors displayed
- Error history per device
- Resolution notes
- Time to resolution tracking

### Phase 1B: Trial Period (Weeks 9-16)

**F7: Live Learning**
- Repair actions refined based on real usage
- Success rates improve over time
- New error types added as discovered
- Support team expertise captured

**F8: Team Coordination**
- See who's handling which issue
- Leave notes for others
- Prevent duplicate troubleshooting

### Phase 1C: Full Rollout (Weeks 17-20)

**F9: Multi-Device Type Support**
- PLC systems (Phase 1A)
- Additional device types (Phase 1C)
- Expandable for other device types

**F10: Mobile Support**
- Mobile-friendly dashboard
- Works on phones/tablets
- Support can troubleshoot in field

### Future (Phase 2+)

**F11: Alerting & Notifications** (Phase 1.5)
- Device goes offline → Notification
- Error spike → Alert
- Proactive vs. reactive

**F12: Customer Portal** (Phase 2)
- Customers see own device status
- Read-only access to metrics
- Historical trend data
- Reduces customer calls

**F13: Advanced Analytics** (Phase 2)
- Predict failures before they happen
- Identify systemic issues
- Recommend hardware upgrades

---

## Use Cases

### Use Case 1: Support Resolves Common Error

**Actor:** Sarah (Support Specialist)  
**Trigger:** Customer calls: "My device isn't detecting products"

**Flow:**
1. Sarah opens Device Manager dashboard
2. Searches for customer's device
3. Sees status: "Photoeye Not Detecting" error
4. Dashboard shows 3 repair actions, sorted by success rate:
   - "Check reflector alignment" (95% success)
   - "Clean photoeye lens" (10% success)
   - "Power cycle device" (8% success)
5. Sarah tells customer: "First, check if the reflector is aligned and clean"
6. Customer does it → error clears
7. Sarah clicks: "✓ Action 1 worked, spent 5 minutes"
8. System records: Success for this repair action
9. Device error marked as "resolved"
10. Next time someone sees this error, success rate might increase to 96%

**Result:** Issue resolved in 8 minutes, no developer involved

---

### Use Case 2: Support Escalates Novel Issue

**Actor:** Sarah (Support Specialist)  
**Trigger:** Customer reports unfamiliar error

**Flow:**
1. Sarah opens Device Manager
2. Device shows error: "State Machine Timeout"
3. No repair actions exist for this error yet
4. Sarah sees: "Unknown error, escalate to developer"
5. Sarah clicks: "Escalate" and notes describe the situation
6. Email goes to Alex (developer) with full context
7. Alex investigates, finds cause, tells Sarah what to do
8. Sarah follows steps, issue resolved
9. Sarah clicks: "Add new repair action: [what Alex said]"
10. System learns this new error type
11. Next person with this error will have a solution

**Result:** Novel issue escalated properly, but knowledge captured for future

---

### Use Case 3: Developer Identifies Product Issue

**Actor:** Alex (Developer)  
**Trigger:** Sees same error 20 times in last week

**Flow:**
1. Alex reviews Device Manager error logs
2. Sees "Sensor timeout" occurred 47 times, 80% fail rate
3. Different from typical "sensor disconnected" (95% success)
4. Realizes pattern: happens on specific device types
5. Investigates code: bug in firmware version 1.2
6. Fixes in version 1.3
7. Rolls out to devices
8. Error rate drops to 5% (just hardware failures now)

**Result:** Root cause fixed at product level, not just patched at support level

---

### Use Case 4: Support Team Learns Over Time

**Actor:** Sales/Support team  
**Trigger:** Monthly review meeting

**Flow:**
1. Manager pulls Device Manager report
2. See monthly stats:
   - 200 errors logged
   - 190 resolved by support (95%)
   - 10 escalated to dev (5%)
   - Most common: Sensor timeout (42 occurrences)
   - Most resolved: Photoeye issue (95% success)
3. Team reviews: "What's working well? What needs improvement?"
4. Identify: New support person has lower resolution rate
5. Plan training on top 5 error types
6. Success rate improves next month

**Result:** Continuous improvement through data

---

## Feature Specifications

### F1: Device Registration & Status

**Description:** Devices auto-register and report status in real-time

**User Interaction:**
1. Device powers on
2. Device connects to backend
3. Backend auto-creates device record (if new)
4. Device sends: device_id, device_type, location
5. Dashboard immediately shows device online

**Data Captured:**
- Device ID
- Device type (PLC, sensor_hub)
- Firmware version
- Online status
- Last error
- Current metrics (throughput, cycle time, error rate)
- Last seen timestamp

**API Endpoints:**
- `POST /api/auth/login` — Device gets credentials
- `GET /api/devices/{device_id}/status` — Current status
- `GET /api/devices/{device_id}/metrics` — Historical metrics

**Success Criteria:**
- Device shows up within 5 seconds of powering on
- Status updates within 10 seconds of change
- Metrics appear within 30 seconds

---

### F2: Real-Time Monitoring Dashboard

**Description:** Support staff sees all devices and their status at a glance

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ Device Manager - All Devices                         │
├─────────────────────────────────────────────────────┤
│ Filter: [Online] [Offline] [Error] [Last 24h Error] │
├─────────────────────────────────────────────────────┤
│ Device         │ Status     │ Customer  │ Last Error │
├─────────────────────────────────────────────────────┤
│ plc-001        │ 🟢 Online  │ Acme Inc  │ None       │
│ plc-042        │ 🔴 Offline │ Acme Inc  │ 2h ago     │
│ plc-105        │ 🟡 Error   │ Beta Corp │ Sensor     │
│ plc-099        │ 🟢 Online  │ Gamma Ltd │ None       │
└─────────────────────────────────────────────────────┘

[Click device to see details, metrics, commands, history]
```

**Interactions:**
- Click device → see detail view with repair suggestions
- Filter by status → see only devices with issues
- Search by customer/location → find quickly
- See uptime % per device

**Success Criteria:**
- Page loads <2 seconds
- Filters work instantly
- Real-time updates (status changes appear in <5 seconds)

---

### F3: Intelligent Troubleshooting System

**Description:** Error → Suggested repairs, ranked by success rate

**Data Model:**
```
Error Type (e.g., "Photoeye Not Detecting")
  ├─ Probable Causes: [reflector fallen off, lens dirty, etc.]
  ├─ Repair Action 1: [Check alignment] - 95% success
  ├─ Repair Action 2: [Clean lens] - 10% success
  └─ Repair Action 3: [Power cycle] - 8% success
```

**User Experience:**
1. Device shows error
2. Dashboard displays: "Photoeye Not Detecting"
3. Shows repair actions ranked by success rate
4. Support tries action 1 first (most likely to work)
5. Records outcome: "✓ Worked" or "✗ Didn't work"
6. System updates success rate

**Algorithm:**
```
success_rate = successful_occurrences / total_occurrences
Display order: Sort by success_rate DESC
Color code: 
  - 80%+: Green (try first)
  - 50-79%: Yellow (try second)
  - <50%: Red (try last)
```

**Success Criteria:**
- Most effective repair tries first
- Success rates update in real-time
- New repair actions can be added mid-call

---

### F4: Knowledge Base

**Description:** Living database of errors and solutions that improves over time

**Features:**
- Error type → description → probable causes
- Repair action steps with estimated time
- Success rate tracking (auto-calculated)
- Support staff can add new actions without developer
- Search errors by code or name
- View all actions for an error, sorted by effectiveness

**Support Interface:**
```
Error: Photoeye Not Detecting

Repair Actions:
1. Check reflector aligned (5 min)
   Tried: 23 times, Worked: 20 times (87%)
   [Edit] [Delete]

2. Clean photoeye lens (2 min)
   Tried: 30 times, Worked: 12 times (40%)
   [Edit] [Delete]

[+ Add New Action]
```

**Success Criteria:**
- Support can add action in <1 minute
- Success rates auto-update after each repair
- System shows "trending up/down" indicators

---

### F5: Command Execution

**Description:** Support sends commands to devices without SSH access

**Supported Commands (Phase 1):**
- `restart_plc` — Restart the PLC
- `reset_state_machine` — Clear stuck state machine
- `reboot_device` — Full device reboot
- `clear_error_log` — Clear error history

**Flow:**
1. Support opens device detail
2. Clicks: "Send Command" → Select "Restart PLC"
3. Confirmation: "About to restart PLC on plc-001"
4. Clicks: "Confirm"
5. Dashboard shows: "Command sent, waiting for execution"
6. Device executes, reports back
7. Status changes: "PLC restarted at 14:35"
8. Command logged with "Sent by Sarah at 14:35"

**Security:**
- Requires dashboard login
- Audit trail of all commands
- Only pre-defined commands (no arbitrary execution)
- Command results logged

**Success Criteria:**
- Command executes within 5 seconds
- Support sees confirmation
- Full audit trail

---

### F6: Error & Log Tracking

**Description:** See what went wrong and when

**Displays:**
- Recent errors (last 24 hours)
- Error frequency (how many times this week)
- Error timeline (when it occurred)
- Resolution notes (what we did)
- Time to resolution

**Log Display:**
```
Device: plc-001

Recent Errors:
📍 14:35 - Sensor Timeout
   └─ How long: 15 minutes
   └─ Resolution: Checked sensor cable, was loose
   └─ Resolved by: Sarah
   └─ Fix attempts: 2

📍 09:15 - Photoeye Not Detecting
   └─ How long: 8 minutes
   └─ Resolution: Cleaned reflector
   └─ Resolved by: Mike

📍 Yesterday 16:42 - Internet Disconnected
   └─ How long: 35 minutes (customer's ISP)
   └─ Resolution: Waited for ISP recovery
   └─ Resolved by: Escalated
```

**Success Criteria:**
- Errors visible within 10 seconds of occurrence
- Support can see root cause and resolution
- Trends visible (error X happens every Monday?)

---

## User Experience

### Dashboard Flow

**Entry Point:** Support logs in
```
/login
  → Email/Password (hardcoded in Phase 1)
  → Dashboard shows all devices
```

**Device Status View:**
```
Device: plc-042
Status: 🟡 ERROR
Last Seen: 2 minutes ago
Location: Phoenix, AZ
Customer: Acme Recycling

CURRENT ERROR:
"Photoeye Not Detecting" (2 hours, 15 minutes)

SUGGESTED FIXES (ranked by success):
1. ✅ Check reflector alignment [95% success - 23 times]
   Estimated time: 5 min
   [Try This] [More Info]

2. ⚠️ Clean photoeye lens [40% success - 30 times]
   Estimated time: 2 min
   [Try This] [More Info]

3. ⏰ Power cycle device [8% success - 50 times]
   Estimated time: 3 min
   [Try This] [More Info]

[Don't see your issue? Escalate to Developer]

HISTORY:
14:00 - Error: Photoeye Not Detecting
14:20 - Support: Tried "Check alignment" ✗ Didn't work
14:35 - Support: Tried "Clean lens" ✓ Worked!
14:36 - Device: Error cleared
```

**Mobile Experience:**
- Same information in responsive layout
- One-handed operation
- Large buttons for field use

---

## Phased Rollout

### Phase 1A: Core Platform (Weeks 1-8)

**Scope:**
- PLC systems only
- 5-10 test devices
- Support team using system
- All core features working

**Team:** 2 developers @ 50% bandwidth  
**Infrastructure:** Local Docker Compose development

**Deliverable:** System ready for trial deployment

---

### Phase 2: Trial & Validation (Weeks 9-16, 8 weeks)

**Scope:**
- Live on DigitalOcean
- 15-20 PLC systems in production
- Real errors being captured
- Support team learning

**Team:** Minimal (support team running it, dev available)  
**Infrastructure:** Production on DigitalOcean droplet

**Goals:**
- Prove system works reliably
- Validate support team resolution rate (target: 95%)
- Refine error catalog based on real issues
- Measure time-to-resolution improvement

**Success Check:** Are we hitting all success metrics?

---

### Phase 3: Full Rollout (Weeks 17-20, 4 weeks)

**Scope:**
- Deploy to all remaining devices
- Expand coverage to all device types

**Team:** 2 developers for deployment, then minimal  
**Infrastructure:** Same DigitalOcean, scaled slightly

**Deliverable:** Full fleet managed by system

---

### Phase 1.5: Enhancements (After Phase 3, Concurrent)

**New Features (Not in Phase 1):**
- Alerting & notifications (device offline → alert)
- Mobile app (native iOS/Android)
- Two-factor authentication
- Advanced RBAC (Admin vs Support vs Viewer roles)
- Historical trend analysis
- Scheduled reports

**Timeline:** Weeks 21+

---

### Phase 2: Customer Portal (Month 6+)

**New Features:**
- Customer login
- Customer sees own device status
- Customer sees own metrics/history
- Reduces customer calls

**Timeline:** Month 6+

---

## Constraints & Assumptions

### Technical Constraints

**C1: Device Architecture**
- All field devices are Linux-based
- Devices can reach public internet (no VPN)
- Devices support MQTT TLS protocol
- HTTPS certificate pinning supported

**C2: Infrastructure**
- DigitalOcean droplet ($6-12/month)
- PostgreSQL required
- No advanced infrastructure (Kubernetes, etc.)

**C3: Scalability**
- Phase 1: Designed for 20-100 devices
- Phase 1.5: Designed for 220+ devices
- Performance targets: <1 second API response, 99%+ uptime

### Organizational Constraints

**C4: Team**
- 2 developers @ 50% bandwidth
- No dedicated DevOps (manual deployment)
- Support team existing (not hiring)

**C5: Timeline**
- 5 months from start to full rollout
- 8-week trial period mandatory
- No acceleration without impact

### Business Constraints

**C6: Cost**
- Max $100K development budget (covered by internal resources)
- Infrastructure ~$25-30/month (DigitalOcean)
- No licensing costs (open source stack)

---

### Assumptions

**A1: Support Team Adoption**
- Assume support team will actively use system
- Assume they'll record repair outcomes
- Assume they won't escalate prematurely

**A2: Device Reliability**
- Devices can reach backend 99%+ of time
- No major network outages
- Customers have stable internet

**A3: Error Types**
- Common errors are known (4-5 identified)
- ~80% of issues fall into common categories
- New issues arise <2/week

**A4: Success Rates**
- Repair actions have measurable success rates
- Success rates improve as data accumulates
- Teams follows highest-success-rate actions first

**A5: Operational Stability**
- No major production outages during trial
- Support team doesn't face unexpected high volume
- Rollout doesn't coincide with major product changes

---

## Success Criteria

### Phase 1A (Week 8)

**Technical:**
- ✅ Docker Compose brings up complete system (6/6 services)
- ✅ Database schema matches specification
- ✅ All 6 API endpoints functional and tested (70%+ coverage)
- ✅ Nginx rate limiting working (verified with load testing)
- ✅ TLS certificates auto-renewing
- ✅ Deployment to DigitalOcean successful

**Functional:**
- ✅ Devices can register and report status
- ✅ Support can see all devices on dashboard
- ✅ Support can send commands to devices
- ✅ Support can view repair actions for errors
- ✅ Support can record repair outcomes
- ✅ System calculates and displays success rates

**Documentation:**
- ✅ PLAN.md complete and accurate
- ✅ API documentation with examples
- ✅ Deployment guide written
- ✅ Local development guide written

---

### Phase 2 (Week 16)

**Business:**
- ✅ Support resolves 95%+ of issues without escalation
- ✅ Average time-to-resolution: <15 minutes
- ✅ Developer hours reduced to <2 hours/month
- ✅ Error knowledge base has 15-20 error types documented
- ✅ Repair action success rates show improvement trend

**Technical:**
- ✅ Zero unplanned outages >1 hour
- ✅ 99%+ uptime
- ✅ All metrics flowing to InfluxDB
- ✅ Response times <1 second average

**Team:**
- ✅ Support team fully trained
- ✅ Support team confident using system
- ✅ Team reports high satisfaction (8/10+)

---

### Phase 3 (Week 20)

**Scope:**
- ✅ All PLC systems (15+) managed
- ✅ All devices online

**Operations:**
- ✅ No issues with scaling to 40 devices
- ✅ Support team handles all device types
- ✅ Knowledge base covers all common errors

**Business:**
- ✅ Customer downtime reduced 15-20%
- ✅ Developer freed from support
- ✅ Support team empowered
- ✅ Foundation built for Phase 1.5 features

---

## Out of Scope

### Phase 1 Exclusions

**NOT Included:**
- ❌ Customer-facing portal (Phase 2)
- ❌ Advanced analytics/ML predictions (Phase 2)
- ❌ Two-factor authentication (Phase 1.5)
- ❌ User RBAC (Phase 1.5) — all users are "support"
- ❌ Scheduled reports (Phase 1.5)
- ❌ Mobile app (Phase 1.5)
- ❌ Slack/Teams integration (Phase 1.5)
- ❌ Webhook notifications (Phase 1.5)
- ❌ Advanced filtering/saved searches (Phase 1.5)
- ❌ Multi-language support (Phase 2)
- ❌ Custom device types (hardcoded 1-2 types in Phase 1)
- ❌ Distributed deployment (only one server in Phase 1)
- ❌ Backup/disaster recovery automation (Phase 1.5)
- ❌ Custom branding (Phase 1.5)

### Why Excluded

- **Customer Portal:** Different user base, requires different auth model, deferred to Phase 2 when core is stable
- **Advanced Features:** Add complexity, not needed for MVP, can add in Phase 1.5 with user feedback
- **Multi-tenancy:** Not needed, all users are internal team
- **Advanced Auth:** Hardcoded credentials simpler, can upgrade in Phase 1.5

---

## Decision Log

### Why Device Manager (not existing tool)?

**Considered:** Zendesk, Jira, ServiceNow  
**Rejected:** 
- Wrong use case (ticketing, not real-time device monitoring)
- Expensive for small team
- Would still need custom development for device integration
- Can't track success rates of repairs

**Chosen:** Custom platform  
**Rationale:** Tightly integrated with devices, learns from repairs, optimized for field device support

---

### Why Public Backend (not VPN)?

**Considered:** VPN to internal network  
**Rejected:**
- Scales poorly (IP conflicts at 100+ devices)
- Single point of failure
- Complex to manage across geographies
- Doesn't support future customer API

**Chosen:** Public backend with certificate pinning + API keys  
**Rationale:** Standard for field devices, secure, scalable, proven pattern

---

### Why Database-Driven Knowledge Base?

**Considered:** Wiki (BookStack), Google Sheets, static JSON  
**Rejected:**
- Wiki: Overkill for Phase 1, adds complexity
- Sheets: Can't track success rates automatically
- JSON: Not updatable by support team, breaks separation

**Chosen:** PostgreSQL database with API  
**Rationale:** Support team can update via UI, success rates auto-calculated, integrates with system

---

## Dependencies & Risks

### External Dependencies

**D1: Device Firmware**
- Devices must support MQTT TLS
- Devices must have Python runtime for agent
- **Risk:** Legacy devices incompatible
- **Mitigation:** Test with existing device fleet first

**D2: Customer Network**
- Devices need internet connectivity
- MQTT port 8883 must not be blocked
- **Risk:** Corporate firewalls block outbound
- **Mitigation:** Certificate pinning + flexible auth

**D3: DigitalOcean**
- Relies on DigitalOcean uptime
- **Risk:** Outage affects all devices
- **Mitigation:** Monitoring, failover to backup droplet (Phase 1.5)

### Internal Dependencies

**D4: Support Team Adoption**
- Success depends on team using system
- **Risk:** Resistance to change, "old way works"
- **Mitigation:** Training, show ROI, support buy-in early

**D5: Error Catalog Accuracy**
- System only as good as error definitions
- **Risk:** Missing error types, incorrect repair actions
- **Mitigation:** Team-sourced, 8-week trial to refine

### Risks

**R1: Performance at Scale (220 devices)**
- **Severity:** Medium
- **Probability:** Low (tested design)
- **Mitigation:** Load testing, database indexing, Phase 1.5 optimization

**R2: Security Breach**
- **Severity:** Critical
- **Probability:** Very low (certificate pinning, TLS, rate limiting)
- **Mitigation:** Regular security audits, penetration testing

**R3: Support Team Doesn't Adopt**
- **Severity:** High
- **Probability:** Low (good design, solves real problem)
- **Mitigation:** Early training, gather feedback, iterate

**R4: Novel Errors Not Handled**
- **Severity:** Medium
- **Probability:** Medium (all systems have edge cases)
- **Mitigation:** Clear escalation path, 8-week trial to discover patterns

---

## Appendix

### Glossary

**Device:** Physical equipment in field (PLC system or other field unit)  
**Error Type:** Category of problem (e.g., "Sensor Disconnected")  
**Repair Action:** Step to fix an error (e.g., "Check cable connection")  
**Success Rate:** % of times a repair action fixed the problem  
**Escalate:** Involve developer when support can't handle  
**Knowledge Base:** Database of errors + repair actions + success rates  
**Troubleshooting:** Process of diagnosing and fixing issues  
**Downtime:** Time when device is not operational, losing revenue  
**Resolution:** When an error is fixed and error marked resolved  

---

### Contact & Questions

**Product Owner:** [To be assigned]  
**Tech Lead:** [To be assigned]  
**Support Lead:** [To be assigned]  

---

**Document Status:** ✅ Approved  
**Approval Date:** June 2026  
**Next Review:** Week 8 (Phase 1A completion)
