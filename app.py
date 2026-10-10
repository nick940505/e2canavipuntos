from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from cashless_app.auth import AuthService, AuthenticatedAccount, is_creation_secret_valid
from cashless_app.ui import CashlessApp


BG_COLOR = "#050505"
CARD_COLOR = "#161616"
ACCENT_COLOR = "#22c55e"
ACCENT_HOVER = "#16a34a"
TEXT_COLOR = "#f5f5f5"
MUTED_TEXT = "#9ae6b4"

ROLE_LABELS = {
    "usuario": "Usuario",
    "staff": "Staff",
    "admin": "Administrador",
}

ROLE_INTERFACES = {
    "usuario": ("usuario",),
    "staff": ("usuario", "staff"),
    "admin": ("usuario", "staff", "admin"),
}


def configure_styles(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(bg=BG_COLOR)
    style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR)
    style.configure("TFrame", background=BG_COLOR)
    style.configure("Card.TFrame", background=CARD_COLOR)
    style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR)
    style.configure("Card.TLabel", background=CARD_COLOR, foreground=TEXT_COLOR)
    style.configure("Muted.TLabel", background=CARD_COLOR, foreground=MUTED_TEXT)
    style.configure("Title.TLabel", background=CARD_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 16, "bold"))
    style.configure("TEntry", fieldbackground="#0d0d0d", foreground=TEXT_COLOR, padding=6)
    style.configure("TButton", background=ACCENT_COLOR, foreground="#ffffff", borderwidth=0, padding=(10, 7))
    style.map("TButton", background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)])


def request_creation_secret(parent: tk.Misc | None = None) -> str | None:
    """Solicita y valida la autorización antes de mostrar datos de una cuenta."""
    temporary_root = None
    if parent is None:
        temporary_root = tk.Tk()
        temporary_root.withdraw()
        parent = temporary_root

    secret = simpledialog.askstring(
        "Autorizar creación de cuenta",
        "Ingresa la palabra secreta para continuar:",
        show="●",
        parent=parent,
    )
    if secret is None:
        if temporary_root is not None:
            temporary_root.destroy()
        return None
    if not is_creation_secret_valid(secret):
        messagebox.showerror("Autorización denegada", "La palabra secreta es incorrecta.", parent=parent)
        if temporary_root is not None:
            temporary_root.destroy()
        return None
    if temporary_root is not None:
        temporary_root.destroy()
    return secret


def bootstrap_required_account(auth_service: AuthService, role: str) -> bool:
    creation_secret = request_creation_secret()
    if creation_secret is None:
        return False

    root = tk.Tk()
    role_label = ROLE_LABELS[role]
    root.title(f"Crear cuenta inicial de {role_label}")
    root.minsize(390, 360)
    root.resizable(True, True)
    configure_styles(root)
    result = {"created": False}

    card = ttk.Frame(root, padding=24, style="Card.TFrame")
    card.pack(fill="both", expand=True, padx=16, pady=16)
    ttk.Label(card, text=f"Crear cuenta inicial de {role_label}", style="Title.TLabel").pack(anchor="w")
    ttk.Label(card, text=f"Este acceso controla la interfaz de {role_label}.", style="Muted.TLabel").pack(anchor="w", pady=(4, 16))

    username = tk.StringVar()
    password = tk.StringVar()
    confirmation = tk.StringVar()
    for label, variable, hidden in [
        ("Usuario", username, False),
        ("Contraseña", password, True),
        ("Confirmar contraseña", confirmation, True),
    ]:
        ttk.Label(card, text=label, style="Card.TLabel").pack(anchor="w", pady=(6, 2))
        ttk.Entry(card, textvariable=variable, show="●" if hidden else "").pack(fill="x")

    def create() -> None:
        if password.get() != confirmation.get():
            messagebox.showerror("Contraseñas distintas", "La confirmación no coincide.", parent=root)
            return
        try:
            auth_service.create_required_account(username.get(), password.get(), role, creation_secret)
        except ValueError as error:
            messagebox.showerror("No se pudo crear", str(error), parent=root)
            return
        result["created"] = True
        root.destroy()

    ttk.Button(card, text=f"Crear {role_label}", command=create).pack(fill="x", pady=(18, 0))
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.update_idletasks()
    root.geometry(f"{max(410, root.winfo_reqwidth() + 16)}x{max(400, root.winfo_reqheight() + 16)}")
    root.mainloop()
    return result["created"]


def ensure_required_accounts(auth_service: AuthService) -> bool:
    for role in ("admin", "staff"):
        if not auth_service.has_role_account(role):
            if not bootstrap_required_account(auth_service, role):
                return False
    return True


def login(auth_service: AuthService) -> AuthenticatedAccount | None:
    root = tk.Tk()
    root.title("Iniciar sesión · E2 Cana VIPuntos")
    root.minsize(390, 330)
    root.resizable(True, True)
    configure_styles(root)
    result: dict[str, AuthenticatedAccount | None] = {"account": None}

    card = ttk.Frame(root, padding=24, style="Card.TFrame")
    card.pack(fill="both", expand=True, padx=16, pady=16)
    ttk.Label(card, text="E2 Cana VIPuntos", style="Title.TLabel").pack(anchor="w")
    ttk.Label(card, text="Ingresa con tu cuenta autorizada.", style="Muted.TLabel").pack(anchor="w", pady=(4, 16))

    username = tk.StringVar()
    password = tk.StringVar()
    ttk.Label(card, text="Usuario", style="Card.TLabel").pack(anchor="w", pady=(4, 2))
    username_entry = ttk.Entry(card, textvariable=username)
    username_entry.pack(fill="x")
    ttk.Label(card, text="Contraseña", style="Card.TLabel").pack(anchor="w", pady=(10, 2))
    password_entry = ttk.Entry(card, textvariable=password, show="●")
    password_entry.pack(fill="x")

    def submit() -> None:
        account = auth_service.authenticate(username.get(), password.get())
        if account is None:
            password.set("")
            messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos.", parent=root)
            return
        result["account"] = account
        root.destroy()

    ttk.Button(card, text="Ingresar", command=submit).pack(fill="x", pady=(18, 0))
    root.bind("<Return>", lambda _event: submit())
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.update_idletasks()
    root.geometry(f"{max(410, root.winfo_reqwidth() + 16)}x{max(350, root.winfo_reqheight() + 16)}")
    username_entry.focus_set()
    root.mainloop()
    return result["account"]


def choose_interface(account: AuthenticatedAccount | None = None) -> str | None:
    allowed_roles = ROLE_INTERFACES[account.role] if account else ("usuario", "staff", "admin")
    root = tk.Tk()
    root.title("Seleccionar interfaz · E2 Cana VIPuntos")
    root.minsize(390, 360)
    root.resizable(True, True)
    configure_styles(root)
    selected = tk.StringVar(master=root, value=allowed_roles[-1])
    result: dict[str, str | None] = {"role": None}

    card = ttk.Frame(root, padding=24, style="Card.TFrame")
    card.pack(fill="both", expand=True, padx=16, pady=16)
    ttk.Label(card, text="Selecciona la interfaz", style="Title.TLabel").pack(anchor="w")
    subtitle = (
        f"Sesión: {account.username} · Acceso: {ROLE_LABELS[account.role]}"
        if account
        else "La interfaz Usuario es pública; Staff y Administrador requieren inicio de sesión."
    )
    ttk.Label(card, text=subtitle, style="Muted.TLabel", wraplength=340).pack(anchor="w", pady=(4, 16))

    for role in allowed_roles:
        ttk.Radiobutton(
            card,
            text=ROLE_LABELS[role],
            value=role,
            variable=selected,
        ).pack(anchor="w", pady=4)

    def confirm() -> None:
        result["role"] = selected.get()
        root.destroy()

    ttk.Button(card, text="Continuar", command=confirm).pack(fill="x", pady=(20, 0))
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.update_idletasks()
    root.geometry(f"{max(410, root.winfo_reqwidth() + 16)}x{max(380, root.winfo_reqheight() + 16)}")
    root.mainloop()
    return result["role"]


def main() -> None:
    auth_service = AuthService()
    should_continue = True
    while should_continue:
        should_continue = False
        selected_role = choose_interface()
        if selected_role is None:
            return

        username = ""
        if selected_role != "usuario":
            if not ensure_required_accounts(auth_service):
                should_continue = True
                continue
            account = login(auth_service)
            if account is None:
                should_continue = True
                continue
            if selected_role not in ROLE_INTERFACES[account.role]:
                messagebox.showerror(
                    "Acceso denegado",
                    f"La cuenta {account.username} no tiene permiso para la interfaz {ROLE_LABELS[selected_role]}.",
                )
                should_continue = True
                continue
            username = account.username

        def return_to_login() -> None:
            nonlocal should_continue
            should_continue = True

        app = CashlessApp(
            role=selected_role,
            username=username,
            on_switch_role=return_to_login,
        )
        app.run()


if __name__ == "__main__":
    main()
