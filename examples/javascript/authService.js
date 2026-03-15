// ==============================================================
// FILE: authService.js
// PURPOSE: JWT authentication, login, and session verification
// DEPENDS_ON: db.js → getUser(), config.js → JWT_SECRET
// EXPORTS: login(credentials) → Promise<{token, user}>, verify(token) → user
// STYLE: none (pure logic, Node.js)
// DB_TABLES: users (id, email, password_hash, last_login)
// LAST_MODIFIED: initial Beacon Framework example
// ==============================================================

const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
// → from db.js: getUser fetches user row by email, returns null if not found
const { getUser } = require('./db');
// → from config.js: JWT_SECRET loaded from environment variable
const { JWT_SECRET, JWT_EXPIRES_IN } = require('./config');

/**
 * Authenticate a user with email and password.
 * ← used by: routes/auth.js POST /login
 *
 * @param {{ email: string, password: string }} credentials
 * @returns {Promise<{ token: string, user: object }>}
 * @throws {Error} if credentials are invalid
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
 * ← used by: middleware/auth.js → protects all /api routes
 *
 * @param {string} token
 * @returns {object} decoded user payload
 */
function verify(token) {
  return jwt.verify(token, JWT_SECRET);
}

module.exports = { login, verify };
