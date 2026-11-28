# HushMonitor

API REST para cadastrar e monitorar endpoints HTTP. Construída com FastAPI, SQLAlchemy e Alembic.

## Estado atual

O núcleo da aplicação está completo e funcional:

**Autenticação**
- Registro e login com senha bcrypt e tokens JWT
- Todas as rotas de monitores exigem autenticação
- Usuários são completamente isolados entre si

**Monitores (CRUD)**
- Criar, listar (paginado), detalhar, atualizar parcialmente e excluir monitores
- Cada monitor tem URL, método HTTP, intervalo de verificação, timeout, status code esperado e webhook opcional
- `updated_at` atualizado automaticamente em toda alteração via `PATCH`

**Verificações**
- Verificação manual via `POST /monitors/{id}/check`
- Verificações automáticas em background — o scheduler verifica todos os monitores ativos respeitando o `interval_seconds` de cada um
- Histórico paginado de verificações com `GET /monitors/{id}/checks`
- Estatísticas de uptime e latência média com `GET /monitors/{id}/stats`

**Alertas via webhook**
- Cada monitor pode ter um `webhook_url` opcional
- O sistema dispara um `POST` para esse endpoint sempre que o estado muda: de saudável para falho (`monitor.down`) ou de falho para saudável (`monitor.recovered`)
- Falhas no webhook são logadas e nunca interrompem o ciclo de verificações

**Infraestrutura**
- Logging estruturado em JSON (arquivo `logs/app.log` + console)
- Request ID único (UUID) por requisição, retornado no header `X-Request-ID`
- Suíte de testes automatizados cobrindo auth, CRUD, isolamento multi-usuário, paginação e stats

## Tecnologias

- Python
- FastAPI
- Pydantic v2 + pydantic-settings
- SQLAlchemy 2.x
- Alembic
- SQLite
- APScheduler 3.x
- python-jose (JWT) + passlib (bcrypt)
- httpx
- python-json-logger
- pytest

## Estrutura

```text
app/
  core/
    config.py          # configurações via variáveis de ambiente
    security.py        # dependência JWT (get_current_user)
    logging.py         # setup de logging estruturado
  db/
    database.py        # engine, sessão e dependência get_db
    models.py          # modelos ORM: User, Monitor, MonitorCheck
  routers/
    auth.py            # rotas /auth/*
    monitors.py        # rotas /monitors/*
  schemas/
    auth.py            # contratos de entrada/saída de autenticação
    monitor.py         # contratos de entrada/saída de monitores
  services/
    auth.py            # hashing de senha, criação de JWT, CRUD de usuário
    checker.py         # execução da verificação HTTP via httpx
    scheduler.py       # loop automático de verificações (APScheduler)
    alerting.py        # detecção de transição de estado e envio de webhooks
  middleware/
    logging.py         # middleware de rastreamento por request
alembic/               # migrations
tests/                 # suíte de testes
main.py                # ponto de entrada da aplicação
```

Consulte a referência completa de endpoints em [docs/api.md](docs/api.md).

## Configuração local

Crie e ative o ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
pip install -r requirements.txt
```

Crie o arquivo `.env` a partir de `.env.example`:

```env
DATABASE_URL=sqlite:///./monitor.db
SECRET_KEY=sua-chave-secreta-com-pelo-menos-32-caracteres
ACCESS_TOKEN_EXPIRE_MINUTES=30
SCHEDULER_ENABLED=true
```

## Banco de dados e migrations

Aplicar todas as migrations:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

Ver a migration atualmente aplicada:

```powershell
.\.venv\Scripts\alembic.exe current
```

Criar uma nova migration após alterar os modelos:

```powershell
.\.venv\Scripts\alembic.exe revision --autogenerate -m "descricao da alteracao"
```

Revise sempre a migration gerada antes de aplicar `upgrade head`.

## Executar a API

```powershell
.\.venv\Scripts\fastapi.exe dev main.py
```

Depois, acesse:

- Documentação interativa: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Testes

```powershell
.\.venv\Scripts\pytest.exe
```

Os testes usam um SQLite temporário em memória e não alteram o arquivo `monitor.db`.
