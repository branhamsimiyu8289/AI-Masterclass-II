from flask import Flask, jsonify, request

app = Flask(__name__)

orders = [
    {"id": 1, "customer": "Hassan Traders", "product": "maize flour", "qty": 50, "status": "pending"},
    {"id": 2, "customer": "Otieno Wholesale", "product": "rice", "qty": 30, "status": "delivered"}
]

@app.route("/")
def index():
    return jsonify({"message": "Orders API is running", "orders": "/api/orders"})

@app.route("/api/orders", methods=["GET"])
def get_orders():
    return jsonify(orders)

@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    if not data or "customer" not in data or "product" not in data:
        return jsonify({"error": "customer and product are required"}), 400

    new_order = {
        "id": len(orders) + 1,
        "customer": data["customer"],
        "product": data["product"],
        "qty": data.get("qty", 1),
        "status": "pending"
    }
    orders.append(new_order)
    return jsonify(new_order), 201

@app.route("/api/orders/<int:order_id>", methods=["GET"])
def get_order(order_id):
    order = next((o for o in orders if o["id"] == order_id), None)
    if order:
        return jsonify(order)
    return jsonify({"error": "Order not found"}), 404

@app.route("/api/orders/<int:order_id>/status", methods=["PUT"])
def update_status(order_id):
    order = next((o for o in orders if o["id"] == order_id), None)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    data = request.get_json()
    order["status"] = data.get("status", order["status"])
    return jsonify(order)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)