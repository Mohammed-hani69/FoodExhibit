from app import app
from extensions import socketio
import routes  # noqa: F401
import socket

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # نتصل بعنوان خارجي عشان يجيب الـ IP الصحيح
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000
    print(f"\n✅ Server running at: http://{get_ip()}:{port}\n")
    socketio.run(app, host=host, port=port, debug=True)
