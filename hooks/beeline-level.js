#!/usr/bin/env node
// beeline — keeps the active level in context on every turn.
//
// Why this exists: the skill's "Persistence" section is a paragraph asking the
// model not to drift, which is the weakest enforcement available. In practice
// it decays — during tool-heavy work the model slides back to its default
// register within a message or two, and the user has to ask "are you using
// beeline?" over and over. Ponytail does not decay, because a hook restates it
// every turn. This is that hook.
//
// Opt-in by construction: it writes nothing until the user types /beeline, and
// emits nothing while no level is set. The skill stays inert until invoked.
//
// ponytail: one file, one state file holding one word. No config module, no
// multi-harness branching — this plugin targets Claude Code, and stdout is the
// injected context there.

const fs = require('fs');
const os = require('os');
const path = require('path');

// Global on purpose, and worth knowing: the level is stored once per machine, so
// enabling beeline in one project applies it to every Claude Code session until
// you turn it off. Per-project scoping would mean the hook needs the project
// root, which it is not reliably given. Documented rather than silently assumed.
//
// BEELINE_STATE_FILE overrides it. Read per call rather than captured at require
// time, so tests can point at a temp file — two test files sharing the real one
// raced and failed intermittently.
function statePath() {
  return process.env.BEELINE_STATE_FILE
    || path.join(os.homedir(), '.claude', '.beeline-level');
}
const LEVELS = ['lite', 'full', 'ultra'];

// Deliberately short. This is re-read every single turn, so it must earn its
// tokens: the level, plus only the rules that actually drift. Structure and
// tool discipline slip least; prose compression slips first, so it leads.
const PROSE = {
  lite: 'Grammatical, filler cut.',
  full: 'Stripped. Fragments allowed in status lines.',
  ultra: 'Telegraphic. Articles dropped.',
};

function read() {
  try {
    const v = fs.readFileSync(statePath(), 'utf8').trim();
    return LEVELS.includes(v) ? v : null;
  } catch (e) { return null; }
}

function write(level) {
  fs.mkdirSync(path.dirname(statePath()), { recursive: true });
  fs.writeFileSync(statePath(), level);
}

function clear() {
  try { fs.unlinkSync(statePath()); } catch (e) {}
}

function reminder(level) {
  // Cost-bearing rules first. Prose compression governs well under 1% of an
  // agent session's spend; turns and context govern the rest, so the rules that
  // prevent a round-trip lead and the style rule follows.
  return [
    `BEELINE ACTIVE — level: ${level}`,
    'Batch independent tool calls into one block. Never cause a round-trip just',
    'to save words — answer with a placeholder and ask in the same reply.',
    'Filter tool output at the source; quote the shortest decisive line; write a',
    'file once, in its final location.',
    'Lead with the action; number 2+ ordered steps; errors state cause and fix;',
    'one concrete next action when the ball is with the user.',
    `Prose: ${PROSE[level]}`,
  ].join('\n');
}

// Returns the level after applying any command in the prompt, or null if off.
// Exported so the tests can drive it without spawning processes.
function apply(prompt) {
  const p = String(prompt || '').trim();

  if (/\b(stop beeline|normal mode)\b/i.test(p)) {
    clear();
    return null;
  }

  // /beeline, /beeline ultra, /beeline:beeline ultra — the plugin-qualified form
  // is what Claude Code sends when the skill is invoked by its full name.
  const m = p.match(/^[/@$]beeline(?::beeline)?\b\s*(\w+)?/i);
  if (m) {
    const arg = (m[1] || '').toLowerCase();
    const level = LEVELS.includes(arg) ? arg : 'full';
    write(level);
    return level;
  }

  return read();
}

function main() {
  let input = '';
  process.stdin.on('data', c => { input += c; });
  process.stdin.on('end', () => {
    let prompt = '';
    try {
      // Some shells prepend a BOM when piping, which breaks JSON.parse.
      prompt = (JSON.parse(input.replace(/^﻿/, '')).prompt) || '';
    } catch (e) { /* SessionStart sends no prompt — fall through to read() */ }

    const level = apply(prompt);
    if (level) process.stdout.write(reminder(level));
  });
}

if (require.main === module) main();

module.exports = { apply, reminder, read, write, clear, statePath };
