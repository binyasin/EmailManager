const path = require('path');
const skillDir = path.join(__dirname, 'skills', 'smart-email');
const nodemailer = require(path.join(skillDir, 'node_modules', 'nodemailer'));
const { initDb, getAccounts } = require(path.join(skillDir, 'store'));

initDb();
const accounts = getAccounts();
const acct = accounts[0]; // binyasin39@gmail.com

const replyTo = 'aamir7601@gmail.com'; // Syed Aamir Ali's email (found in original email headers)

const subject = 'Re: Sales figures — Analysis & Suggestions';
const body = `Dear Aamir,

Thank you for sharing the July 2026 sales figures. I've reviewed the data in detail and wanted to share my observations along with some actionable suggestions.

━━━━━━━━━━━━━━━━━━━━━━━━
KEY CONCERNS
━━━━━━━━━━━━━━━━━━━━━━━━

1. ZERO SALES — 7 out of 16 Employees (44%)
Employee codes 1000003 (J;ALSDK), 1000005 (DFJLD), 1000006 (DLFKJD), 1000007 (ASDLFKJD), 1000010 (DFJLD), 1000012 (ASDLFKJD), and 1000013 (J;ALSDK) recorded absolutely no sales. This is a serious concern — nearly half the team is contributing nothing.

2. Inconsistent Performance
Some employees like ASDLFKJD have wildly inconsistent results — Rs. 3,000 in one entry and Rs. 0 in another. This suggests possible data entry issues or uneven territory/lead distribution.

3. Data Quality Issues
The employee names appear as keyboard-mash strings (AS;DJFL, ADKL;JF, etc.) and some remarks are incomplete ("tst", "ets"). Proper naming would make tracking and accountability much easier.

━━━━━━━━━━━━━━━━━━━━━━━━
QUESTIONS — Please Address
━━━━━━━━━━━━━━━━━━━━━━━━

I'd appreciate your insights on the following:

• What are the primary reasons for the 7 zero-sales employees? Is it lack of leads, territory issues, training gaps, motivation problems, or something else?

• For inconsistent performers like ASDLFKJD (Rs. 3,000 vs Rs. 0), is there a known reason for the fluctuation?

• Are the employee names placeholders? If so, can we get actual names assigned to each code?

• What is the sales period covered — weekly, monthly, or bi-weekly? Knowing this helps benchmark against targets.

• Is there a defined sales target per employee? Without one, it's hard to measure who is underperforming.

━━━━━━━━━━━━━━━━━━━━━━━━
SUGGESTIONS TO BOOST SALES
━━━━━━━━━━━━━━━━━━━━━━━━

1. Set Clear Targets
Assign a minimum monthly sales target (e.g., Rs. 5,000) per employee. This creates accountability and makes it obvious who needs intervention.

2. Pair Zero-Sellers with Top Performers
Create mentorship pairs — each top performer (Rs. 3,000 earners) mentors 1-2 zero-sales employees. Shadowing and joint calls can quickly transfer skills.

3. Daily/Weekly Check-ins
Instead of waiting until end-of-period reports, implement brief daily stand-ups or weekly reviews to catch issues early. A 10-minute call can prevent a zero-sales month.

4. Lead Distribution Audit
Ensure territory/leads are fairly distributed. If some employees get better leads than others, the data will always be skewed.

5. Incentive Program
Introduce small rewards — even a "Top Performer of the Week" recognition — to create healthy competition and motivate the middle performers.

6. Training & Role-Play
For consistently low performers, conduct product knowledge sessions and sales role-playing exercises. Often the issue is confidence, not capability.

7. Track Activity, Not Just Results
Require employees to log daily calls, meetings, and follow-ups. Activity metrics help identify if the problem is effort or conversion.

8. Clean Up Data Entry
Standardize employee names and codes. Add a "Sales Period" column so we know exactly what timeframe each row covers.

━━━━━━━━━━━━━━━━━━━━━━━━

I look forward to hearing your thoughts, especially on the reasons behind the zero-sales employees. Happy to discuss this over a call if that's easier.

Best regards,
Siraj Uddin Binyasin`;

async function sendEmail() {
  const transporter = nodemailer.createTransport({
    host: 'smtp.gmail.com',
    port: 465,
    secure: true,
    auth: {
      user: acct.email,
      pass: acct.password,
    },
  });

  try {
    const info = await transporter.sendMail({
      from: acct.email,
      to: replyTo,
      subject: subject,
      text: body,
      // Reply to original email thread
      inReplyTo: 'sales_figures_july2026',
      references: 'sales_figures_july2026',
    });
    console.log('Email sent successfully!');
    console.log('Message ID:', info.messageId);
    console.log('Response:', info.response);
  } catch (err) {
    console.error('Error sending email:', err.message);
  }
}

sendEmail();
