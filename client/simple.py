import base64
import hashlib
import re
import uuid
from string import ascii_letters

from bclib import edge
from bson import ObjectId

from db import mongo_connention

# This is options for connecting to edge
options = {
    "server": "localhost:8000",
    "router": "client_source",
}

app = edge.from_options(options)


def remove_extraFields(dict):
    del dict["description"]  # it does not show the description of products in here
    if dict["inventory"] > 5:  # it does not show the inventory of products if that was too much (greater than 5)
        del dict["inventory"]
    return dict


# This is a function for check the validation of username
def validate_username(username):
    error = None
    for letter in username:
        if letter not in ascii_letters and letter != '_' and letter not in '0123456789':
            error = 'Please use only letters (a-z,A-Z), numbers, or underline for username'
    database = mongo_connention.get_db()
    if len(list(database.user.find({"username": username}))) != 0:
        error = 'This username is already exist'
    if error:
        return {
            "status": False,
            "error": error
        }
    return {
        "status": True
    }


# This is a function for check the validation of password
def validate_password(password):
    error = None
    if len(password) < 8:
        error = 'The password is too short. It must be at least 8 characters'
    for letter in password:
        if letter not in ascii_letters and letter not in '0123456789':
            error = 'Please use only letters (a-z,A-Z), numbers for password'
    if error:
        return {
            "status": False,
            "error": error
        }
    return {
        "status": True
    }


# This is a function for check the validation of phone
def validate_phone(phone):
    error = None
    regex_for_phone = r"^(\+98?)?{?(0?9[0-9]{9,9}}?)$"
    if not re.search(regex_for_phone, phone):
        error = "This phone number is not valid !"
    database = mongo_connention.get_db()
    if len(list(database.user.find({"username": phone}))) != 0:
        error = 'This phone number is already exist'
    if error:
        return {
            "status": False,
            "error": error
        }
    return {
        "status": True
    }


# This is a function for check the validation of email
def validate_email(email):
    error = None
    regex_for_email = r"^[a-zA-Z0-9]+[\._]?[a-zA-Z0-9]+[@]\w+[.]\w{2,3}$"
    if not re.search(regex_for_email, email):
        error = "This email is not valid !"
    if error:
        return {
            "status": False,
            "error": error
        }
    return {
        "status": True
    }


# this function runs when the client sends a request
@app.client_source_action(
    app.equal("context.command.source", "basiscore"),
    app.equal("context.command.name", "client"))
def client_function(context: edge.ClientSourceContext):
    print("Client sent a request")
    return context.command.member


# Register User
@app.client_source_member_action(
    app.in_list("context.member.action", "register"),
    app.equal("context.command.name", "client")
)
def register(context: edge.ClientSourceMemberContext):
    print("Client sent a request for register")
    database = mongo_connention.get_db()
    is_valid_username = validate_username(context.member["username"])
    is_valid_phone = validate_phone(context.member["phone"])
    is_valid_email = validate_email(context.member["email"])
    is_valid_password = validate_password(context.member["password"])
    if not is_valid_username["status"]:
        return {
            "status": "false",
            "message": is_valid_username["error"]
        }
    if not is_valid_phone["status"]:
        return {
            "status": "false",
            "message": is_valid_phone["error"]
        }
    if not is_valid_email["status"]:
        return {
            "status": "false",
            "message": is_valid_email["error"]
        }
    if not is_valid_password["status"]:
        return {
            "status": "false",
            "message": is_valid_password["error"]
        }
    salt = base64.urlsafe_b64encode(uuid.uuid4().bytes).hex()
    hashed_password = hashlib.sha512((context.member["password"] + salt).encode()).hexdigest()
    user_information = {
        "username": context.member["username"],
        "phone": context.member["phone"],
        "email": context.member["email"],
        "salt": salt,
        "password": hashed_password,
        "full_name": context.member.get("full_name", ''),
        "deleted": 0
    }
    database.user.insert_one(user_information)
    return {
        "status": "true",
        "message": "Registration completed."
    }


# Login User
@app.client_source_member_action(
    app.in_list("context.member.action", "login"),
    app.equal("context.command.name", "client")
)
def login_user(context: edge.ClientSourceMemberContext):
    username_input = context.member["username"]
    password_input = context.member["password"]
    print("Client sent a request for login")
    database = mongo_connention.get_db()
    user = list(database.user.find({"username": username_input}))
    if len(list(user)) == 0:
        return {
            "status": "false",
            "message": "Username is not correct"
        }
    valid_password = user[0]["password"]
    generated_password = hashlib.sha512((password_input + user[0]["salt"]).encode()).hexdigest()
    if valid_password != generated_password:
        return {
            "status": "false",
            "message": "Password is not correct"
        }
    return {
        "status": "true"
    }


# Display All Products
@app.client_source_member_action(
    app.in_list("context.member.action", "show_all"),
    app.equal("context.command.name", "client")
)
def show_products(context: edge.ClientSourceMemberContext):
    print("Client sent a request for showing all products")
    database = mongo_connention.get_db()
    list_of_products = []
    per_page = int(context.member["per_page"])
    page = int(context.member["page"])
    status = 1
    if context.member.get("asc"):  # -1 => descending ; 1 => ascending
        status = int(context.member["asc"])
    if context.member.get("sort") == "price":
        for product in database.product.find({"deleted": 0}).sort("price", status):
            product["_id"] = str(product["_id"])
            list_of_products.append(remove_extraFields(product))
    elif context.member.get("sort") == "inventory":
        for product in database.product.find({"deleted": 0}).sort("inventory", status):
            product["_id"] = str(product["_id"])
            list_of_products.append(remove_extraFields(product))
    else:
        for product in database.product.find({"deleted": 0}):
            product["_id"] = str(product["_id"])
            list_of_products.append(remove_extraFields(product))
        if status == -1:
            list_of_products.reverse()

    return {
        f"products:<page:{page}>": list_of_products[(page - 1) * per_page: (page * per_page)]
    }


# Display Details Of A Product
@app.client_source_member_action(
    app.in_list("context.member.action", "show_detail"),
    app.equal("context.command.name", "client")
)
def show_details(context: edge.RESTfulContext):
    print("Client sent a request for showing details of a product")
    database = mongo_connention.get_db()
    selectedProduct = database.product.find({"_id": ObjectId(context.url_segments.id)})[0]
    selectedProduct["_id"] = str(selectedProduct["_id"])
    return {
        "detail of this product": selectedProduct
    }


# Update The Order (Add A Product Or Remove)
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


# Checkout The Order
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


# Run
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
