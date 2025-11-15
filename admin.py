import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from datetime import datetime
import re

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# --- INÍCIO DA CLASSE FutsalAdminApp (AGORA UNIFICADA, usando Google Sheets) ---

class FutsalAdminApp:
    def __init__(self, master):
        self.master = master
        master.title("⚽ Gerenciador de Futsal (Admin, Times e Boletos)")
        
        # Configuração para tela cheia
        try:
            master.state('zoomed')
        except tk.TclError:
            screen_width = master.winfo_screenwidth()
            screen_height = master.winfo_screenheight()
            master.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # ---------------- Google Sheets CONFIG ----------------
        # Substitua pelo seu ID de planilha
        self.SHEET_ID = "1OrF458H7gU3U2J4lamcX4uV_7cIcdLOr52jTK956aWU"
        # Nomes das abas/worksheets
        self.ARQUIVO_PENDENTES = 'pendentes'
        self.ARQUIVO_AUTORIZADOS = 'aprovados'

        # Escopos
        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # cabeçalhos esperados (mesmo formato que você já usa)
        self.COLUNAS_CADASTRO = [
            'Nome_do_Jogador',
            'CPF_do_Jogador',
            'Data_de_Nascimento',
            'Nome_do_Responsavel',
            'CPF_do_Responsavel',
            'Tel_do_Responsavel',
            'Turma'
        ]
        self.COLUNAS_AUTORIZADOS = self.COLUNAS_CADASTRO.copy()
        self.CHAVE_CADASTRO = 'CPF_do_Responsavel'

        # Tenta conectar ao Google Sheets
        try:
            creds_info = None
            if os.getenv("GOOGLE_SERVICE_ACCOUNT"):
                creds_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT"))
                creds = Credentials.from_service_account_info(creds_info, scopes=self.scope)
            else:
                # arquivo service_account.json no mesmo diretório
                creds = Credentials.from_service_account_file("service_account.json", scopes=self.scope)

            self.client = gspread.authorize(creds)

            # abre as worksheets (se não existirem, cria)
            spreadsheet = self.client.open_by_key(self.SHEET_ID)
            try:
                self.sheet_pendentes = spreadsheet.worksheet(self.ARQUIVO_PENDENTES)
            except gspread.WorksheetNotFound:
                self.sheet_pendentes = spreadsheet.add_worksheet(title=self.ARQUIVO_PENDENTES, rows="1000", cols="20")
            try:
                self.sheet_aprovados = spreadsheet.worksheet(self.ARQUIVO_AUTORIZADOS)
            except gspread.WorksheetNotFound:
                self.sheet_aprovados = spreadsheet.add_worksheet(title=self.ARQUIVO_AUTORIZADOS, rows="1000", cols="20")
            
            # garante cabeçalhos
            self._garantir_cabecalhos()

        except Exception as e:
            messagebox.showerror("Erro Google Sheets", f"Falha ao conectar ao Google Sheets: {e}")
            raise e

        # --- DADOS (Abas Times e Boletos) ---
        # (Dados estão vazios, precisam ser carregados ou preenchidos)
        self.times = {}
        self.boletos = []
        
        # --- Inicialização de Variáveis de Instância (Todas as Abas) ---
        self.entries_admin = {}      
        self.tree_pendentes = None 
        self.tree_autorizados = None 
        self.tree_times = None
        self.tree_jogadores = None
        self.tree_boletos = None
        self.label_det_jogadores = None
        
        self.jogador_selecionado_dados_originais = None 
        self.modo_edicao = 'PENDENTE' 
        
        # --- Configuração de Estilo (Todas as Abas) ---
        self.style = ttk.Style()
        self.style.theme_use('clam') 
        
        # Estilos de Botão
        self.style.configure('Principal.TButton', font=('Times New Roman', 11, 'bold'), foreground='white', background='#007BFF', padding=8)
        self.style.map('Principal.TButton', background=[('active', '#0056b3')]) 
        
        self.style.configure('Remover.TButton', font=('Times New Roman', 11, 'bold'), foreground='white', background='#C0392B', padding=8)
        self.style.map('Remover.TButton', background=[('active', '#922B21')]) 
        
        self.style.configure('Edicao.TButton', font=('Times New Roman', 11, 'bold'), foreground='white', background='#17A2B8', padding=8)
        self.style.map('Edicao.TButton', background=[('active', '#138496')]) 
        
        # Estilo base da Treeview
        self.style.configure("Custom.Treeview", rowheight=25, font=('Times New Roman', 10))
        self.style.map('Custom.Treeview', background=[('selected', '#007BFF')], foreground=[('selected', 'white')])

        # --- Estilos de Cabeçalho (Treeview Headings) ---
        self.style.configure('Pendentes.Treeview', **self.style.configure('Custom.Treeview'))
        self.style.configure('Pendentes.Treeview.Heading', background='#F39C12', foreground='black', font=('Times New Roman', 10, 'bold'), anchor='center')
        self.style.configure('Autorizados.Treeview', **self.style.configure('Custom.Treeview'))
        self.style.configure('Autorizados.Treeview.Heading', background='#27AE60', foreground='white', font=('Times New Roman', 10, 'bold'), anchor='center')
        self.style.configure('Times.Treeview', **self.style.configure('Custom.Treeview'))
        self.style.configure('Times.Treeview.Heading', background='#5E35B1', foreground='white', font=('Times New Roman', 10, 'bold'), anchor='center')
        self.style.configure('Boleto.Treeview', **self.style.configure('Custom.Treeview'))
        self.style.configure('Boleto.Treeview.Heading', background='#1E88E5', foreground='white', font=('Times New Roman', 10, 'bold'), anchor='center')

        # Cria a interface principal
        self._criar_interface()
        

    # ------------------------ Google Sheets helpers ------------------------
    def _garantir_cabecalhos(self):
        """
        Garante que ambas as abas (pendentes e aprovados) tenham o cabeçalho.
        Se a primeira linha estiver vazia, escreve os HEADERS.
        """
        try:
            # Pendentes
            try:
                row1 = self.sheet_pendentes.row_values(1)
            except Exception:
                row1 = []
            if not row1 or all(not c for c in row1):
                self.sheet_pendentes.append_row(self.COLUNAS_CADASTRO)
            # Aprovados
            try:
                row1a = self.sheet_aprovados.row_values(1)
            except Exception:
                row1a = []
            if not row1a or all(not c for c in row1a):
                self.sheet_aprovados.append_row(self.COLUNAS_AUTORIZADOS)
        except Exception as e:
            messagebox.showerror("Erro Cabeçalhos", f"Falha ao garantir cabeçalhos nas abas do Google Sheets: {e}")
            raise

    def _sheet_por_nome(self, nome_arquivo):
        if nome_arquivo == self.ARQUIVO_PENDENTES:
            return self.sheet_pendentes
        elif nome_arquivo == self.ARQUIVO_AUTORIZADOS:
            return self.sheet_aprovados
        else:
            raise ValueError("Nome de aba inválido")

    # ------------------------ Interface (Notebook + Abas) ------------------------
    def _criar_interface(self):
        # Notebook para interligar as 3 interfaces
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # --- Aba 1: Administração ---
        self.aba_admin = ttk.Frame(self.notebook, padding=10) 
        self.notebook.add(self.aba_admin, text=" ⚙️ Administração (Aprovação e Edição)")
        self._criar_aba_admin(self.aba_admin) 

        # --- Aba 2: Times ---
        self.aba_times = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.aba_times, text=" 🏃 Times e Jogadores")
        self._criar_aba_times(self.aba_times)

        # --- Aba 3: Boletos ---
        self.aba_boletos = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.aba_boletos, text=" 💳 Controle de Boletos")
        self._criar_aba_boletos(self.aba_boletos)
        
        # --- Carregamento Inicial (Aba Admin) ---
        # substitui verificação de arquivos por garantia de cabeçalho já feita
        self._carregar_admin_dados()


    # ----------------------------------------------------------------------
    # --- MÉTODO PARA CRIAR ABA 1: ADMINISTRAÇÃO ---
    # ----------------------------------------------------------------------
    def _criar_aba_admin(self, aba):
        aba.grid_columnconfigure(0, weight=1) 
        aba.grid_rowconfigure(1, weight=1) 
        aba.grid_rowconfigure(2, weight=1) 
        aba.grid_rowconfigure(0, weight=0) 
        
        frame_top = ttk.Frame(aba)
        frame_top.grid(row=0, column=0, pady=5, sticky="ew") 
        frame_top.grid_columnconfigure(0, weight=1) 

        frame_cadastro_label, _ = self._criar_aba_cadastro_form(frame_top, self.entries_admin, self.COLUNAS_AUTORIZADOS)
        
        self.frame_botoes_acao = ttk.Frame(frame_cadastro_label) 
        self.frame_botoes_acao.pack(pady=(5, 15), padx=10, fill="x")
        
        self.frame_botoes_acao.columnconfigure(0, weight=1)
        self.frame_botoes_acao.columnconfigure(1, weight=1)
        self.frame_botoes_acao.columnconfigure(2, weight=1)
        
        self.btn_aprovar = ttk.Button(self.frame_botoes_acao, text="✅ AUTORIZAR CADASTRO", command=self.aprovar_jogador, style='Principal.TButton')
        self.btn_rejeitar = ttk.Button(self.frame_botoes_acao, text="❌ REJEITAR CADASTRO", command=self.rejeitar_jogador, style='Remover.TButton')
        self.btn_limpar = ttk.Button(self.frame_botoes_acao, text="Limpar", command=self._limpar_campos_admin)
        
        self.btn_salvar_alteracao = ttk.Button(self.frame_botoes_acao, text="📝 SALVAR ALTERAÇÃO", command=self.editar_jogador_autorizado, style='Edicao.TButton')
        
        self.btn_remover_jogador_form = ttk.Button(self.frame_botoes_acao, 
                                                   text="🗑️ REMOVER JOGADOR", 
                                                   command=self.remover_jogador_autorizado_form, 
                                                   style='Remover.TButton')
        
        self._alternar_botoes('PENDENTE') 

        # 1. Lista de Pendentes
        frame_pendentes = ttk.LabelFrame(aba, text="1. LISTA DE ESPERA: CADASTROS PENDENTES (Amarelo - Clique para carregar e Autorizar/Rejeitar)", padding="5")
        frame_pendentes.grid(row=1, column=0, padx=10, pady=5, sticky="nsew") 
        frame_pendentes.grid_columnconfigure(0, weight=1) 
        frame_pendentes.grid_rowconfigure(0, weight=1)

        self.tree_pendentes = self._criar_treeview_com_scroll(frame_pendentes, self.COLUNAS_CADASTRO, tree_style_name='Pendentes.Treeview', altura=5)
        self.tree_pendentes.bind("<<TreeviewSelect>>", self._carregar_pendente_para_aprovacao)
        
        # 2. Lista de Autorizados
        frame_autorizados = ttk.LabelFrame(aba, text="2. JOGADORES AUTORIZADOS (Verde - Clique para EDITAR/Salvar Alteração ou Excluir)", padding="5")
        frame_autorizados.grid(row=2, column=0, padx=10, pady=5, sticky="nsew") 
        frame_autorizados.grid_columnconfigure(0, weight=1) 
        frame_autorizados.grid_rowconfigure(0, weight=1) 

        self.tree_autorizados = self._criar_treeview_com_scroll(frame_autorizados, self.COLUNAS_AUTORIZADOS, tree_style_name='Autorizados.Treeview', altura=5)
        self.tree_autorizados.bind("<<TreeviewSelect>>", self._carregar_autorizado_para_edicao) 
        
        frame_botoes_excluir_autorizado = ttk.Frame(frame_autorizados)
        frame_botoes_excluir_autorizado.pack(pady=5, fill="x")
        frame_botoes_excluir_autorizado.columnconfigure(0, weight=1)

        ttk.Button(frame_botoes_excluir_autorizado, text="🗑️ EXCLUIR JOGADOR SELECIONADO DA LISTA (Ação Rápida)", command=self.excluir_jogador_autorizado, style='Remover.TButton').pack(fill="x") 

    # ----------------------------------------------------------------------
    # --- MÉTODO PARA CRIAR ABA 2: TIMES ---
    # ----------------------------------------------------------------------
    def _criar_aba_times(self, aba):
        paned_window = ttk.PanedWindow(aba, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, pady=5)

        frame_times_container = ttk.LabelFrame(paned_window, text="Times", padding=10)
        paned_window.add(frame_times_container, weight=1)

        label_times = ttk.Label(frame_times_container, text="Contagem de Jogadores por Time", font=("Times New Roman", 12, 'bold'))
        label_times.pack(pady=5)

        frame_tree_times = ttk.Frame(frame_times_container)
        frame_tree_times.pack(fill="both", expand=True)

        tree_times_vscroll = ttk.Scrollbar(frame_tree_times, orient="vertical")
        tree_times_hscroll = ttk.Scrollbar(frame_tree_times, orient="horizontal")
        
        self.tree_times = ttk.Treeview(frame_tree_times, columns=("time", "jogadores"), show="headings", 
                                       style="Times.Treeview",
                                       yscrollcommand=tree_times_vscroll.set,
                                       xscrollcommand=tree_times_hscroll.set)
        
        tree_times_vscroll.config(command=self.tree_times.yview)
        tree_times_hscroll.config(command=self.tree_times.xview)
        
        tree_times_hscroll.pack(side="bottom", fill="x")
        tree_times_vscroll.pack(side="right", fill="y")
        self.tree_times.pack(side="left", fill="both", expand=True)

        self.tree_times.heading("time", text="Nome do Time")
        self.tree_times.column("time", width=200, minwidth=150)
        self.tree_times.heading("jogadores", text="Nº Jogadores")
        self.tree_times.column("jogadores", width=100, minwidth=80, anchor='center')

        for time, jogadores in self.times.items():
            self.tree_times.insert("", tk.END, values=(time, len(jogadores)), text=time)

        frame_det = ttk.LabelFrame(paned_window, text="Jogadores do Time", padding=10)
        paned_window.add(frame_det, weight=2)

        self.label_det_jogadores = ttk.Label(frame_det, text="Selecione um time ao lado para ver os jogadores.", font=("Times New Roman", 12))
        self.label_det_jogadores.pack(pady=5)

        frame_tree_jogadores = ttk.Frame(frame_det)
        frame_tree_jogadores.pack(fill="both", expand=True)

        tree_jog_vscroll = ttk.Scrollbar(frame_tree_jogadores, orient="vertical")
        tree_jog_hscroll = ttk.Scrollbar(frame_tree_jogadores, orient="horizontal")

        self.tree_jogadores = ttk.Treeview(frame_tree_jogadores, columns=("nome", "idade"), show="headings", 
                                           style="Times.Treeview",
                                           yscrollcommand=tree_jog_vscroll.set,
                                           xscrollcommand=tree_jog_hscroll.set)

        tree_jog_vscroll.config(command=self.tree_jogadores.yview)
        tree_jog_hscroll.config(command=self.tree_jogadores.xview)

        tree_jog_hscroll.pack(side="bottom", fill="x")
        tree_jog_vscroll.pack(side="right", fill="y")
        self.tree_jogadores.pack(side="left", fill="both", expand=True)

        self.tree_jogadores.heading("nome", text="Nome do Jogador")
        self.tree_jogadores.column("nome", width=200, minwidth=150)
        self.tree_jogadores.heading("idade", text="Idade")
        self.tree_jogadores.column("idade", width=100, minwidth=80, anchor='center')

        self.tree_times.bind("<ButtonRelease-1>", self._mostrar_jogadores)

    def _mostrar_jogadores(self, event):
        selection = self.tree_times.focus()
        if not selection:
            return

        valores = self.tree_times.item(selection)
        time = valores["text"] 

        self.label_det_jogadores.config(text=f"Jogadores do {time}")
        self.tree_jogadores.delete(*self.tree_jogadores.get_children())

        if time in self.times:
            for jogador in self.times[time]:
                self.tree_jogadores.insert("", tk.END, values=(jogador["nome"], jogador["idade"]))

    # ----------------------------------------------------------------------
    # --- MÉTODO PARA CRIAR ABA 3: BOLETOS ---
    # ----------------------------------------------------------------------
    def _criar_aba_boletos(self, aba):
        frame_boletos_container = ttk.LabelFrame(aba, text="Controle de Pagamentos", padding=10)
        frame_boletos_container.pack(fill="both", expand=True, pady=5)

        label_boletos = ttk.Label(frame_boletos_container, text="Status de Pagamento dos Jogadores", font=("Times New Roman", 12, 'bold'))
        label_boletos.pack(pady=5)

        frame_tree_boletos = ttk.Frame(frame_boletos_container)
        frame_tree_boletos.pack(fill="both", expand=True, pady=10)

        tree_bol_vscroll = ttk.Scrollbar(frame_tree_boletos, orient="vertical")
        tree_bol_hscroll = ttk.Scrollbar(frame_tree_boletos, orient="horizontal")

        self.tree_boletos = ttk.Treeview(frame_tree_boletos, columns=("nome", "status"), show="headings", 
                                         style="Boleto.Treeview",
                                         yscrollcommand=tree_bol_vscroll.set,
                                         xscrollcommand=tree_bol_hscroll.set)
        
        tree_bol_vscroll.config(command=self.tree_boletos.yview)
        tree_bol_hscroll.config(command=self.tree_boletos.xview)

        tree_bol_hscroll.pack(side="bottom", fill="x")
        tree_bol_vscroll.pack(side="right", fill="y")
        self.tree_boletos.pack(side="left", fill="both", expand=True)

        self.tree_boletos.heading("nome", text="Nome do Jogador")
        self.tree_boletos.column("nome", width=250, minwidth=200)
        self.tree_boletos.heading("status", text="Status")
        self.tree_boletos.column("status", width=150, minwidth=120, anchor='center')

        self.tree_boletos.tag_configure('pago', background='#D4EFDF', foreground='#145A32')
        self.tree_boletos.tag_configure('pendente', background='#FADBD8', foreground='#922B21')

        for b in self.boletos:
            status = b["status"]
            tag = 'pago' if status == "Pago" else 'pendente'
            self.tree_boletos.insert("", tk.END, values=(b["nome"], status), tags=(tag,))


    # ----------------------------------------------------------------------
    # --- MÉTODOS AUXILIARES E DE BACKEND (SUBSTITUINDO CSV POR GOOGLE SHEETS) ---
    # ----------------------------------------------------------------------

    def _ler_todos_dados(self, nome_arquivo, colunas):
        """
        Retorna lista de listas (linhas) sem o cabeçalho.
        """
        try:
            sheet = self._sheet_por_nome(nome_arquivo)
            all_vals = sheet.get_all_values()
            if not all_vals or len(all_vals) <= 1:
                return []
            rows = all_vals[1:]  # ignora cabeçalho
            # garante que cada linha tenha o tamanho de colunas (preenche com '')
            normalized = []
            for r in rows:
                if len(r) < len(colunas):
                    r = r + [''] * (len(colunas) - len(r))
                normalized.append(r[:len(colunas)])
            return normalized
        except Exception as e:
            messagebox.showerror("Erro Leitura", f"Falha ao ler dados da aba '{nome_arquivo}': {e}")
            return []

    def _adicionar_registro(self, nome_arquivo, dados, colunas):
        """
        Adiciona uma linha na aba correspondente.
        'dados' deve ser uma lista com o mesmo número de colunas.
        """
        try:
            sheet = self._sheet_por_nome(nome_arquivo)
            # Se dados tiverem menos colunas, completa com vazios
            row = list(dados)[:len(colunas)]
            if len(row) < len(colunas):
                row += [''] * (len(colunas) - len(row))
            sheet.append_row(row)
            return True
        except Exception as e:
            messagebox.showerror("Erro Escrita", f"Falha ao adicionar registro na aba '{nome_arquivo}': {e}")
            return False

    def _remover_registro_por_dados(self, nome_arquivo, dados_para_remover, colunas):
        """
        Procura a primeira linha que corresponda exatamente aos dados fornecidos (após strip)
        e a remove. Retorna True se removeu.
        """
        try:
            sheet = self._sheet_por_nome(nome_arquivo)
            all_vals = sheet.get_all_values()
            if not all_vals or len(all_vals) <= 1:
                return False
            # procura linha
            dados_alvo_normalizados = [d.strip() for d in dados_para_remover]
            for idx, linha in enumerate(all_vals[1:], start=2):  # start=2 -> índice real no sheet
                linha_norm = [c.strip() for c in linha]
                # normaliza comprimento
                if len(linha_norm) < len(colunas):
                    linha_norm += [''] * (len(colunas) - len(linha_norm))
                if linha_norm[:len(dados_alvo_normalizados)] == dados_alvo_normalizados:
                    sheet.delete_rows(idx)
                    return True
            return False
        except Exception as e:
            messagebox.showerror("Erro Remoção", f"Falha ao remover registro da aba '{nome_arquivo}': {e}")
            return False

    def _atualizar_registro_por_dados(self, nome_arquivo, dados_antigos, novos_dados, colunas):
        """
        Encontra a primeira ocorrência exata de dados_antigos e substitui pela lista novos_dados.
        """
        try:
            sheet = self._sheet_por_nome(nome_arquivo)
            all_vals = sheet.get_all_values()
            if not all_vals or len(all_vals) <= 1:
                return False
            dados_alvo_normalizados = [d.strip() for d in dados_antigos]
            for idx, linha in enumerate(all_vals[1:], start=2):
                linha_norm = [c.strip() for c in linha]
                if len(linha_norm) < len(colunas):
                    linha_norm += [''] * (len(colunas) - len(linha_norm))
                if linha_norm == dados_alvo_normalizados:
                    # prepara novos dados com comprimento correto
                    novos = list(novos_dados)[:len(colunas)]
                    if len(novos) < len(colunas):
                        novos += [''] * (len(colunas) - len(novos))
                    # atualiza linha inteira (A..G)
                    col_range = f"A{idx}:{chr(ord('A') + len(colunas) - 1)}{idx}"
                    sheet.update(col_range, [novos])
                    return True
            return False
        except Exception as e:
            messagebox.showerror("Erro Atualização", f"Falha ao atualizar registro na aba '{nome_arquivo}': {e}")
            return False

    def _atualizar_treeview(self, treeview, nome_arquivo, colunas):
        """
        Atualiza o treeview com os dados da aba nome_arquivo.
        """
        if not treeview:
            return
        for i in treeview.get_children():
            treeview.delete(i)
        dados = self._ler_todos_dados(nome_arquivo, colunas)
        for linha in dados:
            if len(linha) == len(colunas):
                treeview.insert('', 'end', values=linha, text=linha[0])
            else:
                treeview.insert('', 'end', values=linha, tags=('erro',))
                treeview.tag_configure('erro', background='#FFDDDD')

    # --- Funções de Criação de Widget (Helpers) ---
    def _cria_scrollable_frame(self, container):
        outer_frame = ttk.Frame(container)
        outer_frame.pack(fill="both", expand=True) 
        
        canvas = tk.Canvas(outer_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=17)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(window_id, width=event.width) 

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        scrollable_frame.bind("<Configure>", on_frame_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        scrollable_frame.grid_columnconfigure(1, weight=1) 
        return scrollable_frame

    def _criar_treeview_com_scroll(self, parent_frame, colunas, tree_style_name, altura=5):
        frame_tree = ttk.Frame(parent_frame)
        frame_tree.pack(fill="both", expand=True, pady=5) 

        vsb = ttk.Scrollbar(frame_tree, orient="vertical")
        hsb = ttk.Scrollbar(frame_tree, orient="horizontal") 
        
        tree = ttk.Treeview(frame_tree, columns=colunas, show='headings', height=altura,
                            yscrollcommand=vsb.set, xscrollcommand=hsb.set, 
                            style=tree_style_name) 
        
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        
        hsb.pack(side="bottom", fill="x") 
        vsb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True) 

        for col in colunas:
            tree.heading(col, text=col.replace('_', ' '), anchor='center') 
            tree.column(col, width=int(800 / len(colunas)), minwidth=50, anchor='center') 
            
        if self.CHAVE_CADASTRO in colunas:
            tree.column(self.CHAVE_CADASTRO, width=120, minwidth=100, anchor='center') 

        return tree
        
    def _criar_aba_cadastro_form(self, aba, target_entries, colunas_ref):
        frame_cadastro = ttk.LabelFrame(aba, text="Dados do Jogador e Responsável em Análise/Visualização", padding="5")
        frame_cadastro.pack(pady=3, fill="x") 
        
        scrollable_content = self._cria_scrollable_frame(frame_cadastro)
        form_content = scrollable_content 
        
        form_content.grid_columnconfigure(1, weight=1) 
        
        campos_dict = {
            'Nome_do_Jogador': "Nome do Jogador:",
            'CPF_do_Jogador': "CPF do Jogador:",
            'Data_de_Nascimento': "Data de Nascimento (DD/MM/AAAA):", 
            'Nome_do_Responsavel': "Nome do Responsável:",
            'CPF_do_Responsavel': "CPF do Responsável:", 
            'Tel_do_Responsavel': "Telefone do Responsável:",
            'Turma': "Turma (Ex: A, B, C):" 
        }
        
        row_index = 0
        colunas_filtro_form = self.COLUNAS_CADASTRO 
        for col_name in colunas_filtro_form: 
            if col_name in campos_dict:
                ttk.Label(form_content, text=campos_dict[col_name]).grid(row=row_index, column=0, padx=10, pady=5, sticky="w")
                
                entry = ttk.Entry(form_content, font=('Times New Roman', 11)) 
                entry.grid(row=row_index, column=1, padx=301, pady=5, sticky="ew") 
                
                target_entries[col_name] = entry
                row_index += 1
                
        return frame_cadastro, row_index

    # --- Funções de Eventos e Lógica (Aba Admin) ---
    def _alternar_botoes(self, modo):
        self.modo_edicao = modo
        for widget in self.frame_botoes_acao.winfo_children():
            widget.grid_forget()
        
        if modo == 'PENDENTE': 
            self.btn_aprovar.grid(row=0, column=0, padx=5, sticky="ew")
            self.btn_rejeitar.grid(row=0, column=1, padx=5, sticky="ew")
            self.btn_limpar.grid(row=0, column=2, padx=5, sticky="ew")
        elif modo == 'EDICAO_AUTORIZADO': 
            self.btn_salvar_alteracao.grid(row=0, column=0, padx=5, sticky="ew")
            self.btn_remover_jogador_form.grid(row=0, column=1, padx=5, sticky="ew") 
            self.btn_limpar.grid(row=0, column=2, padx=5, sticky="ew")
            
    def _limpar_campos_admin(self, event=None):
        self.jogador_selecionado_dados_originais = None 
        for col_name, entry in self.entries_admin.items(): 
            entry.delete(0, tk.END)
            entry.config(state='normal') 
        self._alternar_botoes('PENDENTE')
            
    def _carregar_pendente_para_aprovacao(self, event):
        item_selecionado_id = self.tree_pendentes.focus()
        if not item_selecionado_id: return
        
        self._limpar_campos_admin()
        self._alternar_botoes('PENDENTE')

        dados_pendentes = self.tree_pendentes.item(item_selecionado_id, 'values')
        
        for i, col_name in enumerate(self.COLUNAS_CADASTRO):
            if col_name in self.entries_admin and i < len(dados_pendentes):
                self.entries_admin[col_name].insert(0, dados_pendentes[i])
        
        self.jogador_selecionado_dados_originais = list(dados_pendentes)
        
        nome_responsavel = dados_pendentes[self.COLUNAS_CADASTRO.index('Nome_do_Responsavel')]
        messagebox.showinfo("Carregado", f"Cadastro do Responsável **{nome_responsavel}** carregado para AUTORIZAR/REJEITAR.")


    def _carregar_autorizado_para_edicao(self, event):
        item_selecionado_id = self.tree_autorizados.focus()
        if not item_selecionado_id: return
        
        self._limpar_campos_admin() 
        self._alternar_botoes('EDICAO_AUTORIZADO') 
        
        dados_autorizados = self.tree_autorizados.item(item_selecionado_id, 'values')
        
        if len(dados_autorizados) < len(self.COLUNAS_AUTORIZADOS):
            messagebox.showerror("Erro de Leitura", "Os dados do jogador selecionado estão incompletos no arquivo.")
            return

        for i, col_name in enumerate(self.COLUNAS_AUTORIZADOS):
            if col_name in self.entries_admin:
                self.entries_admin[col_name].insert(0, dados_autorizados[i])
        
        self.jogador_selecionado_dados_originais = list(dados_autorizados)
        
        nome_responsavel = dados_autorizados[self.COLUNAS_AUTORIZADOS.index('Nome_do_Responsavel')]
        messagebox.showinfo("Carregado", f"Cadastro do Responsável **{nome_responsavel}** carregado para EDIÇÃO. Altere os campos e clique em 'SALVAR ALTERAÇÃO'.")

    def _validar_data_nascimento(self, data_str):
        if not data_str: return False 
        
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", data_str):
            messagebox.showwarning("Aviso", "A Data de Nascimento deve estar no formato **DD/MM/AAAA**.")
            return False
        
        try:
            datetime.strptime(data_str, '%d/%m/%Y')
            return True
        except ValueError:
            messagebox.showwarning("Aviso", f"A data '{data_str}' não é uma data válida.")
            return False

    def _validar_campos(self, dados_completos):
        campos_vazios = any(not valor for valor in dados_completos)
        if campos_vazios:
            messagebox.showwarning("Aviso", "Todos os **7 campos** devem ser preenchidos.")
            return False
            
        data_nascimento_index = self.COLUNAS_CADASTRO.index('Data_de_Nascimento')
        data_nasc_str = dados_completos[data_nascimento_index]
        
        if not self._validar_data_nascimento(data_nasc_str):
            return False
            
        return True

    def aprovar_jogador(self):
        dados_pendentes_originais = self.jogador_selecionado_dados_originais
        
        if self.modo_edicao != 'PENDENTE' or not dados_pendentes_originais:
            messagebox.showwarning("Aviso", "Selecione um cadastro na lista **Pendente (Amarela)** para AUTORIZAR.")
            return
            
        dados_completos = [self.entries_admin.get(col_name).get().strip() for col_name in self.COLUNAS_AUTORIZADOS]
            
        if not self._validar_campos(dados_completos): return
            
        if self._adicionar_registro(self.ARQUIVO_AUTORIZADOS, dados_completos, colunas=self.COLUNAS_AUTORIZADOS):
            if self._remover_registro_por_dados(self.ARQUIVO_PENDENTES, dados_pendentes_originais, colunas=self.COLUNAS_CADASTRO):
                nome_responsavel = dados_completos[self.COLUNAS_AUTORIZADOS.index('Nome_do_Responsavel')]
                messagebox.showinfo("Sucesso", f"Cadastro do Responsável **{nome_responsavel}** **AUTORIZADO** e **removido** da lista pendente.")
                self._carregar_admin_dados() 
            else:
                messagebox.showwarning("Aviso", "Autorizado, mas houve **falha na remoção** da lista pendente. Remova manualmente.")
        else: 
            messagebox.showerror("Erro", "Falha ao adicionar registro autorizado.")

    def editar_jogador_autorizado(self):
        dados_antigos = self.jogador_selecionado_dados_originais
        
        if self.modo_edicao != 'EDICAO_AUTORIZADO' or not dados_antigos:
            messagebox.showwarning("Aviso", "Selecione um jogador na lista **Autorizados (Verde)** e altere os campos para SALVAR ALTERAÇÃO.")
            return
            
        dados_completos = [self.entries_admin.get(col_name).get().strip() for col_name in self.COLUNAS_AUTORIZADOS]
            
        if not self._validar_campos(dados_completos): return
        
        nome_responsavel = dados_completos[self.COLUNAS_AUTORIZADOS.index('Nome_do_Responsavel')]
        cpf_atual = dados_completos[self.COLUNAS_AUTORIZADOS.index(self.CHAVE_CADASTRO)]
        
        confirmar = messagebox.askyesno("Confirmar Edição", f"Deseja salvar as alterações para o cadastro do Responsável {nome_responsavel} (CPF: {cpf_atual})?")

        if not confirmar: return
            
        if self._atualizar_registro_por_dados(self.ARQUIVO_AUTORIZADOS, dados_antigos, dados_completos, colunas=self.COLUNAS_AUTORIZADOS):
            messagebox.showinfo("Sucesso", f"Cadastro do Responsável **{nome_responsavel}** **EDITADO** (Salvo Alteração) com sucesso.")
            self.jogador_selecionado_dados_originais = dados_completos 
            self._carregar_admin_dados() 
        else: 
            messagebox.showerror("Erro", "Falha ao editar o registro de autorizado. Nenhuma correspondência exata encontrada para os dados originais.")

    def rejeitar_jogador(self):
        dados_rejeitar = self.jogador_selecionado_dados_originais
        
        if self.modo_edicao != 'PENDENTE' or not dados_rejeitar:
            messagebox.showwarning("Aviso", "Selecione um cadastro na lista **Pendente (amarela)** para rejeitar.")
            return
            
        cpf_referencia = dados_rejeitar[self.COLUNAS_CADASTRO.index(self.CHAVE_CADASTRO)]
        
        confirmar = messagebox.askyesno("Confirmar Rejeição", f"Deseja **rejeitar** e remover o cadastro com CPF do Responsável: {cpf_referencia} da lista pendente?")
        
        if not confirmar: return
        
        if self._remover_registro_por_dados(self.ARQUIVO_PENDENTES, dados_rejeitar, colunas=self.COLUNAS_CADASTRO):
            messagebox.showinfo("Rejeitado", f"Cadastro com CPF do Responsável **{cpf_referencia}** foi removido da lista pendente.")
            self._limpar_campos_admin()
            self._carregar_admin_dados()
        else: 
            messagebox.showerror("Erro", "Falha ao rejeitar o cadastro.")
            
    def remover_jogador_autorizado_form(self):
        dados_remover = self.jogador_selecionado_dados_originais
        
        if self.modo_edicao != 'EDICAO_AUTORIZADO' or not dados_remover:
            messagebox.showwarning("Aviso", "Selecione um jogador na lista **Autorizados (Verde)** e carregue-o para o formulário para REMOVER.")
            return
        
        dados_completos_originais = self.jogador_selecionado_dados_originais
        nome_resp_index = self.COLUNAS_AUTORIZADOS.index('Nome_do_Responsavel')
        chave_index = self.COLUNAS_AUTORIZADOS.index(self.CHAVE_CADASTRO)
        nome_responsavel = dados_completos_originais[nome_resp_index]
        cpf_referencia = dados_completos_originais[chave_index]
        
        confirmar = messagebox.askyesno(
            "Confirmar Remoção", 
            f"Tem certeza que deseja **REMOVER permanentemente** o cadastro do Responsável **{nome_responsavel}** (CPF: **{cpf_referencia}**) da lista de Autorizados? Esta ação não pode ser desfeita."
        )
        
        if not confirmar: return
            
        if self._remover_registro_por_dados(self.ARQUIVO_AUTORIZADOS, dados_completos_originais, colunas=self.COLUNAS_AUTORIZADOS):
            messagebox.showinfo("Sucesso", f"Cadastro do Responsável **{nome_responsavel}** foi **REMOVIDO** com sucesso.")
            self._carregar_admin_dados() 
        else: 
            messagebox.showerror("Erro", "Falha ao remover o cadastro autorizado. Nenhuma correspondência exata encontrada para os dados originais.")

    def excluir_jogador_autorizado(self):
        item_selecionado_id = self.tree_autorizados.focus()
        if not item_selecionado_id:
            messagebox.showwarning("Aviso", "Selecione um cadastro na lista VERDE de Autorizados para excluir.")
            return

        dados_autorizados = self.tree_autorizados.item(item_selecionado_id, 'values')
        
        if not dados_autorizados:
            messagebox.showerror("Erro", "Não foi possível obter os dados completos do cadastro selecionado.")
            return

        nome_resp_index = self.COLUNAS_AUTORIZADOS.index('Nome_do_Responsavel')
        chave_index = self.COLUNAS_AUTORIZADOS.index(self.CHAVE_CADASTRO)
        
        nome_responsavel = dados_autorizados[nome_resp_index] if len(dados_autorizados) > nome_resp_index else "N/A"
        cpf_referencia = dados_autorizados[chave_index] if len(dados_autorizados) > chave_index else "N/A"
        
        confirmar = messagebox.askyesno(
            "Confirmar Exclusão", 
            f"Tem certeza que deseja **EXCLUIR permanentemente** o cadastro do Responsável **{nome_responsavel}** (CPF: **{cpf_referencia}**) da lista de Autorizados? (Ação Rápida)"
        )
        
        if not confirmar: return
            
        if self._remover_registro_por_dados(self.ARQUIVO_AUTORIZADOS, list(dados_autorizados), colunas=self.COLUNAS_AUTORIZADOS):
            messagebox.showinfo("Sucesso", f"Cadastro do Responsável **{nome_responsavel}** foi excluído da lista de Autorizados.")
            self._carregar_admin_dados() 
        else: 
            messagebox.showerror("Erro", "Falha ao excluir o cadastro autorizado.")

    def _carregar_admin_dados(self):
        # Atualiza as treeviews da aba admin lendo do Google Sheets
        self._atualizar_treeview(self.tree_pendentes, self.ARQUIVO_PENDENTES, colunas=self.COLUNAS_CADASTRO)
        self._atualizar_treeview(self.tree_autorizados, self.ARQUIVO_AUTORIZADOS, colunas=self.COLUNAS_AUTORIZADOS)
        self._limpar_campos_admin()
        
        # (Nota: As abas Times e Boletos não são atualizadas aqui, pois seus dados (self.times, self.boletos) estão separados)
        

# --- EXECUTA O PROGRAMA ---
if __name__ == "__main__":
    root = tk.Tk()
    app = FutsalAdminApp(root) # Instancia a classe unificada
    root.mainloop()
