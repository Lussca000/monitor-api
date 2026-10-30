# HushMonitor

API para cadastrar e monitorar endpoints HTTP. O projeto está sendo construído
incrementalmente com FastAPI, SQLAlchemy e Alembic.

## Estado atual

- endpoint `GET /health`;
- modelo `Monitor`;
- banco de dados SQLite local;
- migration inicial que cria a tabela `monitors`;
- schemas Pydantic para criar, atualizar e serializar monitores.

As rotas CRUD de monitores ainda serão implementadas.

## Tecnologias

- Python;
- FastAPI;
- Pydantic;
- SQLAlchemy 2.x;
- Alembic;
- SQLite.

## Estrutura

```text
app/
  core/config.py       # configurações da aplicação
  db/database.py       # engine, sessão e dependência get_db
  db/models.py         # modelos SQLAlchemy
  schemas/monitor.py   # contratos de entrada e saída da API
alembic/               # migrations
main.py                # aplicação FastAPI
```

## Configuração local

Crie e ative o ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependências utilizadas pelo projeto:

```powershell
pip install -r requirements.txt
```

Crie o arquivo `.env` a partir de `.env.example`:

```env
DATABASE_URL=sqlite:///./monitor.db
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

Criar uma nova migration depois de alterar os modelos:

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

Execute a suíte automatizada com:

```powershell
.\.venv\Scripts\pytest.exe
```

Os testes usam um SQLite temporário e não alteram o arquivo local `monitor.db`.
