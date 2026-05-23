# tuut — ImportPlan Automator

> Ferramenta web interna que processa catalogos PDF e preenche automaticamente a coluna **No. Seq.** na planilha ImportPlan.

## Como usar

1. Acesse a URL do GitHub Pages
2. Selecione o catalogo PDF (qualquer tamanho - processado no browser)
3. Selecione a planilha ImportPlan `.xlsx`
4. Clique em **Processar**
5. O XLSX atualizado e baixado automaticamente

## Estrutura

```
catalog-import-processor/
├── frontend/            # GitHub Pages
│   ├── index.html
│   ├── style.css
│   └── app.js
├── backend/             # Render.com (FastAPI)
│   ├── main.py
│   ├── pdf_extractor.py
│   ├── xlsx_updater.py
│   ├── requirements.txt
│   └── render.yaml
└── .github/workflows/
    └── deploy-frontend.yml
```

## Deploy

### Frontend — GitHub Pages
1. Va em **Settings > Pages > Source: GitHub Actions**
2. Qualquer push em `main/frontend/` dispara o deploy automaticamente

### Backend — Render.com
1. Crie um novo **Web Service** no Render.com
2. Variavel de ambiente: `FRONTEND_ORIGIN` = `https://SEU-USUARIO.github.io`
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Configurar URL do backend
Edite `frontend/app.js` linha 7:
```js
const API_URL = 'https://seu-app-id.onrender.com';
```

## Dev local

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# Abrir frontend/index.html com Live Server
```

## Stack

| Camada | Tecnologia |
|--------|------------|
| Frontend | HTML5 + CSS3 + Vanilla JS + PDF.js |
| Backend | Python 3.11 + FastAPI + openpyxl |
| Frontend Hosting | GitHub Pages (gratuito) |
| Backend Hosting | Render.com free tier |
| CI/CD | GitHub Actions |

---
*Tuut · Uso interno · Sem login · Sem armazenamento de dados*
