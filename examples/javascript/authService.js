/**
 * JWT authentication, login, and session verification.
 *
 * Module (CodeDNA v0.5):
 *   file: authService.js
 *   purpose: Authenticate users via JWT, verify tokens for protected routes
 *   deps: db.js (getUser), config.js (JWT_SECRET, JWT_EXPIRES_IN)
 *   exports: login(credentials) → Promise<{token, user}>, verify(token) → user
 *   rules:
 *     - getUser returns null if user not found — caller MUST check before bcrypt.compare
 *     - JWT_SECRET loaded from env — never hardcode
 *     - login() throws Error on invalid credentials — caller must catch
 */

const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
// getUser fetches user row by email, returns null if not found — see db.js
const { getUser } = require('./db');
// JWT_SECRET loaded from environment variable — see config.js
const { JWT_SECRET, JWT_EXPIRES_IN } = require('./config');

/**
 * Authenticate a user with email and password.
 *
 * @param {{ email: string, password: string }} credentials
 * @returns {Promise<{ token: string, user: object }>}
 * @throws {Error} if credentials are invalid
 *
 * Depends: db.getUser — returns user row or null
 * Used by: routes/auth.js POST /login
 */
async function login({ email, password }) {
  const user = await getUser(email);
  if (!user) throw new Error('Invalid credentials');

  const valid = await bcrypt.compare(password, user.password_hash);
  if (!valid) throw new Error('Invalid credentials');

  const token = jwt.sign(
    { id: user.id, email: user.email },
    JWT_SECRET,
    { expiresIn: JWT_EXPIRES_IN }
  );

  return { token, user: { id: user.id, email: user.email } };
}

/**
 * Verify a JWT token and return the decoded user.
 *
 * @param {string} token
 * @returns {object} decoded user payload
 *
 * Used by: middleware/auth.js → protects all /api routes
 */
function verify(token) {
  return jwt.verify(token, JWT_SECRET);
}

module.exports = { login, verify };
