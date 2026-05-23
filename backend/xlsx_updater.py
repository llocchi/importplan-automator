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
    log.info('Sheets no XLSX: %s | Ativa: %s', wb.sheetnames, wb.active.title)
    ws = wb.active
    log.info('XLSX: sheet=%s linhas=%d colunas=%d', ws.title, ws.max_row, ws.max_column)

    updated = 0
    not_found = []
    total_rows = 0
    cnt_nseq = 0
    cnt_miss = 0

    for row in ws.iter_rows(min_row=2):
        if len(row) < 4:
            continue
        seq_cell = row[0]
        s = _norm(row[2].value)
        r = _norm(row[3].value)
        if not s or not r or s in ('None', 'SISTEMA') or r in ('None', 'REF.'):
            continue
        total_rows += 1
        key = (s, r)
        row_num = seq_cell.row

        if key in triplas:
            seq = triplas[key]
            pag = encontrados.get(key, '?')
            try:
                seq_cell.value = int(seq)
            except ValueError:
                seq_cell.value = seq
            updated += 1
            log.debug('[OK  ] row=%4d sys=%-8s ref=%-15s seq=%-4s pag=%s', row_num, s, r, seq, pag)

        elif key in encontrados:
            pag_n = encontrados.get(key, '?')
            cnt_nseq += 1
            not_found.append({'sistema': s, 'ref': r, 'motivo': 'Inn sem seq'})
            log.info('[NSEQ] row=%4d sys=%-8s ref=%-15s (Inn sem seq)  pag=%s', row_num, s, r, pag_n)

        else:
            cnt_miss += 1
            not_found.append({'sistema': s, 'ref': r, 'motivo': 'nao no PDF'})
            log.info('[MISS] row=%4d sys=%-8s ref=%-15s (nao no PDF)', row_num, s, r)

    log.info('UPDATE: total=%d | atualizadas=%d | nao_enc=%d (NSEQ=%d MISS=%d)',
             total_rows, updated, len(not_found), cnt_nseq, cnt_miss)

    if updated == 0:
        log.error('ZERO linhas atualizadas! Veja diagnostico acima.')

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
            'total_rows': total_rows,
            'updated': updated,
            'not_found': not_found,
            'output_filename': output_filename,
            'processed_at': datetime.now().isoformat(),
        }
    }