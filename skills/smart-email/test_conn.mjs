import { ImapFlow } from 'imapflow';

const client = new ImapFlow({
  host: 'outlook.office365.com',
  port: 993,
  secure: true,
  auth: { user: 'siraj.yasin001@outlook.com', pass: process.env.OUTLOOK_PASS },
  logger: false
});

try {
  await client.connect();
  console.log('OK - CONNECTED');
  await client.logout();
} catch (err) {
  console.error('CODE:', err.serverResponseCode || 'none');
  console.error('RESP:', err.response || 'none');
  console.error('MSG:', err.message);
  try { await client.logout(); } catch {}
}
