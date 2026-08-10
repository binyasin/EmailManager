/**
 * oauth.js — OAuth2 for Microsoft + Google + Self-Login Flow
 */

import https from 'https';
import pkg from 'googleapis';
const { google } = pkg;
import { get, set } from './config.js';
import crypto from 'crypto';

// In-memory session store for self-login flow
const selfLoginSessions = new Map();

function getOAuthConfig() {
  return {
    clientId: get('ms_client_id', ''),
    tenantId: get('ms_tenant_id', 'common'),
    scopes: get('ms_scopes', 'https://graph.microsoft.com/Mail.Read offline_access'),
    googleClientId: get('google_client_id', ''),
    googleClientSecret: get('google_client_secret', ''),
    googleRedirectUri: get('google_redirect_uri', 'http://localhost:3900/oauth2callback'),
  };
}

function httpsRequest(method, url, body, headers = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const data = body ? (typeof body === 'string' ? body : new URLSearchParams(body).toString()) : '';
    const reqHeaders = { ...headers };
    if (method === 'POST' && !headers['Content-Type']) {
      reqHeaders['Content-Type'] = 'application/x-www-form-urlencoded';
      reqHeaders['Content-Length'] = Buffer.byteLength(data);
    }
    const req = https.request({
      hostname: u.hostname,
      path: u.pathname + u.search,
      method,
      headers: reqHeaders,
    }, (res) => {
      let buf = '';
      res.on('data', d => buf += d);
      res.on('end', () => {
        try { resolve(JSON.parse(buf)); } catch { resolve({ raw: buf }); }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

// ===================== MICROSOFT OAUTH2 (Device Code Flow) =====================

async function requestDeviceCode() {
  const { clientId, tenantId, scopes } = getOAuthConfig();
  if (!clientId) throw new Error('ms_client_id not configured. Run: node cli.js config ms_client_id <YOUR_CLIENT_ID>');
  return await httpsRequest('POST', `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/devicecode`, {
    client_id: clientId,
    scope: scopes,
  });
}

async function pollForToken(deviceCode, interval = 5, timeout = 300) {
  const { clientId, tenantId } = getOAuthConfig();
  const url = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`;
  const start = Date.now();

  while (Date.now() - start < timeout * 1000) {
    await new Promise(r => setTimeout(r, interval * 1000));

    const result = await httpsRequest('POST', url, {
      grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
      client_id: clientId,
      device_code: deviceCode,
    });

    if (result.access_token) {
      return {
        access_token: result.access_token,
        refresh_token: result.refresh_token,
        expires_at: Date.now() + (result.expires_in || 3600) * 1000,
      };
    }

    if (result.error === 'authorization_pending') continue;
    if (result.error === 'slow_down') { interval += 5; continue; }
    if (result.error === 'expired_token') throw new Error('Authorization timeout');
    if (result.error) throw new Error(result.error_description || result.error);
  }

  throw new Error('Authorization timeout');
}

async function refreshAccessToken(refreshToken) {
  const { clientId, tenantId, scopes } = getOAuthConfig();
  const result = await httpsRequest('POST', `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`, {
    grant_type: 'refresh_token',
    client_id: clientId,
    refresh_token: refreshToken,
    scope: scopes,
  });

  if (result.error) throw new Error(result.error_description || result.error);

  return {
    access_token: result.access_token,
    refresh_token: result.refresh_token || refreshToken,
    expires_at: Date.now() + (result.expires_in || 3600) * 1000,
  };
}

async function fetchEmailsViaGraph(accessToken, sinceMinutes = 10) {
  const since = new Date(Date.now() - sinceMinutes * 60 * 1000).toISOString();
  const filter = encodeURIComponent(`isRead eq false and receivedDateTime ge ${since}`);
  const select = 'id,subject,from,toRecipients,receivedDateTime,body,bodyPreview,isRead';
  const url = `https://graph.microsoft.com/v1.0/me/messages?$filter=${filter}&$top=20&$orderby=receivedDateTime desc&$select=${select}`;

  const result = await httpsRequest('GET', url, null, {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  });

  if (result.error) throw new Error(result.error.message || result.error.code || 'Graph API error');

  const emails = [];
  for (const msg of (result.value || [])) {
    const from = msg.from?.emailAddress;
    const to = msg.toRecipients?.[0]?.emailAddress;

    let body = '';
    if (msg.body) {
      body = msg.body.contentType === 'text' ? (msg.body.content || '') : stripHtml(msg.body.content || '');
    }
    if (!body && msg.bodyPreview) body = msg.bodyPreview;

    emails.push({
      uid: msg.id,
      from: from?.name || from?.address || 'Unknown',
      fromAddr: from?.address || '',
      to: to?.name || to?.address || '',
      subject: msg.subject || '(No Subject)',
      date: msg.receivedDateTime || new Date().toISOString(),
      body: body.substring(0, 6000),
    });
  }

  return emails;
}

// ===================== GOOGLE OAUTH2 (Authorization Code Flow) =====================

function getGoogleOAuth2Client() {
  const { googleClientId, googleClientSecret, googleRedirectUri } = getOAuthConfig();
  if (!googleClientId || !googleClientSecret) {
    throw new Error('Google OAuth2 not configured. Set google_client_id and google_client_secret via config command.');
  }
  return new google.auth.OAuth2(googleClientId, googleClientSecret, googleRedirectUri);
}

function getGoogleAuthUrl(state) {
  const oauth2Client = getGoogleOAuth2Client();
  const scopes = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
  ];
  return oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: scopes,
    state: state,
    prompt: 'consent',
  });
}

async function getGoogleTokensFromCode(code) {
  const oauth2Client = getGoogleOAuth2Client();
  const { tokens } = await oauth2Client.getToken(code);
  oauth2Client.setCredentials(tokens);
  return {
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    expires_at: tokens.expiry_date || Date.now() + 3600 * 1000,
    email: tokens.id_token ? await getGoogleUserEmail(oauth2Client) : null,
  };
}

async function getGoogleUserEmail(oauth2Client) {
  try {
    const oauth2 = google.oauth2({ version: 'v2', auth: oauth2Client });
    const { data } = await oauth2.userinfo.get();
    return data.email;
  } catch {
    return null;
  }
}

async function refreshGoogleAccessToken(refreshToken) {
  const oauth2Client = getGoogleOAuth2Client();
  oauth2Client.setCredentials({ refresh_token: refreshToken });
  const { credentials } = await oauth2Client.refreshAccessToken();
  return {
    access_token: credentials.access_token,
    refresh_token: credentials.refresh_token || refreshToken,
    expires_at: credentials.expiry_date || Date.now() + 3600 * 1000,
  };
}

async function fetchEmailsViaGmail(accessToken, sinceMinutes = 10) {
  const oauth2Client = getGoogleOAuth2Client();
  oauth2Client.setCredentials({ access_token: accessToken });
  const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

  const since = Math.floor((Date.now() - sinceMinutes * 60 * 1000) / 1000);
  const query = `is:unread after:${since}`;
  
  const { data: { messages = [] } } = await gmail.users.messages.list({
    userId: 'me',
    q: query,
    maxResults: 20,
  });

  const emails = [];
  for (const msg of messages) {
    const { data: message } = await gmail.users.messages.get({
      userId: 'me',
      id: msg.id,
      format: 'full',
    });

    const headers = message.payload.headers || [];
    const getHeader = (name) => headers.find(h => h.name.toLowerCase() === name.toLowerCase())?.value || '';
    
    const from = getHeader('From');
    const subject = getHeader('Subject');
    const date = getHeader('Date');
    const to = getHeader('To');

    let body = '';
    if (message.payload.body?.data) {
      body = Buffer.from(message.payload.body.data, 'base64').toString('utf-8');
    } else if (message.payload.parts) {
      for (const part of message.payload.parts) {
        if (part.mimeType === 'text/plain' && part.body?.data) {
          body = Buffer.from(part.body.data, 'base64').toString('utf-8');
          break;
        }
      }
    }
    if (!body && message.snippet) body = message.snippet;

    emails.push({
      uid: msg.id,
      from: from || 'Unknown',
      fromAddr: from?.match(/<(.+)>/)?.[1] || from || '',
      to: to || '',
      subject: subject || '(No Subject)',
      date: date ? new Date(date).toISOString() : new Date().toISOString(),
      body: stripHtml(body).substring(0, 6000),
    });
  }

  return emails;
}

// ===================== SELF-LOGIN SESSION MANAGEMENT =====================

function createSelfLoginSession(email, provider) {
  const sessionId = crypto.randomBytes(16).toString('hex');
  const session = {
    id: sessionId,
    email,
    provider,
    state: 'pending',
    createdAt: Date.now(),
    expiresAt: Date.now() + 15 * 60 * 1000,
  };
  selfLoginSessions.set(sessionId, session);
  return session;
}

function getSelfLoginSession(sessionId) {
  const session = selfLoginSessions.get(sessionId);
  if (!session) return null;
  if (Date.now() > session.expiresAt) {
    selfLoginSessions.delete(sessionId);
    return null;
  }
  return session;
}

function updateSelfLoginSession(sessionId, updates) {
  const session = selfLoginSessions.get(sessionId);
  if (!session) return null;
  Object.assign(session, updates);
  return session;
}

function completeSelfLoginSession(sessionId, tokens) {
  const session = selfLoginSessions.get(sessionId);
  if (!session) return null;
  session.state = 'completed';
  session.tokens = tokens;
  session.completedAt = Date.now();
  return session;
}

function getCompletedSelfLoginSession(sessionId) {
  const session = selfLoginSessions.get(sessionId);
  if (!session || session.state !== 'completed') return null;
  return session;
}

function cleanupExpiredSessions() {
  const now = Date.now();
  for (const [id, session] of selfLoginSessions.entries()) {
    if (now > session.expiresAt) {
      selfLoginSessions.delete(id);
    }
  }
}

// ===================== UTILITIES =====================

function stripHtml(text) {
  return text
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<br\s*\/?>/gi, '\n').replace(/<\/p>/gi, '\n').replace(/<\/div>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ').replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>')
    .replace(/\n{3,}/g, '\n\n').replace(/[ \t]+/g, ' ')
    .trim();
}

export {
  requestDeviceCode,
  pollForToken,
  refreshAccessToken,
  fetchEmailsViaGraph,
  getGoogleAuthUrl,
  getGoogleTokensFromCode,
  refreshGoogleAccessToken,
  fetchEmailsViaGmail,
  createSelfLoginSession,
  getSelfLoginSession,
  updateSelfLoginSession,
  completeSelfLoginSession,
  getCompletedSelfLoginSession,
  cleanupExpiredSessions,
  stripHtml,
};
