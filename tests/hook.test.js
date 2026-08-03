const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const os = require('os');
process.env.BEELINE_STATE_FILE = path.join(os.tmpdir(), '.beeline-level-test-hook');

const hook = require('../hooks/beeline-level');

// The hook writes to ~/.claude/.beeline-level. Stash any real value so running
// the suite does not clobber the developer's own active level.
let saved = null;
test.before(() => {
  try { saved = fs.readFileSync(hook.statePath(), 'utf8'); } catch (e) { saved = null; }
});
test.after(() => {
  if (saved === null) hook.clear();
  else { fs.mkdirSync(path.dirname(hook.statePath()), { recursive: true }); fs.writeFileSync(hook.statePath(), saved); }
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

// The reminder is the only thing re-stated every turn, so it has to carry the
// rules that actually cost money. Prose compression governs a third of one
// percent of an agent session; turns and context govern the rest.
test('the reminder carries the cost-bearing rules, not just the style one', () => {
  const r = hook.reminder('full');
  assert.match(r, /[Bb]atch independent tool calls/, 'rule 15 must be present');
  assert.match(r, /round-trip/, 'rule 16 must be present');
  assert.match(r, /file once/, 'rule 17 must be present');
});

test('the cost-bearing rules come before the prose rule', () => {
  const r = hook.reminder('full');
  assert.ok(r.indexOf('Batch independent') < r.indexOf('Prose:'),
    'a turn costs far more than a sentence; order the reminder accordingly');
});
