# 🏥 MRI Planning Guide

Guia técnico de planejamento de exames de Ressonância Magnética para Técnicos de Radiologia.

---

## 📋 Pré-requisitos

- Python 3.9 ou superior instalado
- Conexão com a internet (para baixar dependências)

---

## 🚀 Passo a Passo para Rodar o Projeto

### Passo 1 — Baixar / Preparar os arquivos

Coloque a pasta `mri_planning_guide` em qualquer lugar do seu computador.

---

### Passo 2 — Abrir o Terminal

- **Windows:** Pressione `Win + R`, digite `cmd` e pressione Enter.
- **Mac:** Abra o Spotlight (`Cmd + Espaço`), digite `Terminal`.
- **Linux:** Use o atalho do seu sistema.

---

### Passo 3 — Navegar até a pasta do projeto

No terminal, entre na pasta do projeto substituindo o caminho abaixo:

```bash
cd C:\Users\SeuNome\Desktop\mri_planning_guide   # Windows
cd /Users/SeuNome/Desktop/mri_planning_guide      # Mac/Linux
```

---

### Passo 4 — Criar o Ambiente Virtual (recomendado)

Isso isola as dependências do projeto do resto do sistema:

```bash
python -m venv venv
```

Agora **ative** o ambiente virtual:

```bash
# Windows:
venv\Scripts\activate

# Mac / Linux:
source venv/bin/activate
```

Você saberá que funcionou quando aparecer `(venv)` no início da linha do terminal.

---

### Passo 5 — Instalar as dependências

```bash
pip install -r requirements.txt
```

Aguarde o download terminar. Isso só precisa ser feito **uma vez**.

---

### Passo 6 — Rodar a aplicação

```bash
python app.py
```

Você verá algo assim no terminal:

```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

---

### Passo 7 — Acessar no navegador

Abra o seu navegador e acesse:

```
http://127.0.0.1:5000
```

O site já abrirá com 6 categorias e 1 exame de exemplo cadastrados! ✅

---

## 🔐 Acessar a Área Administrativa

Acesse: `http://127.0.0.1:5000/admin/login`

| Campo    | Valor          |
|----------|----------------|
| Usuário  | `admin`        |
| Senha    | `mri@admin2024` |

> ⚠️ **IMPORTANTE:** Antes de colocar em produção, altere a senha no arquivo `app.py` na linha:
> ```python
> ADMIN_PASSWORD = generate_password_hash('SUA_NOVA_SENHA_AQUI')
> ```

---

## 📁 Estrutura do Projeto

```
mri_planning_guide/
├── app.py                   # Aplicação principal (backend Flask)
├── requirements.txt         # Dependências Python
├── mri_guide.db             # Banco de dados SQLite (criado automaticamente)
├── static/
│   └── uploads/             # Imagens enviadas pelo admin
└── templates/
    ├── base.html            # Layout base (navbar, footer)
    ├── index.html           # Página inicial (categorias)
    ├── category.html        # Lista de exames de uma categoria
    ├── exam.html            # Detalhe do protocolo
    └── admin/
        ├── login.html       # Tela de login
        ├── dashboard.html   # Painel admin
        ├── category_form.html
        └── exam_form.html
```

---

## ➕ Como Usar o Admin

1. **Criar uma nova categoria** (ex: "Mama") → `+ CATEGORIA`
2. **Criar um novo exame** → `+ EXAME`
   - Selecione a categoria
   - Digite o nome, descrição, planos de corte, sequências e notas técnicas
   - Faça upload de imagens de planejamento
3. **Editar** qualquer item clicando em ✎
4. **Excluir** com o botão ✕ (confirmação antes de apagar)

---

## 🛑 Para Parar o Servidor

No terminal onde está rodando, pressione `Ctrl + C`.

---

## 🔁 Para Rodar Novamente (depois de fechar)

```bash
# Entre na pasta
cd mri_planning_guide

# Ative o ambiente virtual
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

# Rode
python app.py
```

---

## ❓ Dúvidas Comuns

**"ModuleNotFoundError: No module named 'flask'"**
→ Você esqueceu de instalar as dependências ou ativar o ambiente virtual.

**"Port 5000 already in use"**
→ Altere no final do `app.py`: `app.run(debug=True, port=5001)`

**Perdi o banco de dados**
→ Apague o arquivo `mri_guide.db` e reinicie. Os dados de exemplo voltam automaticamente.
