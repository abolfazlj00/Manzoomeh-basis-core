from bclib import edge
from bson import ObjectId

from db import mongo_connention

# this is options for connecting to edge
options = {
    "server": "localhost:8080",
    "router": "client_source"
}

app = edge.from_options(options)


def remove_extraFields(dict):
    del dict["description"]  # it does not show the description of products in here
    if dict["inventory"] > 5:  # it does not show the inventory of products if that was too much (greater than 5)
        del dict["inventory"]
    return dict


# this function runs when the client sends a request
@app.client_source_action(
    app.equal("context.command.source", "basiscore"),
    app.equal("context.command.name", "client"))
def client_function(context: edge.ClientSourceContext):
    print("Client sent a request")
    return context.command.member


# display all products
@app.client_source_member_action(
    app.in_list("context.member.action", "show_all"),
    app.equal("context.command.name", "client")
)
def show_products(context: edge.ClientSourceMemberContext):
    print("Client sent a request for showing all products")
    database = mongo_connention.get_db()
    list_of_products = []
    page = int(context.member.get("page"))  # display 5 product in each page
    status = 1
    if context.member.get("asc"):  # -1 => descending ; 1 => ascending
        status = int(context.member["asc"])
    if context.member.get("sort") == "price":
        for product in database.product.find().sort("price", status):
            product["_id"] = str(product["_id"])
            list_of_products.append(remove_extraFields(product))
    elif context.member.get("sort") == "inventory":
        for product in database.product.find().sort("inventory", status):
            product["_id"] = str(product["_id"])
            list_of_products.append(remove_extraFields(product))
    else:
        for product in database.product.find():
            product["_id"] = str(product["_id"])
            list_of_products.append(remove_extraFields(product))
        if status == -1:
            list_of_products.reverse()

    return {
        f"products:<page:{page}>": list_of_products[(page - 1) * 5: (page * 5)]
    }


# display detail of a product
@app.client_source_member_action(
    app.in_list("context.member.action", "show_detail"),
    app.equal("context.command.name", "client")
)
def show_details(context: edge.ClientSourceMemberContext):
    print("Client sent a request for showing details of a product")
    database = mongo_connention.get_db()
    selectedProduct = database.product.find({"_id": ObjectId(context.member["id"])})[0]
    selectedProduct["_id"] = str(selectedProduct["_id"])
    return {
        "detail of this product": selectedProduct
    }


# update the order (add a product or remove)
@app.client_source_member_action(
    app.in_list("context.member.action", "+", "-"),
    app.equal("context.command.name", "client")
)
def update_order(context: edge.ClientSourceMemberContext):
    print("Client sent a data for updating products in order list")
    database = mongo_connention.get_db()
    username = context.member["username"]
    proId = context.member["id"]
    selectedProduct = database.product.find({"_id": ObjectId(proId)})[0]

    if context.member["action"] == "+":

        if selectedProduct["inventory"] == 0:
            return {
                "status": "false",
                "message": "This is more than the inventory of this product"
            }
        if len(list(database.order.find(
                {"username": username, "is_complete": False}))) == 0:
            create_order = {
                "username": username,
                "is_complete": False
            }
            database.order.insert_one(create_order)
        user_order = database.order.find({"username": username, "is_complete": False})[0]
        if len(list(database.orderItem.find(
                {"orderId": user_order["_id"], "productId": selectedProduct["_id"]}))) == 0:
            create_orderItem = {
                "orderId": user_order["_id"],
                "productId": selectedProduct["_id"],
                "quantity": 0
            }
            database.orderItem.insert_one(create_orderItem)
        user_orderItem = database.orderItem.find({"orderId": user_order["_id"], "productId": selectedProduct["_id"]})[
            0]

        new_quantity = user_orderItem["quantity"] + 1
        new_value = {"$set": {'quantity': new_quantity}}
        database.orderItem.update_one(user_orderItem, new_value)
        new_inventory = selectedProduct["inventory"] - 1
        new_value = {"$set": {'inventory': new_inventory}}
        database.product.update_one(selectedProduct, new_value)

        return {
            "status": "true",
            "message": f"You have {new_quantity} of this product now"
        }

    if len(list(database.order.find({"username": username, "is_complete": False}))) == 0:
        return {
            "status": "false",
            "message": "You dont have any order list"
        }
    user_order = database.order.find({"username": username, "is_complete": False})[0]
    if len(list(
            database.orderItem.find({"orderId": user_order["_id"], "productId": selectedProduct["_id"]}))) == 0 \
            or database.orderItem.find({"orderId": user_order["_id"], "productId": selectedProduct["_id"]})[0][
        "quantity"] == 0:
        return {
            "status": "false",
            "message": "You dont have this product in your order list"
        }
    user_orderItem = database.orderItem.find({"orderId": user_order["_id"], "productId": selectedProduct["_id"]})[
        0]

    new_quantity = user_orderItem["quantity"] - 1
    new_value = {"$set": {'quantity': new_quantity}}
    database.orderItem.update_one(user_orderItem, new_value)
    new_inventory = selectedProduct["inventory"] + 1
    new_value = {"$set": {'inventory': new_inventory}}
    database.product.update_one(selectedProduct, new_value)
    return {
        "status": "true",
        "message": f"You have {new_quantity} of this product now"
    }


# checkout the order
@app.client_source_member_action(
    app.equal("context.member.action", "checkout"),
    app.equal("context.command.name", "client")
)
def checkout(context: edge.ClientSourceMemberContext):
    print("Client sent a request for checkout the order")
    database = mongo_connention.get_db()

    username = context.member["username"]
    if len(list(database.order.find({"username": username, "is_complete": False}))) == 0:
        return {
            "status": "false",
            "message": "Order list not exist"
        }

    user_order = database.order.find({"username": username, "is_complete": False})[0]
    new_value = {"$set": {'is_complete': True}}
    database.order.update_one(user_order, new_value)

    return {
        "status": "true",
        "message": "Order list checked out"
    }


# run
app.listening()

'''
example of command for add the quantity of product: 

<basis core='dbsource' run='atclient' source='basiscore'  name='client' dmnid='' ownerpermit='' >
        <member action='+' username='ali' id='628e57a90a54f1d2e68d97ba'></member>
         
</basis>
..............................
example of command for mines the quantity of product: 

<basis core='dbsource' run='atclient' source='basiscore'  name='client' dmnid='' ownerpermit='' >
        <member action='-' username='ali' id='628e57a90a54f1d2e68d97ba'></member>
         
</basis>
..............................
example of command for checkout the order:

<basis core='dbsource' run='atclient' source='basiscore'  name='client' dmnid='' ownerpermit='' >
        <member action='checkout' username='ali'></member>
         
</basis>
'''
