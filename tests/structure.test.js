const { describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');

// Reads YAML frontmatter, including folded scalars (`description: >` followed by
// indented continuation lines). A naive line-by-line parser reports a 1-character
// description for every skill here and fails for the wrong reason.
function readFrontmatter(relPath) {
  const raw = fs.readFileSync(path.join(ROOT, relPath), 'utf8');
  const m = raw.match(/^---\n([\s\S]*?)\n---/);
  assert.ok(m, `${relPath} has no frontmatter block`);
  const lines = m[1].split('\n');
  const fields = {};
  for (let i = 0; i < lines.length; i++) {
    const kv = lines[i].match(/^([a-zA-Z-]+):[ \t]*(.*)$/);
    if (!kv) continue;
    let value = kv[2].trim();
    if (value === '>' || value === '>-' || value === '|' || value === '|-') value = '';
    for (let j = i + 1; j < lines.length && !/^[a-zA-Z-]+:/.test(lines[j]); j++) {
      value += (value ? ' ' : '') + lines[j].trim();
      i = j;
    }
    fields[kv[1]] = value.trim();
  }
  return { fields, body: raw.slice(m[0].length) };
}

describe('plugin structure', () => {
  it('plugin.json declares the beeline plugin', () => {
    const p = JSON.parse(fs.readFileSync(path.join(ROOT, '.claude-plugin/plugin.json'), 'utf8'));
    assert.strictEqual(p.name, 'beeline');
    assert.match(p.version, /^\d+\.\d+\.\d+$/);
    assert.ok(p.description && p.description.length > 20, 'description too short');
  });

  it('plugin.json declares no hooks — activation is /beeline only', () => {
    const p = JSON.parse(fs.readFileSync(path.join(ROOT, '.claude-plugin/plugin.json'), 'utf8'));
    assert.strictEqual(p.hooks, undefined, 'beeline must not auto-activate via hooks');
  });

  it('marketplace.json lists the plugin', () => {
    const m = JSON.parse(fs.readFileSync(path.join(ROOT, '.claude-plugin/marketplace.json'), 'utf8'));
    assert.strictEqual(m.name, 'beeline');
    assert.ok(Array.isArray(m.plugins) && m.plugins.length === 1);
    assert.strictEqual(m.plugins[0].name, 'beeline');
    assert.strictEqual(m.plugins[0].source, './');
  });

  it('both skills exist with valid frontmatter', () => {
    const main = readFrontmatter('skills/beeline/SKILL.md');
    assert.strictEqual(main.fields.name, 'beeline');
    assert.ok(main.fields.description.length > 40, 'description too short to be useful in the listing');

    const help = readFrontmatter('skills/beeline-help/SKILL.md');
    assert.strictEqual(help.fields.name, 'beeline-help');
  });

  it('the main skill is user-invocable only', () => {
    const main = readFrontmatter('skills/beeline/SKILL.md');
    assert.strictEqual(main.fields['disable-model-invocation'], 'true');
  });
});
