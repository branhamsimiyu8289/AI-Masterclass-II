from flask import Flask, jsonify, request

app = Flask(__name__)

balances = {
    "Amina Wanjiku": 12500,
    "Brian Kiptoo": 8300,
    "Chebet Jepkosgei": 21400,
    "David Mwangi": 5600,
    "Faith Naliaka": 17250,
}


@app.route("/")
def home():
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Eldoret Hardware | Customer Balances</title>
        <style>
          body { font: 16px system-ui, sans-serif; margin: 3rem auto; max-width: 38rem; padding: 0 1rem; color: #17231d; }
          h1 { color: #176b45; }
          form { display: flex; flex-wrap: wrap; gap: .6rem; }
          input, button { font: inherit; padding: .7rem; }
          input { flex: 1; min-width: 14rem; }
          button { background: #176b45; border: 0; color: white; cursor: pointer; }
          #result { margin-top: 1.25rem; font-weight: 600; }
        </style>
      </head>
      <body>
        <h1>Eldoret Hardware</h1>
        <p>Search for a customer to check their outstanding balance.</p>
        <form id="search-form">
          <label for="customer-name">Customer name</label>
          <input id="customer-name" name="name" required autocomplete="name">
          <button type="submit">Check balance</button>
        </form>
        <p id="result" aria-live="polite"></p>
        <script>
          const form = document.querySelector("#search-form");
          const result = document.querySelector("#result");
          form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const name = new FormData(form).get("name");
            result.textContent = "Looking up balance...";
            try {
              const response = await fetch(`/api/balance?name=${encodeURIComponent(name)}`);
              const data = await response.json();
              result.textContent = response.ok
                ? `${data.customer} owes KES ${data.balance.toLocaleString()}.`
                : data.error;
            } catch {
              result.textContent = "Could not retrieve the balance. Please try again.";
            }
          });
        </script>
      </body>
    </html>
    """


@app.route("/api/balance")
def get_balance():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Please provide a customer name using the 'name' query parameter."}), 400

    customer = next((known_name for known_name in balances if known_name.casefold() == name.casefold()), None)
    if customer is None:
        return jsonify({"error": f"No balance found for '{name}'."}), 404

    return jsonify({"customer": customer, "balance": balances[customer], "currency": "KES"})


if __name__ == "__main__":
    app.run(debug=True)
