# Email Validator API

Authenticated HTTP API for Grok (or any client) to verify one or more emails.

## Setup

```bash
# from repo root
pip install -e .
pip install -r api/requirements.txt
cp api/.env.example api/.env
# edit api/.env and set EMAIL_API_SECRET to a long random value
python api/run.py
```

Server listens on `http://0.0.0.0:8080` by default.

## Auth

Send the secret as either:

- `Authorization: Bearer <EMAIL_API_SECRET>`
- `X-API-Key: <EMAIL_API_SECRET>`

## Endpoints

### `GET /health`

No auth. Returns `{"status":"ok"}`.

### `GET /v1/verify?emails=a@b.com,c@d.com`

```bash
curl -s "http://127.0.0.1:8080/v1/verify?emails=alice@example.com,bad@@x,bob@gmail.com" \
  -H "Authorization: Bearer YOUR_SECRET"
```

### `POST /v1/verify`

Comma-separated string:

```bash
curl -s http://127.0.0.1:8080/v1/verify \
  -H "Authorization: Bearer YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"emails":"alice@example.com, bob@gmail.com"}'
```

Or a JSON array:

```bash
curl -s http://127.0.0.1:8080/v1/verify \
  -H "X-API-Key: YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"emails":["alice@example.com","bob@gmail.com"],"check_deliverability":true}'
```

### Example response

```json
{
  "count": 2,
  "valid_count": 1,
  "invalid_count": 1,
  "results": [
    {"email": "alice@example.com", "valid": true, "normalized": "alice@example.com", "error": null},
    {"email": "bad@@x", "valid": false, "normalized": null, "error": "The email address is not valid..."}
  ]
}
```

## Grok / tool config

Point Grok at:

- URL: `https://YOUR_HOST/v1/verify`
- Method: `POST` (or `GET` with `?emails=`)
- Header: `Authorization: Bearer <EMAIL_API_SECRET>`
- Body: `{"emails":"<comma-separated emails>"}`

This checks syntax + domain MX (deliverability). It does not prove a mailbox exists.
