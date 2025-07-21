# Built-in modules:
import io, logging, re, subprocess, sys
from base64 import b64encode
from urllib import parse

# Third-party modules:
from flask import Flask, request, jsonify, send_file
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

browser = subprocess.run (["playwright", "install", "--list"], capture_output = True)
browser.check_returncode ()
if "chromium_headless_shell" not in browser.stdout.decode ("utf-8"):
    if input ("Playwright chromium-headless-shell is not installed. Install now? (Y/n) ").lower () != "y":
        raise SystemExit
    browser = subprocess.run (["playwright", "install", "chromium-headless-shell"])
    browser.check_returncode ()

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
    with page.expect_request (lambda req: "reportAnalytics" in req.url or "analyticsStatus" in req.url) as _:
        page.goto (request.args ["url"])
    page.close ()
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
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Apple Maps highway shield generator</title>
    <meta charset="utf-8">
    <script src="https://cdn.jsdelivr.net/npm/brython@3/brython.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/brython@3/brython_stdlib.min.js"></script>
    <style>
        * {
            margin: 0px;
            padding: 0px;
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
            -webkit-appearance: none;
            -moz-appearance: none;
            line-height: normal;
            font-weight: normal;
            text-decoration: none;
            border: none;
        }
        p, h1, h2, h3, h4, h5, h6, input, button {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
        p, input, button {
            font-size: 20px;
        }
        h1 {
            font-size: 36px;
            font-weight: bold;
        }
        a, a:visited {
            color: blue;
            text-decoration: underline;
        }
        input[type="text"], button {
            color: black;
            padding: 5px 7px;
            border-radius: 0px;
            background-color: #f8f8f8;
            border: 1px solid gray;
        }
        #url[url-valid="true"] {
            background-color: #bfffbf;
        }
        ::placeholder {
            color: gray;
            opacity: 1;
        }
        ::-ms-input-placeholder {
            color: gray;
        }
        .row, label, #status {
            margin: 0px 10px;
        }
        div.row {
            display: flex;
            flex-direction: row;
            align-items: center;
        }
        input.row {
            flex: 1;
            min-width: 0;
        }
        input[type="radio"] {
            position: absolute;
            opacity: 0;
            width: 0;
            height: 0;
        }
        input[type="radio"] + img {
            border-radius: 15px;
            padding: 10px;
            height: 160px;
            border: 5px solid #bfbfbf;
        }
        input[type="radio"]:checked + img {
            border-color: black;
        }
        #shield {
            margin: 20px;
            height: 240px;
        }
        #styles {
            overflow-x: scroll;
            padding-bottom: 20px;
        }
    </style>
</head>
<body onload="brython(0)">
    <noscript>
        <p>JavaScript is required to use this website.</p>
    </noscript>
    <h1>Apple Maps highway shield generator</h1>
    <p>1. Visit <a href="https://maps.apple.com/" target="_blank">Apple Maps</a> and navigate to an area with your desired highway shield visible.</p>
    <p>2. Paste the full URL below (the input box will turn green if the URL is valid).</p>
    <div class="row">
        <button class="row" id="search">Search</button>
        <input class="row" id="url" type="text" placeholder="https://maps.apple.com/frame?center=" />
        <p id="status">Invalid</p>
    </div>
    <p>3. Click "Search" and select the style of shield you want below.</p>
    <div class="row" id="styles">
        <label>
            <input type="radio" value="null" name="null" disabled />
            <img src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==">
        </label>
    </div>
    <p>4. Enter text and click "Generate" (click "Search" to refresh the API key if shield does not display).</p>
    <div class="row">
        <button class="row" id="generate">Generate</button>
        <input class="row" id="text" type="text" placeholder="Shield text" />
    </div>
    <img id="shield" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==">
    <script type="text/python">
        from browser import ajax, document, html, window
        import re
        access_key, selected = None, None
        def validate (ev):
            regex = r"(https:\/\/)?maps\.apple\.com\/frame\?center=-?[0-9]+\.[0-9]+(%2C|,)-?[0-9]+\.[0-9]+&span=-?[0-9]+\.[0-9]+(%2C|,)-?[0-9]+\.[0-9]+"
            if re.fullmatch (regex, document ["url"].value):
                document ["url"].attrs ["url-valid"] = "true"
                document ["status"].textContent = "Valid"
            else:
                if "url-valid" in document ["url"].attrs:
                    del document ["url"].attrs ["url-valid"]
                document ["status"].textContent = "Invalid"
        document ["url"].bind ("input", validate)

        def search (ev):
            if "url-valid" not in document ["url"].attrs:
                return
            del document ["url"].attrs ["url-valid"]
            document ["url"].attrs ["disabled"] = "disabled"
            document ["status"].textContent = "Searching..."
            def set_selected (ev):
                ev.stopPropagation ()
                global selected
                if ev.target.checked:
                    selected = ev.target.value
            def complete (res):
                global selected
                validate (None)
                del document ["url"].attrs ["disabled"]
                global access_key, selected
                access_key = res.json ["access_key"]
                document ["styles"].clear ()
                for i in res.json ["shields"]:
                    radio = html.INPUT (type = "radio", name = "style", value = i ["id"], checked = i ["id"] == selected)
                    radio.bind ("change", set_selected)
                    document ["styles"] <= html.LABEL ((radio, html.IMG (src = i ["image"])))
            ajax.get ("/styles?url=" + window.encodeURIComponent(document["url"].value), oncomplete = complete, cache = True)
        document ["search"].bind ("click", search)

        def generate (ev):
            global access_key, selected
            if (not access_key) or (not selected):
                return
            document ["shield"].attrs ["src"] = "/shield?text={}&id={}&variant={}&access_key={}".format (*(
                window.encodeURIComponent (i) for i in (document ["text"].value, *selected.split (), access_key)
            ))
        document ["generate"].bind ("click", generate)

        document ["url"].bind ("keyup", lambda ev: (ev.preventDefault (), search(ev)) if ev.key == "Enter" else None)
        document ["text"].bind ("keyup", lambda ev: (ev.preventDefault (), generate(ev)) if ev.key == "Enter" else None)
    </script>
</body>
</html>
    """

def main ():
    server = make_server ("0.0.0.0", sys.argv [1] if len (sys.argv) > 1 else 5033, app)
    logging.getLogger ("werkzeug").setLevel (logging.ERROR)
    try:
        server.serve_forever ()
    except:
        if context:
            context.close ()

if __name__ == "__main__":
    main ()