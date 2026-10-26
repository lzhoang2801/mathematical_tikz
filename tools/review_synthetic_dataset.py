"""Review Generate/Edit candidates locally: delete or move usable mismatches to Reconstruct."""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from tools import run_synthetic_dataset as production

author, drawing = production.author, production.drawing


class Review:
    def __init__(self, output: Path):
        self.output = output.resolve()
        self.lock = threading.Lock()
        self.token = secrets.token_urlsafe(32)
        self.bases = drawing.saved_rows(self.output / 'drawings')
        self.rows = {}
        self.reload()
        if (self.output / 'excluded.jsonl').is_file() or self.moves:
            self.save()  # Replay committed decisions if an export was interrupted.

    def reload(self):
        self.rows = {}
        self.reconstructed = {}
        self.moves = []
        digest = hashlib.sha256()
        registry_path = self.output / 'sources.json'
        registry_exists = registry_path.is_file()
        registry_data = registry_path.read_bytes() if registry_exists else b'{}'
        self.sources = json.loads(registry_data)
        digest.update(registry_data)
        for name in ('generate.jsonl', 'edit.jsonl', 'excluded.jsonl',
                     'reconstruct/candidates.jsonl', 'reconstruct/moves.jsonl'):
            path = self.output / name
            data = path.read_bytes() if path.is_file() else b''
            digest.update(name.encode() + b'\0' + data)
            rows = [json.loads(line) for line in data.decode('utf-8-sig').splitlines() if line.strip()]
            if name == 'excluded.jsonl':
                self.excluded = {row['id']: row for row in rows}
            elif name == 'reconstruct/candidates.jsonl':
                self.reconstructed = {row['id']: row for row in rows}
            elif name == 'reconstruct/moves.jsonl':
                self.moves = rows
            else:
                for row in rows:
                    if row['id'] in self.rows or row['task'].lower() + '.jsonl' != name:
                        raise ValueError('Duplicate ID or task/file mismatch')
                    self.rows[row['id']] = row
        for move in self.moves:
            self.excluded[move['original']['id']] = move['original']
            self.reconstructed[move['reconstruct']['id']] = move['reconstruct']
        self.rows = {key: row for key, row in self.rows.items() if key not in self.excluded}
        if not registry_exists:
            source_ids = set()
            for row in self.rows.values():
                provenance = row.get('provenance', {})
                for field in ('parent_sources', 'parent_hashes'):
                    references = provenance.get(field)
                    if isinstance(references, dict):
                        source_ids.update(references)
            if source_ids:
                selected, _, _ = author.load_pool()
                self.sources = {key: selected[key] for key in sorted(source_ids) if key in selected}
                digest.update(drawing.encoded(self.sources).encode('utf-8'))
        for row in self.rows.values():
            provenance = row.get('provenance', {})
            references = provenance.get('parent_sources', {})
            file_hashes = provenance.get('parent_hashes', {})
            if references or file_hashes:
                parents = provenance.get('parents', [])
                if not isinstance(parents, list) or not isinstance(references, dict) or not isinstance(file_hashes, dict):
                    raise ValueError(f"{row['id']}: invalid audited source provenance")
                for parent in parents:
                    source = self.sources.get(parent)
                    reference = references.get(parent)
                    if not isinstance(source, dict) or not isinstance(reference, dict):
                        raise ValueError(f"{row['id']}: audited source missing from registry or current selection: {parent}")
                    actual_text = source.get('source_text')
                    actual_text_hash = (hashlib.sha256(actual_text.encode('utf-8')).hexdigest()
                                        if isinstance(actual_text, str) else None)
                    expected_file_hash = file_hashes.get(parent) or reference.get('source_sha256')
                    if (not isinstance(actual_text, str) or not actual_text.strip()
                            or source.get('source_sha256') != expected_file_hash
                            or source.get('source_text_sha256') != reference.get('source_text_sha256')
                            or actual_text_hash != reference.get('source_text_sha256')
                            or source.get('source_path') != reference.get('source_path')
                            or source.get('locator') != reference.get('locator')):
                        raise ValueError(f"{row['id']}: audited source changed; regenerate and review the pair")
            for parent, expected in provenance.get('parent_sha256', {}).items():
                actual = hashlib.sha256(drawing.encoded(self.sources.get(parent)).encode()).hexdigest()
                if actual != expected:
                    raise ValueError(f"{row['id']}: source registry changed; regenerate and review the pair")
        self.revision = digest.hexdigest()

    def save(self):
        if self.moves:
            production.write_rows(self.output / 'excluded.jsonl', list(self.excluded.values()))
            directory = self.output / 'reconstruct'
            production.write_rows(directory / 'candidates.jsonl', list(self.reconstructed.values()))
            drawing.write_parquet(list(self.reconstructed.values()), directory / 'candidates.parquet')
        generated = [row for row in self.rows.values() if row['task'] == 'Generate']
        edits = [row for row in self.rows.values() if row['task'] == 'Edit']
        for name, rows in (('generate', generated), ('edit', edits)):
            production.write_rows(self.output / (name + '.jsonl'), rows)
            drawing.write_parquet(rows, self.output / (name + '.parquet'))
        report_path = self.output / 'report.json'
        report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.is_file() else {}
        report.update(completed_candidates={'Generate': len(generated), 'Edit': len(edits)},
            source_families=len({row.get('source_group') for row in self.rows.values()} - {None}),
            derived_generate=sum(bool(row.get('provenance', {}).get('derived_from_edit')) for row in generated),
            independently_reviewed=sum(row.get('verification', {}).get('status') == 'ready' and
                row['verification'].get('reviewed_input_sha256') == drawing.review_digest(row) for row in self.rows.values()),
            excluded_candidates=len(self.excluded), reconstruct_candidates=len(self.reconstructed),
            moved_to_reconstruct=len(self.moves))
        state_path = self.output / 'state.json'
        if state_path.is_file():
            state = json.loads(state_path.read_text(encoding='utf-8'))
            report['source_coverage'] = production.source_coverage(
                {'Generate': generated, 'Edit': edits}, state.get('source_hashes', {}))
        drawing.save_json(report_path, report)
        production.write_review(self.output, generated + edits, self.bases)
        if (self.output / 'hf').is_dir():
            from tools.export_hf_dataset import export
            assignments = self.output / 'hf/split_assignments.json'
            seed = json.loads(assignments.read_text(encoding='utf-8'))['seed'] if assignments.is_file() else 20261009
            export(None, self.output, self.output / 'hf', seed)
        self.reload()

    def validate_selection(self, ids: list[str], revision: str):
        self.reload()
        if revision != self.revision:
            raise RuntimeError('The dataset changed. Reload before saving.')
        if not isinstance(ids, list) or not ids or any(not isinstance(key, str) or key not in self.rows for key in ids):
            raise ValueError('Select existing candidate IDs')

    def delete(self, ids: list[str], revision: str):
        self.validate_selection(ids, revision)
        for key in set(ids):
            self.excluded[key] = self.rows.pop(key)
        production.write_rows(self.output / 'excluded.jsonl', list(self.excluded.values()))
        self.save()

    def move_to_reconstruct(self, ids: list[str], revision: str):
        self.validate_selection(ids, revision)
        selected = [self.rows[key] for key in dict.fromkeys(ids)]
        images = []
        for row in selected:
            image = drawing.target_image(row)
            if image is None:
                raise ValueError(f"{row['id']}: verified target preview required before moving")
            drawing.validate_tikz(row['target_tikz'])
            images.append(image['bytes'])
        directory = self.output / 'reconstruct'
        (directory / 'images').mkdir(parents=True, exist_ok=True)
        reconstructed = dict(self.reconstructed)
        moves = list(self.moves)
        for row, data in zip(selected, images):
            image_hash = hashlib.sha256(data).hexdigest()
            code_hash = hashlib.sha256(row['target_tikz'].encode('utf-8')).hexdigest()
            key = 'reconstruct-' + hashlib.sha256((code_hash + ':' + image_hash).encode()).hexdigest()
            path = directory / 'images' / (image_hash + '.png')
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(data)
            drawing.replace_snapshot(temporary, path)
            previous = reconstructed.get(key, {})
            provenance = {**row.get('provenance', {}), **previous.get('provenance', {})}
            provenance['parents'] = sorted(set(provenance.get('parents', [])) | set(row.get('provenance', {}).get('parents', [])))
            provenance['moved_from'] = list(dict.fromkeys([*provenance.get('moved_from', []), row['id']]))
            provenance['source_groups'] = sorted(set(provenance.get('source_groups', [])) | ({row['source_group']} if row.get('source_group') else set()))
            splits = [split for split in (row.get('split'), previous.get('split')) if split is not None]
            target = {**{field: row.get(field) for field in
                ('schema_version', 'source', 'source_group')},
                'id': key, 'task': 'Reconstruct', 'current_tikz': None,
                'instruction': None,
                'target_tikz': row['target_tikz'], 'image': {'path': str(path), 'sha256': image_hash},
                'split': max(splits, key=('train', 'validation', 'test').index) if splits else None,
                'provenance': provenance, 'rendered_png_path': str(path),
                'rendered_png_sha256': image_hash, 'rendered_tikz_sha256': code_hash,
                'verification': {'status': 'ready', 'reviewed_by': 'human:local-review',
                    'reviewed_at': datetime.now(timezone.utc).isoformat(),
                    'method': 'manual_reconstruct_review', 'original_instruction_match': False,
                    'decision': 'Usable monochrome diagram; mathematical consistency, visible content, readability and spacing reviewed.'}}
            target['verification']['reviewed_input_sha256'] = drawing.review_digest(target)
            reconstructed[key] = target
            moves.append({'original': row, 'reconstruct': target})
        # Commit full originals and destinations together before removing any source rows.
        production.write_rows(directory / 'moves.jsonl', moves)
        added = len(reconstructed) - len(self.reconstructed)
        self.reload()
        self.save()
        return {'moved': len(selected), 'added': added}

    def preview(self, row: dict, before: bool):
        if before:
            if isinstance(row.get('current_render'), dict):
                return drawing.target_image({**row['current_render'], 'target_tikz': row.get('current_tikz')})
            base = self.bases.get(row.get('provenance', {}).get('starting_record_id'))
            if not base or base.get('target_tikz') != row.get('current_tikz'):
                return None
            row = base
        return drawing.target_image(row)


PAGE = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TikZ candidate review</title>
<style>
body{font:16px system-ui;margin:1.5rem;line-height:1.5}header{background:white;border-bottom:1px solid #ccc;padding:.5rem 0}
nav{display:flex;flex-wrap:wrap;gap:.75rem;align-items:center}article{border-bottom:1px solid #ccc;padding:1rem 0;overflow-wrap:anywhere}
.pictures{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:1rem}figure{margin:0;max-width:100%}img{max-width:100%;max-height:430px}pre{white-space:pre-wrap;overflow-wrap:anywhere}
button,input,select{font:inherit}h1{font-size:1.5rem;margin:0}h2{font-size:1rem}#status{min-height:1.5em}input[type=search]{max-width:100%}
</style>
<header><h1>TikZ candidate review</h1>
<p>Select diagrams, then choose an action. <strong>Delete</strong> removes unwanted samples.
<strong>Move to Reconstruct</strong> confirms that each selected target fails its original instruction but is a usable black-and-white diagram:
the mathematics and visible content are consistent, labels are readable, and points, edges and labels have enough spacing.
Both actions remove the selected Generate/Edit rows and retain originals for recovery.</p>
<nav><label>Task <select id="task"><option value="">All</option><option>Generate</option><option>Edit</option></select></label>
<label>Search <input id="search" type="search" placeholder="Instruction, source or ID"></label>
<button id="reload">Reload</button><button id="select">Select page</button><button id="clear">Clear selection</button>
<button id="delete" disabled>Delete selected (0)</button><button id="reconstruct" disabled>Move to Reconstruct (0)</button></nav>
<p id="status" role="status" aria-live="polite">Loading...</p>
<nav><button id="prev">Previous</button><span id="page"></span><button id="next">Next</button></nav></header>
<main id="cards"></main>
<script>
const token = '__TOKEN__';
const $ = id => document.getElementById(id);
let rows=[], revision='', offset=0, selected=new Set(), shown=[], busy=false;
const size=12;
const text=(tag,value,parent)=>{const e=document.createElement(tag);e.textContent=value;parent.append(e);return e};
async function request(url, options){const r=await fetch(url,options);if(!r.ok)throw new Error((await r.json()).error || 'Request failed');return r.json()}
function selection(){for(const [id,label] of [['delete','Delete selected'],['reconstruct','Move to Reconstruct']]){
 $(id).disabled=busy||!selected.size;$(id).textContent=`${label} (${selected.size})`}}
function render(){
 const query=$('search').value.toLocaleLowerCase();
 const filtered=rows.filter(r=>(!$('task').value||r.task===$('task').value)&&[r.id,r.instruction,r.source,r.source_group].join(' ').toLocaleLowerCase().includes(query));
 offset=Math.min(offset,Math.max(0,Math.floor((filtered.length-1)/size)*size));shown=filtered.slice(offset,offset+size);
 $('page').textContent=`${filtered.length?offset+1:0}–${Math.min(offset+size,filtered.length)} of ${filtered.length}`;
 $('prev').disabled=offset===0;$('next').disabled=offset+size>=filtered.length;$('cards').replaceChildren();
 for(const r of shown){
  const card=document.createElement('article');$('cards').append(card);
  const h=text('h2','',card), label=document.createElement('label'), check=document.createElement('input');check.type='checkbox';check.checked=selected.has(r.id);
  check.onchange=()=>{check.checked?selected.add(r.id):selected.delete(r.id);selection()};label.append(check,document.createTextNode(` ${r.task} · ${r.id}`));h.append(label);
  text('p',r.instruction,card);text('small',r.source || r.source_group || '',card);
  const pictures=document.createElement('div');pictures.className='pictures';card.append(pictures);
  for(const before of r.task==='Edit'?[true,false]:[false]){const figure=document.createElement('figure');pictures.append(figure);
   text('figcaption',before?'Before':'Target',figure);const img=document.createElement('img');img.alt=before?'Starting diagram':'Target diagram';img.loading='lazy';
   img.src=`/image?id=${encodeURIComponent(r.id)}&before=${before?1:0}`;img.onerror=()=>{img.remove();text('p','Verified preview unavailable; inspect the TikZ below.',figure)};figure.append(img)}
  const details=document.createElement('details');text('summary','TikZ and source details',details);card.append(details);
  details.ontoggle=async()=>{if(!details.open||details.dataset.loaded)return;details.dataset.loaded='1';try{const full=await request('/api/row?id='+encodeURIComponent(r.id));
   if(full.current_tikz){text('h3','Current TikZ',details);text('pre',full.current_tikz,details)}text('h3','Target TikZ',details);text('pre',full.target_tikz,details);
   text('h3','Source metadata',details);text('pre',JSON.stringify(full.provenance,null,2),details);
   for(const source of full.sources || []){text('h3',source.source || source.id,details);text('pre',source.source_text,details);
    if(source.givens)text('p','Audited givens: '+source.givens,details)}
  }catch(e){details.dataset.loaded='';text('p',e.message,details)}};
 }
 selection();
}
async function load(){const data=await request('/api/rows');rows=data.rows;revision=data.revision;selected=new Set([...selected].filter(id=>rows.some(r=>r.id===id)));render();
 $('status').textContent=`${rows.filter(r=>r.task==='Generate').length} Generate · ${rows.filter(r=>r.task==='Edit').length} Edit · ${data.reconstruct} Reconstruct · ${data.excluded-data.moved} deleted · ${data.moved} moved`}
function fail(e){$('status').textContent=e.message}
$('task').onchange=$('search').oninput=()=>{offset=0;render()};$('prev').onclick=()=>{offset-=size;render()};$('next').onclick=()=>{offset+=size;render()};
$('select').onclick=()=>{shown.forEach(r=>selected.add(r.id));render()};$('clear').onclick=()=>{selected.clear();render()};$('reload').onclick=()=>load().catch(fail);
for(const action of ['delete','reconstruct'])$(action).onclick=async()=>{const count=selected.size;busy=true;selection();$('status').textContent='Saving review decision...';try{
 const result=await request('/api/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':token},body:JSON.stringify({ids:[...selected],revision})});
 selected.clear();await load();$('status').textContent+=action==='delete'?` · Deleted ${count} samples.`:` · Moved ${count} samples; added ${result.added} unique Reconstruct pairs.`;
}catch(e){fail(e)}finally{busy=false;selection()}};
load().catch(fail);
</script></html>'''


def make_server(review: Review, port: int = 8765):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, value, content_type='application/json; charset=utf-8'):
            data = value if isinstance(value, bytes) else drawing.encoded(value).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def allowed(self):
            host = f'127.0.0.1:{self.server.server_port}'
            return self.headers.get('Host') == host and self.headers.get('Sec-Fetch-Site') != 'cross-site'

        def do_GET(self):
            if not self.allowed():
                return self.reply(403, {'error': 'Local access only'})
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            with review.lock:
                if url.path == '/':
                    return self.reply(200, PAGE.replace('__TOKEN__', review.token).encode('utf-8'), 'text/html; charset=utf-8')
                if url.path == '/api/rows':
                    review.reload()
                    fields = ('id', 'task', 'instruction', 'source', 'source_group')
                    return self.reply(200, {'rows': [{k: row.get(k) for k in fields} for row in review.rows.values()],
                        'revision': review.revision, 'excluded': len(review.excluded),
                        'reconstruct': len(review.reconstructed), 'moved': len(review.moves)})
                row = review.rows.get(query.get('id', [''])[0])
                if url.path == '/api/row' and row:
                    return self.reply(200, {**row, 'sources': [review.sources[parent]
                        for parent in row.get('provenance', {}).get('parents', []) if parent in review.sources]})
                if url.path == '/image' and row:
                    image = review.preview(row, query.get('before', ['0'])[0] == '1')
                    if image:
                        return self.reply(200, image['bytes'], 'image/png')
                self.reply(404, {'error': 'Not found'})

        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if (not self.allowed() or self.path not in ('/api/delete', '/api/reconstruct') or self.headers.get('Origin') != origin
                    or self.headers.get('X-Review-Token') != review.token
                    or self.headers.get('Content-Type') != 'application/json'):
                return self.reply(403, {'error': 'Invalid local review request'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 100000:
                    raise ValueError('Invalid request size')
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise TypeError('Expected an object')
                with review.lock:
                    if self.path == '/api/reconstruct':
                        result = review.move_to_reconstruct(payload.get('ids'), payload.get('revision'))
                    else:
                        review.delete(payload.get('ids'), payload.get('revision'))
                        result = {'deleted': len(set(payload['ids']))}
                self.reply(200, result)
            except (TypeError, ValueError) as error:
                self.reply(400, {'error': str(error)})
            except RuntimeError as error:
                self.reply(409, {'error': str(error)})
            except OSError as error:
                self.reply(500, {'error': f'Export failed; restart the reviewer to replay saved decisions: {error}'})

    # shortcut: one reviewer process; add a file lock if concurrent writers become necessary.
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dataset/synthetic')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    review = Review(args.output)
    with make_server(review, args.port) as server:
        print(f'Review {len(review.rows)} samples at http://127.0.0.1:{server.server_port}', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
