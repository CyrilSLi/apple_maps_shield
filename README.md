# apple_maps_shield

A web server & app that generates highway shields used in Apple Maps with arbitrary text.

## Installation

```
pip install -r requirements.txt && playwright install chromium-headless-shell
```

## Usage

```
python app.py [PORT]
```

The web app is available at the computer's local IP address (and [localhost](http://localhost:5033)), port 5033 or specified in the argument.