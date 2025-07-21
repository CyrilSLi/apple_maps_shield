# apple_maps_shield

A userscript or web server & app that generates highway shields used in Apple Maps with arbitrary text.

Use this project in one of two ways below:

## Userscript

Install the userscript [here](https://greasyfork.org/en/scripts/543159-apple-maps-custom-shields).

## Web server & app

### Installation & Usage

```
pip install dist/apple_maps_shield-1.0.0-py3-none-any.whl
apple-maps-shield [PORT]
```

or

```
pip install -r requirements.txt
python app.py [PORT]
```

The web app is available at the computer's local IP address (and [localhost](http://localhost:5033)), port 5033 or specified in the argument.