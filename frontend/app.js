/* =================================================================
   app.js - Catalog Import Processor | Tuut ImportPlan Automator
   ================================================================= */

/* -- Configuracao ------------------------------------------------- */
// Substitua pela URL real do seu servico Render.com antes do deploy
const API_URL = window.__API_URL__ || 'https://catalog-import-api.onrender.com';

/* -- Estado ------------------------------------------------------- */
let pdfFile  = null;
let xlsxFile = null;
let processing = false;

/* -- Inicializacao ------------------------------------------------ */
function init() {
  setupZone('pdf',  '.pdf');
  setupZone('xlsx', '.xlsx,.xls');
  document.getElementById('btn-process').addEventListener('click', handleProcess);
  document.getElementById('btn-reset').addEventListener('click', resetForm);
  document.getElementById('btn-download-again').addEventListener('click', downloadAgain);
  document.getElementById('btn-download-log').addEventListener('click', downloadLog);
  updateProcessButton();
}
// app.js e carregado dinamicamente pelo modulo PDF.js, DOMContentLoaded pode ja ter disparado
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

/* -- Zones de Upload ---------------------------------------------- */
function setupZone(type, accept) {
  const zone  = document.getElementById('zone-' + type);
  const input = document.getElementById('input-' + type);
  zone.addEventListener('click', (e) => { if (e.target === input) return; if (!zone.classList.contains('upload-zone--disabled')) input.click(); });
  input.setAttribute('accept', accept);
  input.addEventListener('change', e => { if (e.target.files[0]) handleFile(type, e.target.files[0]); });
  zone.addEventListener('dragover', e => { e.preventDefault(); if (!zone.classList.contains('upload-zone--disabled')) zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('dragover'); const f = e.dataTransfer.files[0]; if (f) handleFile(type, f); });
}

function handleFile(type, file) {
  const zone  = document.getElementById('zone-' + type);
  const errEl = document.getElementById('error-' + type);
  const fname = document.getElementById('filename-' + type);
  const hint  = document.getElementById('hint-' + type);
  const icon  = document.getElementById('icon-' + type);
  const valid = type === 'pdf'
    ? (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'))
    : (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls'));
  if (!valid) {
    zone.classList.add('upload-zone--error'); zone.classList.remove('upload-zone--selected');
    errEl.textContent = type === 'pdf' ? 'Selecione um arquivo PDF.' : 'Selecione um arquivo .xlsx';
    errEl.classList.remove('hidden'); fname.classList.add('hidden');
    if (type === 'pdf') pdfFile = null; else xlsxFile = null;
    updateProcessButton(); return;
  }
  if (type === 'pdf') pdfFile = file; else xlsxFile = file;
  zone.classList.add('upload-zone--selected'); zone.classList.remove('upload-zone--error');
  errEl.classList.add('hidden'); hint.classList.add('hidden');
  fname.textContent = file.name + ' (' + formatBytes(file.size) + ')';
  fname.classList.remove('hidden');
  icon.textContent = '\u2705';
  updateProcessButton();
}

/* -- Botao Processar ---------------------------------------------- */
function updateProcessButton() {
  document.getElementById('btn-process').disabled = !(pdfFile && xlsxFile && !processing);
}

async function handleProcess() {
  if (!pdfFile || !xlsxFile || processing) return;
  processing = true; updateProcessButton();
  const btn = document.getElementById('btn-process');
  btn.classList.add('btn--loading');
  document.getElementById('btn-icon').innerHTML = '<span class="spinner"></span>';
  document.getElementById('btn-text').textContent = 'Processando...';
  hideStatuses();
  try {
    setStatus('processing', true);
    updateStep(1);
    const pdfPages = await extractPdfPages(pdfFile);
    updateStep(2);
    const xlsxB64 = await fileToBase64(xlsxFile);
    updateStep(3);
    const data = await callApi(pdfPages, xlsxB64);
    setStatus('processing', false);
    showReport(data);
    autoDownload(data);
  } catch (err) {
    setStatus('processing', false);
    showError(err.message || 'Erro desconhecido. Tente novamente.');
  } finally {
    processing = false;
    btn.classList.remove('btn--loading');
    document.getElementById('btn-icon').textContent = '\u26a1';
    document.getElementById('btn-text').textContent = 'Processar';
    updateProcessButton();
  }
}

/* -- Extracao PDF.js ---------------------------------------------- */
async function extractPdfPages(file) {
  const url  = URL.createObjectURL(file);
  const task = pdfjsLib.getDocument({ url, cMapUrl: 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.4.168/cmaps/', cMapPacked: true });
  const pdf  = await task.promise;
  const pages = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    setProgressMsg('Extraindo p\u00e1gina ' + i + ' de ' + pdf.numPages + '...');
    const page    = await pdf.getPage(i);
    const content = await page.getTextContent();
    pages.push(content.items.map(x => x.str).join('\n'));
  }
  URL.revokeObjectURL(url);
  setProgressMsg('Enviando dados ao servidor...');
  return pages;
}

/* -- API Call ----------------------------------------------------- */
async function callApi(pdfPages, xlsxB64) {
  const coldTimer = setTimeout(() => document.getElementById('status-coldstart').classList.remove('hidden'), 8000);
  let response;
  try {
    response = await fetch(API_URL + '/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pdf_pages: pdfPages, xlsx_base64: xlsxB64, pdf_name: pdfFile.name, xlsx_name: xlsxFile.name })
    });
  } finally {
    clearTimeout(coldTimer);
    document.getElementById('status-coldstart').classList.add('hidden');
  }
  if (!response.ok) {
    const txt = await response.text().catch(() => 'Erro ' + response.status);
    let msg = txt;
    try { msg = JSON.parse(txt).detail || txt; } catch {}
    throw new Error(msg);
  }
  return response.json();
}

/* -- Relatorio ---------------------------------------------------- */
function showReport(data) {
  const r = data.report;
  document.getElementById('report').classList.remove('hidden');
  document.getElementById('stat-total').textContent   = r.total_rows || 0;
  document.getElementById('stat-updated').textContent = r.updated    || 0;
  document.getElementById('stat-missing').textContent = (r.not_found || []).length;
  const triplasEl = document.getElementById('stat-triplas');
  if (triplasEl) triplasEl.textContent = r.triplas_found || 0;

  // Amostra sequenciais do PDF
  const dbgEl   = document.getElementById('triplas-debug');
  const dbgBody = document.getElementById('triplas-sample-body');
  if (dbgEl) {
    dbgEl.style.display = '';
    if (dbgBody) {
      if (r.triplas_sample && r.triplas_sample.length > 0) {
        dbgBody.textContent = r.triplas_sample.map(t => t.sistema + ' | ' + t.ref + '  ->  seq ' + t.seq).join('\n');
      } else {
        dbgBody.textContent = '(nenhum sequencial capturado do PDF)';
      }
    }
  }

  const nfList = document.getElementById('report-not-found-list');
  const nfSect = document.getElementById('report-not-found');
  nfList.innerHTML = '';
  if (r.not_found && r.not_found.length > 0) {
    nfSect.classList.remove('hidden');
    r.not_found.forEach(item => {
      const li = document.createElement('li');
      li.className = 'report__not-found-item';
      li.textContent = item.sistema + ' | ' + item.ref;
      nfList.appendChild(li);
    });
  } else { nfSect.classList.add('hidden'); }

  const log = document.getElementById('proc-log-body');
  const ts  = new Date().toLocaleString('pt-BR');
  log.innerHTML = [
    '<span class="proc-log__line proc-log__line--sep">-----------------------------------------</span>',
    '<span class="proc-log__line proc-log__line--label">Processado em   </span><span class="proc-log__line proc-log__line--time">' + ts + '</span>',
    '<span class="proc-log__line proc-log__line--label">PDF             </span><span class="proc-log__line proc-log__line--value">' + (r.pdf_name  || pdfFile.name)  + '</span>',
    '<span class="proc-log__line proc-log__line--label">XLSX entrada    </span><span class="proc-log__line proc-log__line--value">' + (r.xlsx_name || xlsxFile.name) + '</span>',
    '<span class="proc-log__line proc-log__line--label">XLSX gerado     </span><span class="proc-log__line proc-log__line--ok">'    + (r.output_filename || '-')    + '</span>',
    '<span class="proc-log__line proc-log__line--label">Linhas totais   </span><span class="proc-log__line proc-log__line--value">' + (r.total_rows || 0) + '</span>',
    '<span class="proc-log__line proc-log__line--label">Atualizadas     </span><span class="proc-log__line proc-log__line--ok">'    + (r.updated    || 0) + '</span>',
    '<span class="proc-log__line proc-log__line--label">Nao encontradas </span><span class="proc-log__line proc-log__line--value">' + (r.not_found || []).length + '</span>',
    '<span class="proc-log__line proc-log__line--label">Seq. no PDF     </span><span class="proc-log__line proc-log__line--ok">'    + (r.triplas_found  || 0) + '</span>',
    '<span class="proc-log__line proc-log__line--label">Duracao backend </span><span class="proc-log__line proc-log__line--time">'  + (r.duration_seconds || '-') + 's</span>',
    '<span class="proc-log__line proc-log__line--sep">-----------------------------------------</span>'
  ].join('');
  window._lastResult = data; window._outputName = r.output_filename; window._lastLog = data.log_content || '';
}

/* -- Download ----------------------------------------------------- */
function autoDownload(data) { triggerDownload(data.xlsx_base64, data.report.output_filename || 'ImportPlan_atualizado.xlsx'); }
function downloadAgain()    { if (window._lastResult) autoDownload(window._lastResult); }
function downloadLog() {
  var t = window._lastLog;
  if (!t) { alert('Log nao disponivel'); return; }
  var ts = new Date().toISOString().slice(0,19).replace(/[T:]/g,'-');
  var b = new Blob([t], {type: 'text/plain;charset=utf-8'});
  var a = Object.assign(document.createElement('a'), {href: URL.createObjectURL(b), download: 'processamento_'+ts+'.log'});
  a.click(); setTimeout(function(){ URL.revokeObjectURL(a.href); }, 5000);
}
  var ts = new Date().toISOString().slice(0,19).replace(/[T:]/g,'-');
  var b = new Blob([t], {type: 'text/plain;charset=utf-8'});
  var a = Object.assign(document.createElement('a'), {href: URL.createObjectURL(b), download: 'processamento_'+ts+'.log'});
  a.click(); setTimeout(function(){ URL.revokeObjectURL(a.href); }, 5000);
}
function triggerDownload(b64, name) {
  const bin = atob(b64); const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const blob = new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: name });
  a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

/* -- Helpers de UI ------------------------------------------------ */
function hideStatuses() { ['status-processing','status-coldstart','status-error','report'].forEach(id => document.getElementById(id).classList.add('hidden')); }
function setStatus(id, show) { document.getElementById('status-' + id).classList.toggle('hidden', !show); }
function showError(msg) { const el = document.getElementById('status-error'); el.classList.remove('hidden'); const t = el.querySelector('.status-msg__text'); if (t) t.textContent = msg; }
function setProgressMsg(msg) { const el = document.getElementById('progress-msg'); if (el) el.textContent = msg; }
function updateStep(n) {
  [1,2,3].forEach(i => {
    const el = document.getElementById('step-' + i);
    if (!el) return;
    el.classList.toggle('active',  i === n);
    el.classList.toggle('done',    i  <  n);
    el.classList.toggle('pending', i  >  n);
  });
}
function resetForm() {
  pdfFile = xlsxFile = null; processing = false;
  ['pdf','xlsx'].forEach(t => {
    document.getElementById('zone-'+t).classList.remove('upload-zone--selected','upload-zone--error');
    document.getElementById('icon-'+t).textContent = t==='pdf' ? '\ud83d\udcc4' : '\ud83d\udcca';
    document.getElementById('hint-'+t).classList.remove('hidden');
    document.getElementById('filename-'+t).classList.add('hidden');
    document.getElementById('error-'+t).classList.add('hidden');
    document.getElementById('input-'+t).value = '';
  });
  hideStatuses();
  document.getElementById('btn-icon').textContent = '\u26a1';
  document.getElementById('btn-text').textContent = 'Processar';
  updateProcessButton();
  window._lastResult = window._outputName = window._lastLog = null;
}
function formatBytes(b) { return b<1024 ? b+' B' : b<1048576 ? (b/1024).toFixed(1)+' KB' : (b/1048576).toFixed(1)+' MB'; }
function fileToBase64(file) {
  return new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result.split(',')[1]); r.onerror = rej; r.readAsDataURL(file); });
}
