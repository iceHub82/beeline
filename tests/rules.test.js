const { describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const SKILL = fs.readFileSync(
  path.join(__dirname, '..', 'skills', 'beeline', 'SKILL.md'),
  'utf8'
);

describe('beeline rules', () => {
  it('documents all three rule groups', () => {
    for (const heading of ['### Structure', '### Prose', '### Tool discipline']) {
      assert.ok(SKILL.includes(heading), `missing ${heading}`);
    }
  });

  it('marks structure and tool discipline as invariant across levels', () => {
    assert.match(SKILL, /### Structure \(invariant/);
    assert.match(SKILL, /### Tool discipline \(invariant/);
  });

  it('documents exactly three levels with full as default', () => {
    for (const level of ['lite', 'full', 'ultra']) {
      assert.ok(SKILL.includes(`| ${level} `), `level ${level} missing from the table`);
    }
    assert.match(SKILL, /\|\s*full\s*\|[^\n]*\*\*Default\.\*\*/, 'full must be marked Default in the levels table');

    const rows = SKILL.split('\n').filter((l) => /^\|\s*(lite|full|ultra|[a-z-]+)\s*\|/.test(l) && !/^\|\s*-+/.test(l) && !/\|\s*Prose\s*\|/.test(l));
    assert.strictEqual(rows.length, 3, `levels table must have exactly 3 data rows, found ${rows.length}`);
  });

  it('states the precedence order', () => {
    // Scope to the Precedence section. Searching the whole document fails by
    // construction: "Structure" first appears as the ### Structure rule-group
    // heading, which necessarily precedes ## Precedence.
    const start = SKILL.indexOf('## Precedence');
    assert.ok(start > -1, 'no ## Precedence section');
    const section = SKILL.slice(start, SKILL.indexOf('## Levels'));
    const order = ['Safety', 'Harness', 'The answer itself', 'Structure', 'Prose compression'];
    let cursor = -1;
    for (const item of order) {
      const at = section.indexOf(item);
      assert.ok(at > cursor, `${item} out of order or missing in Precedence`);
      cursor = at;
    }
  });

  it('carries the three ponytail boundary rules', () => {
    assert.match(SKILL, /three short lines/, 'ponytail three-line cap boundary missing');
    assert.match(SKILL, /per-skill dials|name the skill with the level/i, 'level-collision boundary missing');
    assert.match(SKILL, /literal templates/, 'template-override boundary missing');
  });

  it('names its off switch', () => {
    assert.ok(SKILL.includes('stop beeline'));
    assert.ok(SKILL.includes('normal mode'));
  });

  it('exempts code and commits from compression', () => {
    assert.match(SKILL, /Code, commits, PRs.*normal/s);
  });

  it('skill, help card and README agree on the level names', () => {
    const help = fs.readFileSync(path.join(__dirname, '..', 'skills', 'beeline-help', 'SKILL.md'), 'utf8');
    const readme = fs.readFileSync(path.join(__dirname, '..', 'README.md'), 'utf8');
    for (const level of ['lite', 'full', 'ultra']) {
      assert.ok(help.includes(level), `help card missing level ${level}`);
      assert.ok(readme.includes(level), `README missing level ${level}`);
    }
    for (const phrase of ['stop beeline', 'normal mode']) {
      assert.ok(help.includes(phrase), `help card missing off-switch "${phrase}"`);
      assert.ok(readme.includes(phrase), `README missing off-switch "${phrase}"`);
    }
  });
});
