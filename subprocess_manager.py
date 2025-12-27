# subprocess_manager.py
import subprocess
import os
import time
import requests
import logging
import signal

logger = logging.getLogger("subprocess_manager")

_server = None
_port = 8001

def start_model_server(model_type: str, model_path: str = "", port: int = 8001):
    global _server, _port
    stop_model_server()  # stop existing

    env = os.environ.copy()
    env["MODEL_TYPE"] = model_type
    if model_path:
        env["MODEL_PATH"] = model_path
    cmd = [
        "uvicorn",
        "model_server:app",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--log-level", "error"
    ]

    logger.info(f"Starting model subprocess with MODEL_TYPE={model_type}")
    _server = subprocess.Popen(cmd, env=env, stdout=None, stderr=None)
    _port = port

    # wait until server responds
    for _ in range(30):
        try:
            r = requests.get(f"http://127.0.0.1:{port}/docs", timeout=1)
            if r.status_code == 200:
                logger.info("Model server ready!")
                return
        except:
            time.sleep(0.2)

    logger.warning("Model server startup timeout")


def stop_model_server():
    global _server

    logger.info("--------------------")
    logger.info("Stopping model subprocess")
    logger.info("--------------------") 

    if _server is None:
        return
    try:
        _server.terminate()
        _server.wait(3)
    except:
        try:
            _server.kill()
        except:
            pass
    _server = None
