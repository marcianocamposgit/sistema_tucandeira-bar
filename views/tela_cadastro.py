import tkinter as tk
from tkinter import ttk, messagebox

BG_COLOR = "#004d26"
BTN_COLOR = "#000000"
TEXT_COLOR = "#ffffff"
ACCENT_COLOR = "#c0c0c0"
HIGHLIGHT_COLOR = "#ffcc00"

def abrir_tela_cadastro(root, CARDAPIO):
    janela = tk.Toplevel(root)
    janela.title("➕ Novo Produto")
    janela.geometry("380x280")
    janela.configure(bg=BG_COLOR)
    
    tk.Label(janela, text="Nome do Produto:", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 11)).pack(pady=(10, 2))
    entry_nome = tk.Entry(janela, width=40, font=("Arial", 11))
    entry_nome.pack(pady=2)

    tk.Label(janela, text="Categoria:", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 11)).pack(pady=(8, 2))
    categorias = ["Bebida", "Tira-Gosto", "Lanche", "Cigarro"]
    combo_cat = ttk.Combobox(janela, values=categorias, state="readonly", font=("Arial", 10))
    combo_cat.set(categorias[0])
    combo_cat.pack(pady=2)

    tk.Label(janela, text="Preço (R$):", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 11)).pack(pady=(8, 2))
    entry_preco = tk.Entry(janela, width=15, font=("Arial", 11))
    entry_preco.pack(pady=2)

    tk.Label(janela, text="Estoque Inicial:", bg=BG_COLOR, fg=TEXT_COLOR, font=("Arial", 11)).pack(pady=(8, 2))
    entry_estoque = tk.Entry(janela, width=15, font=("Arial", 11))
    entry_estoque.insert(0, "0")
    entry_estoque.pack(pady=2)

    def salvar():
        nome = entry_nome.get().strip()
        categoria = combo_cat.get()
        try:
            preco = float(entry_preco.get().replace(",", "."))
            estoque = int(entry_estoque.get() or 0)
            if not nome:
                messagebox.showerror("Erro", "Nome é obrigatório!")
                return
            CARDAPIO.append({
                "nome": nome,
                "categoria": categoria,
                "preco": preco,
                "estoque": estoque
            })
            messagebox.showinfo("Sucesso", f"Produto '{nome}' adicionado!")
            janela.destroy()
        except ValueError:
            messagebox.showerror("Erro", "Preço ou estoque inválido!")

    tk.Button(janela, text="💾 Salvar Produto", command=salvar,
              bg=HIGHLIGHT_COLOR, fg="#000", font=("Impact", 12), height=1).pack(pady=15)