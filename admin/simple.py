from bclib import edge
from bson import ObjectId

from db import mongo_connention

# this is options for connecting to edge
options = {
    "server": "localhost:8080",
    "router": "client_source"
}

app = edge.from_options(options)


# this function runs when the client sends a request
@app.client_source_action(
    app.equal("context.command.source", "basiscore"),
    app.equal("context.command.name", "admin"))
def admin_function(context: edge.ClientSourceContext):
    print("Admin sent a request")
    return context.command.member


# add products
@app.client_source_member_action(
    app.equal("context.member.action", "add"),
    app.equal("context.command.name", "admin")
)
def add_product(context: edge.ClientSourceMemberContext):
    print("Admin sent a data for adding products")
    database = mongo_connention.get_db()
    product_collection = database["product"]
    new_product = {
        "name": context.member["name"],
        "inventory": int(context.member["inventory"]),
        "price": int(context.member["price"]),
        "description": context.member["description"],
        "deleted": 0,
    }
    product_collection.insert_one(new_product)
    return {
        "message": "This product added successfully"
    }


# delete a product
@app.client_source_member_action(
    app.equal("context.member.action", "delete"),
    app.equal("context.command.name", "admin")
)
def delete_product(context: edge.ClientSourceMemberContext):
    print("Admin sent a data for deleting a product")
    database = mongo_connention.get_db()
    product_collection = database["product"]
    if len(list(product_collection.find({"_id": ObjectId(context.member["id"])}))) == 0:
        return {
            "status": "false",
            "message": "This product does not exist"
        }
    selected_product = product_collection.find({"_id": ObjectId(context.member["id"])})[0]
    new_value = {"$set": {'deleted': 1}}
    product_collection.update_one(selected_product, new_value)
    return {
        'message': f'{selected_product["name"]} with id={context.member["id"]} deleted.'
    }


# update a product
@app.client_source_member_action(
    app.equal("context.member.action", "update"),
    app.equal("context.command.name", "admin")
)
def update_product(context: edge.ClientSourceMemberContext):
    print("Admin sent a data for updating a product")
    database = mongo_connention.get_db()
    product_collection = database["product"]
    product_id = ObjectId(context.member["id"])
    if len(list(product_collection.find({"_id": ObjectId(context.member["id"])}))) == 0:
        return {
            "status": "false",
            "message": "This product does not exist"
        }
    selected_product = product_collection.find({"_id": product_id})[0]
    update_type = context.member["type"]  # name/price/inventory/description
    updated_value = context.member["value"]  # new value for the update_type
    if update_type == "price" or update_type == "inventory":
        updated_value = int(updated_value)
    new_value = {"$set": {update_type: updated_value}}
    product_collection.update_one(selected_product, new_value)
    return {
        "message": f"The {update_type} of this product updated."
    }


# list of products
@app.client_source_member_action(
    app.equal("context.member.action", "show_all"),
    app.equal("context.command.name", "admin")
)
def show_products(context: edge.ClientSourceMemberContext):
    print("Admin sent a request for showing all products")
    database = mongo_connention.get_db()
    product_collection = database["product"]
    list_of_products = []
    for product in product_collection.find():
        product["_id"] = str(product["_id"])
        list_of_products.append(product)
    return {
        "products": list_of_products
    }


# run
app.listening()

'''
example of command for add a product:

<basis core='dbsource' run='atclient' source='basiscore' name='admin' dmnid='' ownerpermit='' >
        <member action='add' name='product1' price='1000' inventory='20' description='some text'></member>
        <member action='add' name='product2' price='2000' inventory='10' description='some text'></member>
</basis>
..............................

example of command for delete a product: 

<basis core='dbsource' run='atclient' source='basiscore'  name='admin' dmnid='' ownerpermit='' >
        <member action='delete' id='628d117975241281ae40da61'></member>
</basis>
..............................

example of command for update a product: 

<basis core='dbsource' run='atclient' source='basiscore'  name='admin' dmnid='' ownerpermit='' >
        <member action='update' id='628d117975241281ae40da61' type='price' value='50000'></member>
        <member action='update' id='628d117975241281ae40da61' type='inventory' value='50'></member>
</basis>
..............................

example of command for show all products: 

<basis core='dbsource' run='atclient' source='basiscore'  name='admin' dmnid='' ownerpermit='' >
        <member action='show_all'></member>
</basis>
'''
