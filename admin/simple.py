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
    app.equal("context.member.action", "add")
)
def add_product(context: edge.ClientSourceMemberContext):
    print("Admin sent a data for adding products")
    database = mongo_connention.get_db()
    product_collection = database["product"]
    for pro_data in context.data:
        del pro_data["action"]
        pro_data["inventory"] = int(pro_data["inventory"])
        product_collection.insert_one(pro_data)
    return True


# delete a product
@app.client_source_member_action(
    app.equal("context.member.action", "delete")
)
def delete_product(context: edge.ClientSourceMemberContext):
    print("Admin sent a data for deleting a product")
    database = mongo_connention.get_db()
    product_collection = database["product"]
    query = {"_id": ObjectId(context.data[0]["id"])}
    product_collection.delete_one(query)
    return True


# list of products
@app.client_source_member_action(
    app.equal("context.member.action", "show_all")
)
def show_products(context: edge.ClientSourceMemberContext):
    print("Admin sent a data for showing all product")
    database = mongo_connention.get_db()
    product_collection = database["product"]
    list_of_products = []
    for product in product_collection.find():
        product["_id"] = str(product["_id"])
        list_of_products.append(product)
    return {"products": list_of_products}


# run
app.listening()

'''
example of command for add a product: 

<basis core='dbsource' run='atclient' source='basiscore' name='admin' dmnid='' ownerpermit='' >
        <member action='add' name='product1' price='price1' inventory='20'></member>
        
</basis>
..............................
example of command for delete a product: 

<basis core='dbsource' run='atclient' source='basiscore'  name='admin' dmnid='' ownerpermit='' >
        <member action='delete' id='628d117975241281ae40da61'></member>
        
</basis>

'''
