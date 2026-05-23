import os, time, logging
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from pdf_extractor import extract_triplas
from xlsx_updater import update_xlsx
from logger_setup import get_logger, LOG_DIR

log = get_logger('tuut.api')
app = FastAPI(title='Catalog Import Processor API', version='1.0.0')

FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', 'http://localhost')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, 'http://localhost', 'http://localhost:5500', 'http://127.0.0.1:5500', 'null', 'https://llocchi.github.io'],
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['Content-Type', 'Accept'],
    max_age=600,
)


class ProcessRequest(BaseModel):
    pdf_pages:   List[str]
    xlsx_base64: str
    pdf_name:    str = 'catalogo.pdf'
    xlsx_name:   str = 'importplan.xlsx'

    @field_validator('pdf_pages')
    @classmethod
    def pages_not_empty(cls, v):
        if not v: raise ValueError('pdf_pages nao pode ser vazio')
        return v

    @field_validator('xlsx_base64')
    @classmethod
    def b64_not_empty(cls, v):
        if not v or len(v) < 10: raise ValueError('xlsx_base64 invalido')
        return v


@app.get('/')
def root(): return {'message': 'Catalog Import Processor API', 'version': '1.0.0'}

@app.get('/health')
def health(): return {'status': 'ok'}


@app.post('/process')
async def process(req: ProcessRequest):
    MAX_BYTES = 60 * 1024 * 1024
    payload_size = sum(len(p) for p in req.pdf_pages) + len(req.xlsx_base64)
    if payload_size > MAX_BYTES:
        raise HTTPException(413, 'Payload excede 60 MB')

    log.info('REQUEST: pdf=%s xlsx=%s paginas=%d payload_kb=%d',
             req.pdf_name, req.xlsx_name, len(req.pdf_pages), payload_size // 1024)

    start = time.time()
    try:
        extract_result = extract_triplas(req.pdf_pages)
        triplas    = extract_result['triplas']
        encontrados = extract_result.get('encontrados', set())
        diag_samples = extract_result.get('diag', [])
        print(f'[API] TRIPLAS extraidas: {len(triplas)}')

        if not triplas:
            print(f'[API] ERRO: nenhum sequencial em {len(req.pdf_pages)} paginas')
            raise HTTPException(422, 'Nenhum sequencial encontrado no PDF. Verifique se o catalogo contem texto extraivel e o formato SISTEMA | REF.')

        result = update_xlsx(req.xlsx_base64, triplas, encontrados, req.xlsx_name)
    except HTTPException:
        raise
    except ValueError as exc:
        log.error('ValueError: %s', exc)
        raise HTTPException(422, str(exc))
    except Exception as exc:
        log.error('Erro inesperado: %s', exc, exc_info=True)
        raise HTTPException(500, 'Erro interno ao processar. Tente novamente.')

    duration = round(time.time() - start, 2)
    result['report']['duration_seconds'] = duration
    result['report']['pdf_name']  = req.pdf_name
    result['report']['xlsx_name'] = req.xlsx_name
    result['report']['triplas_found'] = len(triplas)
    sample = [{'sistema': k[0], 'ref': k[1], 'seq': v} for k, v in list(triplas.items())[:10]]
    result['report']['triplas_sample'] = sample
    result['report']['diag_inn_sem_seq'] = diag_samples[:5]

    log.info('CONCLUIDO: atualizadas=%d nao_encontradas=%d duracao=%ss',
             result['report']['updated'], len(result['report']['not_found']), duration)

    # Flush handlers e lê app.log para retornar ao frontend
    for h in logging.getLogger('tuut').handlers:
        h.flush()
    try:
        log_path = LOG_DIR / 'app.log'
        result['log_content'] = log_path.read_text(encoding='utf-8') if log_path.exists() else ''
    except Exception:
        result['log_content'] = ''

    return result