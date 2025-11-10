# ⚽ Futsal Data Collector

Este é um projeto simples e funcional desenvolvido em Python com o framework Flask. Seu objetivo principal é fornecer uma interface web para o **cadastro de atletas e seus responsáveis** em uma escolinha ou liga de futsal, com a possibilidade de **exportação imediata dos dados em formato CSV**.

A aplicação foi otimizada para ser leve e está configurada para deploy contínuo na plataforma Vercel.

## 🚀 Funcionalidades Principais
* **Formulário Web Completo:** Coleta informações essenciais do Responsável (Nome, E-mail, CPF, Telefone, Endereço) e do Atleta (Nome, CPF).
* **Validação de Dados no Servidor:** Implementa regras de validação seguras em Python:
    * **E-mail:** Verifica a presença do caractere `@`.
    * **CPF:** Limpa (remove pontos/hífens) e verifica se há **exatamente 11 dígitos**.
* **Exportação CSV:** Rota dedicada que gera e força o download dos dados cadastrados em um arquivo `.csv` para uso em planilhas (Excel, Google Sheets).

## ⚙️ Tecnologias Envolvidas
| Categoria | Tecnologia | Uso no Projeto |
| :--- | :--- | :--- |
| **Backend** | Python 3.x | Linguagem principal para lógica e servidor. |
| **Framework** | Flask | Micro-framework web para roteamento e requisições HTTP. |
| **Templates** | Jinja2 | Motor de templates para renderizar o HTML dinamicamente. |
| **Deploy** | Vercel | Plataforma de hosting para deploy contínuo via GitHub. |

---

## 🛠️ Como Rodar Localmente (Desenvolvimento)

Siga estas instruções para executar a aplicação em sua máquina local.

### 1. Instalação em Python

Você precisará do **Python 3** e do seu gerenciador de pacotes, o **pip**.

#### 📥 Baixar o Python:

* Acesse o site oficial: [**python.org/downloads/**](https://www.python.org/downloads/)
* Baixe o instalador mais recente para o seu sistema operacional (Windows, macOS ou Linux).

#### ⚠️ Configuração Crítica (Windows)

Durante a instalação no Windows, é **crucial** marcar a caixa de seleção:

> ✅ **"Add python.exe to PATH"**

Marcar essa opção garante que você possa usar os comandos `python` e `pip` diretamente no seu terminal. Se você esquecer, terá que usar `py` ou configurar o PATH manualmente.

<br>

---------------------------------------------
## Conectando a API - GABRIEL

<h5>Tarefa :</h5>

<p>Conectar a parte do cadastro do Otávio com a API do google Sheets, utlizando as princiapis tecnlogias do mercado, e conecatr com a parte do Matheus, ao abrir o programa temq eu mostrar a lista de espera.</p>

<h9>*OBSERVAÇÃO 1*: **VOCÊ VAI MEXER DESDA DA CONFIGURAÇÃO DO GOOGLE SHEETS, ATE NO NOSSO CÓDIGO PARA VER SE ESTÁ PUXANDO CERTO OU NÃO**</h9>

<br>

<p>Página Web</p>
<img src="/images/cadastro_template.png">
<h2> Assim que forem cadastrados deveram aparecerem na lista dos aprovados </h2>

<p>Jogadores pendendes</p>
<img src="/images/jogadores_pendentes.png">
<h2> Assim que forem aprovados deveram aparecerem na lista dos aprovados </h2>

<br>

<h9>*OBSERVAÇÃO 2*: **QUALQUER ALTERAÇÃO NO CÓDIGO VOCÊ PODERA FAZER SEM AVISO PREVIO**</h9>
<br>

---------------------------------------------
## Criação da Página Web Utilizando Python - OTAVIO

<h5>Tarefa :</h5>

<p>Fazer uma página web em python utilizando a estrutura de pasta a baixo, utilizando as princiapis tecnologias do mercado de trabalho.</p>

```
futsal-api-python/  
├── index.py — Otávio -> ponto de entrada da aplicação; contém a app Flask e rotas  
├── requirements.txt —> Matheus Bezerra  
├── vercel.json —> Matheus Bezerra
└── templates/  
    └── formulario.html —> Otávio
```



1. Atualize pip (opcional, mas recomendado)
```bash
pip install --upgrade 
```

2. Instale as dependências a partir do 
```bash
pip install -r requirements.txt
```

3. Instalar o Flask:
```bash
pip install Flask
```
<br>

<h9>**Sua página de cadastro precisa ter:**<h9>

- Nome do Responsavel
- CPF do Responsavel
- Tel do Responsavel
- Endereço do Responsavel
- Nome do Jogador
- Idade do Jogador
<br>
<p>Template a seguir, logo a baixo</p>
<img src="/images/cadastro_template.png">

---------------------------------------------

## Criação da Interface de Times e Boleto - LUIZ

<h5>Tarefa :</h5>

<p>Fazer 2 interface juntos de Times e Boletos. Ao clicar no Times vai mostrar quais são os jogadores que estão neste times.</p>

<img src="/images/Times.png">
<img src="/images/Time_Click.png">

<br>

<p>Depois fazer outra para boleto se está pago ou não.</p>

<img src="/images/Boletos.png">


