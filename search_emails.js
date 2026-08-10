const { initDb, getAccounts } = require('./skills/smart-email/store');
const { ImapFlow } = require('imapflow');

async function searchEmails() {
  initDb();
  const accounts = getAccounts();
  if (accounts.length === 0) {
    console.log("No accounts configured.");
    return;
  }

  for (const acct of accounts) {
    console.log(`Checking account: ${acct.email}`);
    const client = new ImapFlow({
      host: 'imap.gmail.com',
      port: 993,
      secure: true,
      auth: {
        user: acct.email,
        pass: acct.password
      },
      logger: false
    });

    try {
      await client.connect();
      const lock = await client.getMailboxLock('INBOX');
      try {
        // Search for emails containing "Searl" or "Searle" in the "from" field
        // We do not restrict to "seen: false"
        const uids1 = await client.search({ header: { key: 'from', value: 'Searle' } });
        const uids2 = await client.search({ header: { key: 'from', value: 'Searl' } });
        
        // De-duplicate uids
        const uids = Array.from(new Set([...uids1, ...uids2]));
        console.log(`Found ${uids.length} emails matching 'Searl' or 'Searle'.`);

        if (uids.length > 0) {
          // Fetch details for the found emails
          for await (const msg of client.fetch(uids, {
            uid: true,
            envelope: true,
            source: { maxBytes: 15000 },
          })) {
            const env = msg.envelope || {};
            const from = env.from?.[0];
            const fromStr = from ? `${from.name || ''} <${from.mailbox}@${from.host}>` : 'Unknown';
            const subject = env.subject || '(No Subject)';
            const date = env.date || new Date();
            console.log(JSON.stringify({
              uid: msg.uid,
              from: fromStr,
              subject: subject,
              date: date instanceof Date ? date.toISOString() : String(date),
              preview: msg.source ? msg.source.toString('utf8').substring(0, 1000) : ''
            }, null, 2));
          }
        }
      } finally {
        lock.release();
      }
      await client.logout();
    } catch (err) {
      console.error(`Error with ${acct.email}:`, err.message);
    }
  }
}

searchEmails();
