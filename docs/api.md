# Referência da API

Base local: `http://127.0.0.1:8000`  
Documentação interativa: `http://127.0.0.1:8000/docs`

Todos os exemplos usam JSON. Os erros de validação retornam `422`.

## Health

### `GET /health`

Confirma que a aplicação está respondendo.

Resposta `200`:

```json
{
  "status": "ok"
}
```

## Monitores

### `POST /monitors`

Cria um monitor.

Corpo:

```json
{
  "name": "API principal",
  "url": "https://example.com/health",
  "method": "GET",
  "interval_seconds": 60,
  "timeout_seconds": 5,
  "is_active": true,
  "expected_status_code": 200
}
```

Os campos `method`, `interval_seconds`, `timeout_seconds`, `is_active` e
`expected_status_code` possuem valores padrão. A URL deve usar `http` ou
`https`. Métodos aceitos: `GET`, `HEAD`, `POST`, `PUT`, `PATCH`, `DELETE` e
`OPTIONS`.

Resposta `201`: o monitor criado, incluindo `id`, `created_at` e `updated_at`.

### `GET /monitors`

Lista todos os monitores em ordem crescente de ID.

Resposta `200`: uma lista de monitores.

### `GET /monitors/{monitor_id}`

Retorna um monitor pelo ID.

Resposta `200`: o monitor encontrado.  
Resposta `404`:

```json
{
  "detail": "Monitor not found"
}
```

### `PATCH /monitors/{monitor_id}`

Atualiza parcialmente um monitor. Envie somente os campos que devem mudar.

Corpo de exemplo:

```json
{
  "name": "API principal v2",
  "interval_seconds": 120,
  "is_active": false
}
```

Resposta `200`: o monitor atualizado.  
Resposta `404`: monitor não encontrado.

### `DELETE /monitors/{monitor_id}`

Remove um monitor.

Resposta `204`: sem corpo.  
Resposta `404`: monitor não encontrado.

## Verificações

### `POST /monitors/{monitor_id}/check`

Executa uma requisição HTTP usando as configurações do monitor e persiste o
resultado em `monitor_checks`.

Resposta `200`:

```json
{
  "id": 1,
  "monitor_id": 1,
  "status_code": 200,
  "response_time_ms": 182.45,
  "success": true,
  "error_type": null,
  "error_message": null,
  "checked_at": "2026-10-30T20:00:00"
}
```

Em timeout, `status_code` é `null`, `success` é `false` e `error_type` é
`"TIMEOUT"`. Outras falhas de conexão usam `"REQUEST_ERROR"`.

Resposta `404`: monitor não encontrado.

### `GET /monitors/{monitor_id}/checks`

Retorna o histórico de verificações, da mais recente para a mais antiga.

Parâmetros de query:

| Parâmetro | Padrão | Limites | Descrição |
| --- | --- | --- | --- |
| `page` | `1` | mínimo `1` | Página solicitada. |
| `page_size` | `20` | de `1` a `100` | Itens por página. |

Exemplo: `GET /monitors/1/checks?page=1&page_size=20`

Resposta `200`:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

Resposta `404`: monitor não encontrado.

### `GET /monitors/{monitor_id}/stats`

Calcula estatísticas a partir do histórico persistido.

Resposta `200`:

```json
{
  "monitor_id": 1,
  "total_checks": 3,
  "successful_checks": 2,
  "failed_checks": 1,
  "uptime_percentage": 66.67,
  "average_response_time_ms": 182.45
}
```

Para um monitor sem checks, o uptime é `0.0` e a latência média é `null`.
Resposta `404`: monitor não encontrado.

## Manutenção

Sempre que uma rota for criada, removida ou tiver seu contrato alterado,
atualize este arquivo na mesma alteração de código. Os testes em `tests/` devem
cobrir o novo comportamento antes do commit.
