import { ImapFlow } from 'imapflow';
import { simpleParser } from 'mailparser';
import fs from 'fs';
import Database from 'better-sqlite3';

const db = new Database('data/email.db');
const account = db.prepare('SELECT * FROM email_accounts WHERE email = ?').get('support@stellarstech.com');
if (!account) {
  console.log(JSON.stringify({error: 'Account not found'}));
  process.exit(1);
}

const client = new ImapFlow({
  host: account.imap_host || 'mail.stellarstech.com',
  port: account.imap_port || 993,
  secure: true,
  auth: { user: account.email, pass: account.password },
  logger: false
});

async function main() {
  await client.connect();
  await client.mailboxOpen('INBOX');
  const messages = await client.fetch(
    { uid: [6] },
    { source: true, uid: true },
    { uid: true }
  );

  const outDir = 'C:/Users/DELL LATITUDE 5520/.openclaw/workspace/temp_attachments';
  fs.mkdirSync(outDir, { recursive: true });

  for await (const msg of messages) {
    try {
      const parsed = await simpleParser(msg.source);
      const result = {
        subject: parsed.subject,
        from: parsed.from ? parsed.from.text : '',
        date: parsed.date,
        text: parsed.text,
        attachments: []
      };

      for (const a of parsed.attachments) {
        const filePath = `${outDir}/${a.filename}`;
        fs.writeFileSync(filePath, a.content);
        result.attachments.push({
          filename: a.filename,
          contentType: a.contentType,
          size: a.size,
          savedPath: filePath
        });
      }

      console.log(JSON.stringify(result));
    } catch (e) {
      console.log(JSON.stringify({error: e.message}));
    }
  }

  await client.logout();
}

main().catch(e => console.log(JSON.stringify({error: e.message})));
