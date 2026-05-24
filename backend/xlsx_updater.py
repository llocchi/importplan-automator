import base64, io
from datetime import datetime
from typing import Dict, Tuple
import openpyxl
from logger_setup import get_logger

log = get_logger('tuut.xlsx')


def _norm(val):
    if val is None:
        return ''
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val).strip()


def update_xlsx(xlsx_base64: str, triplas: Dict[Tuple[str,str],str],
                encontrados: Dict[Tuple[str,str],int], original_name: str) -> dict:
    try:
        xlsx_bytes = base64.b64decode(xlsx_base64)
    except Exception:
        raise ValueError('xlsx_base64 invalido')

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    log.info('XLSX: sheet=%s max_row=%d max_col=%d', ws.title, ws.max_row, ws.max_column)

    header = [_norm(ws.cell(1, c).value) for c in range(1, ws.max_column + 1)]
    log.info('XLSX cabecalho: %s', ' | '.join(f'C{i+1}={h}' for i, h in enumerate(header)))

    desc_col_idx = None
    for idx, h in enumerate(header):
        hl = h.lower()
        if any(kw in hl for kw in ('desc', 'produto', 'nome', 'product', 'item', 'designa')):
            desc_col_idx = idx
            break
    if desc_col_idx is None and len(header) > 1:
        desc_col_idx = 1

    # --- 1. Monta indice XLSX: (SIS, REF) -> lista de (row_num, seq_cell) ---
    xlsx_index: Dict[Tuple[str,str], list] = {}
    total_xlsx_linhas = 0
    for row in ws.iter_rows(min_row=2):
        if len(row) < 4:
            continue
        s = _norm(row[2].value)
        r = _norm(row[3].value)
        if not s or not r or s in ('None', 'SISTEMA') or r in ('None', 'REF.'):
            continue
        total_xlsx_linhas += 1
        key = (s, r)
        if key not in xlsx_index:
            xlsx_index[key] = []
        xlsx_index[key].append((row[0].row, row[0]))

    log.info('XLSX index: %d pares unicos | %d linhas | %d produtos no PDF', len(xlsx_index), total_xlsx_linhas, len(triplas))

    # --- 2. Atualiza XLSX: correspondencia exata SIS+REF (sem fallback) ---
    updated = 0
    not_found_list = []
    not_found_count = 0

    for (sis, ref), xlsx_rows in xlsx_index.items():
        if (sis, ref) in triplas:
            seq = triplas[(sis, ref)]
            pag = encontrados.get((sis, ref), '?')
            for (row_num, seq_cell) in xlsx_rows:
                try:
                    seq_cell.value = int(seq)
                except ValueError:
                    seq_cell.value = seq
                updated += 1
                log.info('UPDATE seq=%s | sis=%s | ref=%s | pag=%s | row=%d', seq, sis, ref, pag, row_num)
        else:
            not_found_count += 1
            not_found_list.append({'sistema': sis, 'ref': ref, 'motivo': 'nao no PDF'})
            log.warning('NAO_ENCONTRADO sis=%s | ref=%s', sis, ref)

    log.info('XLSX FIM: linhas_xlsx=%d | pdf_produtos=%d | atualizadas=%d | nao_encontradas=%d', total_xlsx_linhas, len(triplas), updated, not_found_count)

    if updated == 0:
        log.error('ZERO linhas atualizadas!')

    # --- 3. Dump catalogo completo (estado apos atualizacao) ---
    log.info('CATALOGO INICIO: %d produtos', total_xlsx_linhas)
    for row in ws.iter_rows(min_row=2):
        if len(row) < 4:
            continue
        s = _norm(row[2].value)
        r = _norm(row[3].value)
        if not s or not r or s in ('None', 'SISTEMA') or r in ('None', 'REF.'):
            continue
        seq_val = _norm(row[0].value)
        desc_val = ''
        if desc_col_idx is not None and desc_col_idx < len(row):
            desc_val = _norm(row[desc_col_idx].value)
        log.info('CATALOGO seq=%-6s | sis=%-6s | ref=%-15s | desc=%s', seq_val, s, r, desc_val)
    log.info('CATALOGO FIM: %d produtos', total_xlsx_linhas)

    base_name = original_name
    for ext in ('.xlsx', '.xls', '.XLSX', '.XLS'):
        base_name = base_name.replace(ext, '')
    ts = datetime.now().strftime('%d-%m-%Y_%H%M%S')
    output_filename = f'{base_name}_atualizado_{ts}.xlsx'
    out = io.BytesIO()
    wb.save(out); out.seek(0)
    b64 = base64.b64encode(out.read()).decode()
    return {
        'xlsx_base64': b64,
        'report': {
            'total_rows': total_xlsx_linhas,
            'updated': updated,
            'not_found': not_found_list,
            'output_filename': output_filename,
            'processed_at': datetime.now().isoformat(),
        }
    }
