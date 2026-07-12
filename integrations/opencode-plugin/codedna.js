/**
 * codedna.js — CodeDNA v0.9 warn-only enforcement plugin for OpenCode.
 *
 * exports: CodeDNAPlugin
 * used_by: .opencode/plugins/ → auto-loaded by OpenCode at startup
 * rules:   WARN ONLY — hooks must NEVER throw; a plugin error must not block the
 *          host tool call. Hard enforcement lives in the pre-commit hook, not here.
 *          client.app.log takes { body: { service, level, message } } — the
 *          positional form log('warn', msg) silently no-ops on OpenCode.
 * agent:   deepseek-v4-pro | deepseek | 2026-07-10 | s_20260710_docblock | fix log API + try/catch + path/fileName fallbacks; detect docblock headers; kept warn-only
 *
 * Installation:
 *   mkdir -p .opencode/plugins
 *   cp codedna.js .opencode/plugins/codedna.js
 *   (restart OpenCode — plugins are loaded once at startup)
 *
 * What it does (warn-only, never blocks the host):
 *   - After every file write: warns if the file is missing a CodeDNA header
 *   - After every session: reminds to update .codedna and commit with AI git trailers
 *
 * Enforcement note:
 *   This plugin only WARNS — it never throws to block a tool call. Hard
 *   enforcement belongs in the pre-commit hook (tools/pre-commit), so an
 *   editor-hook/API mismatch can never wedge the user's workflow.
 *
 * Supported languages (11):
 *   Python, TypeScript, JavaScript, Go, PHP, Rust, Java, Kotlin, Ruby, C#, Swift
 *
 * Detection logic mirrors base.py has_codedna_header():
 *   scan first 30 lines, strip comment prefix (//, #, * for docblocks),
 *   look for exports: or used_by:
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
 * Resolve the file path from a tool's args across OpenCode versions.
 * Different versions / tools use filePath, file_path, path or fileName.
 */
function resolveFilePath(args) {
  return args?.filePath ?? args?.file_path ?? args?.path ?? args?.fileName ?? null
}

/**
 * Emit a log line through the OpenCode client.
 *
 * OpenCode's client.app.log expects a single object argument:
 *   { body: { service, level, message } }
 * The old positional form client.app.log('warn', '...') silently no-ops.
 */
async function log(client, level, message) {
  try {
    await client.app.log({ body: { service: 'codedna', level, message } })
  } catch (_) { /* logging must never break the host */ }
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
    // Strip leading comment prefix — handles //, #, * (JSDoc/PHPDoc docblocks),
    // and """ for Python.
    const bare = line.replace(/^(\/\/+|#+|\/\*+|\*+|"{3})\s*/, '').trim()
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
      try {
        const tool = input?.tool
        if (!tool) return

        // --- write: full content available, most reliable check ---
        if (tool === 'write') {
          const filePath = resolveFilePath(output?.args)
          if (!filePath) return

          const ext = getExt(filePath)
          if (!LANG[ext]) return // unsupported language — skip silently

          const content = output?.args?.content ?? ''
          if (!content) return

          if (!hasCodeDNAHeader(content)) {
            await log(client, 'warn',
              `[CodeDNA] ${shortPath(filePath)} — missing exports: / used_by: header. ` +
              `Add a CodeDNA v0.9 module docstring before committing. ` +
              `See: https://github.com/Larens94/codedna`
            )
          }
          return
        }

        // --- edit: only the patch (new_string) is available ---
        if (tool === 'edit') {
          const filePath = resolveFilePath(output?.args)
          if (!filePath) return

          const ext = getExt(filePath)
          if (!LANG[ext]) return

          const newString = output?.args?.new_string ?? output?.args?.newString ?? ''
          // Only warn if the patch itself introduces a new top-level definition
          // (function/class/def/fn/func) without CodeDNA markers — this avoids
          // false positives for small inline edits. Note: edits on files that
          // already carry a header are expected NOT to repeat the header, so we
          // never hard-block edits.
          const defPattern = /^\s*(export\s+)?(function|class|def |fn |func |public |private |protected )/m
          if (defPattern.test(newString) && !hasCodeDNAHeader(newString)) {
            await log(client, 'warn',
              `[CodeDNA] ${shortPath(filePath)} — patch adds a definition; ` +
              `ensure the module header has exports: and used_by:.`
            )
          }
          return
        }
      } catch (_) {
        // A plugin error must never block the host tool call.
      }
    },

    /**
     * End of session — remind the agent to update .codedna and commit
     * with the required AI git trailers (v0.9 session end protocol).
     */
    'event': async ({ event }) => {
      try {
        if (event?.type !== 'session.idle') return
        await log(client, 'info',
          '[CodeDNA] Session complete. Before closing: ' +
          '(1) Append an agent_sessions: entry to .codedna ' +
          '(agent, provider, date, session_id, task, changed, visited, message). ' +
          '(2) Commit with AI git trailers: AI-Agent, AI-Provider, AI-Session, ' +
          'AI-Visited, AI-Message.'
        )
      } catch (_) {
        // never break the host on the idle hook
      }
    },

  }
}
