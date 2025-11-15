from flask import Flask, render_template, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# Caminho correto dos templates quando hospedado no Vercel
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "../templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)

# -----------------------------
# CONFIG GOOGLE SHEETS
# -----------------------------
SHEET_ID = "1OrF458H7gU3U2J4lamcX4uV_7cIcdLOr52jTK956aWU"
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# --- CARREGA A CHAVE DO SERVICE ACCOUNT ---
try:
    if os.getenv("GOOGLE_SERVICE_ACCOUNT"):
        # Vercel: chave vem da variável de ambiente (STRING JSON)
        info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT"))
    else:
        # Local: arquivo JSON
        with open("service_account.json") as f:
            info = json.load(f)

    creds = Credentials.from_service_account_info(info, scopes=scope)
    client = gspread.authorize(creds)

    sheet_pendentes = client.open_by_key(SHEET_ID).worksheet("pendentes")
    sheet_aprovados = client.open_by_key(SHEET_ID).worksheet("aprovados")

except Exception as e:
    print("ERRO ao conectar ao Google Sheets:", e)
    raise e


# -----------------------------
# CABEÇALHOS
# -----------------------------
HEADERS = [
    "Nome_do_Responsavel",
    "CPF_do_Responsavel",
    "Telefone_do_Responsavel",
    "Nome_do_Jogador",
    "CPF_do_Jogador",
    "Data_Nascimento_do_Jogador"
]

def garantir_cabecalhos():
    try:
        if not sheet_pendentes.row_values(1):
            sheet_pendentes.append_row(HEADERS)
        if not sheet_aprovados.row_values(1):
            sheet_aprovados.append_row(HEADERS)
    except Exception as e:
        print("ERRO ao garantir cabeçalhos:", e)

garantir_cabecalhos()


# -----------------------------
# ROTAS
# -----------------------------
@app.route("/")
def formulario():
    return render_template("formulario.html")


@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    try:
        dados = [
            request.form.get("nome_responsavel", ""),
            request.form.get("cpf_responsavel", ""),
            request.form.get("telefone_responsavel", ""),
            request.form.get("nome_jogador", ""),
            request.form.get("cpf_jogador", ""),
            request.form.get("data_nascimento", "")
        ]
        sheet_pendentes.append_row(dados)
        return "Cadastro realizado com sucesso!"
    except Exception as e:
        print("ERRO ao cadastrar:", e)
        return "Erro ao cadastrar.", 500


@app.route("/pendentes")
def pendentes():
    try:
        registros = sheet_pendentes.get_all_records()
        return jsonify({"pendentes": registros})
    except Exception as e:
        print("ERRO ao listar:", e)
        return "Erro ao listar.", 500


@app.route("/aprovar/<int:linha>")
def aprovar(linha):
    try:
        linha_real = linha + 2
        dados = sheet_pendentes.row_values(linha_real)
        sheet_aprovados.append_row(dados)
        sheet_pendentes.delete_rows(linha_real)
        return "Aprovado!"
    except Exception as e:
        print("ERRO ao aprovar:", e)
        return "Erro ao aprovar.", 500


# -----------------------------
# HANDLER PARA VERCEL
# -----------------------------
def handler(request, response=None):
    return app(request, response)
