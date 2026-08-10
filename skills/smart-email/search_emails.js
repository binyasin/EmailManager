const { initDb, getAccounts } = require('./store');
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
        // Search for emails containing "Searl" or "Searle" in the "from" field or query body
        const uids1 = await client.search({ header: { key: 'from', value: 'Searle' } });
        const uids2 = await client.search({ header: { key: 'from', value: 'Searl' } });
        
        // Let's also do a search by subject or text just in case:
        const uids3 = await client.search({ subject: 'Searle' });
        const uids4 = await client.search({ subject: 'Searl' });
        const uids5 = await client.search({ body: 'Searle' });
        const uids6 = await client.search({ body: 'Searl' });

        // De-duplicate uids
        const uids = Array.from(new Set([...uids1, ...uids2, ...uids3, ...uids4, ...uids5, ...uids6]));
        console.log(`Found ${uids.length} emails matching 'Searl' or 'Searle'.`);

        if (uids.length > 0) {
          // Fetch details for the found emails, sort/slice to latest if needed, let's list latest 10
          const latestUids = uids.sort((a,b) => b - a).slice(0, 10);
          for await (const msg of client.fetch(latestUids, {
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
              preview: msg.source ? msg.source.toString('utf8').substring(0, 300) : ''
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
