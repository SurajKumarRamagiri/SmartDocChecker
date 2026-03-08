import subprocess
import time
import os
import signal
import sys

def ensure_backend_venv(backend_dir):
    """Create venv and install requirements if venv doesn't exist."""
    venv_dir = os.path.join(backend_dir, "venv")
    if sys.platform == "win32":
        python_in_venv = os.path.join(venv_dir, "Scripts", "python.exe")
        pip_in_venv = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        python_in_venv = os.path.join(venv_dir, "bin", "python")
        pip_in_venv = os.path.join(venv_dir, "bin", "pip")

    if not os.path.exists(python_in_venv):
        print("Creating backend virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        print("Installing backend dependencies (this may take a few minutes)...")
        subprocess.run([python_in_venv, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        req_file = os.path.join(backend_dir, "requirements.txt")
        subprocess.run([python_in_venv, "-m", "pip", "install", "-r", req_file], check=True)
        # Install spaCy model
        subprocess.run([python_in_venv, "-m", "spacy", "download", "en_core_web_sm"],
                       check=False)
        print("Backend dependencies installed successfully!")
    else:
        print("Backend venv already exists.")
    return venv_dir

def run_services():
    # Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")

    print("=" * 50)
    print("  SmartDocChecker — Local Development Launcher")
    print("=" * 50)

    # Ensure backend venv exists
    venv_dir = ensure_backend_venv(backend_dir)

    # Determine uvicorn path
    if sys.platform == "win32":
        uvicorn_path = os.path.join(venv_dir, "Scripts", "uvicorn.exe")
    else:
        uvicorn_path = os.path.join(venv_dir, "bin", "uvicorn")

    if not os.path.exists(uvicorn_path):
        print(f"ERROR: uvicorn not found at {uvicorn_path}")
        print("Try deleting backend/venv and running again.")
        sys.exit(1)

    # Start Backend
    print("\nStarting Backend (FastAPI)...")
    backend_process = subprocess.Popen(
        [uvicorn_path, "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
        cwd=backend_dir,
    )

    # Start Frontend
    print("Starting Frontend (Vite)...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_process = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=frontend_dir,
    )

    print("\nServices are running!")
    print("   FastAPI Backend:  http://127.0.0.1:8000")
    print("   React+Vite Frontend: http://localhost:5173 (usually)")
    print("\nPress Ctrl+C to stop both services.\n")

    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping services...")
        
        # Terminate processes
        backend_process.terminate()
        frontend_process.terminate()
        
        # Ensure they are killed on Windows
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(backend_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("All services stopped.")

if __name__ == "__main__":
    run_services()
