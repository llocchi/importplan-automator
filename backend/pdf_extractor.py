import re
from typing import List, Dict, Tuple
from logger_setup import get_logger

log = get_logger('tuut.pdf')

PATTERN_PRODUTO     = re.compile(r'(\d{4,6})\s*\|\s*([A-Z][A-Z0-9-]{2,15}|\d{1,3}[A-Z][A-Z0-9-]{0,12})')
PATTERN_INN         = re.compile(r'Inn\.|Mas\.|M[uU]lt\.|Unid\.|Cx\.|Conj\.|Par\.', re.IGNORECASE)
PATTERN_BARCODE_SEQ = re.compile(r'^\s*\d[\d\s]{8,}\s+(\d{1,4})\s*$')
PATTERN_SEQ         = re.compile(r'^\s*(\d{1,4})\s*$')


def _find_seq(lines, start, end, stop_at_produto=False, page_sistemas_set=None):
    if page_sistemas_set is None:
        page_sistemas_set = set()
    # Tenta 1: barcode + sequencial na mesma linha (sem filtro - seguro por estrutura)
    for k in range(start, end):
        if stop_at_produto and PATTERN_PRODUTO.search(lines[k]):
            break
        bm = PATTERN_BARCODE_SEQ.match(lines[k])
        if bm:
            return bm.group(1).strip()
    # Tenta 2: sequencial standalone (sempre para no proximo produto + filtro SISTEMA)
    for k in range(start, end):
        if PATTERN_PRODUTO.search(lines[k]):
            break
        sm = PATTERN_SEQ.match(lines[k])
        if sm:
            c = sm.group(1).strip()
            if c not in page_sistemas_set:
                return c
    return None


def extract_triplas(pages: List[str]) -> Dict:
    triplas: Dict[Tuple[str, str], str] = {}
    encontrados: Dict[Tuple[str, str], int] = {}
    total_pages = len(pages)
    total_produto = 0
    total_seq = 0
    total_sem_seq = 0

    for page_num, page_text in enumerate(pages, start=1):
        lines = page_text.split('\n')
        n = len(lines)
        page_prod = 0
        page_seqs = 0
        page_sistemas_set = set()
        i = 0

        while i < n:
            m = PATTERN_PRODUTO.search(lines[i])
            if m:
                sistema = m.group(1).strip()
                ref     = m.group(2).strip()
                key     = (sistema, ref)
                if key not in encontrados:
                    encontrados[key] = page_num
                total_produto += 1
                page_prod += 1
                page_sistemas_set.add(sistema)

                inn_line = -1
                for j in range(i + 1, min(i + 30, n)):
                    if PATTERN_INN.search(lines[j]):
                        inn_line = j
                        break

                seq_found = None
                if inn_line >= 0:
                    seq_found = _find_seq(lines, inn_line, min(inn_line + 10, n), stop_at_produto=False, page_sistemas_set=page_sistemas_set)
                else:
                    seq_found = _find_seq(lines, i + 1, min(i + 30, n), stop_at_produto=True, page_sistemas_set=page_sistemas_set)

                if seq_found is not None:
                    triplas[key] = seq_found
                    total_seq += 1
                    page_seqs += 1
                    log.info('PDF seq=%s | sis=%s | ref=%s | pag=%d', seq_found, sistema, ref, page_num)
                else:
                    total_sem_seq += 1
                    log.warning('PDF SEM-SEQ sis=%s | ref=%s | pag=%d | inn=%s', sistema, ref, page_num, inn_line >= 0)
                    dump_start = max(0, i - 1)
                    dump_end   = min(n, i + 16)
                    for di, dl in enumerate(lines[dump_start:dump_end]):
                        log.debug('  DIAG[%d] %r', dump_start + di, dl)
            i += 1
        log.info('Pagina %d/%d: %d produtos | %d seq', page_num, total_pages, page_prod, page_seqs)

    log.info('PDF FIM: paginas=%d | total_linhas=%d | unicos=%d | seq=%d | sem_seq=%d', total_pages, total_produto, len(encontrados), total_seq, total_sem_seq)

    return {'triplas': triplas, 'encontrados': encontrados, 'diag': []}
