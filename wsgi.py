import os
import sys

# Adiciona o diretório do projeto ao PYTHONPATH
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

from backend.app import app

if __name__ == "__main__":
    app.run()
