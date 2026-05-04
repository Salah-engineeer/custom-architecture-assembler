import tkinter as tk
from tkinter import scrolledtext


def load_object_code(memory, htme_file):
    with open(htme_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('T'):
                parts = line.split('.')
                start_addr = int(parts[1], 16)
                for code in parts[3:]:
                    code = code.replace(' ', '')
                    for i in range(0, len(code), 2):
                        byte_val = int(code[i:i + 2], 16)
                        memory[start_addr] = byte_val
                        start_addr += 1
    return memory


def display_memory(memory, text_widget):
    text_widget.config(state=tk.NORMAL)
    text_widget.delete('1.0', tk.END)

    text_widget.insert(tk.END, "Address:  0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F\n", "header")
    text_widget.insert(tk.END, "-" * 58 + "\n", "header")

    max_addr = max(memory.keys()) if memory else 0
    end_addr = max(0x100, ((max_addr // 16) + 2) * 16)

    for row in range(0, end_addr, 16):
        addr_str = f"{row:06X}: "
        bytes_str = " ".join(f"{memory.get(row + col, 0):02X}" for col in range(16))
        text_widget.insert(tk.END, addr_str, "addr")
        text_widget.insert(tk.END, bytes_str + "\n", "bytes")

    text_widget.config(state=tk.DISABLED)


def build_gui():
    memory = {}

    root = tk.Tk()
    root.title("SIC/XE Memory Visualizer")
    root.configure(bg="#1e1e1e")
    root.geometry("780x520")

    tk.Label(
        root, text="SIC/XE Memory Visualizer",
        font=("Courier", 14, "bold"),
        bg="#1e1e1e", fg="#61dafb"
    ).pack(pady=8)

    text = scrolledtext.ScrolledText(
        root, font=("Courier", 10),
        width=72, height=26,
        bg="#0d0d0d", fg="#00ff99",
        insertbackground="white",
        state=tk.DISABLED
    )
    text.tag_config("header", foreground="#ffcc00")
    text.tag_config("addr", foreground="#61dafb")
    text.tag_config("bytes", foreground="#00ff99")
    text.pack(padx=10, pady=5)

    def on_load():
        nonlocal memory
        memory = load_object_code({}, "HTME.txt")
        display_memory(memory, text)
        btn.config(text="Reload Object Code")

    btn = tk.Button(
        root, text="Load Object Code",
        command=on_load,
        bg="#61dafb", fg="#000000",
        font=("Courier", 10, "bold"),
        relief=tk.FLAT, padx=10, pady=4
    )
    btn.pack(pady=6)

    display_memory(memory, text)
    root.mainloop()


build_gui()
