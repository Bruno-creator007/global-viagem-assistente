import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
