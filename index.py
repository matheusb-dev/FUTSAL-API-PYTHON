from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials
import json
import os

app = Flask(__name__)

# -----------------------------
# CONFIG GOOGLE SHEETS
# -----------------------------

SHEET_ID = "1OrF458H7gU3U2J4lamcX4uV_7cIcdLOr52jTK956aWU"

# Escopo do Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

# --- CARREGA A CHAVE DE FORMA COMPATÍVEL COM O VERCEL ---
if os.getenv("GOOGLE_SERVICE_ACCOUNT"):
    # Vercel: chave vem da variável de ambiente
    info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT"))
else:
    # Local: usa o arquivo service_account.json
    with open("service_account.json") as f:
        info = json.load(f)

creds = Credentials.from_service_account_info(info, scopes=scope)
client = gspread.authorize(creds)

sheet_pendentes = client.open_by_key(SHEET_ID).worksheet("pendentes")
sheet_aprovados = client.open_by_key(SHEET_ID).worksheet("aprovados")

HEADERS = [
    "Nome_do_Responsavel",
    "CPF_do_Responsavel",
    "Telefone_do_Responsavel",
    "Nome_do_Jogador",
    "CPF_do_Jogador",
    "Data_Nascimento_do_Jogador"
]

def garantir_cabecalhos():
    if sheet_pendentes.row_values(1) == []:
        sheet_pendentes.append_row(HEADERS)
    if sheet_aprovados.row_values(1) == []:
        sheet_aprovados.append_row(HEADERS)

garantir_cabecalhos()

# -----------------------------
# ROTAS DO SISTEMA
# -----------------------------

@app.route("/")
def formulario():
    return render_template("formulario.html")

@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    dados = [
        request.form["nome_responsavel"],
        request.form["cpf_responsavel"],
        request.form["telefone_responsavel"],
        request.form["nome_jogador"],
        request.form["cpf_jogador"],
        request.form["data_nascimento"]
    ]

    sheet_pendentes.append_row(dados)
    return "Cadastro realizado com sucesso! O jogador agora está na lista de pendentes."

@app.route("/pendentes")
def lista_pendentes():
    registros = sheet_pendentes.get_all_records()
    return {"pendentes": registros}

@app.route("/aprovar/<int:linha>")
def aprovar(linha):
    linha_real = linha + 2
    dados = sheet_pendentes.row_values(linha_real)

    sheet_aprovados.append_row(dados)
    sheet_pendentes.delete_rows(linha_real)

    return "Jogador aprovado com sucesso!"

if __name__ == "__main__":
    app.run(debug=True)

# Deploy Vercel: atualizando variável de ambiente