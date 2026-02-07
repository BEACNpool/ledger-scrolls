from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import Tk, StringVar, IntVar, BooleanVar, filedialog, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "examples" / "scrolls.json"


@dataclass
class ScrollEntry:
    id: str
    data: dict


def load_catalog() -> list[ScrollEntry]:
    if not CATALOG.exists():
        return []
    raw = json.loads(CATALOG.read_text(encoding="utf-8"))
    out = []
    for item in raw.get("scrolls", []):
        sid = item.get("id")
        if sid:
            out.append(ScrollEntry(id=sid, data=item))
    return out


def run_command(cmd: list[str], log: ScrolledText) -> None:
    log.configure(state="normal")
    log.insert("end", f"$ {' '.join(cmd)}\n")
    log.see("end")
    log.configure(state="disabled")

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert proc.stdout
        for line in proc.stdout:
            log.configure(state="normal")
            log.insert("end", line)
            log.see("end")
            log.configure(state="disabled")
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"Command failed with exit code {rc}")
    except Exception as exc:
        log.configure(state="normal")
        log.insert("end", f"[error] {exc}\n")
        log.see("end")
        log.configure(state="disabled")


def main() -> None:
    root = Tk()
    root.title("Ledger Scrolls — P2P Viewer")
    root.geometry("980x700")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background="#f6f1e7")
    style.configure("TLabel", background="#f6f1e7", foreground="#2c2a26", font=("Segoe UI", 10))
    style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
    style.configure("Subheader.TLabel", font=("Segoe UI", 11, "italic"))
    style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)

    banner = ttk.Frame(root, padding=12)
    banner.pack(fill="x")
    ttk.Label(banner, text="Ledger Scrolls — P2P Viewer", style="Header.TLabel").pack(anchor="w")
    ttk.Label(
        banner,
        text="A library that cannot burn. Direct relay reads. No indexer. No gatekeepers.",
        style="Subheader.TLabel",
    ).pack(anchor="w")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=8)

    tab_catalog = ttk.Frame(notebook, padding=10)
    tab_manual = ttk.Frame(notebook, padding=10)
    notebook.add(tab_catalog, text="Catalog")
    notebook.add(tab_manual, text="Manual Entry")

    # Settings bar
    settings = ttk.Frame(root, padding=10)
    settings.pack(fill="x")
    relay_var = StringVar(value="backbone.cardano.iog.io")
    port_var = IntVar(value=3001)
    topology_var = StringVar(value="")

    ttk.Label(settings, text="Relay:").grid(row=0, column=0, sticky="w")
    ttk.Entry(settings, textvariable=relay_var, width=32).grid(row=0, column=1, sticky="w")
    ttk.Label(settings, text="Port:").grid(row=0, column=2, sticky="w", padx=(10, 2))
    ttk.Entry(settings, textvariable=port_var, width=8).grid(row=0, column=3, sticky="w")

    ttk.Label(settings, text="Topology (optional):").grid(row=0, column=4, sticky="w", padx=(10, 2))
    ttk.Entry(settings, textvariable=topology_var, width=40).grid(row=0, column=5, sticky="w")
    def browse_topology():
        path = filedialog.askopenfilename(title="Select topology.json", filetypes=[("JSON", "*.json"), ("All", "*")])
        if path:
            topology_var.set(path)
    ttk.Button(settings, text="Browse", command=browse_topology).grid(row=0, column=6, padx=(6, 0))

    # Catalog tab
    catalog_entries = load_catalog()
    catalog_list = ttk.Treeview(tab_catalog, columns=("type", "details"), show="headings", height=10)
    catalog_list.heading("type", text="Type")
    catalog_list.heading("details", text="Details")
    catalog_list.column("type", width=180)
    catalog_list.column("details", width=640)
    catalog_list.pack(fill="x", pady=6)

    for entry in catalog_entries:
        kind = entry.data.get("type", "")
        details = []
        if entry.data.get("policy_id"):
            details.append(f"policy={entry.data['policy_id']}")
        if entry.data.get("manifest_asset"):
            details.append(f"manifest={entry.data['manifest_asset']}")
        if entry.data.get("tx_hash"):
            details.append(f"tx={entry.data['tx_hash']}")
        if entry.data.get("block_slot"):
            details.append(f"slot={entry.data['block_slot']}")
        catalog_list.insert("", "end", iid=entry.id, values=(kind, "  ".join(details)))

    out_catalog_var = StringVar(value=str(ROOT / "output.bin"))
    ttk.Label(tab_catalog, text="Output file:").pack(anchor="w")
    out_catalog_entry = ttk.Entry(tab_catalog, textvariable=out_catalog_var, width=80)
    out_catalog_entry.pack(anchor="w")

    def browse_output_catalog():
        path = filedialog.asksaveasfilename(title="Save output")
        if path:
            out_catalog_var.set(path)
    ttk.Button(tab_catalog, text="Choose output…", command=browse_output_catalog).pack(anchor="w", pady=(4, 8))

    log = ScrolledText(root, height=12, background="#0f1115", foreground="#d9e1e8", insertbackground="#ffffff")
    log.configure(state="disabled")
    log.pack(fill="both", expand=False, padx=10, pady=(0, 10))

    def build_base_cmd() -> list[str]:
        cmd = [sys.executable, "-m", "lsview"]
        topo = topology_var.get().strip()
        if topo:
            cmd += ["--topology", topo]
        else:
            cmd += ["--relay", relay_var.get().strip(), "--port", str(port_var.get())]
        return cmd

    def run_catalog():
        selection = catalog_list.selection()
        if not selection:
            messagebox.showerror("Select a scroll", "Pick a scroll from the catalog list.")
            return
        sid = selection[0]
        entry = next((e for e in catalog_entries if e.id == sid), None)
        if entry is None:
            return
        out_path = out_catalog_var.get().strip()
        if not out_path:
            messagebox.showerror("Output required", "Choose an output file.")
            return
        base = build_base_cmd()
        if entry.data.get("type") == "utxo_datum_bytes_v1":
            cmd = base + ["reconstruct-utxo", "--scroll", sid, "--out", out_path]
        else:
            cmd = base + ["reconstruct-cip25", "--scroll", sid, "--out", out_path]
        threading.Thread(target=run_command, args=(cmd, log), daemon=True).start()

    ttk.Button(tab_catalog, text="Reconstruct Selected", command=run_catalog).pack(anchor="w", pady=6)

    # Manual tab
    manual_type = StringVar(value="utxo")
    ttk.Label(tab_manual, text="Manual Entry", style="Header.TLabel").pack(anchor="w")

    type_frame = ttk.Frame(tab_manual)
    type_frame.pack(anchor="w", pady=6)
    ttk.Radiobutton(type_frame, text="Standard (UTxO datum)", variable=manual_type, value="utxo").pack(side="left", padx=6)
    ttk.Radiobutton(type_frame, text="Legacy (CIP‑25 pages)", variable=manual_type, value="cip25").pack(side="left", padx=6)

    # Manual fields
    mf = ttk.Frame(tab_manual)
    mf.pack(fill="x", pady=6)

    tx_hash_var = StringVar(value="")
    tx_ix_var = IntVar(value=0)
    block_slot_var = StringVar(value="")
    block_hash_var = StringVar(value="")

    policy_var = StringVar(value="")
    manifest_var = StringVar(value="")
    start_slot_var = StringVar(value="")
    start_hash_var = StringVar(value="")

    out_manual_var = StringVar(value=str(ROOT / "manual_output.bin"))

    ttk.Label(mf, text="Tx Hash:").grid(row=0, column=0, sticky="w")
    ttk.Entry(mf, textvariable=tx_hash_var, width=64).grid(row=0, column=1, sticky="w")
    ttk.Label(mf, text="Tx Ix:").grid(row=0, column=2, sticky="w", padx=(8, 2))
    ttk.Entry(mf, textvariable=tx_ix_var, width=6).grid(row=0, column=3, sticky="w")

    ttk.Label(mf, text="Block Slot:").grid(row=1, column=0, sticky="w")
    ttk.Entry(mf, textvariable=block_slot_var, width=20).grid(row=1, column=1, sticky="w")
    ttk.Label(mf, text="Block Hash:").grid(row=1, column=2, sticky="w", padx=(8, 2))
    ttk.Entry(mf, textvariable=block_hash_var, width=48).grid(row=1, column=3, sticky="w")

    ttk.Label(mf, text="Policy ID:").grid(row=2, column=0, sticky="w")
    ttk.Entry(mf, textvariable=policy_var, width=64).grid(row=2, column=1, sticky="w")
    ttk.Label(mf, text="Manifest Asset:").grid(row=2, column=2, sticky="w", padx=(8, 2))
    ttk.Entry(mf, textvariable=manifest_var, width=28).grid(row=2, column=3, sticky="w")

    ttk.Label(mf, text="Start Slot:").grid(row=3, column=0, sticky="w")
    ttk.Entry(mf, textvariable=start_slot_var, width=20).grid(row=3, column=1, sticky="w")
    ttk.Label(mf, text="Start Hash:").grid(row=3, column=2, sticky="w", padx=(8, 2))
    ttk.Entry(mf, textvariable=start_hash_var, width=48).grid(row=3, column=3, sticky="w")

    ttk.Label(mf, text="Output:").grid(row=4, column=0, sticky="w")
    ttk.Entry(mf, textvariable=out_manual_var, width=64).grid(row=4, column=1, sticky="w")

    def browse_output_manual():
        path = filedialog.asksaveasfilename(title="Save output")
        if path:
            out_manual_var.set(path)
    ttk.Button(mf, text="Choose output…", command=browse_output_manual).grid(row=4, column=2, sticky="w", padx=(8, 2))

    def run_manual():
        out_path = out_manual_var.get().strip()
        if not out_path:
            messagebox.showerror("Output required", "Choose an output file.")
            return

        base = build_base_cmd()
        if manual_type.get() == "utxo":
            cmd = base + ["reconstruct-utxo", "--tx-ix", str(tx_ix_var.get()), "--out", out_path]
            if tx_hash_var.get().strip():
                cmd += ["--tx-hash", tx_hash_var.get().strip()]
            if block_slot_var.get().strip() and block_hash_var.get().strip():
                cmd += ["--block-slot", block_slot_var.get().strip(), "--block-hash", block_hash_var.get().strip()]
        else:
            if not (policy_var.get().strip() and manifest_var.get().strip() and start_slot_var.get().strip() and start_hash_var.get().strip()):
                messagebox.showerror("Missing fields", "CIP‑25 requires policy, manifest asset, start slot, and start hash.")
                return
            cmd = base + [
                "reconstruct-cip25",
                "--policy",
                policy_var.get().strip(),
                "--manifest-asset",
                manifest_var.get().strip(),
                "--start-slot",
                start_slot_var.get().strip(),
                "--start-hash",
                start_hash_var.get().strip(),
                "--out",
                out_path,
            ]
        threading.Thread(target=run_command, args=(cmd, log), daemon=True).start()

    ttk.Button(tab_manual, text="Reconstruct (Manual)", command=run_manual).pack(anchor="w", pady=6)

    root.mainloop()


if __name__ == "__main__":
    main()
