# Orders API

A small Flask API for listing, creating, and looking up sample orders. Orders
are stored in memory and reset when the server restarts.

## Run

From this folder, install the dependency and start the server:

```powershell
python -m pip install -r requirements.txt
python restapi.py
```

The server listens on `http://127.0.0.1:5000`.

## Endpoints

- `GET /` reports that the API is running.
- `GET /api/orders` returns all orders.
- `POST /api/orders` creates an order. Send JSON with `customer` and `product`;
  `qty` is optional and defaults to `1`.
- `GET /api/orders/<id>` returns one order.
- `PUT /api/orders/<id>/status` updates an order's status.

Example requests:

```powershell
curl.exe http://127.0.0.1:5000/api/orders

curl.exe -X POST http://127.0.0.1:5000/api/orders `
  -H "Content-Type: application/json" `
  -d '{"customer":"Baraka Stores","product":"sugar","qty":20}'
```
