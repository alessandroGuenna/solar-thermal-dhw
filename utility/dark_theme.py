from tkinter import ttk

def apply_dark_theme(root):
    BG = "#1e1e1e"
    FIELD = "#2d2d2d"
    TEXT = "#e6e6e6"
    MUTED = "#8a8a8a"
    ACCENT = "#3987e5"

    root.configure(background=BG)

    style = ttk.Style(root)
    style.theme_use("clam")     # built-in theme that accepts custom colors

    style.configure(".", background=BG, foreground=TEXT, fieldbackground=FIELD,
                    bordercolor="#444444", lightcolor=BG, darkcolor=BG,
                    troughcolor=FIELD, insertcolor=TEXT)
    style.configure("TLabelframe.Label", background=BG, foreground=TEXT)
    style.configure("TButton", background=FIELD, padding=6)
    style.map("TButton",
              background=[("disabled", BG), ("active", ACCENT)],
              foreground=[("disabled", MUTED)])
    style.map("TEntry", fieldbackground=[("disabled", BG)])
    style.map("TCombobox",
              fieldbackground=[("readonly", FIELD)],
              foreground=[("readonly", TEXT)],
              background=[("readonly", FIELD)],
              selectbackground=[("readonly", FIELD)],
              selectforeground=[("readonly", TEXT)])
    style.configure("TRadiobutton", indicatorbackground=FIELD, indicatorforeground=TEXT,
                    upperbordercolor="#666666", lowerbordercolor="#666666")
    style.map("TRadiobutton",
              background=[("active", BG)],
              indicatorbackground=[("selected", ACCENT), ("!selected", FIELD)],
              indicatorforeground=[("selected", TEXT), ("!selected", FIELD)])

    # the combobox drop-down list is a classic tk widget: styled separately
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)