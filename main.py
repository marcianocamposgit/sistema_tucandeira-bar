import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta

# === CORES ===
BG_COLOR = "#004d26"
BTN_COLOR = "#000000"
TEXT_COLOR = "#ffffff"
ACCENT_COLOR = "#c0c0c0"
HIGHLIGHT_COLOR = "#ffcc00"

# === DADOS EM MEMÓRIA ===
NUM_MESAS = 8
mesas_status = {i: "livre" for i in range(1, NUM_MESAS + 1)}
pedidos_abertos = {}
historico_vendas = []

CARDAPIO = [
    {"nome": "Brahma Lata", "categoria": "Bebida", "preco": 8.00, "estoque": 30},
    {"nome": "Heineken Long Neck", "categoria": "Bebida", "preco": 12.00, "estoque": 15},
    {"nome": "Whisky 50ml", "categoria": "Bebida", "preco": 15.00, "estoque": 12},
    {"nome": "Porção Calabresa", "categoria": "Tira-Gosto", "preco": 28.00, "estoque": 8},
    {"nome": "Pastel Carne", "categoria": "Lanche", "preco": 7.00, "estoque": 15},
    {"nome": "Marlboro 20un", "categoria": "Cigarro", "preco": 18.00, "estoque": 10},
]

# === FUNÇÕES DE NEGÓCIO ===
def atualizar_estoque(nome_produto, qtd=1):
    for p in CARDAPIO:
        if p["nome"] == nome_produto:
            if p["estoque"] >= qtd:
                p["estoque"] -= qtd
                if p["estoque"] <= 5:
                    messagebox.showwarning("⚠️ Estoque Baixo", f"Só restam {p['estoque']} unidades de {p['nome']}!")
            else:
                p["estoque"] = 0
                messagebox.showinfo("Sem Estoque", f"{p['nome']} está esgotado, mas o pedido foi aceito.")
            return

def registrar_venda(total, forma_pagamento, tipo, id_ref=None):
    registro = {
        "id": id_ref or f"B{len(historico_vendas)+1}",
        "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "forma_pagamento": forma_pagamento,
        "tipo": tipo
    }
    historico_vendas.append(registro)

def calcular_caixa(periodo):
    agora = datetime.now()
    total = 0
    if periodo == "dia":
        hoje = agora.strftime("%Y-%m-%d")
        total = sum(v["total"] for v in historico_vendas if v["data_hora"].startswith(hoje))
    elif periodo == "semana":
        inicio = agora - timedelta(days=7)
        total = sum(v["total"] for v in historico_vendas if datetime.strptime(v["data_hora"], "%Y-%m-%d %H:%M:%S") >= inicio)
    elif periodo == "mes":
        mes_ano = agora.strftime("%Y-%m")
        total = sum(v["total"] for v in historico_vendas if v["data_hora"].startswith(mes_ano))
    return total

def confirmar_pagamento(forma, total, janela_pag, janela_pedido, mesa_id):
    if messagebox.askyesno("Confirmar", f"Pagar R$ {total:.2f} com {forma}?"):
        tipo = "mesa" if mesa_id else "balcao"
        id_ref = f"M{mesa_id}" if mesa_id else None
        registrar_venda(total, forma, tipo, id_ref)
        if mesa_id:
            mesas_status[mesa_id] = "livre"
            pedidos_abertos.pop(mesa_id, None)
            from views.tela_principal import atualizar_tela_mesas
            atualizar_tela_mesas(root_global, frame_mesas_global)
        else:
            chaves_balc = [k for k in pedidos_abertos.keys() if isinstance(k, str)]
            if chaves_balc:
                pedidos_abertos.pop(chaves_balc[-1], None)
        janela_pag.destroy()
        janela_pedido.destroy()
        messagebox.showinfo("Sucesso", f"Conta paga com {forma}!")

# === FUNÇÕES DE INTERFACE ===
def abrir_tela_pedido(mesa_id=None):
    from views.tela_pedido import abrir_tela_pedido_view
    abrir_tela_pedido_view(root_global, mesa_id, CARDAPIO, atualizar_estoque, escolher_forma_pagamento)

def escolher_forma_pagamento(total, janela_pedido, mesa_id):
    from views.tela_pagamento import escolher_forma_pagamento_view
    escolher_forma_pagamento_view(root_global, total, janela_pedido, mesa_id, confirmar_pagamento)

def abrir_relatorios():
    janela_rel = tk.Toplevel(root_global)
    janela_rel.title("Relatórios")
    janela_rel.geometry("400x250")
    janela_rel.configure(bg=BG_COLOR)
    
    tk.Label(janela_rel, text="RELATÓRIOS", font=("Impact", 20), bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=15)
    
    for texto, periodo in [("Caixa do Dia", "dia"), ("Caixa da Semana", "semana"), ("Caixa do Mês", "mes")]:
        total = calcular_caixa(periodo)
        btn = tk.Button(
            janela_rel,
            text=f"{texto} - R$ {total:.2f}",
            command=lambda p=periodo, t=total: messagebox.showinfo(
                f"Detalhes - {p.capitalize()}",
                f"Total: R$ {t:.2f}\nVendas registradas: {len(historico_vendas)}"
            ),
            bg=BTN_COLOR,
            fg=TEXT_COLOR,
            font=("Arial", 12),
            height=1
        )
        btn.pack(pady=5, padx=20, fill="x")

def abrir_cadastro():
    from views.tela_cadastro import abrir_tela_cadastro
    abrir_tela_cadastro(root_global, CARDAPIO)

def abrir_sobre():
    messagebox.showinfo(
        "Sobre o Sistema",
        "Tucandeira Rock Bar\n"
        "Sistema de Gestão para Bares\n\n"
        "Desenvolvido por Marciano Campos\n"
        "Versão 1.0 – Python + Tkinter"
    )

# === INICIALIZAÇÃO ===
if __name__ == "__main__":
    root = tk.Tk()
    root_global = root
    
    from views.tela_principal import criar_tela_principal
    
    frame_mesas = criar_tela_principal(
        root,
        NUM_MESAS,
        mesas_status,
        abrir_tela_pedido,
        abrir_relatorios,
        abrir_cadastro,
        abrir_sobre
    )
    
    frame_mesas_global = frame_mesas
    root.mainloop()