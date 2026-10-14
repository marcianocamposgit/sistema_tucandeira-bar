import tkinter as tk
from tkinter import messagebox

BG_COLOR = "#004d26"
BTN_COLOR = "#000000"
TEXT_COLOR = "#ffffff"
ACCENT_COLOR = "#c0c0c0"

def abrir_relatorios(root):
    janela_rel = tk.Toplevel(root)
    janela_rel.title("Relatórios")
    janela_rel.geometry("400x250")
    janela_rel.configure(bg=BG_COLOR)
    
    tk.Label(janela_rel, text="RELATÓRIOS", font=("Impact", 20), bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=15)
    
    from main import calcular_caixa
    for texto, periodo in [("Caixa do Dia", "dia"), ("Caixa da Semana", "semana"), ("Caixa do Mês", "mes")]:
        total = calcular_caixa(periodo)
        btn = tk.Button(janela_rel, text=f"{texto} - R$ {total:.2f}",
                        command=lambda p=periodo, t=total: messagebox.showinfo(
                            f"Detalhes - {p.capitalize()}",
                            f"Total: R$ {t:.2f}"
                        ),
                        bg=BTN_COLOR, fg=TEXT_COLOR, font=("Arial", 12))
        btn.pack(pady=5, padx=20, fill="x")