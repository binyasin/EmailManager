import { initDb, addAccount, getAccount } from './store.js';
import { fetchNewEmails } from './imap.js';

initDb();

// Remove if exists first
const existing = getAccount('support@stellarstech.com');
if (existing) {
  console.log('Account exists, testing connection...');
}

const server = { host: 'mail.stellarstech.com', port: 993 };

try {
  const emails = await fetchNewEmails('support@stellarstech.com', 'Paki@9870', 60, server);
  // Store with custom host info
  addAccount('support@stellarstech.com', 'Paki@9870', 'custom:mail.stellarstech.com:993');
  console.log(JSON.stringify({ success: true, email: 'support@stellarstech.com', type: 'Custom IMAP (mail.stellarstech.com)', unread: emails.length }));
} catch (err) {
  console.error('Failed:', err.message);
}
