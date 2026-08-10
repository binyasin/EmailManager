const path = require('path');
const skillDir = path.join(__dirname, 'skills', 'smart-email');
const nodemailer = require(path.join(skillDir, 'node_modules', 'nodemailer'));
const { initDb, getAccounts } = require(path.join(skillDir, 'store'));

initDb();
const accounts = getAccounts();
const acct = accounts[0];

const subject = 'Re: Sales figures — Next Month Sales Plan';

const body = `Dear Aamir,

Following up on my earlier analysis of the July sales figures, here is the proposed sales plan for next month (August 2026). The goal is to reduce zero-sales employees from 44% to under 20% and increase total sales by at least 40%.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUGUST 2026 SALES PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━

═══════════════════════════════
1. MONTHLY SALES TARGETS
═══════════════════════════════

| Tier         | Target (Rs.) | Employees |
|--------------|-------------|-----------|
| Gold         | 6,000+      | Top 4     |
| Silver       | 4,000-5,999 | Mid 5     |
| Bronze       | 2,500-3,999 | Developing|
| Starter      | 1,500+ (minimum) | Zero-sales |

Minimum acceptable: Rs. 1,500 per employee
Stretch goal: Rs. 25,000 total (+22% over July's Rs. 20,500)

═══════════════════════════════
2. MENTORSHIP PROGRAM
═══════════════════════════════

Pair each zero-sales employee with a top performer:

  Mentor (Rs. 3,000)        →  Mentee (Rs. 0)
  ─────────────────────────────────────────────
  ASDLFKJD (1000002)        →  ASDLFKJD (1000007)
  J;ALSDK (1000008)         →  J;ALSDK (1000003)
  ADKL;JF (1000014)         →  ADKL;JF (1000012)
  DLFKJD (1000011)          →  DLFKJD (1000006)
  DFJLD (1000015)           →  DFJLD (1000005) + DFJLD (1000010)

Mentors receive 5% bonus on mentee's sales as incentive.

═══════════════════════════════
3. WEEKLY CHECK-IN SCHEDULE
═══════════════════════════════

Week 1 (Aug 1-7):   Kickoff meeting — assign targets & mentors
Week 2 (Aug 8-14):  First review — activity check, lead status
Week 3 (Aug 15-21): Mid-month review — adjust struggling employees
Week 4 (Aug 22-28): Pre-close push — final week sprint
Week 5 (Aug 29-31): Month-end wrap-up & reporting

Format: 15-minute group call every Monday + 5-min 1:1 with zero-sellers every Wednesday.

═══════════════════════════════
4. LEAD DISTRIBUTION
═══════════════════════════════

- Create lead bank: 80 leads minimum per month
- Each employee receives minimum 10 fresh leads
- Top performers get first pick of 15 leads
- Zero-sellers get additional 5 warm leads from mentor's pipeline
- Uncontacted leads recycle after 7 days

═══════════════════════════════
5. INCENTIVE STRUCTURE
═══════════════════════════════

- Top Performer of the Week: Rs. 500 bonus
- Top Performer of the Month: Rs. 2,000 bonus
- Most Improved: Rs. 1,000 (for zero→active transition)
- Mentorship Bonus: 5% of mentee's first-month sales
- Team Bonus: Rs. 3,000 pool if total exceeds Rs. 25,000

═══════════════════════════════
6. ACTIVITY TRACKING
═══════════════════════════════

Daily log (simple WhatsApp or sheet):

| Metric            | Minimum Daily |
|-------------------|--------------|
| Calls attempted   | 20           |
| Calls connected   | 10           |
| Follow-ups sent   | 5            |
| Meetings booked   | 1            |
| Sales closed      | Track weekly |

This gives visibility BEFORE month-end, so we can intervene early.

═══════════════════════════════
7. EXPECTED RESULTS
═══════════════════════════════

If this plan is followed:

  July (Actual)          →  August (Target)
  ─────────────────────────────────────────
  Total: Rs. 20,500      →  Rs. 25,000-30,000
  Active: 9/16 (56%)     →  13/16 (81%)
  Zero Sales: 7 (44%)    →  3 or fewer (≤19%)
  Avg per active: 2,278  →  2,300+
  Top performers: 4      →  6+

═══════════════════════════════
NEXT STEPS
═══════════════════════════════

1. Confirm this plan or suggest modifications
2. Share actual employee names (replace placeholder codes)
3. Set launch date (recommend Aug 1)
4. Create WhatsApp group for daily reporting
5. Distribute lead bank before Day 1

I'm happy to jump on a call to walk through this in detail. Let me know your thoughts.

Best regards,
Siraj Uddin Binyasin`;

async function sendEmail() {
  const transporter = nodemailer.createTransport({
    host: 'smtp.gmail.com', port: 465, secure: true,
    auth: { user: acct.email, pass: acct.password },
  });

  try {
    const info = await transporter.sendMail({
      from: acct.email,
      to: 'aamir7601@gmail.com',
      subject: subject,
      text: body,
    });
    console.log('Sent! ID:', info.messageId);
  } catch (err) {
    console.error('Error:', err.message);
  }
}

sendEmail();
