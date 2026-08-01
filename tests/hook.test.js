const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const os = require('os');

const hook = require('../hooks/beeline-level');

// The hook writes to ~/.claude/.beeline-level. Stash any real value so running
// the suite does not clobber the developer's own active level.
let saved = null;
test.before(() => {
  try { saved = fs.readFileSync(hook.STATE, 'utf8'); } catch (e) { saved = null; }
});
test.after(() => {
  if (saved === null) hook.clear();
  else { fs.mkdirSync(path.dirname(hook.STATE), { recursive: true }); fs.writeFileSync(hook.STATE, saved); }
});

test('bare /beeline activates at full', () => {
  hook.clear();
  assert.strictEqual(hook.apply('/beeline'), 'full');
});

test('explicit levels are honoured', () => {
  for (const lvl of ['lite', 'full', 'ultra']) {
    hook.clear();
    assert.strictEqual(hook.apply('/beeline ' + lvl), lvl);
  }
});

test('the plugin-qualified form works', () => {
  hook.clear();
  assert.strictEqual(hook.apply('/beeline:beeline ultra'), 'ultra');
});

test('an unknown argument falls back to full rather than off', () => {
  hook.clear();
  assert.strictEqual(hook.apply('/beeline sideways'), 'full');
});

// The whole reason the hook exists: the level has to survive turns that say
// nothing about beeline. This is the drift the SKILL.md paragraph failed to stop.
test('level persists across unrelated turns', () => {
  hook.clear();
  hook.apply('/beeline ultra');
  assert.strictEqual(hook.apply('check the logs on prod'), 'ultra');
  assert.strictEqual(hook.apply('what about the database?'), 'ultra');
  assert.strictEqual(hook.apply(''), 'ultra');
});

test('stop beeline and normal mode turn it off', () => {
  for (const phrase of ['stop beeline', 'normal mode']) {
    hook.apply('/beeline ultra');
    assert.strictEqual(hook.apply(phrase), null, phrase + ' should deactivate');
    assert.strictEqual(hook.apply('some later turn'), null);
  }
});

test('inert until invoked — no level means no output', () => {
  hook.clear();
  assert.strictEqual(hook.apply('just a normal question'), null);
});

test('the reminder names the level and the prose rule', () => {
  const r = hook.reminder('ultra');
  assert.match(r, /level: ultra/);
  assert.match(r, /Telegraphic/);
  assert.match(r, /one concrete/);
});
