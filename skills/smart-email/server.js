// Enhanced server.js with self-login capabilities
/**
 * server.js — Email Skill Web UI with Self-Login
 *
 * Usage: node server.js [--port 3900]
 */

import http from 'http';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import pkg from 'googleapis';
const { OAuth2 } = pkg;

import { initDb, addAccount, addOAuthAccount, addGoogleOAuthAccount, updateTokens, getAccounts, getAccount,
        saveSelfLoginSession, getSelfLoginSession, getCompletedSelfLoginSession, removeSelfLoginSession,
        cleanupOldSelfLoginSessions } from './store.js';
import { fetchNewEmails, detectEmailType } from './imap.js';
import { refreshAccessToken, requestDeviceCode, pollForToken, fetchEmailsViaGraph,
        getGoogleAuthUrl, getGoogleTokensFromCode, refreshGoogleAccessToken, fetchEmailsViaGmail } from './oauth.js';
import { summarizeEmail, summarizeBatch } from './ai.js';
import { get, set, getAll } from './config.js';
const config = { get, set, getAll };

import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DATA_DIR = path.join(__dirname, 'data');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

// ─── Args ────────────────────────────────────────────────────

const args = process.argv.slice(2);
function getArg(name, def) {
  const idx = args.indexOf('--' + name);
  return idx !== -1 && args[idx + 1] ? args[idx + 1] : def;
}

const PORT = parseInt(getArg('port', '3900'));

// ─── Auth ────────────────────────────────────────────────────

function getOrCreateToken() {
  let token = config.get('web_token', '');
  if (!token) {
    token = crypto.randomBytes(24).toString('hex');
    config.set('web_token', token);
  }
  return token;
}

function checkAuth(req) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const cookieToken = (req.headers.cookie || '').split(';')
    .map(c => c.trim().split('='))
    .find(([k]) => k === 'token')?.[1];
  const queryToken = url.searchParams.get('token');
  const expected = getOrCreateToken();
  return cookieToken === expected || queryToken === expected;
}

// ─── API Routes ──────────────────────────────────────────────

async function handleApi(req, res, pathname, body) {
  const json = (data, status = 200) => {
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(data));
  };

  // Auth check
  if (pathname !== '/api/login') {
    if (!checkAuth(req)) return json({ error: 'Unauthorized' }, 401);
  }

  try {
    // POST /api/login
    if (pathname === '/api/login' && req.method === 'POST') {
      const { token } = JSON.parse(body);
      if (token === getOrCreateToken()) {
        res.writeHead(200, {
          'Content-Type': 'application/json',
          'Set-Cookie': `token=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000`,
        });
        res.end(JSON.stringify({ success: true }));
      } else {
        json({ error: 'Invalid token' }, 401);
      }
      return;
    }

    // GET /api/config
    if (pathname === '/api/config' && req.method === 'GET') {
      const all = config.getAll();
      const masked = {};
      for (const [k, v] of Object.entries(all)) {
        if (k === 'web_token') continue;
        masked[k] = (k.includes('key') || k.includes('password') || k.includes('secret'))
          ? (String(v).substring(0, 8) + '****') : v;
      }
      return json({ config: masked });
    }

    // POST /api/config
    if (pathname === '/api/config' && req.method === 'POST') {
      const { key, value } = JSON.parse(body);
      if (!key) return json({ error: 'key required' }, 400);
      config.set(key, value);
      return json({ success: true });
    }

    // GET /api/accounts
    if (pathname === '/api/accounts') {
      const accounts = getAccounts();
      return json({
        accounts: accounts.map(a => ({
          email: a.email,
          type: a.email_type,
          auth: a.auth_type,
        })),
      });
    }

    // POST /api/accounts/add
    if (pathname === '/api/accounts/add' && req.method === 'POST') {
      const { email, password, auth } = JSON.parse(body);
      if (!email) return json({ error: 'email required' }, 400);

      if (getAccount(email)) return json({ error: `${email} already exists` }, 400);

      const detected = await detectEmailType(email);

      if (auth === 'oauth') {
        const dc = await requestDeviceCode();
        if (dc.error) return json({ error: dc.error_description || dc.error }, 500);
        // Return device code for user to authorize
        return json({
          action: 'oauth_pending',
          email,
          detected: detected.label,
          verification_uri: dc.verification_uri,
          user_code: dc.user_code,
          device_code: dc.device_code,
          interval: dc.interval || 5,
        });
      }

      if (!password) return json({ error: 'password required', detected: detected.label }, 400);

      const serverArg = detected.host
        ? { host: detected.host, port: detected.port || 993 }
        : detected.type;

      const emails = await fetchNewEmails(email, password, 60, serverArg);
      let storeType = detected.type;
      if (detected.host && !['gmail', 'outlook', 'workspace'].includes(detected.type)) {
        storeType = `custom:${detected.host}:${detected.port || 993}`;
      }
      addAccount(email, password, storeType);
      return json({ success: true, email, type: detected.label, unread: emails.length });
    }

    // POST /api/accounts/oauth-poll
    if (pathname === '/api/accounts/oauth-poll' && req.method === 'POST') {
      const { email, device_code, interval } = JSON.parse(body);
      const tokens = await pollForToken(device_code, interval || 5, 300);
      const emails = await fetchEmailsViaGraph(tokens.access_token, 60);
      const detected = await detectEmailType(email);
      addOAuthAccount(email, detected.type || 'outlook', tokens.access_token, tokens.refresh_token, tokens.expires_at);
      return json({ success: true, email, unread: emails.length });
    }

    // POST /api/accounts/google-oauth-start
    if (pathname === '/api/accounts/google-oauth-start' && req.method === 'POST') {
      const { email } = JSON.parse(body);
      if (!email) return json({ error: 'email required' }, 400);

      const state = crypto.randomBytes(16).toString('hex');
      const session = {
        id: state,
        email,
        provider: 'google',
        state: 'pending',
        createdAt: Date.now(),
        expiresAt: Date.now() + 15 * 60 * 1000,
      };
      saveSelfLoginSession(session);

      const authUrl = getGoogleAuthUrl(state);

      return json({
        action: 'google_oauth_pending',
        email,
        auth_url: authUrl,
        state: state,
        message: `Please authorize the application in your browser to continue.`,
      });
    }

    // POST /api/accounts/google-oauth-callback
    if (pathname === '/api/accounts/google-oauth-callback' && req.method === 'POST') {
      const { email, code, state } = JSON.parse(body);
      if (!email || !code || !state) return json({ error: 'Missing required parameters' }, 400);

      const session = getSelfLoginSession(state);
      if (!session || session.email !== email) return json({ error: 'Invalid or expired session' }, 400);

      try {
        const tokens = await getGoogleTokensFromCode(code);
        const emails = await fetchEmailsViaGmail(tokens.access_token, 60);

        addGoogleOAuthAccount(email, tokens.access_token, tokens.refresh_token, tokens.expires_at);

        updateSelfLoginSession(state, {
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
          token_expires: tokens.expires_at,
          state: 'completed',
          completed_at: Date.now(),
        });

        return json({ success: true, email, unread: emails.length, provider: 'google' });
      } catch (err) {
        return json({ error: `Google OAuth failed: ${err.message}` }, 500);
      }
    }

    // POST /api/accounts/microsoft-oauth-start
    if (pathname === '/api/accounts/microsoft-oauth-start' && req.method === 'POST') {
      const { email } = JSON.parse(body);
      if (!email) return json({ error: 'email required' }, 400);

      const dc = await requestDeviceCode();
      if (dc.error) return json({ error: dc.error_description || dc.error }, 500);

      const state = crypto.randomBytes(16).toString('hex');
      const session = {
        id: state,
        email,
        provider: 'microsoft',
        device_code: dc.device_code,
        state: 'pending',
        createdAt: Date.now(),
        expiresAt: Date.now() + 15 * 60 * 1000,
      };
      saveSelfLoginSession(session);

      return json({
        action: 'microsoft_oauth_pending',
        email,
        verification_uri: dc.verification_uri,
        user_code: dc.user_code,
        device_code: dc.device_code,
        interval: dc.interval || 5,
        state: state,
        message: `Please open ${dc.verification_uri} and enter the code: ${dc.user_code} to continue.`,
      });
    }

    // POST /api/accounts/microsoft-oauth-poll
    if (pathname === '/api/accounts/microsoft-oauth-poll' && req.method === 'POST') {
      const { email, device_code, state } = JSON.parse(body);
      if (!email || !device_code || !state) return json({ error: 'Missing required parameters' }, 400);

      const session = getSelfLoginSession(state);
      if (!session || session.email !== email) return json({ error: 'Invalid or expired session' }, 400);

      try {
        const tokens = await pollForToken(device_code, session.interval || 5, 300);
        const emails = await fetchEmailsViaGraph(tokens.access_token, 60);

        addOAuthAccount(email, 'outlook', tokens.access_token, tokens.refresh_token, tokens.expires_at);

        updateSelfLoginSession(state, {
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
          token_expires: tokens.expires_at,
          state: 'completed',
          completed_at: Date.now(),
        });

        return json({ success: true, email, unread: emails.length, provider: 'microsoft' });
      } catch (err) {
        return json({ error: `Microsoft OAuth failed: ${err.message}` }, 500);
      }
    }

    // POST /api/accounts/remove
    if (pathname === '/api/accounts/remove' && req.method === 'POST') {
      const { email } = JSON.parse(body);
      const removed = removeAccount(email);
      return json({ success: removed });
    }

    // POST /api/check
    if (pathname === '/api/check' && req.method === 'POST') {
      const { account, max = 10, since = 60, summarize = false, token } = JSON.parse(body || '{}');

      let accounts = getAccounts().filter(a => a.email === account);

      if (!accounts.length && token) {
        const completedSession = getCompletedSelfLoginSession(token);
        if (completedSession && completedSession.email === account) {
          accounts = [completedSession];
        }
      }

      if (!accounts.length) return json({ error: 'No accounts configured' }, 400);

      const results = [];
      for (const acct of accounts) {
        try {
          const emails = await fetchAccountEmails(acct, since);
          for (const email of emails.slice(0, max)) {
            const entry = {
              account: acct.email,
              uid: email.uid,
              from: email.from,
              fromAddr: email.fromAddr,
              subject: email.subject,
              date: email.date,
              bodyPreview: (email.body || '').substring(0, 300),
            };
            if (summarize) {
              entry.summary = await summarizeEmail(email.from, email.subject, email.body);
            }
            results.push(entry);
          }
        } catch (err) {
          results.push({ account: acct.email, error: err.message });
        }
      }

      return json({ emails: results, total: results.length });
    }

    // POST /api/read
    if (pathname === '/api/read' && req.method === 'POST') {
      const { uid, account, token } = JSON.parse(body);

      let accounts = getAccounts().filter(a => a.email === account);

      if (!accounts.length && token) {
        const completedSession = getCompletedSelfLoginSession(token);
        if (completedSession && completedSession.email === account) {
          accounts = [completedSession];
        }
      }

      for (const acct of accounts) {
        try {
          const emails = await fetchAccountEmails(acct, 1440);
          const match = emails.find(e => e.uid === uid || e.uid === String(uid));
          if (match) {
            const summary = await summarizeEmail(match.from, match.subject, match.body);
            return json({ ...match, account: acct.email, summary });
          }
        } catch {}
      }
      return json({ error: 'Email not found' }, 404);
    }

    // POST /api/digest
    if (pathname === '/api/digest' && req.method === 'POST') {
      const { account, since = 1440, token } = JSON.parse(body || '{}');

      let accounts = getAccounts().filter(a => a.email === account);

      if (!accounts.length && token) {
        const completedSession = getCompletedSelfLoginSession(token);
        if (completedSession && completedSession.email === account) {
          accounts = [completedSession];
        }
      }

      const allEmails = [];

      for (const acct of accounts) {
        try {
          const emails = await fetchAccountEmails(acct, since);
          for (const e of emails) allEmails.push({ ...e, account: acct.email });
        } catch {}
      }

      if (!allEmails.length) return json({ digest: 'No emails found', total: 0 });
      const digest = await summarizeBatch(allEmails);
      return json({ digest, total: allEmails.length });
    }

    // POST /api/self-login-check
    if (pathname === '/api/self-login-check' && req.method === 'POST') {
      const { email, provider } = JSON.parse(body);
      if (!email || !provider) return json({ error: 'Missing required parameters' }, 400);

      const detected = await detectEmailType(email);

      const selfLoginResult = {
        email: email,
        detected_type: detected.type,
        detected_label: detected.label,
        provider: provider,
        support_methods: [],
      };

      if (provider === 'google') {
        selfLoginResult.support_methods.push('oauth2');
      }

      if (provider === 'microsoft' || detected.type === 'outlook') {
        selfLoginResult.support_methods.push('oauth2');
      }

      if (provider === 'manual' || detected.type === 'gmail' || detected.type === 'workspace') {
        selfLoginResult.support_methods.push('password');
      }

      if (selfLoginResult.support_methods.length === 0) {
        return json({ error: 'No supported authentication methods for this provider' }, 400);
      }

      return json(selfLoginResult);
    }

    json({ error: 'Not found' }, 404);
  } catch (err) {
    json({ error: err.message }, 500);
  }
}

async function fetchAccountEmails(acct, sinceMinutes) {
  if (acct.auth_type === 'oauth') {
    let accessToken = acct.access_token;
    const needsRefresh = !accessToken || (acct.token_expires && Date.now() > acct.token_expires - 300000);

    if (needsRefresh) {
      const newTokens = await refreshAccessToken(acct.refresh_token);
      accessToken = newTokens.access_token;
      updateTokens(acct.email, newTokens.access_token, newTokens.refresh_token, newTokens.expires_at);
    }

    if (acct.email_type === 'google') {
      return await fetchEmailsViaGmail(accessToken, sinceMinutes);
    } else {
      return await fetchEmailsViaGraph(accessToken, sinceMinutes);
    }
  }

  let serverArg = acct.email_type || 'gmail';
  if (serverArg.startsWith('custom:')) {
    const p = serverArg.split(':');
    serverArg = { host: p[1], port: parseInt(p[2]) || 993 };
  }
  return await fetchNewEmails(acct.email, acct.password, sinceMinutes, serverArg);
}

// HTML UI
function getHtml() {
  return fs.readFileSync(path.join(__dirname, 'ui.html'), 'utf-8');
}

function cleanupSessions() {
  cleanupOldSelfLoginSessions();
}

// Server
initDb();
setInterval(cleanupSessions, 60 * 60 * 1000);

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const pathname = url.pathname;

  // Collect body
  let body = '';
  if (req.method === 'POST') {
    for await (const chunk of req) body += chunk;
  }

  // API
  if (pathname.startsWith('/api/')) {
    return handleApi(req, res, pathname, body);
  }

  // UI
  if (pathname === '/' || pathname === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(getHtml());
    return;
  }

  res.writeHead(404);
  res.end('Not Found');
});

server.listen(PORT, () => {
  console.log(`Self-login web server running at http://localhost:${PORT}`);
  console.log(`Use this URL to access the self-login interface`);
  console.log(`Token: ${getOrCreateToken()}`);
});