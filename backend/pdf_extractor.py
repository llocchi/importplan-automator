import re
from typing import List, Dict, Tuple
from logger_setup import get_logger

log = get_logger('tuut.pdf')

PATTERN_PRODUTO     = re.compile(r'(\d{4,6})\s*\|\s*([A-Z][A-Z0-9-]{2,15}|\d{1,3}[A-Z][A-Z0-9-]{0,12})')
PATTERN_INN         = re.compile(r'Inn\.|Mas\.|M[uU]lt\.', re.IGNORECASE)
PATTERN_BARCODE_SEQ = re.compile(r'^\s*\d[\d\s]{8,}\s+(\d{1,4})\s*$')
PATTERN_SEQ         = re.compile(r'^\s*(\d{1,4})\s*$')


def _find_seq(lines, start, end, page_sistemas_set, stop_at_produto=False):
    # Tenta 1: barcode + sequencial na mesma linha: '7 908976 128021   280'
    for k in range(start, end):
        if stop_at_produto and PATTERN_PRODUTO.search(lines[k]):
            break
        bm = PATTERN_BARCODE_SEQ.match(lines[k])
        if bm:
            c = bm.group(1).strip()
            if c not in page_sistemas_set:
                return c
    # Tenta 2: sequencial standalone em linha propria: '280'
    for k in range(start, end):
        if stop_at_produto and PATTERN_PRODUTO.search(lines[k]):
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

        page_sistemas_set = set()
        for ln in lines:
            pm = PATTERN_PRODUTO.search(ln)
            if pm:
                page_sistemas_set.add(pm.group(1).strip())

        page_prod = 0
        page_seqs = 0
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

                # Busca marcador Inn./Mas./Mult. nas proximas 30 linhas
                inn_line = -1
                for j in range(i + 1, min(i + 30, n)):
                    if PATTERN_INN.search(lines[j]):
                        inn_line = j
                        break

                seq_found = None
                if inn_line >= 0:
                    # Sequencial esta na linha do barcode, logo apos o marcador Inn.
                    seq_found = _find_seq(lines, inn_line, min(inn_line + 10, n), page_sistemas_set, stop_at_produto=False)
                else:
                    # Sem marcador Inn.: busca direta ate o proximo produto
                    seq_found = _find_seq(lines, i + 1, min(i + 30, n), page_sistemas_set, stop_at_produto=True)

                if seq_found is not None:
                    triplas[key] = seq_found
                    total_seq += 1
                    page_seqs += 1
                    log.info('PDF seq=%s | sis=%s | ref=%s | pag=%d', seq_found, sistema, ref, page_num)
                else:
                    total_sem_seq += 1
                    log.warning('PDF SEM-SEQ sis=%s | ref=%s | pag=%d | inn=%s', sistema, ref, page_num, inn_line >= 0)
            i += 1
        log.info('Pagina %d/%d: %d produtos | %d seq', page_num, total_pages, page_prod, page_seqs)

    log.info('PDF FIM: paginas=%d | produtos=%d | seq=%d | sem_seq=%d', total_pages, total_produto, total_seq, total_sem_seq)

    return {'triplas': triplas, 'encontrados': encontrados, 'diag': []}
