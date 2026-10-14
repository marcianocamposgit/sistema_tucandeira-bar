import tkinter as tk
from tkinter import messagebox
from itertools import groupby

BG_COLOR = "#004d26"
BTN_COLOR = "#000000"
TEXT_COLOR = "#ffffff"
ACCENT_COLOR = "#c0c0c0"
HIGHLIGHT_COLOR = "#ffcc00"

def abrir_tela_pedido_view(root, mesa_id, CARDAPIO, atualizar_estoque_callback, escolher_forma_pagamento_callback):
    janela_pedido = tk.Toplevel(root)
    janela_pedido.title(f"Pedido - {'Mesa ' + str(mesa_id) if mesa_id else 'Balcão'}")
    janela_pedido.geometry("420x550")
    janela_pedido.configure(bg=BG_COLOR)
    
    itens_selecionados = []
    total_valor = tk.DoubleVar(value=0.0)

    def atualizar_total():
        total = sum(item["preco"] * item["qtd"] for item in itens_selecionados)
        total_valor.set(round(total, 2))

    def adicionar_item(produto):
        for item in itens_selecionados:
            if item["nome"] == produto["nome"]:
                item["qtd"] += 1
                atualizar_total()
                return
        itens_selecionados.append({
            "nome": produto["nome"],
            "preco": produto["preco"],
            "qtd": 1
        })
        atualizar_total()

    # === CABEÇALHO ===
    tk.Label(janela_pedido, text="CARDÁPIO", font=("Impact", 18), bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=10)

    # === ÁREA DE ROLAGEM ===
    canvas = tk.Canvas(janela_pedido, bg=BG_COLOR)
    scrollbar = tk.Scrollbar(janela_pedido, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # === CARDÁPIO AGRUPADO POR CATEGORIA ===
    produtos_ordenados = sorted(CARDAPIO, key=lambda x: x["categoria"])
    for categoria, grupo in groupby(produtos_ordenados, key=lambda x: x["categoria"]):
        icon = "🍺" if categoria == "Bebida" else "🥩" if categoria == "Tira-Gosto" else "🚬" if categoria == "Cigarro" else "🥟"
        tk.Label(scrollable_frame, text=f"{icon} {categoria.upper()}",
                 bg=BG_COLOR, fg=ACCENT_COLOR, font=("Impact", 14), anchor="w").pack(fill="x", padx=10, pady=(12, 6))
        
        for prod in grupo:
            frame = tk.Frame(scrollable_frame, bg=BG_COLOR)
            frame.pack(fill="x", padx=20, pady=3)
            
            estoque_txt = f" ({prod['estoque']} und)" if prod["estoque"] <= 10 else ""
            tk.Label(frame, text=f"{prod['nome']} — R$ {prod['preco']:.2f}{estoque_txt}",
                     bg=BG_COLOR, fg=TEXT_COLOR, anchor="w").pack(side="left")
            
            btn_add = tk.Button(frame, text="+", 
                                command=lambda p=prod: (
                                    adicionar_item(p),
                                    atualizar_estoque_callback(p["nome"])
                                ),
                                bg=BTN_COLOR, fg=ACCENT_COLOR, width=3)
            btn_add.pack(side="right")

    # === EMPACOTAR SCROLL ===
    canvas.pack(side="left", fill="both", expand=True, padx=10)
    scrollbar.pack(side="right", fill="y")

    # === TOTAL E FECHAMENTO ===
    frame_total = tk.Frame(janela_pedido, bg=BG_COLOR)
    frame_total.pack(pady=10, padx=10, fill="x")
    tk.Label(frame_total, text="Total:", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Impact", 14)).pack()
    tk.Label(frame_total, textvariable=total_valor, bg=BG_COLOR, fg=HIGHLIGHT_COLOR, font=("Impact", 16)).pack()

    def fechar_conta():
        if total_valor.get() == 0:
            messagebox.showwarning("Atenção", "Nenhum item adicionado!")
            return
        escolher_forma_pagamento_callback(total_valor.get(), janela_pedido, mesa_id)

    tk.Button(janela_pedido, text="💰 FECHAR CONTA", command=fechar_conta,
              bg=HIGHLIGHT_COLOR, fg="#000", font=("Impact", 12), height=2).pack(pady=10, padx=20, fill="x")