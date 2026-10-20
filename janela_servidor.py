"""Janela do servidor (Tkinter), usada pelo TucandeiraBar.exe e pelo servidor.py.

Substitui a janela de console do Windows, que pode "congelar" o servidor com um
simples clique (modo de edição rápida / QuickEdit). Mostra o endereço para os
tablets, o último backup e os botões para abrir o sistema e parar o servidor.
Fechar a janela pergunta antes e para o servidor.
"""
import tkinter as tk
import webbrowser
from tkinter import messagebox

import config

VERDE = "#004d26"
VERDE_ESCURO = "#003319"
AMARELO = "#ffcc00"
PRETO = "#000000"
BRANCO = "#ffffff"
CINZA = "#c0c0c0"
TITULO = "Tucandeira Rock Bar — Servidor"
FONTE_TITULO = ("Impact", 28)
FONTE_ENDERECO = ("Segoe UI", 26, "bold")
FONTE_TEXTO = ("Segoe UI", 12)
FONTE_BOTAO = ("Segoe UI", 12, "bold")
ATUALIZAR_A_CADA_MS = 60 * 1000


def _aplicar_icone(janela):
    try:
        janela.iconbitmap(default=str(config.ICONE_PROGRAMA))
    except tk.TclError:
        pass  # sem o ícone, a janela funciona igual


class JanelaServidor:
    """`informacoes`: dict com 'local', 'enderecos' (lista), 'pasta_dados'.
    `texto_backup`: função sem argumentos que devolve o texto do último backup.
    `ao_parar`: chamada quando o usuário confirma que quer parar o servidor."""

    def __init__(self, informacoes, texto_backup, ao_parar):
        self.informacoes = informacoes
        self.texto_backup = texto_backup
        self.ao_parar = ao_parar
        self.codigo_saida = 0

        self.raiz = tk.Tk()
        self.raiz.title(TITULO)
        self.raiz.configure(bg=VERDE, padx=28, pady=20)
        self.raiz.minsize(560, 0)
        _aplicar_icone(self.raiz)
        self.raiz.protocol("WM_DELETE_WINDOW", self.pedir_para_parar)
        self._montar()
        self._atualizar_backup()

    def _rotulo(self, texto, fonte=FONTE_TEXTO, cor=BRANCO, espaco=0):
        rotulo = tk.Label(self.raiz, text=texto, font=fonte, fg=cor, bg=VERDE, justify="left")
        rotulo.pack(anchor="w", pady=espaco)
        return rotulo

    def _montar(self):
        self._rotulo("TUCANDEIRA ROCK BAR", FONTE_TITULO, AMARELO)
        self.situacao = self._rotulo("● Sistema funcionando", FONTE_BOTAO, "#6bdc8b", espaco=4)

        self._rotulo("Nos tablets e celulares, digite no Chrome:", espaco=(10, 0))
        enderecos = self.informacoes["enderecos"] or ["(sem rede: conecte este computador ao Wi-Fi ou ao cabo)"]
        for endereco in enderecos:
            # Campo só de leitura: dá para selecionar e copiar, mas não para apagar sem querer.
            campo = tk.Entry(self.raiz, font=FONTE_ENDERECO, fg=AMARELO, bg=VERDE_ESCURO,
                             readonlybackground=VERDE_ESCURO, relief="flat", justify="left",
                             width=max(22, len(endereco) + 1))
            campo.insert(0, endereco)
            campo.configure(state="readonly")
            campo.pack(anchor="w", pady=4, ipady=4, ipadx=6)

        self._rotulo(f"Neste computador (caixa): {self.informacoes['local']}", espaco=(10, 0))
        self.backup = self._rotulo("", cor=CINZA)
        self._rotulo(f"Pasta de dados: {self.informacoes['pasta_dados']}", cor=CINZA)

        self._rotulo("Deixe esta janela aberta (pode minimizar).\n"
                     "Se ela for fechada, o sistema para no caixa e nos tablets.",
                     FONTE_BOTAO, AMARELO, espaco=(14, 10))

        botoes = tk.Frame(self.raiz, bg=VERDE)
        botoes.pack(anchor="w", fill="x")
        tk.Button(botoes, text="Abrir o sistema neste computador", font=FONTE_BOTAO, fg=PRETO, bg=AMARELO,
                  activebackground=BRANCO, relief="flat", padx=14, pady=10, cursor="hand2",
                  command=self.abrir_navegador).pack(side="left")
        tk.Button(botoes, text="Parar o servidor", font=FONTE_BOTAO, fg=BRANCO, bg=PRETO,
                  activebackground="#333333", activeforeground=BRANCO, relief="flat", padx=14, pady=10,
                  cursor="hand2", command=self.pedir_para_parar).pack(side="right")

    def _atualizar_backup(self):
        try:
            self.backup.configure(text=self.texto_backup())
        finally:
            self.raiz.after(ATUALIZAR_A_CADA_MS, self._atualizar_backup)

    def abrir_navegador(self):
        webbrowser.open(self.informacoes["local"])

    def pedir_para_parar(self):
        if messagebox.askyesno(
                "Parar o servidor?",
                "Parar o servidor agora?\n\nO sistema deixa de funcionar no caixa e nos tablets até ser aberto "
                "de novo. Nada do que já foi lançado se perde.",
                icon="warning", default="no", parent=self.raiz):
            self.parar(0)

    def parar(self, codigo=0):
        self.codigo_saida = codigo
        try:
            self.ao_parar()
        finally:
            self.raiz.destroy()

    def falhou(self, mensagem):
        """O servidor caiu: avisa e fecha com código de erro (o Windows tenta abrir de novo)."""
        def mostrar():
            self.situacao.configure(text="● O servidor parou", fg="#ff6b6b")
            messagebox.showerror(TITULO, mensagem, parent=self.raiz)
            self.parar(1)
        self.raiz.after(0, mostrar)

    def rodar(self):
        self.raiz.mainloop()
        return self.codigo_saida


def aviso(titulo, mensagem, erro=False):
    """Caixa de mensagem sozinha (ex.: o servidor já está aberto)."""
    raiz = tk.Tk()
    raiz.withdraw()
    _aplicar_icone(raiz)
    (messagebox.showerror if erro else messagebox.showinfo)(titulo, mensagem, parent=raiz)
    raiz.destroy()
