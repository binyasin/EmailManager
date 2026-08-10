import { ImapFlow } from 'C:/Users/DELL LATITUDE 5520/.openclaw/workspace/skills/smart-email/node_modules/imapflow/index.js';
import { simpleParser } from 'C:/Users/DELL LATITUDE 5520/.openclaw/workspace/skills/smart-email/node_modules/mailparser/index.js';
import fs from 'fs';
import path from 'path';
import Database from 'better-sqlite3';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillDir = 'C:/Users/DELL LATITUDE 5520/.openclaw/workspace/skills/smart-email';
const db = new Database(path.join(skillDir, 'data', 'email.db'));

const account = db.prepare('SELECT * FROM email_accounts WHERE email = ?').get('support@stellarstech.com');
if (!account) {
  console.log(JSON.stringify({error: 'Account not found'}));
  process.exit(1);
}

const client = new ImapFlow({
  host: account.imap_host || 'mail.stellarstech.com',
  port: account.imap_port || 993,
  secure: true,
  auth: {
    user: account.email,
    pass: account.password
  },
  logger: false
});

async function main() {
  await client.connect();
  const mailbox = await client.mailboxOpen('INBOX');
  const messages = await client.fetch({ uid: [6] }, { source: true, uid: true }, { uid: true });
  
  for await (const msg of messages) {
    try {
      const parsed = await simpleParser(msg.source);
      const result = {
        subject: parsed.subject,
        from: parsed.from ? parsed.from.text : '',
        date: parsed.date,
        text: parsed.text,
        attachments: parsed.attachments.map(a => ({
          filename: a.filename,
          contentType: a.contentType,
          size: a.size
        }))
      };
      
      const outDir = path.join(__dirname, 'temp_attachments');
      if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, {recursive: true});
      
      for (const a of parsed.attachments) {
        const filePath = path.join(outDir, a.filename);
        fs.writeFileSync(filePath, a.content);
        result.attachments.find(ra => ra.filename === a.filename).savedPath = filePath;
      }
      
      console.log(JSON.stringify(result, null, 2));
    } catch (e) {
      console.log(JSON.stringify({error: e.message}));
    }
  }
  
  await client.logout();
}

main().catch(e => console.log(JSON.stringify({error: e.message})));
