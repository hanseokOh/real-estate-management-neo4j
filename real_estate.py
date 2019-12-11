from json import dumps
from flask import Flask, g, Response, request
from neo4j import GraphDatabase, basic_auth

app = Flask(__name__, static_url_path='/static/')

user = 'neo4j'
password = 'neo4j'

driver = GraphDatabase.driver('bolt://localhost:', auth=basic_auth(user, password))

def get_db():
    if not hasattr(g, 'neo4j_db'):
        g.neo4j_db = driver.session()
    return g.neo4j_db


@app.teardown_appcontext
def close_db(error):
   if hasattr(g, 'neo4j_db'):
        g.neo4j_db.close()

@app.route("/")
def get_index():
    return app.send_static_file('real_estate.html')

def serialize_product(product):
    return {
        'address': product['address'],
        'size': product['size'],
        'type': product['type'],
        'PriceMonth': product['PriceMonth'],
        'floor': product['floor'],
        'parking': product['parking'],
        'elevator': product['elevator'],
        'duration': product['duration']
    }
def serialize_consumer(consumer):
    return {
        'name': consumer[0],
        # 'age' : consumer[1],
        # 'email': consumer[2],
        # 'area_interest': consumer[3],
        'relation': consumer[1]
        #'email': consumer['email'],
        #'area_interest':consumer['area_interest']
    }
@app.route("/graph")
def get_graph():
    db = get_db()
    results = db.run("MATCH (product:Product)<-[:INTERESTED_IN]-(consumer:Consumer) "
             "RETURN DISTINCT product.address as product, collect(consumer.name) as consumer "
             "LIMIT {limit}", {"limit": request.args.get("limit", 100)})
    nodes = []
    rels = []
    i = 0
    for record in results:
        print(record)
        nodes.append({"address": record["product"], "label": "product"})
        target = i
        i += 1
        for name in record['consumer']:
            consumer = {"address": name, "label": "consumer"}
            try:
                source = nodes.index(consumer)
            except ValueError:
                nodes.append(consumer)
                source = i
                i += 1
            rels.append({"source": source, "target": target})
    return Response(dumps({"nodes": nodes, "links": rels}), mimetype="application/json")



@app.route("/search")
def get_search():
    try:
        q = request.args["q"]
    except KeyError:
        return []
    else:
        db = get_db()
        results = db.run("MATCH (product:Product) "
                 "WHERE product.address =~ {address} "
                 "RETURN DISTINCT product", {"address": "(?i).*" + q + ".*"}
        )
        print(results)
        return Response(dumps([serialize_product(record['product']) for record in results]), mimetype="application/json")




@app.route("/product/<address>")
def get_product(address):
    print(address)
    db = get_db()

    results = db.run("MATCH (product:Product{address:{address}}) " 
                    "OPTIONAL MATCH (product)<-[r]-(consumer:Consumer) "
                    "RETURN DISTINCT product.address as address, collect([consumer.name, head(split(lower(type(r)),'_'))]) as consumer "
                    "LIMIT 1", {"address": address})
    result = results.single()
    print(result)
    return Response(dumps({"address": result['address'], "consumer": [serialize_consumer(member) for member in result['consumer']]}))

if __name__ == '__main__':
    app.run(port=8080,debug=True)
