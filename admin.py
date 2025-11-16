import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from datetime import datetime
import re
import gspread
from google.oauth2.service_account import Credentials

# --- INÍCIO DA CLASSE FutsalAdminApp ---

class FutsalAdminApp:
    def __init__(self, master):
        self.master = master
        master.title("⚽ Gerenciador de Futsal (Admin, Times e Boletos)")
        
        try:
            master.state('zoomed')
        except tk.TclError:
            screen_width = master.winfo_screenwidth()
            screen_height = master.winfo_screenheight()
            master.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # ---------------- Google Sheets CONFIG ----------------
        self.SHEET_ID = "1OrF458H7gU3U2J4lamcX4uV_7cIcdLOr52jTK956aWU" # Substitua pelo seu ID
        self.ARQUIVO_PENDENTES = 'pendentes'
        self.ARQUIVO_AUTORIZADOS = 'aprovados'
        self.ARQUIVO_BOLETOS = 'boletos'
        self.ARQUIVO_PRE_CADASTRO = self.ARQUIVO_PENDENTES

        self.scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        self.COLUNAS_CADASTRO = [
            'Nome_do_Jogador',
            'CPF_do_Jogador',
            'Data_de_Nascimento',
            'Nome_do_Responsavel',
            'CPF_do_Responsavel',
            'Tel_do_Responsavel'
        ]
        self.COLUNAS_AUTORIZADOS = self.COLUNAS_CADASTRO + ['Turma'] 
        
        # COLUNAS REQUERIDAS PARA A TELA DE BOLETOS E PERSISTÊNCIA NO SHEETS
        self.COLUNAS_BOLETO = [ 
            'Nome_do_Responsavel', 
            'Nome_do_Jogador',
            'CPF_do_Responsavel',  
            'Tel_do_Responsavel',
            'Turma', 
            'Vencimento', 
            'Status'
        ]

        self.CHAVE_CADASTRO = 'CPF_do_Responsavel' # CHAVE PRIMÁRIA PARA BUSCA

        try:
            creds_info = None
            if os.getenv("GOOGLE_SERVICE_ACCOUNT"):
                creds_info = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT"))
                creds = Credentials.from_service_account_info(creds_info, scopes=self.scope)
            else:
                creds = Credentials.from_service_account_file("service_account.json", scopes=self.scope)

            self.client = gspread.authorize(creds)
            spreadsheet = self.client.open_by_key(self.SHEET_ID)
            
            try: self.sheet_pendentes = spreadsheet.worksheet(self.ARQUIVO_PENDENTES)
            except gspread.WorksheetNotFound: self.sheet_pendentes = spreadsheet.add_worksheet(title=self.ARQUIVO_PENDENTES, rows="1000", cols="20")
            
            try: self.sheet_aprovados = spreadsheet.worksheet(self.ARQUIVO_AUTORIZADOS)
            except gspread.WorksheetNotFound: self.sheet_aprovados = spreadsheet.add_worksheet(title=self.ARQUIVO_AUTORIZADOS, rows="1000", cols="20")
            
            # Inicializa a nova Sheet de Boletos
            try: self.sheet_boletos = spreadsheet.worksheet(self.ARQUIVO_BOLETOS)
            except gspread.WorksheetNotFound: self.sheet_boletos = spreadsheet.add_worksheet(title=self.ARQUIVO_BOLETOS, rows="1000", cols="20")
            
            self._garantir_cabecalhos()

        except Exception as e:
            messagebox.showerror("Erro Google Sheets", f"Falha ao conectar ao Google Sheets: {e}")

        # --- DADOS E VARIÁVEIS ---
        self.times = {}
        self.boletos = []
        self.entries_admin = {} 
        self.entries_cadastro = {} 
        self.tree_pendentes = None 
        self.tree_autorizados = None 
        self.tree_times = None
        self.tree_jogadores = None
        self.tree_boletos = None
        self.label_det_jogadores = None
        
        self.jogador_selecionado_dados_originais = None 
        self.modo_edicao = None 
        
        self._configurar_estilos()
        self._criar_interface()
        
        self._carregar_admin_dados()
    
    def _configurar_estilos(self):
        self.style = ttk.Style()
        self.style.theme_use('clam') 
        self.style.configure('Principal.TButton', font=('Times New Roman', 11, 'bold'), foreground='white', background='#007BFF', padding=8)
        self.style.map('Principal.TButton', background=[('active', '#0056b3')]) 
        self.style.configure('Remover.TButton', font=('Times New Roman', 11, 'bold'), foreground='white', background='#C0392B', padding=8)
        self.style.map('Remover.TButton', background=[('active', '#922B21')]) 
        self.style.configure('Edicao.TButton', font=('Times New Roman', 11, 'bold'), foreground='white', background='#17A2B8', padding=8)
        self.style.map('Edicao.TButton', background=[('active', '#138496')]) 
        self.style.configure('Cadastro.TButton', font=('Times New Roman', 12, 'bold'), foreground='white', background='#28A745', padding=10)
        self.style.map('Cadastro.TButton', background=[('active', '#1E7E34')])
        self.style.configure("Custom.Treeview", rowheight=25, font=('Times New Roman', 10))
        self.style.map('Custom.Treeview', background=[('selected', '#007BFF')], foreground=[('selected', 'white')])
        self.style.configure('Pendentes.Treeview.Heading', background='#F39C12', foreground='black', font=('Times New Roman', 10, 'bold'), anchor='center')
        self.style.configure('Autorizados.Treeview.Heading', background='#27AE60', foreground='white', font=('Times New Roman', 10, 'bold'), anchor='center')
        self.style.configure('Times.Treeview.Heading', background='#5E35B1', foreground='white', font=('Times New Roman', 10, 'bold'), anchor='center')
        self.style.configure('Boleto.Treeview.Heading', background='#1E88E5', foreground='white', font=('Times New Roman', 10, 'bold'), anchor='center')

    def _garantir_cabecalhos(self):
        try:
            if not self.sheet_pendentes.row_values(1) or all(not c for c in self.sheet_pendentes.row_values(1)):
                self.sheet_pendentes.append_row(self.COLUNAS_AUTORIZADOS)
            if not self.sheet_aprovados.row_values(1) or all(not c for c in self.sheet_aprovados.row_values(1)):
                self.sheet_aprovados.append_row(self.COLUNAS_AUTORIZADOS)
            # Garante cabeçalhos para a sheet de boletos
            if not self.sheet_boletos.row_values(1) or all(not c for c in self.sheet_boletos.row_values(1)):
                self.sheet_boletos.append_row(self.COLUNAS_BOLETO)

        except Exception as e:
            messagebox.showerror("Erro Cabeçalhos", f"Falha ao garantir cabeçalhos nas abas do Google Sheets: {e}")
            raise

    def _sheet_por_nome(self, nome_arquivo):
        if nome_arquivo == self.ARQUIVO_PENDENTES: return self.sheet_pendentes
        elif nome_arquivo == self.ARQUIVO_AUTORIZADOS: return self.sheet_aprovados
        elif nome_arquivo == self.ARQUIVO_BOLETOS: return self.sheet_boletos 
        else: raise ValueError("Nome de aba inválido")

    def _criar_interface(self):
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")
        
        self.aba_cadastro = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.aba_cadastro, text=" 📝 Pré-Cadastro de Jogadores")
        self._criar_aba_cadastro(self.aba_cadastro)

        self.aba_admin = ttk.Frame(self.notebook, padding=10) 
        self.notebook.add(self.aba_admin, text=" ⚙️ Administração (Aprovação e Edição)")
        self._criar_aba_admin(self.aba_admin) 

        self.aba_times = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.aba_times, text=" 🏃 Times e Jogadores")
        self._criar_aba_times(self.aba_times)

        self.aba_boletos = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.aba_boletos, text=" 💳 Controle de Boletos")
        self._criar_aba_boletos(self.aba_boletos)
        
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        selected_tab = self.notebook.tab(self.notebook.select(), "text").strip()
        if "Times" in selected_tab or "Boletos" in selected_tab: self._carregar_dados_times_boletos()
        if "Administração" in selected_tab: self._carregar_admin_dados() 
            
    def _criar_treeview_com_scroll(self, parent, colunas, tree_style_name, altura=10):
        frame_tree = ttk.Frame(parent)
        frame_tree.pack(fill="both", expand=True)
        tree_vscroll = ttk.Scrollbar(frame_tree, orient="vertical")
        tree_hscroll = ttk.Scrollbar(frame_tree, orient="horizontal")
        tree = ttk.Treeview(frame_tree, columns=colunas, show="headings", 
                            style=tree_style_name, yscrollcommand=tree_vscroll.set,
                            xscrollcommand=tree_hscroll.set, height=altura)
        tree_vscroll.config(command=tree.yview)
        tree_hscroll.config(command=tree.xview)
        tree_hscroll.pack(side="bottom", fill="x")
        tree_vscroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        for col in colunas:
            tree.heading(col, text=col.replace('_', ' '))
            tree.column(col, width=120, minwidth=100, anchor='w')
        return tree
        
    def _criar_aba_cadastro_form(self, parent, entries_dict, colunas, titulo):
        frame_master = ttk.LabelFrame(parent, text=titulo, padding=10)
        frame_interna = ttk.Frame(frame_master)
        frame_interna.pack(padx=10, pady=10, fill="x")
        num_cols = 3 
        for i, col_name in enumerate(colunas):
            row = i // num_cols
            col = i % num_cols
            label_text = col_name.replace('_', ' ') + ":"
            ttk.Label(frame_interna, text=label_text, font=('Times New Roman', 10, 'bold')).grid(row=row, column=col*2, sticky='w', padx=5, pady=5)
            entry = ttk.Entry(frame_interna, width=30, font=('Times New Roman', 10))
            entry.grid(row=row, column=col*2 + 1, sticky='ew', padx=5, pady=5)
            frame_interna.grid_columnconfigure(col*2 + 1, weight=1)
            entries_dict[col_name] = entry
        return frame_master, entries_dict

    def _alternar_botoes(self, modo):
        self.modo_edicao = modo
        for btn in [self.btn_aprovar, self.btn_rejeitar, self.btn_limpar, self.btn_salvar_alteracao, self.btn_remover_jogador_form]:
            btn.grid_forget()

        if modo == 'PENDENTE':
            self.btn_aprovar.grid(row=0, column=0, padx=5, sticky="ew")
            self.btn_rejeitar.grid(row=0, column=1, padx=5, sticky="ew")
            self.btn_limpar.grid(row=0, column=2, padx=5, sticky="ew")
            state = 'normal' 
        elif modo == 'AUTORIZADO':
            self.btn_salvar_alteracao.grid(row=0, column=0, padx=5, sticky="ew")
            self.btn_remover_jogador_form.grid(row=0, column=1, padx=5, sticky="ew")
            self.btn_limpar.grid(row=0, column=2, padx=5, sticky="ew")
            state = 'normal' 
        else:
            self.btn_limpar.grid(row=0, column=2, padx=5, sticky="ew")
            state = 'readonly' 

        for entry in self.entries_admin.values():
            entry.config(state=state)

    def _limpar_campos_admin(self, event=None):
        for entry in self.entries_admin.values():
            entry.delete(0, tk.END)
        self.jogador_selecionado_dados_originais = None
        self._alternar_botoes(None)

    def _limpar_campos_cadastro(self, event=None):
        for col_name, entry in self.entries_cadastro.items(): 
            entry.config(state='normal')
            entry.delete(0, tk.END)

    # ----------------------------------------------------------------------
    # --- ABA 1: PRÉ-CADASTRO (Turma Removida) ---
    # ----------------------------------------------------------------------
    def _criar_aba_cadastro(self, aba):
        aba.grid_columnconfigure(0, weight=1)
        aba.grid_rowconfigure(0, weight=0)
        
        frame_cadastro_label, _ = self._criar_aba_cadastro_form(
            aba, self.entries_cadastro, self.COLUNAS_CADASTRO, 
            titulo="Formulário de Pré-Cadastro de Jogador"
        )
        frame_cadastro_label.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        frame_botoes = ttk.Frame(aba)
        frame_botoes.grid(row=1, column=0, pady=(0, 20), sticky="ew")
        frame_botoes.columnconfigure(0, weight=1)
        frame_botoes.columnconfigure(1, weight=1)
        
        ttk.Button(frame_botoes, 
                   text="➕ CADASTRAR JOGADOR (Enviar para Aprovação)", 
                   command=self.cadastrar_jogador_pendente, 
                   style='Cadastro.TButton').grid(row=0, column=0, padx=5, sticky="ew")
        
        ttk.Button(frame_botoes, 
                   text="Limpar Campos", 
                   command=self._limpar_campos_cadastro).grid(row=0, column=1, padx=5, sticky="ew")

    def cadastrar_jogador_pendente(self):
        dados_completos = [self.entries_cadastro.get(col_name).get().strip() for col_name in self.COLUNAS_CADASTRO]
        
        if not self._validar_campos(dados_completos): return
        
        if self._verificar_duplicidade(dados_completos):
            messagebox.showwarning("Duplicidade", "Um cadastro com este CPF de Responsável ou Jogador já está pendente ou autorizado.")
            return

        dados_completos_com_turma_vazia = dados_completos + [''] 

        if self._adicionar_registro(self.ARQUIVO_PRE_CADASTRO, dados_completos_com_turma_vazia, self.COLUNAS_AUTORIZADOS):
            nome_jogador = dados_completos[self.COLUNAS_CADASTRO.index('Nome_do_Jogador')]
            messagebox.showinfo("Sucesso", f"O jogador **{nome_jogador}** foi cadastrado com sucesso e está na lista de **PENDENTES** para aprovação!")
            self._limpar_campos_cadastro()
            self._carregar_admin_dados()

    # ----------------------------------------------------------------------
    # --- ABA 2: ADMINISTRAÇÃO ---
    # ----------------------------------------------------------------------
    def _criar_aba_admin(self, aba):
        aba.grid_columnconfigure(0, weight=1) 
        aba.grid_rowconfigure(1, weight=1) 
        aba.grid_rowconfigure(2, weight=1) 
        aba.grid_rowconfigure(0, weight=0) 
        
        frame_top = ttk.Frame(aba)
        frame_top.grid(row=0, column=0, pady=5, sticky="ew") 
        frame_top.grid_columnconfigure(0, weight=1) 

        frame_cadastro_label, _ = self._criar_aba_cadastro_form(
            frame_top, self.entries_admin, self.COLUNAS_AUTORIZADOS, 
            titulo="Dados do Jogador e Responsável em Análise/Visualização/Edição"
        )
        frame_cadastro_label.pack(pady=3, fill="x")
        
        self.frame_botoes_acao = ttk.Frame(frame_cadastro_label) 
        self.frame_botoes_acao.pack(pady=(5, 15), padx=10, fill="x")
        self.frame_botoes_acao.columnconfigure(0, weight=1)
        self.frame_botoes_acao.columnconfigure(1, weight=1)
        self.frame_botoes_acao.columnconfigure(2, weight=1)
        
        self.btn_aprovar = ttk.Button(self.frame_botoes_acao, text="✅ AUTORIZAR CADASTRO", command=self.aprovar_jogador, style='Principal.TButton')
        self.btn_rejeitar = ttk.Button(self.frame_botoes_acao, text="❌ REJEITAR CADASTRO", command=self.rejeitar_jogador, style='Remover.TButton')
        self.btn_limpar = ttk.Button(self.frame_botoes_acao, text="Limpar", command=self._limpar_campos_admin)
        self.btn_salvar_alteracao = ttk.Button(self.frame_botoes_acao, text="📝 SALVAR ALTERAÇÃO", command=self.editar_jogador_autorizado, style='Edicao.TButton')
        self.btn_remover_jogador_form = ttk.Button(self.frame_botoes_acao, text="🗑️ REMOVER JOGADOR", command=self.remover_jogador_autorizado_form, style='Remover.TButton')
        
        self._alternar_botoes(None) 

        frame_pendentes = ttk.LabelFrame(aba, text="1. LISTA DE ESPERA: CADASTROS PENDENTES (Amarelo - Clique para carregar e Autorizar/Rejeitar)", padding="5")
        frame_pendentes.grid(row=1, column=0, padx=10, pady=5, sticky="nsew") 
        frame_pendentes.grid_columnconfigure(0, weight=1) 
        frame_pendentes.grid_rowconfigure(0, weight=1)

        self.tree_pendentes = self._criar_treeview_com_scroll(frame_pendentes, self.COLUNAS_AUTORIZADOS, tree_style_name='Pendentes.Treeview', altura=5)
        self.tree_pendentes.bind("<<TreeviewSelect>>", self._carregar_pendente_para_aprovacao)
        
        frame_autorizados = ttk.LabelFrame(aba, text="2. JOGADORES AUTORIZADOS (Verde - Clique para EDITAR/Salvar Alteração ou Excluir)", padding="5")
        frame_autorizados.grid(row=2, column=0, padx=10, pady=5, sticky="nsew") 
        frame_autorizados.grid_columnconfigure(0, weight=1) 
        frame_autorizados.grid_rowconfigure(0, weight=1) 

        self.tree_autorizados = self._criar_treeview_com_scroll(frame_autorizados, self.COLUNAS_AUTORIZADOS, tree_style_name='Autorizados.Treeview', altura=5)
        self.tree_autorizados.bind("<<TreeviewSelect>>", self._carregar_autorizado_para_edicao) 
        
    def _carregar_pendente_para_aprovacao(self, event):
        selection = self.tree_pendentes.focus()
        if not selection: return

        dados = self.tree_pendentes.item(selection, 'values')
        self.jogador_selecionado_dados_originais = list(dados) 
        
        self._limpar_campos_admin()
        self._alternar_botoes('PENDENTE')

        for i, col_name in enumerate(self.COLUNAS_AUTORIZADOS):
            self.entries_admin[col_name].config(state='normal') 
            self.entries_admin[col_name].delete(0, tk.END)
            valor = dados[i] if i < len(dados) else '' 
            self.entries_admin[col_name].insert(0, valor)
            
    def _carregar_autorizado_para_edicao(self, event):
        selection = self.tree_autorizados.focus()
        if not selection: return

        dados = self.tree_autorizados.item(selection, 'values')
        self.jogador_selecionado_dados_originais = list(dados) 
        
        self._limpar_campos_admin()
        self._alternar_botoes('AUTORIZADO') 

        for i, col_name in enumerate(self.COLUNAS_AUTORIZADOS):
            self.entries_admin[col_name].config(state='normal') 
            self.entries_admin[col_name].delete(0, tk.END)
            self.entries_admin[col_name].insert(0, dados[i])

    def aprovar_jogador(self):
        selection = self.tree_pendentes.focus()
        if not selection:
            messagebox.showwarning("Aviso", "Nenhum jogador pendente selecionado para aprovação.")
            return

        dados_originais = self.tree_pendentes.item(selection, 'values')
        if not dados_originais:
            messagebox.showwarning("Aviso", "Não foi possível recuperar os dados do jogador selecionado.")
            return
        
        dados_editados = [self.entries_admin.get(col_name).get().strip() for col_name in self.COLUNAS_AUTORIZADOS]

        if not self._validar_campos(dados_editados, modo_admin=True): return
        
        if self._adicionar_registro(self.ARQUIVO_AUTORIZADOS, dados_editados, self.COLUNAS_AUTORIZADOS):
            if self._remover_registro_por_dados(self.ARQUIVO_PENDENTES, dados_originais, self.COLUNAS_AUTORIZADOS): 
                messagebox.showinfo("Sucesso", f"O jogador **{dados_editados[0]}** foi aprovado e autorizado com sucesso!")
                self._carregar_admin_dados()
                # APROVOU? Atualiza a lista de boletos na próxima carga para definir o vencimento inicial.
                self._carregar_dados_times_boletos()
            else:
                messagebox.showwarning("Aviso", f"O jogador {dados_editados[0]} foi adicionado a autorizados, mas a remoção de pendentes falhou. Por favor, remova manualmente de 'pendentes'.")
        else:
            messagebox.showerror("Erro", "Falha ao adicionar jogador à lista de autorizados.")

    def rejeitar_jogador(self):
        selection = self.tree_pendentes.focus()
        if not selection:
            messagebox.showwarning("Aviso", "Nenhum jogador pendente selecionado para rejeição.")
            return
            
        dados_originais = self.tree_pendentes.item(selection, 'values')
        if not dados_originais:
            messagebox.showwarning("Aviso", "Não foi possível recuperar os dados do jogador selecionado.")
            return
        
        if not messagebox.askyesno("Confirmar Rejeição", f"Tem certeza que deseja rejeitar o cadastro de **{dados_originais[0]}**?"):
            return

        if self._remover_registro_por_dados(self.ARQUIVO_PENDENTES, dados_originais, self.COLUNAS_AUTORIZADOS):
            messagebox.showinfo("Sucesso", f"O cadastro de **{dados_originais[0]}** foi rejeitado e removido da lista de pendentes.")
            self._carregar_admin_dados()
        else:
            messagebox.showerror("Erro", "Falha ao remover jogador da lista de pendentes.")

    def editar_jogador_autorizado(self):
        dados_antigos = self.jogador_selecionado_dados_originais
        
        # Correção anterior: Tenta pegar a seleção ativa na Treeview se a variável do formulário estiver vazia
        if not dados_antigos:
            selection = self.tree_autorizados.focus()
            if selection:
                dados_antigos = self.tree_autorizados.item(selection, 'values')
        
        if not dados_antigos:
            messagebox.showwarning("Aviso", "Nenhum jogador autorizado selecionado para edição.")
            return

        novos_dados = [self.entries_admin.get(col_name).get().strip() for col_name in self.COLUNAS_AUTORIZADOS]
        
        if not self._validar_campos(novos_dados, modo_admin=True): return

        cpf_antigo = dados_antigos[self.COLUNAS_AUTORIZADOS.index('CPF_do_Responsavel')].strip()
        cpf_novo = novos_dados[self.COLUNAS_AUTORIZADOS.index('CPF_do_Responsavel')].strip()
        
        if cpf_antigo != cpf_novo and self._verificar_duplicidade(novos_dados):
            messagebox.showwarning("Duplicidade", "O novo CPF de Responsável ou Jogador já está em uso.")
            return

        # Chamada da função atualizada com busca por CPF
        if self._atualizar_registro_por_dados(self.ARQUIVO_AUTORIZADOS, dados_antigos, novos_dados, self.COLUNAS_AUTORIZADOS):
            messagebox.showinfo("Sucesso", f"Dados do jogador **{novos_dados[0]}** atualizados com sucesso!")
            self._carregar_admin_dados()
            # EDITOU? Atualiza a lista de boletos na próxima carga.
            self._carregar_dados_times_boletos()
        else:
            messagebox.showerror("Erro", "Falha ao atualizar dados do jogador autorizado.")

    def remover_jogador_autorizado_form(self):
        selection = self.tree_autorizados.focus()
        
        if selection:
            dados_originais = self.tree_autorizados.item(selection, 'values')
        else:
            dados_originais = self.jogador_selecionado_dados_originais
        
        if not dados_originais:
            messagebox.showwarning("Aviso", "Nenhum jogador autorizado selecionado para remoção.")
            return
            
        nome_jogador = dados_originais[0]
        
        if not messagebox.askyesno("Confirmar Remoção", f"Tem certeza que deseja remover **{nome_jogador}** da lista de Autorizados (e da Turma)?"):
            return

        # Chamada da função atualizada com busca por CPF
        if self._remover_registro_por_dados(self.ARQUIVO_AUTORIZADOS, dados_originais, self.COLUNAS_AUTORIZADOS):
            messagebox.showinfo("Sucesso", f"O jogador **{nome_jogador}** foi removido com sucesso!")
            self._carregar_admin_dados()
            # REMOVEU? Atualiza a lista de boletos na próxima carga.
            self._carregar_dados_times_boletos()
        else:
            messagebox.showerror("Erro", "Falha ao remover jogador da lista de autorizados.")

    def excluir_jogador_autorizado(self):
        selection = self.tree_autorizados.focus()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um jogador na lista de autorizados para excluir.")
            return
            
        dados = self.tree_autorizados.item(selection, 'values')
        if not dados: return
        
        if not messagebox.askyesno("Confirmar Exclusão Rápida", f"Tem certeza que deseja EXCLUIR **{dados[0]}** da lista de Autorizados (e da Turma)?"):
            return

        if self._remover_registro_por_dados(self.ARQUIVO_AUTORIZADOS, dados, self.COLUNAS_AUTORIZADOS):
            messagebox.showinfo("Sucesso", f"O jogador **{dados[0]}** foi excluído com sucesso!")
            self.tree_autorizados.delete(selection)
            self._limpar_campos_admin()
        else:
            messagebox.showerror("Erro", "Falha ao excluir jogador da lista de autorizados.")

    def _criar_aba_times(self, aba):
        paned_window = ttk.PanedWindow(aba, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, pady=5)
        frame_times_container = ttk.LabelFrame(paned_window, text="Times", padding=10)
        paned_window.add(frame_times_container, weight=1)
        label_times = ttk.Label(frame_times_container, text="Contagem de Jogadores por Time (Agrupado por Turma)", font=("Times New Roman", 12, 'bold'))
        label_times.pack(pady=5)
        frame_tree_times = ttk.Frame(frame_times_container)
        frame_tree_times.pack(fill="both", expand=True)
        self.tree_times = self._criar_treeview_com_scroll(frame_tree_times, colunas=("time", "jogadores"), tree_style_name="Times.Treeview")
        self.tree_times.heading("time", text="Nome do Time/Turma")
        self.tree_times.column("time", width=200, minwidth=150)
        self.tree_times.heading("jogadores", text="Nº Jogadores")
        self.tree_times.column("jogadores", width=100, minwidth=80, anchor='center')
        self.tree_times.bind("<<TreeviewSelect>>", self._mostrar_jogadores)
        frame_det = ttk.LabelFrame(paned_window, text="Jogadores do Time", padding=10)
        paned_window.add(frame_det, weight=2)
        self.label_det_jogadores = ttk.Label(frame_det, text="Selecione um time ao lado para ver os jogadores.", font=("Times New Roman", 12))
        self.label_det_jogadores.pack(pady=5)
        frame_tree_jogadores = ttk.Frame(frame_det)
        frame_tree_jogadores.pack(fill="both", expand=True)
        self.tree_jogadores = self._criar_treeview_com_scroll(frame_tree_jogadores, colunas=("nome", "cpf_jogador", "data_nasc", "responsavel"), tree_style_name='Custom.Treeview', altura=10)
        self.tree_jogadores.heading("nome", text="Nome do Jogador"); self.tree_jogadores.column("nome", width=150, minwidth=100)
        self.tree_jogadores.heading("cpf_jogador", text="CPF Jogador"); self.tree_jogadores.column("cpf_jogador", width=120, minwidth=80)
        self.tree_jogadores.heading("data_nasc", text="Nascimento"); self.tree_jogadores.column("data_nasc", width=100, minwidth=80)
        self.tree_jogadores.heading("responsavel", text="Responsável"); self.tree_jogadores.column("responsavel", width=150, minwidth=100)
        
    def _mostrar_jogadores(self, event):
        selection = self.tree_times.focus()
        if not selection: return
        valores = self.tree_times.item(selection)
        time = valores["text"] 
        self.label_det_jogadores.config(text=f"Jogadores do {time}")
        self.tree_jogadores.delete(*self.tree_jogadores.get_children())
        if time in self.times:
            for jogador in self.times[time]:
                nome = jogador.get('Nome_do_Jogador', 'N/A'); cpf_jogador = jogador.get('CPF_do_Jogador', 'N/A')
                data_nasc = jogador.get('Data_de_Nascimento', 'N/A'); responsavel = jogador.get('Nome_do_Responsavel', 'N/A')
                self.tree_jogadores.insert("", tk.END, values=(nome, cpf_jogador, data_nasc, responsavel))

    def _criar_aba_boletos(self, aba):
        frame_boletos_container = ttk.LabelFrame(aba, text="Controle de Pagamentos", padding=10)
        frame_boletos_container.pack(fill="both", expand=True, pady=5)
        label_boletos = ttk.Label(frame_boletos_container, text="Status de Pagamento dos Jogadores", font=("Times New Roman", 12, 'bold'))
        label_boletos.pack(pady=5)
        frame_tree_boletos = ttk.Frame(frame_boletos_container)
        frame_tree_boletos.pack(fill="both", expand=True, pady=10)
        
        colunas_boleto_display = [c.lower().replace('_', '_') for c in self.COLUNAS_BOLETO] 
        self.tree_boletos = self._criar_treeview_com_scroll(
            frame_tree_boletos, 
            colunas=colunas_boleto_display, 
            tree_style_name="Boleto.Treeview", 
            altura=10
        )
        
        self.tree_boletos.heading("nome_do_responsavel", text="Responsável"); 
        self.tree_boletos.column("nome_do_responsavel", width=150, minwidth=100)
        self.tree_boletos.heading("nome_do_jogador", text="Nome do Jogador"); 
        self.tree_boletos.column("nome_do_jogador", width=150, minwidth=100)
        self.tree_boletos.heading("cpf_do_responsavel", text="CPF Resp."); 
        self.tree_boletos.column("cpf_do_responsavel", width=100, minwidth=80)
        self.tree_boletos.heading("tel_do_responsavel", text="Telefone Resp."); 
        self.tree_boletos.column("tel_do_responsavel", width=100, minwidth=80)
        self.tree_boletos.heading("turma", text="Turma"); 
        self.tree_boletos.column("turma", width=80, minwidth=50, anchor='center')
        self.tree_boletos.heading("vencimento", text="Vencimento"); 
        self.tree_boletos.column("vencimento", width=100, minwidth=80, anchor='center')
        self.tree_boletos.heading("status", text="Status"); 
        self.tree_boletos.column("status", width=100, minwidth=80, anchor='center')
        
        self.tree_boletos.tag_configure('pago', background='#D4EFDF', foreground='#145A32')
        self.tree_boletos.tag_configure('pendente', background='#FADBD8', foreground='#922B21')
        frame_botoes_boleto = ttk.Frame(frame_boletos_container)
        frame_botoes_boleto.pack(pady=5, fill="x")
        ttk.Button(frame_botoes_boleto, text="✅ Simular Pagamento (Próximo Status)", command=self._simular_pagamento, style='Principal.TButton').pack(side="left", padx=5)
        ttk.Button(frame_botoes_boleto, text="🔄 Recarregar Dados", command=self._carregar_dados_times_boletos).pack(side="left", padx=5)

    def _simular_pagamento(self):
        selected_item = self.tree_boletos.focus()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione um jogador na lista de boletos.")
            return
            
        current_values = list(self.tree_boletos.item(selected_item, 'values'))
        current_status = current_values[6] # Status é a última coluna na lista (índice 6)
        current_vencimento = current_values[5] # Vencimento é a penúltima coluna (índice 5)
        cpf_responsavel_selecionado = current_values[2] # CPF é a terceira coluna (índice 2)

        novo_status = "Pago" if current_status == "Pendente" else "Pendente"
        novo_vencimento = current_vencimento # Inicialmente, mantém o vencimento atual

        # --- LÓGICA DE RECORRÊNCIA: ATUALIZA O VENCIMENTO PARA O PRÓXIMO MÊS APÓS PAGAMENTO ---
        if novo_status == "Pago":
            try:
                data_atual = datetime.strptime(current_vencimento, '%d/%m/%Y')
                
                # 1. Calcula o próximo mês e ano
                next_month = data_atual.month + 1
                next_year = data_atual.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                
                # 2. Tenta manter o mesmo dia. Se o dia (ex: 31) não existir (ex: em Fev), decrementa o dia.
                day_to_use = data_atual.day
                data_proximo_mes = None
                while day_to_use > 0:
                    try:
                        data_proximo_mes = datetime(next_year, next_month, day_to_use)
                        break
                    except ValueError:
                        day_to_use -= 1
                
                if data_proximo_mes:
                    novo_vencimento = data_proximo_mes.strftime('%d/%m/%Y')
                
            except Exception as e:
                print(f"Erro ao calcular novo vencimento: {e}")
                # Se falhar, novo_vencimento permanece com o valor antigo (current_vencimento)
                pass 
        # --- FIM DA LÓGICA DE RECORRÊNCIA ---


        # 1. Atualiza o array interno de boletos
        for boleto in self.boletos:
            if boleto.get(self.CHAVE_CADASTRO) == cpf_responsavel_selecionado:
                boleto['Status'] = novo_status
                if novo_status == "Pago":
                    boleto['Vencimento'] = novo_vencimento # Atualiza o Vencimento no array
                break
        
        # 2. Atualiza o Treeview
        tag = 'pago' if novo_status == "Pago" else 'pendente'
        current_values[6] = novo_status # Atualiza o Status no Treeview
        current_values[5] = novo_vencimento # Atualiza o Vencimento no Treeview
        
        self.tree_boletos.item(selected_item, values=current_values, tags=(tag,))
        
        # 3. Persiste a alteração no Google Sheets
        if self._atualizar_sheet_boletos():
            messagebox.showinfo("Sucesso", f"Status de pagamento alterado para **{novo_status}**. Próximo vencimento: **{novo_vencimento}**. Dados salvos no Sheets.")
        else:
            messagebox.showwarning("Aviso", f"Status alterado para **{novo_status}**, mas falha ao salvar no Google Sheets.")

    def _carregar_dados_times_boletos(self):
        self.times = {}
        self.boletos = []
        
        # --- NOVO CÁLCULO DO VENCIMENTO INICIAL (1 MÊS APÓS HOJE) ---
        hoje = datetime.now()
        
        day = hoje.day
        month = hoje.month + 1
        year = hoje.year
        
        if month > 12:
            month = 1
            year += 1
            
        data_vencimento_padrao = hoje.strftime('%d/%m/%Y') # Valor padrão de segurança

        # Tenta manter o mesmo dia. Se o dia (ex: 31) não existir (ex: em Fev), decrementa o dia.
        day_to_use = day
        data_proximo_mes = None
        while day_to_use > 0:
            try:
                data_proximo_mes = datetime(year, month, day_to_use)
                break
            except ValueError:
                day_to_use -= 1
        
        if data_proximo_mes:
            data_vencimento_padrao = data_proximo_mes.strftime('%d/%m/%Y')
        else:
             # Se falhar o cálculo robusto, usa o dia 1 do próximo mês como segurança
            data_vencimento_padrao = datetime(year, month, 1).strftime('%d/%m/%Y') 
        # --- FIM DO CÁLCULO DO VENCIMENTO INICIAL ---
        
        # 1. Carrega dados de aprovados (Fonte principal para informações do jogador)
        dados_aprovados_raw = self._ler_todos_dados(self.ARQUIVO_AUTORIZADOS, self.COLUNAS_AUTORIZADOS)
        
        # 2. Carrega dados de boletos persistidos (Fonte para Status e Vencimento atualizados)
        dados_boletos_sheets = self._ler_todos_dados(self.ARQUIVO_BOLETOS, self.COLUNAS_BOLETO)
        boletos_map_sheets = {} # {CPF_do_Responsavel: {Vencimento: '...', Status: '...'}}
        for row in dados_boletos_sheets:
            if len(row) >= len(self.COLUNAS_BOLETO):
                boleto_dict = dict(zip(self.COLUNAS_BOLETO, row))
                cpf = boleto_dict.get('CPF_do_Responsavel', '').strip()
                if cpf:
                    boletos_map_sheets[cpf] = boleto_dict
        
        # Limpa as Treeviews
        self.tree_times.delete(*self.tree_times.get_children())
        self.tree_jogadores.delete(*self.tree_jogadores.get_children())
        self.tree_boletos.delete(*self.tree_boletos.get_children())

        # 3. Processar e consolidar dados
        boletos_a_salvar = []
        for row_values in dados_aprovados_raw:
            try:
                if len(row_values) < len(self.COLUNAS_AUTORIZADOS):
                     row_values += [''] * (len(self.COLUNAS_AUTORIZADOS) - len(row_values))

                jogador_data = dict(zip(self.COLUNAS_AUTORIZADOS, row_values))
                turma = jogador_data.get('Turma', '').strip()
                cpf_responsavel = jogador_data.get('CPF_do_Responsavel', '').strip()
                
                if not turma or not cpf_responsavel: continue

                # --- Lógica de Times ---
                if turma not in self.times:
                    self.times[turma] = []
                self.times[turma].append(jogador_data)
                
                # --- Lógica de Boletos (Consolidação e Padrão) ---
                dados_persistidos = boletos_map_sheets.get(cpf_responsavel, {})
                
                boleto_data = {
                    'Nome_do_Responsavel': jogador_data['Nome_do_Responsavel'],
                    'Nome_do_Jogador': jogador_data['Nome_do_Jogador'],
                    'CPF_do_Responsavel': cpf_responsavel,
                    'Tel_do_Responsavel': jogador_data['Tel_do_Responsavel'],
                    'Turma': turma,
                    # Se não houver persistência (é novo), usa o novo cálculo. Senão, usa o valor persistido.
                    'Vencimento': dados_persistidos.get('Vencimento', data_vencimento_padrao), 
                    'Status': dados_persistidos.get('Status', 'Pendente') 
                }
                self.boletos.append(boleto_data)
                boletos_a_salvar.append(boleto_data) # Armazena para salvar no Sheets
                
            except Exception as e:
                print(f"Erro ao processar linha de jogador aprovado: {e}")
                continue
                
        # 4. Salva a lista consolidada (incluindo novos vencimentos iniciais)
        if boletos_a_salvar:
             self._atualizar_sheet_boletos(boletos_a_salvar)
        
        # 5. Preencher a Treeview de Times
        for time, jogadores in self.times.items():
            self.tree_times.insert("", tk.END, text=time, values=(time, len(jogadores)))

        # 6. Preencher a Treeview de Boletos
        for boleto in self.boletos:
            status = boleto['Status']
            tag = 'pago' if status == 'Pago' else 'pendente'
            
            # Garante que a tupla de valores está na ordem correta
            values_tuple = [boleto.get(col, '') for col in self.COLUNAS_BOLETO]
            self.tree_boletos.insert("", tk.END, values=values_tuple, tags=(tag,))

        self.label_det_jogadores.config(text="Selecione um time ao lado para ver os jogadores.")
        
    def _atualizar_sheet_boletos(self, dados=None):
        """Salva a lista completa de boletos (status, vencimento) no Google Sheets."""
        try:
            if dados is None: dados = self.boletos
            sheet = self._sheet_por_nome(self.ARQUIVO_BOLETOS)
            
            # 1. Monta a lista de linhas a serem salvas
            linhas_a_salvar = []
            for boleto in dados:
                linha = [boleto.get(col, '') for col in self.COLUNAS_BOLETO]
                linhas_a_salvar.append(linha)
            
            # 2. Apaga e re-insere (método mais simples de atualização em gspread)
            sheet.clear() 
            sheet.append_row(self.COLUNAS_BOLETO) 
            if linhas_a_salvar:
                sheet.append_rows(linhas_a_salvar) 
                
            return True
        except Exception as e:
            messagebox.showerror("Erro GSheets", f"Falha ao salvar dados de boletos no Sheets: {e}")
            return False

    def _validar_campos(self, dados_completos, modo_admin=False):
        colunas = self.COLUNAS_AUTORIZADOS if modo_admin else self.COLUNAS_CADASTRO
        dados_map = dict(zip(colunas, dados_completos))
        
        campos_obg = ['Nome_do_Jogador', 'CPF_do_Responsavel']
        if modo_admin:
            campos_obg.append('Turma')

        for campo in campos_obg:
            if not dados_map.get(campo, '').strip():
                messagebox.showerror("Erro de Validação", f"O campo **{campo.replace('_', ' ')}** é obrigatório.")
                return False
        
        cpf_resp = dados_map['CPF_do_Responsavel'].replace('.', '').replace('-', '').strip()
        data_nasc = dados_map.get('Data_de_Nascimento', '').strip()
        
        if cpf_resp and not re.match(r'^\d{11}$', cpf_resp):
            messagebox.showerror("Erro de Validação", "O CPF do Responsável deve conter 11 dígitos.")
            return False

        if data_nasc:
            try: datetime.strptime(data_nasc, '%d/%m/%Y')
            except ValueError: messagebox.showerror("Erro de Validação", "A Data de Nascimento deve estar no formato **DD/MM/AAAA**."); return False
        
        return True

    def _verificar_duplicidade(self, dados_completos):
        colunas_check = self.COLUNAS_AUTORIZADOS 
        
        if len(dados_completos) == len(self.COLUNAS_CADASTRO):
            dados_map = dict(zip(self.COLUNAS_CADASTRO, dados_completos))
        else:
            dados_map = dict(zip(self.COLUNAS_AUTORIZADOS, dados_completos))
        
        cpf_responsavel = dados_map.get('CPF_do_Responsavel', '').strip()
        cpf_jogador = dados_map.get('CPF_do_Jogador', '').strip()
        
        todas_as_linhas = (
            self._ler_todos_dados(self.ARQUIVO_PENDENTES, colunas_check) +
            self._ler_todos_dados(self.ARQUIVO_AUTORIZADOS, colunas_check)
        )
        
        for linha in todas_as_linhas:
            linha_norm = linha + [''] * (len(colunas_check) - len(linha)) 
            linha_map = dict(zip(colunas_check, [c.strip() for c in linha_norm]))

            if cpf_responsavel and linha_map.get('CPF_do_Responsavel') == cpf_responsavel: return True
            if cpf_jogador and linha_map.get('CPF_do_Jogador') == cpf_jogador: return True
                
        return False
        
    def _ler_todos_dados(self, nome_arquivo, colunas):
        try:
            sheet = self._sheet_por_nome(nome_arquivo); all_vals = sheet.get_all_values()
            if not all_vals or len(all_vals) <= 1: return []
            rows = all_vals[1:]; normalized = []
            for r in rows:
                if len(r) < len(colunas): r = r + [''] * (len(colunas) - len(r))
                normalized.append(r[:len(colunas)]) # Garante que só pega as colunas que importam
            return normalized
        except Exception as e:
            print(f"Erro ao ler dados do Google Sheets ({nome_arquivo}): {e}")
            messagebox.showwarning("Erro de Leitura", f"Falha ao ler a aba '{nome_arquivo}'. Verifique a conexão e permissões.")
            return []

    def _adicionar_registro(self, nome_arquivo, dados, colunas):
        try:
            sheet = self._sheet_por_nome(nome_arquivo)
            if len(dados) < len(colunas): dados = dados + [''] * (len(colunas) - len(dados))
            sheet.append_row(dados)
            return True
        except Exception as e:
            messagebox.showerror("Erro ao Adicionar", f"Falha ao adicionar registro em '{nome_arquivo}': {e}")
            return False

    def _remover_registro_por_dados(self, nome_arquivo, dados_chave, colunas):
        try:
            sheet = self._sheet_por_nome(nome_arquivo)
            all_data = self._ler_todos_dados(nome_arquivo, colunas)
            
            index_cpf_resp = colunas.index('CPF_do_Responsavel')
            cpf_chave = dados_chave[index_cpf_resp].strip()
            
            # Encontra a linha que corresponde ao CPF do Responsável (e idealmente ao Nome do Jogador)
            for i, row in enumerate(all_data):
                if len(row) > index_cpf_resp and row[index_cpf_resp].strip() == cpf_chave:
                    # Se for um nome de jogador diferente, ele ainda pode ter o mesmo CPF do responsável.
                    # Adicionamos uma verificação extra para maior segurança (usando o primeiro campo, Nome_do_Jogador)
                    if row[0].strip() == dados_chave[0].strip():
                        sheet.delete_rows(i + 2) # +2 para ignorar o índice 0 e o cabeçalho
                        return True
            return False
        except Exception as e:
            messagebox.showerror("Erro ao Remover", f"Falha ao remover registro em '{nome_arquivo}': {e}")
            return False

    def _atualizar_registro_por_dados(self, nome_arquivo, dados_antigos, novos_dados, colunas):
        try:
            sheet = self._sheet_por_nome(nome_arquivo)
            all_data = self._ler_todos_dados(nome_arquivo, colunas)
            
            index_cpf_resp = colunas.index('CPF_do_Responsavel')
            cpf_chave = dados_antigos[index_cpf_resp].strip()
            nome_jogador_antigo = dados_antigos[0].strip()
            
            # Encontra a linha que corresponde ao CPF do Responsável e Nome do Jogador antigo
            for i, row in enumerate(all_data):
                if len(row) > index_cpf_resp and row[index_cpf_resp].strip() == cpf_chave and row[0].strip() == nome_jogador_antigo:
                    # +2 para obter o número da linha real (ignorando o cabeçalho)
                    sheet.update(f'A{i + 2}', [novos_dados]) 
                    return True
            return False
        except Exception as e:
            messagebox.showerror("Erro ao Atualizar", f"Falha ao atualizar registro em '{nome_arquivo}': {e}")
            return False

    def _carregar_admin_dados(self):
        self.tree_pendentes.delete(*self.tree_pendentes.get_children())
        self.tree_autorizados.delete(*self.tree_autorizados.get_children())
        self._limpar_campos_admin()

        dados_pendentes = self._ler_todos_dados(self.ARQUIVO_PENDENTES, self.COLUNAS_AUTORIZADOS)
        for dados in dados_pendentes:
            self.tree_pendentes.insert("", tk.END, values=dados, tags=('pendente',))

        dados_autorizados = self._ler_todos_dados(self.ARQUIVO_AUTORIZADOS, self.COLUNAS_AUTORIZADOS)
        for dados in dados_autorizados:
            self.tree_autorizados.insert("", tk.END, values=dados, tags=('autorizado',))

if __name__ == '__main__':
    root = tk.Tk()
    app = FutsalAdminApp(root)
    root.mainloop()