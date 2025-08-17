from waitress import serve
from app import app  # importa o app Flask definido no app.py

if __name__ == "__main__":
    print("Iniciando o servidor com Waitress na porta 5100...")
    serve(app, host="0.0.0.0", port=5100)
