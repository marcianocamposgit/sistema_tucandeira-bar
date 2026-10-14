import tkinter as tk
from PIL import Image, ImageTk

BG_COLOR = "#004d26"
BTN_COLOR = "#000000"
TEXT_COLOR = "#ffffff"
ACCENT_COLOR = "#c0c0c0"
HIGHLIGHT_COLOR = "#ffcc00"

def criar_tela_principal(root, NUM_MESAS, mesas_status, abrir_tela_pedido, abrir_relatorios, abrir_cadastro, abrir_sobre):
    root.title("TUCANDEIRA ROCK BAR")
    root.geometry("800x650")
    root.configure(bg=BG_COLOR)

    # === LOGO ===
    logo_path = r"C:\tucandeira-bar\assets\logo.png"
    try:
        img = Image.open(logo_path)
        max_height = 300
        aspect = img.width / img.height
        new_width = int(max_height * aspect)
        if new_width > 800:
            new_width = 800
            new_height = int(new_width / aspect)
        else:
            new_height = max_height
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        logo_img = ImageTk.PhotoImage(img)
        logo_label = tk.Label(root, image=logo_img, bg=BG_COLOR)
        logo_label.image = logo_img
        logo_label.pack(pady=10)
    except Exception as e:
        print(f"[LOGO] Erro: {e}")
        tk.Label(root, text="🛡️ TUCANDEIRA ROCK BAR 🤘🍺",
                 font=("Impact", 28, "bold"), bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=20)

    # === BOTÕES PRINCIPAIS ===
    tk.Button(root, text="➕ Balcão / Para Viagem",
              command=lambda: abrir_tela_pedido(None),
              bg=HIGHLIGHT_COLOR, fg="#000", font=("Impact", 14), height=2).pack(pady=8)

    tk.Button(root, text="📊 Relatórios de Caixa",
              command=abrir_relatorios,
              bg=ACCENT_COLOR, fg="#000", font=("Impact", 12), height=1).pack(pady=5)
    
    tk.Button(root, text="⚙️ Cadastro de Produtos",
              command=abrir_cadastro,
              bg="#555555", fg=TEXT_COLOR, font=("Arial", 10), height=1).pack(pady=5)

    # === FRAME DE MESAS (2 LINHAS × 4 COLUNAS) ===
    frame_mesas = tk.Frame(root, bg=BG_COLOR)
    frame_mesas.pack(pady=15, padx=20)

    # Configura 4 colunas (suporta até 8 mesas)
    for col in range(4):
        frame_mesas.grid_columnconfigure(col, weight=1)

    # Cria os botões de mesa
    for i in range(1, NUM_MESAS + 1):
        row = (i - 1) // 4
        col = (i - 1) % 4
        status = mesas_status.get(i, "livre")
        cor = "#ff3333" if status == "ocupada" else "#33cc33"
        texto = f"Mesa {i} {'🔴' if status == 'ocupada' else '🟢'}"
        
        btn = tk.Button(
            frame_mesas,
            text=texto,
            command=lambda i=i: abrir_tela_pedido(i),
            bg=BTN_COLOR,
            fg=cor,
            font=("Arial", 10, "bold"),
            width=12,
            height=2
        )
        btn.grid(row=row, column=col, padx=6, pady=6, sticky="ew")
        
        # === BOTÃO SOBRE — CANTO SUPERIOR DIREITO ===
        tk.Button(
            root,
            text="Sobre",
            command=abrir_sobre,
            bg="#333333",
            fg="#cccccc",
            font=("Arial", 9, "bold"),
            width=8,
            height=1
        ).place(relx=1.0, rely=0.0, x=-10, y=10, anchor="ne")

    return frame_mesas

def atualizar_tela_mesas(root, frame_mesas):
    """Atualiza visualmente os botões de mesa após pagamento"""
    from main import NUM_MESAS, mesas_status, abrir_tela_pedido
    
    for col in range(4):
        frame_mesas.grid_columnconfigure(col, weight=1)
    
    for widget in frame_mesas.winfo_children():
        widget.destroy()
        
    for i in range(1, NUM_MESAS + 1):
        row = (i - 1) // 4
        col = (i - 1) % 4
        status = mesas_status.get(i, "livre")
        cor = "#ff3333" if status == "ocupada" else "#33cc33"
        texto = f"Mesa {i} {'🔴' if status == 'ocupada' else '🟢'}"
        
        btn = tk.Button(
            frame_mesas,
            text=texto,
            command=lambda i=i: abrir_tela_pedido(i),
            bg=BTN_COLOR,
            fg=cor,
            font=("Arial", 10, "bold"),
            width=12,
            height=2
        )
        btn.grid(row=row, column=col, padx=6, pady=6, sticky="ew")