/**
 * codedna.js — CodeDNA v0.8 Plugin for OpenCode
 *
 * Installation:
 *   mkdir -p .opencode/plugins
 *   cp codedna.js .opencode/plugins/codedna.js
 *
 * What it does:
 *   - After every file write: warns if the file is missing a CodeDNA v0.8 header
 *   - After every session: reminds to update .codedna and commit with AI git trailers
 *
 * Supported languages (11):
 *   Python, TypeScript, JavaScript, Go, PHP, Rust, Java, Kotlin, Ruby, C#, Swift
 *
 * Detection logic mirrors base.py has_codedna_header():
 *   scan first 30 lines, strip comment prefix, look for exports: or used_by:
 */

// ---------------------------------------------------------------------------
// Language registry — extension -> comment prefix
// style: 'python'  → header lives inside a """...""" docstring
//        'line'    → header is a block of single-line comments
// ---------------------------------------------------------------------------
const LANG = {
  '.py':    { prefix: '#',   style: 'python' },
  '.ts':    { prefix: '//',  style: 'line' },
  '.tsx':   { prefix: '//',  style: 'line' },
  '.js':    { prefix: '//',  style: 'line' },
  '.jsx':   { prefix: '//',  style: 'line' },
  '.mjs':   { prefix: '//',  style: 'line' },
  '.cjs':   { prefix: '//',  style: 'line' },
  '.go':    { prefix: '//',  style: 'line' },
  '.php':   { prefix: '//',  style: 'line' },
  '.rs':    { prefix: '//',  style: 'line' },
  '.java':  { prefix: '//',  style: 'line' },
  '.kt':    { prefix: '//',  style: 'line' },
  '.kts':   { prefix: '//',  style: 'line' },
  '.rb':    { prefix: '#',   style: 'line' },
  '.cs':    { prefix: '//',  style: 'line' },
  '.swift': { prefix: '//',  style: 'line' },
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extract lowercase file extension including the dot. */
function getExt(filePath) {
  const i = filePath.lastIndexOf('.')
  return i >= 0 ? filePath.slice(i).toLowerCase() : ''
}

/**
 * Return true if content already contains a CodeDNA v0.8 header.
 *
 * Mirrors base.py LanguageAdapter.has_codedna_header():
 *   scan first 30 lines, strip any leading comment chars (// # """),
 *   look for a line whose content starts with "exports:" or "used_by:".
 */
function hasCodeDNAHeader(content) {
  const lines = content.split('\n').slice(0, 30)
  for (const rawLine of lines) {
    const line = rawLine.trim()
    // Strip leading comment prefix — handles //, #, and inside """ for Python
    const bare = line.replace(/^(\/\/+|#+|"{3})\s*/, '').trim()
    if (bare.startsWith('exports:') || bare.startsWith('used_by:')) {
      return true
    }
  }
  return false
}

/**
 * Return a short display name for a file path (last two path segments).
 * e.g. "src/utils/format.ts" → "utils/format.ts"
 */
function shortPath(filePath) {
  const parts = filePath.replace(/\\/g, '/').split('/')
  return parts.slice(-2).join('/')
}

// ---------------------------------------------------------------------------
// Plugin
// ---------------------------------------------------------------------------
export const CodeDNAPlugin = async ({ client }) => {
  return {

    /**
     * After every tool call — check write operations for missing CodeDNA headers.
     *
     * Covers: write (full file content) and edit (new_string patch).
     * For edit we check only the patch — if the agent is adding the header
     * itself, new_string will contain exports:/used_by: and we skip.
     * If new_string is a code patch with no header fields, we warn only
     * when the patch looks like a new function/class definition.
     */
    'tool.execute.after': async (input, output) => {
      const tool = input?.tool
      if (!tool) return

      // --- write: full content available, most reliable check ---
      if (tool === 'write') {
        const filePath = output?.args?.filePath ?? output?.args?.file_path
        if (!filePath) return

        const ext = getExt(filePath)
        if (!LANG[ext]) return // unsupported language — skip silently

        const content = output?.args?.content ?? ''
        if (!content) return

        if (!hasCodeDNAHeader(content)) {
          await client.app.log(
            'warn',
            `[CodeDNA] ${shortPath(filePath)} — missing exports: / used_by: header.\n` +
            `         Add a CodeDNA v0.8 module docstring before committing.\n` +
            `         See: https://github.com/Larens94/codedna`
          )
        }
        return
      }

      // --- edit: only the patch (new_string) is available ---
      if (tool === 'edit') {
        const filePath = output?.args?.filePath ?? output?.args?.file_path
        if (!filePath) return

        const ext = getExt(filePath)
        if (!LANG[ext]) return

        const newString = output?.args?.new_string ?? ''
        // Only warn if the patch itself introduces a new top-level definition
        // (function/class/def/fn/func) without CodeDNA markers — this avoids
        // false positives for small inline edits.
        const defPattern = /^\s*(export\s+)?(function|class|def |fn |func |public |private |protected )/m
        if (defPattern.test(newString) && !hasCodeDNAHeader(newString)) {
          await client.app.log(
            'warn',
            `[CodeDNA] ${shortPath(filePath)} — patch adds a definition without CodeDNA fields.\n` +
            `         Ensure the module header has exports: and used_by:.`
          )
        }
        return
      }
    },

    /**
     * End of session — remind the agent to update .codedna and commit
     * with the required AI git trailers (v0.8 session end protocol).
     */
    'event': async ({ event }) => {
      if (event?.type !== 'session.idle') return
      await client.app.log(
        'info',
        '[CodeDNA] Session complete. Before closing:\n' +
        '  1. Append an agent_sessions: entry to .codedna\n' +
        '     fields: agent, provider, date, session_id, task, changed, visited, message\n' +
        '  2. Commit with AI git trailers:\n' +
        '     AI-Agent:    <model-id>\n' +
        '     AI-Provider: <provider>\n' +
        '     AI-Session:  <session_id>\n' +
        '     AI-Visited:  <comma-separated files read>\n' +
        '     AI-Message:  <one-line summary>'
      )
    },

  }
}
