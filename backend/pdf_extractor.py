import re
from typing import List, Dict, Tuple
from logger_setup import get_logger

log = get_logger('tuut.pdf')

PATTERN_PRODUTO = re.compile(r'(\d{4,6})\s*\|\s*([A-Z][A-Z0-9-]{2,15}|\d{1,3}[A-Z][A-Z0-9-]{0,12})')
PATTERN_INN     = re.compile(r'Inn\.|Mas\.|M[uU]lt\.', re.IGNORECASE)
PATTERN_SEQ     = re.compile(r'^\s*(\d{1,4})\s*$')


def extract_triplas(pages: List[str]) -> Dict:
    triplas: Dict[Tuple[str, str], str] = {}
    encontrados: Dict[Tuple[str, str], int] = {}
    total_pages = len(pages)
    total_produto = 0
    total_inn = 0
    total_seq = 0
    total_sem_seq = 0
    diag_samples = []

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

                seq_found = None
                path_used = None
                inn_line  = -1

                # Caminho 1: forward via Inn./Mas./Mult.
                for j in range(i + 1, min(i + 25, n)):
                    if PATTERN_INN.search(lines[j]):
                        inn_line = j
                        total_inn += 1
                        for k in range(j, min(j + 13, n)):
                            sm = PATTERN_SEQ.match(lines[k])
                            if sm:
                                candidate = sm.group(1).strip()
                                if candidate not in page_sistemas_set:
                                    seq_found = candidate
                                    path_used = 1
                                    break
                        break

                # Caminho 2: backward se Inn. achado mas seq nao encontrado
                if inn_line >= 0 and seq_found is None:
                    for bk in range(i - 1, max(-1, i - 10), -1):
                        if PATTERN_PRODUTO.search(lines[bk]):
                            break
                        sm = PATTERN_SEQ.match(lines[bk])
                        if sm:
                            candidate = sm.group(1).strip()
                            if candidate not in page_sistemas_set:
                                seq_found = candidate
                                path_used = 2
                            break

                # Caminho 3: sem Inn. ou ainda sem seq - busca direta standalone
                if seq_found is None:
                    for j in range(i + 1, min(i + 30, n)):
                        if PATTERN_PRODUTO.search(lines[j]):
                            break
                        sm = PATTERN_SEQ.match(lines[j])
                        if sm:
                            candidate = sm.group(1).strip()
                            if candidate not in page_sistemas_set:
                                seq_found = candidate
                                path_used = 3
                                break
                    if seq_found is None:
                        for bk in range(i - 1, max(-1, i - 15), -1):
                            if PATTERN_PRODUTO.search(lines[bk]):
                                break
                            sm = PATTERN_SEQ.match(lines[bk])
                            if sm:
                                candidate = sm.group(1).strip()
                                if candidate not in page_sistemas_set:
                                    seq_found = candidate
                                    path_used = 3
                                break

                if seq_found is not None:
                    triplas[key] = seq_found
                    total_seq += 1
                    page_seqs += 1
                    log.info('PDF sistema=%s ref=%s seq=%s pag=%d caminho=%d',
                             sistema, ref, seq_found, page_num, path_used)
                else:
                    total_sem_seq += 1
                    log.warning('PDF sem-seq sistema=%s ref=%s pag=%d inn=%s',
                                sistema, ref, page_num, inn_line >= 0)
                    if len(diag_samples) < 20:
                        after = lines[max(0, i):min(i + 8, n)]
                        before = lines[max(0, i - 8):i]
                        diag_samples.append({'sis': sistema, 'ref': ref, 'pag': page_num, 'after_inn': after, 'before_prod': before})
            i += 1
        log.info('Pagina %d/%d: %d produtos | %d seq', page_num, total_pages, page_prod, page_seqs)

    log.info('PDF FIM: paginas=%d produtos=%d inn=%d seq=%d sem_seq=%d',
             total_pages, total_produto, total_inn, total_seq, total_sem_seq)

    return {'triplas': triplas, 'encontrados': encontrados, 'diag': diag_samples}
