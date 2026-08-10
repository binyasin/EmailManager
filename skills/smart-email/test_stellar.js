import { ImapFlow } from 'imapflow';

const servers = [
  { label: 'mail.stellarstech.com', host: 'mail.stellarstech.com', port: 993 },
  { label: 'imap.stellarstech.com', host: 'imap.stellarstech.com', port: 993 },
  { label: 'stellarstech.com', host: 'stellarstech.com', port: 993 },
];

for (const srv of servers) {
  const client = new ImapFlow({
    host: srv.host,
    port: srv.port,
    secure: true,
    auth: { user: 'support@stellarstech.com', pass: 'Paki@9870' },
    logger: false,
  });
  try {
    console.log(`Trying ${srv.label}...`);
    await Promise.race([
      client.connect(),
      new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 10000)),
    ]);
    console.log(`✅ SUCCESS: ${srv.label} — connected!`);
    await client.logout();
    process.exit(0);
  } catch (err) {
    console.log(`❌ ${srv.label}: ${err.message}`);
    try { await client.logout(); } catch {}
  }
}
console.log('All servers failed');
