import webbrowser
from threading import Timer
import app

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.app.run(host="127.0.0.1", port=5000)