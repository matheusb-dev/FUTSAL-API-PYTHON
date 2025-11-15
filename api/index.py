import json
import os
import gspread
from google.oauth2.service_account import Credentials

# -----------------------------
# CONFIG GOOGLE SHEETS
# -----------------------------
SHEET_ID = "1OrF458H7gU3U2J4lamcX4uV_7cIcdLOr52jTK956aWU"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# -----------------------------
# LOAD SERVICE ACCOUNT KEY
# -----------------------------
def load_sheets():
    if not os.getenv("GOOGLE_SERVICE_ACCOUNT"):
        raise Exception("Variável GOOGLE_SERVICE_ACCOUNT não encontrada!")

    info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT"))
    creds = Credentials.from_service_account_info(info, scopes=scope)
    client = gspread.authorize(creds)

    sheet_pendentes = client.open_by_key(SHEET_ID).worksheet("pendentes")
    sheet_aprovados = client.open_by_key(SHEET_ID).worksheet("aprovados")
    return sheet_pendentes, sheet_aprovados


# -----------------------------
# HANDLER PRINCIPAL DA VERCEL
# -----------------------------
def handler(request):
    method = request.method
    path = request.path

    sheet_pendentes, sheet_aprovados = load_sheets()

    # ------ ROTAS ------
    if path == "/":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "API funcionando"})
        }

    # CADASTRAR
    if path == "/cadastrar" and method == "POST":
        body = request.json

        dados = [
            body.get("nome_responsavel", ""),
            body.get("cpf_responsavel", ""),
            body.get("telefone_responsavel", ""),
            body.get("nome_jogador", ""),
            body.get("cpf_jogador", ""),
            body.get("data_nascimento", "")
        ]

        sheet_pendentes.append_row(dados)

        return {
            "statusCode": 200,
            "body": "Cadastro realizado com sucesso!"
        }

    # LISTAR PENDENTES
    if path == "/pendentes":
        registros = sheet_pendentes.get_all_records()

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"pendentes": registros})
        }

    # APROVAR
    if path.startswith("/aprovar/"):
        try:
            _, _, linha_raw = path.partition("/aprovar/")
            linha = int(linha_raw)

            linha_real = linha + 2
            dados = sheet_pendentes.row_values(linha_real)
            sheet_aprovados.append_row(dados)
            sheet_pendentes.delete_rows(linha_real)

            return {"statusCode": 200, "body": "Aprovado!"}

        except Exception as e:
            return {"statusCode": 500, "body": f"Erro: {str(e)}"}

    return {"statusCode": 404, "body": "Rota não encontrada"}
