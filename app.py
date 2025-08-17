import os
import shutil
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify
from datetime import datetime
from dotenv import load_dotenv

# IMPORTANTE: só use waitress em produção!
# from waitress import serve

app = Flask(__name__)

# Carrega variáveis do .env na raiz do projeto
load_dotenv()

# ===== Configurações =====
API_KEY     = os.environ.get("API_KEY", "F@britech@2025")
ARQORIGEM   = os.environ.get("ARQORIGEM")   # diretório onde VAMOS PROCURAR o arquivo
ARQDESTINO  = os.environ.get("ARQDESTINO")  # diretório para COPIAR o arquivo encontrado
LOGDIR      = os.environ.get("LOGDIR")      # diretório para gravar o log (opcional)
DEBUG_SCAN  = os.environ.get("DEBUG_SCAN", "0") in ("1", "true", "True", "yes")

# Valida diretórios essenciais
if not ARQORIGEM:
    raise RuntimeError("Variável de ambiente ARQORIGEM não definida no .env")
if not ARQDESTINO:
    raise RuntimeError("Variável de ambiente ARQDESTINO não definida no .env")

ORIGEM_PATH  = Path(ARQORIGEM)
DESTINO_PATH = Path(ARQDESTINO)

# Log: usa LOGDIR se definido, senão ./logs
PATH_LOG = Path(LOGDIR) if LOGDIR else (Path(__file__).parent / "logs")
PATH_LOG.mkdir(parents=True, exist_ok=True)
LOG_FILE = PATH_LOG / "api_files_4xml.log"


def write_log(mensagem: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {mensagem}\n")


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("API-KEY")  # você escolheu "API-KEY"
        if not key or key != API_KEY:
            write_log("Acesso negado: API-KEY inválida ou ausente")
            return jsonify({"error": "API key inválida ou ausente"}), 401
        return f(*args, **kwargs)
    return decorated


def find_file(filename: str, origem_path: Path) -> str | None:
    """Procura o arquivo por nome (case-insensitive) dentro de origem_path (subpastas incluídas)."""
    if not origem_path.exists():
        write_log(f"[ERRO] ORIGEM não existe: {origem_path}")
        return None

    target = filename.strip().lower()

    # Converter para str evita arestas em versões mais antigas do Python/Windows
    for root, _, files in os.walk(str(origem_path)):
        if DEBUG_SCAN:
            write_log(f"[SCAN] Pasta: {root} -> {len(files)} arquivos")
        for f in files:
            if DEBUG_SCAN:
                write_log(f"  - {f}")
            # comparação case-insensitive por nome exato
            if f.lower() == target:
                return os.path.join(root, f)

    return None


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"ok": True}), 200


@app.route("/getfile", methods=["GET"])
@require_api_key
def get_file():
    filename = (request.args.get("filename", "")).strip()
    if not filename:
        return jsonify({"error": "Informe ?filename=..."}), 400

    # segurança: só nome do arquivo, sem caminho
    if any(sep in filename for sep in ("/", "\\")):
        return jsonify({"error": "Informe apenas o nome do arquivo (sem caminho)."}), 400

    file_path = find_file(filename, ORIGEM_PATH)
    if not file_path:
        msg = f"Arquivo '{filename}' não encontrado."
        write_log(msg)
        return jsonify({"mensagem": msg}), 404

    DESTINO_PATH.mkdir(parents=True, exist_ok=True)
    dest_path = str(DESTINO_PATH / Path(file_path).name)

    try:
        shutil.copy2(file_path, dest_path)  # sobrescreve se já existir
        msg = f"Arquivo '{filename}' copiado: {file_path} -> {dest_path}"
        write_log(msg)
        return jsonify({"mensagem": "Arquivo encontrado e copiado com sucesso!"}), 200
    except Exception as e:
        msg = f"Erro ao copiar '{file_path}' -> '{dest_path}': {e}"
        write_log(msg)
        return jsonify({"mensagem": "Falha ao copiar o arquivo.", "erro": str(e)}), 500


if __name__ == "__main__":
    # Em DEV, use o servidor do Flask
    app.run(host="0.0.0.0", port=5100)
    # Em produção (exemplo):
    # serve(app, host="0.0.0.0", port=5100)
