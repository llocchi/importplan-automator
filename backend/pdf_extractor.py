import re
from typing import List, Dict, Tuple

PATTERN_PRODUTO = re.compile(r'(\d{4,6})\s*\|\s*([A-Z][A-Z0-9-]{2,15}|\d{1,3}[A-Z][A-Z0-9-]{0,12})')
PATTERN_INN     = re.compile(r'Inn\.|Mas\.|M[uU]lt\.', re.IGNORECASE)
PATTERN_SEQ     = re.compile(r'^\s*(\d{1,4})\s*$')


def extract_triplas(pages: List[str]) -> Dict:
    triplas: Dict[Tuple[str, str], str] = {}
    encontrados: Dict[Tuple[str, str], int] = {}   # no PDF: key -> pagina
    total_pages = len(pages)
    total_produto = 0
    total_inn = 0
    total_seq = 0
    diag_samples = []

    for page_num, page_text in enumerate(pages, start=1):
        lines = page_text.split('\n')
        n = len(lines)
        # Coleta todos os codigos SISTEMA da pagina para evitar falso positivo
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

                # --- busca sequencial: forward via Inn. ---
                seq_found = None
                inn_line  = -1
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
                                    break
                        break

                # --- fallback: busca backward a partir da linha do produto ---
                if inn_line >= 0 and seq_found is None:
                    for bk in range(i - 1, max(-1, i - 10), -1):
                        if PATTERN_PRODUTO.search(lines[bk]):
                            break   # chegou no produto anterior, para
                        sm = PATTERN_SEQ.match(lines[bk])
                        if sm:
                            candidate = sm.group(1).strip()
                            if candidate not in page_sistemas_set:
                                seq_found = candidate
                            break

                if inn_line >= 0 and seq_found is not None:
                    triplas[key] = seq_found
                    total_seq += 1
                    page_seqs += 1
                elif inn_line >= 0 and len(diag_samples) < 10:
                    after = lines[inn_line:min(inn_line + 8, n)]
                    before = lines[max(0, i - 8):i]
                    diag_samples.append({
                        'sis': sistema, 'ref': ref, 'pag': page_num,
                        'after_inn': after, 'before_prod': before
                    })
            i += 1
        if page_prod > 0:
            print(f'[EXTR] p{page_num}/{total_pages}: {page_prod} prod | {page_seqs} seq')

    print(f'[EXTR] FIM: pages={total_pages} prod={total_produto} inn={total_inn} seq={total_seq}')
    if diag_samples:
        print('[EXTR] AMOSTRAS INN-SEM-SEQ:')
        for d in diag_samples[:5]:
            print(f"  pag={d['pag']} sys={d['sis']} ref={d['ref']}")
            print(f"    before_prod={d['before_prod']}")
            print(f"    after_inn  ={d['after_inn']}")

    return {'triplas': triplas, 'encontrados': encontrados, 'diag': diag_samples}