/* Bloomberg du cannabis — navigateur Fusion v2 (statique, GitHub Pages) */
const SHARD_BASE = '../data/compiled/fusion_v2/shard_';
let IDX = [], TYPES = new Set(), shown = 0;
const PAGE = 60;

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

async function init() {
  const r = await fetch('index.json');
  const j = await r.json();
  IDX = j.entries;
  IDX.forEach(e => { if (e.t) TYPES.add(e.t); });
  const sel = $('ftype');
  [...TYPES].sort().forEach(t => { const o = document.createElement('option'); o.value = t; o.textContent = t; sel.appendChild(o); });
  $('loading').style.display = 'none';
  $('q').addEventListener('input', render);
  $('ftype').addEventListener('change', render);
  $('fpop').addEventListener('change', render);
  $('more').addEventListener('click', () => { shown += PAGE; paint(); });
  render();
}

function filtered() {
  const q = $('q').value.trim().toLowerCase();
  const ft = $('ftype').value, fp = $('fpop').checked;
  return IDX.filter(e =>
    (!q || e.n.toLowerCase().includes(q) || (e.b||'').toLowerCase().includes(q)) &&
    (!ft || e.t === ft) && (!fp || e.p));
}

function render() { shown = PAGE; paint(); }

function paint() {
  const res = filtered(), list = $('list');
  $('count').textContent = res.length.toLocaleString('fr-FR') + ' cultivar(s)';
  list.innerHTML = '';
  res.slice(0, shown).forEach(e => {
    const d = document.createElement('div');
    d.className = 'card';
    d.innerHTML = `<h3>${esc(e.n)}${e.p ? '<span class="pop">★</span>' : ''}</h3>
      <div class="meta">${esc(e.b)}${e.t ? ' · ' + esc(e.t) : ''}</div>`;
    d.onclick = () => openDetail(e);
    list.appendChild(d);
  });
  $('more').style.display = res.length > shown ? 'block' : 'none';
}

const shardCache = {};
async function getEntry(e) {
  const s = e.s;
  if (!shardCache[s]) {
    const r = await fetch(SHARD_BASE + String(s).padStart(2, '0') + '.json');
    shardCache[s] = await r.json();
  }
  return shardCache[s][e.k];
}

function val(v) {
  if (v == null || v === '') return '<i style="color:var(--mut)">non documenté</i>';
  if (typeof v === 'object') {
    if (v.value !== undefined) return esc(v.value) + (v.source ? ` <span class="badge">${esc(v.source)}</span>` : '');
    if (Array.isArray(v)) return esc(v.join(', '));
    return esc(JSON.stringify(v));
  }
  return esc(v);
}

async function openDetail(e) {
  $('sheetBody').innerHTML = '<p style="color:var(--mut)">Chargement de la fiche…</p>';
  $('detail').classList.add('open');
  document.body.style.overflow = 'hidden';
  try {
    const f = await getEntry(e);
    const ds = f.donnees_seedfinder || {};
    const conflits = f.conflits_lignee || f.lineage_conflits || [];
    let h = `<h2>${esc(f.name)}</h2><div class="sub">${esc((ds.breeders||[]).join(', '))}</div>`;
    h += `<div>${(f.badges||[]).map(b => `<span class="badge">${esc(b)}</span>`).join('')}</div>`;
    h += `<h4>Caractéristiques</h4><dl class="kv">`;
    h += `<dt>Type</dt><dd>${esc(ds.type_normalise || '')}</dd>`;
    h += `<dt>Graine</dt><dd>${esc(ds.type_graine || '')}</dd>`;
    h += `<dt>Floraison</dt><dd>${val(f.floraison_jours)}${ds.floraison_jours ? ' j (SeedFinder)' : ''}</dd>`;
    h += `<dt>Phénotype</dt><dd>${val(f.phenotype)}</dd>`;
    h += `<dt>Culture</dt><dd>${esc(ds.culture || '')}</dd>`;
    h += `</dl>`;
    if (f.parents || ds.liens_parents) {
      h += `<h4>Lignée</h4><p>${val(f.parents)}${ds.lignage_brut ? '<br><span style="color:var(--mut)">Brut SeedFinder : </span>' + esc(String(ds.lignage_brut).slice(0, 300)) : ''}</p>`;
    }
    if (conflits.length) h += `<div class="warn">⚠ Conflits de lignée exposés (${conflits.length}) — jamais tranchés. Voir le dataset.</div>`;
    const sf = [ds.description_breeder].filter(Boolean);
    if (sf.length) h += `<h4>Description breeder</h4><p>${esc(String(sf[0]).slice(0, 600))}${sf[0].length > 600 ? '…' : ''}</p>`;
    const urls = [...(f.source_urls || []), ...(ds.urls || [])].slice(0, 6);
    if (urls.length) h += `<h4>Sources</h4><ul>${urls.map(u => `<li><a href="${esc(u)}" target="_blank" rel="noopener" style="color:var(--cy)">${esc(String(u).slice(0, 70))}</a></li>`).join('')}</ul>`;
    $('sheetBody').innerHTML = h;
  } catch (err) {
    $('sheetBody').innerHTML = '<p>Impossible de charger la fiche.</p>';
  }
}
function closeDetail() { $('detail').classList.remove('open'); document.body.style.overflow = ''; }
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });
$('detail').addEventListener('click', e => { if (e.target.id === 'detail') closeDetail(); });

init();
