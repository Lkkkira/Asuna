"""Restore a validated local backup while the main assistant is closed."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog,messagebox
from backups import inspect_backup,restore_backup
from single_instance import SingleInstance


def main():
    root = tk.Tk()
    root.withdraw()
    data = Path(__file__).resolve().parent/'data'
    try:
        with SingleInstance(data):
            filename = filedialog.askopenfilename(title='Restore ASUNA backup',filetypes=[('ASUNA backup','*.zip')])
            if not filename:return
            payload = inspect_backup(filename)
            if not messagebox.askyesno('Restore ASUNA','Replace these saved files?\n\n'+'\n'.join(sorted(payload))+'\n\nA safety backup is made first.'):return
            safety = restore_backup(data,filename)
            messagebox.showinfo('ASUNA','Restored. Open Start ASUNA.bat.\nSafety backup: '+str(safety))
    except (OSError,ValueError,RuntimeError) as exc:
        messagebox.showerror('ASUNA',str(exc))
    finally:
        root.destroy()


if __name__=='__main__':main()
