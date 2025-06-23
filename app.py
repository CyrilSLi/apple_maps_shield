# Built-in modules:
import io, logging, re
from base64 import b64encode
from urllib import parse

# Third-party modules:
from flask import Flask, request, jsonify, send_file
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

app = Flask (__name__)
context, playwright = None, None
playwright = sync_playwright ().start ()
def get_context ():
    global context, playwright
    if context:
        context.close ()
    context = playwright.chromium.launch ().new_context (**playwright.devices ["Desktop Chrome"])

@app.route ("/styles", methods = ["GET"])
def styles ():
    global context
    if not re.fullmatch (r"(https:\/\/)?maps\.apple\.com\/frame\?center=-?[0-9]+\.[0-9]+(%2C|,)-?[0-9]+\.[0-9]+&span=-?[0-9]+\.[0-9]+(%2C|,)-?[0-9]+\.[0-9]+", request.args.get ("url", "")):
        return jsonify ({})
    shields, access_key, styles = [], None, set ()
    get_context ()
    def onrequest (req):
        global context
        nonlocal access_key, shields, styles
        if "v1/shield" in req.url:
            parsed = parse.urlparse (req.url)
            params = parse.parse_qs (parsed.query)
            if all (k in params for k in ("id", "variant", "scale", "sizeGroup")):
                style_id = f"{params ['id'] [0]} {params ['variant'] [0]}"
                if style_id in styles:
                    return
                styles.add (style_id)
                params ["scale"] = [3]     # Max scale
                params ["sizeGroup"] = [7] # Max size group
                page = context.new_page ()
                img = page.goto (parsed._replace (query = parse.urlencode (params, doseq = True)).geturl ())
                shields.append ({
                    "id": style_id,
                    "image": "data:image/png;base64," + b64encode (img.body ()).decode ("utf-8"),
                })
                page.close ()
            if params.get ("accessKey"):
                access_key = params ["accessKey"] [0]
    page = context.new_page ()
    page.on ("request", onrequest)
    with page.expect_request (lambda req: "map-type-" in req.url) as _:
        page.goto (request.args ["url"])
    return jsonify ({
        "shields": shields,
        "access_key": access_key,
    })

@app.route ("/shield", methods = ["GET"])
def shield ():
    global context
    if not context: # Reuse existing context if available
        get_context ()
    if not all (k in request.args for k in ("id", "text", "access_key")):
        return jsonify ({})
    id, text, variant, access_key = (parse.quote (request.args.get (k, "0"), safe = "") for k in ("id", "text", "variant", "access_key"))
    page = context.new_page ()
    img = page.goto ("https://cdn.apple-mapkit.com/md/v1/shield?id={}&text={}&scale=3&variant={}&sizeGroup=7&accessKey={}".format (id, text, variant, access_key))
    return send_file (io.BytesIO (img.body ()), mimetype = "image/png")

@app.route ("/", methods = ["GET"])
def index ():
    return send_file ("index.html")

if __name__ == "__main__":
    server = make_server ("0.0.0.0", 5033, app)
    logging.getLogger ("werkzeug").setLevel (logging.ERROR)
    try:
        server.serve_forever ()
    except:
        if context:
            context.close ()