import tkinter as tk
from tkinter import messagebox

BG_COLOR = "#004d26"
BTN_COLOR = "#000000"
TEXT_COLOR = "#ffffff"
ACCENT_COLOR = "#c0c0c0"

def escolher_forma_pagamento(root, total, janela_pedido, mesa_id):
    janela_pag = tk.Toplevel(janela_pedido)
    janela_pag.title("Forma de Pagamento")
    janela_pag.geometry("300x200")
    janela_pag.configure(bg=BG_COLOR)
    
    tk.Label(janela_pag, text=f"Total: R$ {total:.2f}", font=("Impact", 16),
             bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=15)
    
    def confirmar(forma):
        from main import confirmar_pagamento
        confirmar_pagamento(forma, total, janela_pag, janela_pedido, mesa_id)
    
    for forma in ["Dinheiro", "Cartão", "PIX"]:
        tk.Button(janela_pag, text=forma,
                  command=lambda f=forma: confirmar(f),
                  bg=BTN_COLOR, fg=TEXT_COLOR, font=("Arial", 12), height=1).pack(pady=5, padx=20, fill="x")