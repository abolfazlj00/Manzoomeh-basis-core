from bclib import edge

from db import mongo_connection

# This is options for connecting to edge
options = {
    "server": "localhost:5000",
    "router": "restful"
}

app = edge.from_options(options)


# Add products
@app.restful_action()
def add_product(context: edge.RESTfulContext):
    print("Admin sent a data for adding products")
    database = mongo_connection.get_db()
    information = context.body
    products = []
    for item in information["products"]:
        new_product = {
            "name": item["name"],
            "inventory": int(item["inventory"]),
            "price": int(item["price"]),
            "description": item["description"],
            "deleted": 0,
        }
        products.append(new_product)
    database.product.insert_many(products)
    return {
        "message": "products added successfully"
    }


app.listening()
