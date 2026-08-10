/**
 * store.js — Local SQLite storage for email accounts + self-login sessions
 */

import Database from 'better-sqlite3';
import path from 'path';

import { fileURLToPath } from 'url';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DB_PATH = path.join(__dirname, 'data', 'email.db');
let db;

function initDb() {
  db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');

  db.exec(`
    CREATE TABLE IF NOT EXISTS accounts (
      email TEXT PRIMARY KEY,
      password TEXT,
      email_type TEXT DEFAULT 'gmail',
      auth_type TEXT DEFAULT 'password',
      access_token TEXT,
      refresh_token TEXT,
      token_expires INTEGER DEFAULT 0,
      created_at INTEGER
    );

    CREATE TABLE IF NOT EXISTS self_login_sessions (
      session_id TEXT PRIMARY KEY,
      email TEXT,
      provider TEXT,
      access_token TEXT,
      refresh_token TEXT,
      token_expires INTEGER,
      state TEXT DEFAULT 'pending',
      created_at INTEGER,
      completed_at INTEGER
    );
  `);

  return db;
}

// ===================== ACCOUNTS =====================

function addAccount(email, password, emailType) {
  db.prepare(`
    INSERT INTO accounts (email, password, email_type, auth_type, created_at)
    VALUES (?, ?, ?, 'password', ?)
    ON CONFLICT(email) DO UPDATE SET
      password = excluded.password,
      email_type = excluded.email_type,
      auth_type = 'password',
      access_token = NULL,
      refresh_token = NULL,
      token_expires = 0
  `).run(email, password, emailType || 'gmail', Date.now());
}

function addOAuthAccount(email, emailType, accessToken, refreshToken, tokenExpires) {
  db.prepare(`
    INSERT INTO accounts (email, password, email_type, auth_type, access_token, refresh_token, token_expires, created_at)
    VALUES (?, '', ?, 'oauth', ?, ?, ?, ?)
    ON CONFLICT(email) DO UPDATE SET
      email_type = excluded.email_type,
      auth_type = 'oauth',
      access_token = excluded.access_token,
      refresh_token = excluded.refresh_token,
      token_expires = excluded.token_expires
  `).run(email, emailType || 'outlook', accessToken, refreshToken, tokenExpires, Date.now());
}

function addGoogleOAuthAccount(email, accessToken, refreshToken, tokenExpires) {
  db.prepare(`
    INSERT INTO accounts (email, password, email_type, auth_type, access_token, refresh_token, token_expires, created_at)
    VALUES (?, '', 'google', 'oauth', ?, ?, ?, ?)
    ON CONFLICT(email) DO UPDATE SET
      email_type = 'google',
      auth_type = 'oauth',
      access_token = excluded.access_token,
      refresh_token = excluded.refresh_token,
      token_expires = excluded.token_expires
  `).run(email, accessToken, refreshToken, tokenExpires, Date.now());
}

function updateTokens(email, accessToken, refreshToken, tokenExpires) {
  db.prepare(`
    UPDATE accounts SET access_token = ?, refresh_token = ?, token_expires = ? WHERE email = ?
  `).run(accessToken, refreshToken, tokenExpires, email);
}

function getAccounts() {
  return db.prepare('SELECT * FROM accounts').all();
}

function getAccount(email) {
  return db.prepare('SELECT * FROM accounts WHERE email = ?').get(email);
}

function removeAccount(email) {
  return db.prepare('DELETE FROM accounts WHERE email = ?').run(email).changes > 0;
}

// ===================== SELF-LOGIN SESSIONS =====================

function saveSelfLoginSession(session) {
  db.prepare(`
    INSERT INTO self_login_sessions (session_id, email, provider, access_token, refresh_token, token_expires, state, created_at, completed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(session_id) DO UPDATE SET
      email = excluded.email,
      provider = excluded.provider,
      access_token = excluded.access_token,
      refresh_token = excluded.refresh_token,
      token_expires = excluded.token_expires,
      state = excluded.state,
      completed_at = excluded.completed_at
  `).run(
    session.id,
    session.email,
    session.provider,
    session.tokens?.access_token || null,
    session.tokens?.refresh_token || null,
    session.tokens?.expires_at || null,
    session.state,
    session.createdAt,
    session.completedAt || null
  );
}

function getSelfLoginSession(sessionId) {
  return db.prepare('SELECT * FROM self_login_sessions WHERE session_id = ?').get(sessionId);
}

function getCompletedSelfLoginSession(sessionId) {
  const session = db.prepare('SELECT * FROM self_login_sessions WHERE session_id = ? AND state = ?').get(sessionId, 'completed');
  if (!session) return null;
  return {
    id: session.session_id,
    email: session.email,
    provider: session.provider,
    tokens: {
      access_token: session.access_token,
      refresh_token: session.refresh_token,
      expires_at: session.token_expires,
    },
  };
}

function removeSelfLoginSession(sessionId) {
  return db.prepare('DELETE FROM self_login_sessions WHERE session_id = ?').run(sessionId).changes > 0;
}

function cleanupOldSelfLoginSessions() {
  const cutoff = Date.now() - 24 * 60 * 60 * 1000; // 24 hours
  return db.prepare('DELETE FROM self_login_sessions WHERE created_at < ?').run(cutoff).changes;
}

export { 
  initDb, 
  addAccount, 
  addOAuthAccount,
  addGoogleOAuthAccount,
  updateTokens, 
  getAccounts, 
  getAccount, 
  removeAccount,
  saveSelfLoginSession,
  getSelfLoginSession,
  getCompletedSelfLoginSession,
  removeSelfLoginSession,
  cleanupOldSelfLoginSessions,
};