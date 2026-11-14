# -*- coding: utf-8 -*-
"""Editor MP3 liviano: cortar, unir y mezclar. Interfaz Tkinter."""
import os, sys, subprocess, tempfile, threading, shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import imageio_ffmpeg

def ffmpeg():
    return imageio_ffmpeg.get_ffmpeg_exe()

class Editor:
    def __init__(self, root):
        self.root=root
        root.title("Editor MP3 - Cortar, unir y mezclar")
        root.geometry("760x570")
        root.minsize(680,500)
        self.files=[]
        self.current=None
        self.duration=0.0
        self.tempdir=tempfile.mkdtemp(prefix="editor_mp3_")
        self.build()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def build(self):
        top=ttk.Frame(self.root,padding=12); top.pack(fill="x")
        ttk.Label(top,text="EDITOR MP3",font=("Segoe UI",20,"bold")).pack(anchor="w")
        ttk.Label(top,text="Cortá fragmentos, uní canciones y mezclá pistas.",foreground="#555").pack(anchor="w")
        box=ttk.LabelFrame(self.root,text="Canciones",padding=10); box.pack(fill="both",expand=True,padx=12,pady=6)
        self.list=tk.Listbox(box,height=8,selectmode=tk.SINGLE)
        self.list.pack(side="left",fill="both",expand=True)
        sb=ttk.Scrollbar(box,orient="vertical",command=self.list.yview); sb.pack(side="right",fill="y")
        self.list.config(yscrollcommand=sb.set)
        row=ttk.Frame(self.root,padding=(12,3)); row.pack(fill="x")
        ttk.Button(row,text="Agregar MP3",command=self.add).pack(side="left",padx=3)
        ttk.Button(row,text="Quitar",command=self.remove).pack(side="left",padx=3)
        ttk.Button(row,text="Escuchar",command=self.play).pack(side="left",padx=3)
        trim=ttk.LabelFrame(self.root,text="Cortar canción seleccionada",padding=10); trim.pack(fill="x",padx=12,pady=6)
        r=ttk.Frame(trim); r.pack(fill="x")
        ttk.Label(r,text="Desde (segundos):").pack(side="left")
        self.start=tk.StringVar(value="0"); ttk.Entry(r,textvariable=self.start,width=10).pack(side="left",padx=5)
        ttk.Label(r,text="Hasta (segundos):").pack(side="left",padx=(12,0))
        self.end=tk.StringVar(value="30"); ttk.Entry(r,textvariable=self.end,width=10).pack(side="left",padx=5)
        ttk.Button(trim,text="CORTAR Y GUARDAR MP3",command=self.cut).pack(anchor="e",pady=(8,0))
        ops=ttk.LabelFrame(self.root,text="Unir o mezclar",padding=10); ops.pack(fill="x",padx=12,pady=6)
        ttk.Label(ops,text="Unir: concatena las canciones en el orden de la lista.").pack(anchor="w")
        ttk.Button(ops,text="UNIR CANCIONES",command=self.join).pack(anchor="w",pady=4)
        ttk.Separator(ops).pack(fill="x",pady=5)
        ttk.Label(ops,text="Mezclar: superpone las dos primeras canciones de la lista.").pack(anchor="w")
        mr=ttk.Frame(ops); mr.pack(fill="x",pady=4)
        ttk.Label(mr,text="Volumen canción 1 (%):").pack(side="left")
        self.vol1=tk.StringVar(value="100"); ttk.Entry(mr,textvariable=self.vol1,width=6).pack(side="left",padx=5)
        ttk.Label(mr,text="Volumen canción 2 (%):").pack(side="left",padx=(12,0))
        self.vol2=tk.StringVar(value="65"); ttk.Entry(mr,textvariable=self.vol2,width=6).pack(side="left",padx=5)
        ttk.Button(mr,text="MEZCLAR 2 CANCIONES",command=self.mix).pack(side="right")
        self.status=tk.StringVar(value="Listo. Agregá uno o más archivos MP3.")
        ttk.Label(self.root,textvariable=self.status,relief="sunken",anchor="w",padding=7).pack(fill="x",side="bottom")

    def add(self):
        paths=filedialog.askopenfilenames(filetypes=[("Archivos MP3","*.mp3")])
        for p in paths:
            if p not in self.files:
                self.files.append(p); self.list.insert("end",os.path.basename(p))
        if paths: self.status.set(f"{len(self.files)} canción(es) en la lista.")

    def remove(self):
        sel=self.list.curselection()
        if sel:
            i=sel[0]; self.files.pop(i); self.list.delete(i)

    def selected(self):
        sel=self.list.curselection()
        if not sel:
            messagebox.showinfo("Seleccionar","Seleccioná una canción de la lista."); return None
        return self.files[sel[0]]

    def run_ff(self,args):
        p=subprocess.run([ffmpeg(),"-y"]+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if p.returncode: raise RuntimeError(p.stderr.decode("utf-8","replace")[-1800:])
    
    def play(self):
        p=self.selected()
        if not p: return
        try:
            import winsound
            wav=os.path.join(self.tempdir,"preview.wav")
            self.run_ff(["-i",p,"-vn","-ac","2","-ar","44100",wav])
            winsound.PlaySound(wav,winsound.SND_FILENAME|winsound.SND_ASYNC)
            self.status.set("Reproduciendo. Para detener, presioná Escuchar otra vez.")
        except Exception as e: messagebox.showerror("Audio",str(e))

    def output(self, initial):
        return filedialog.asksaveasfilename(defaultextension=".mp3",initialfile=initial,filetypes=[("Audio MP3","*.mp3")])

    def cut(self):
        p=self.selected()
        if not p: return
        out=self.output("corte.mp3")
        if not out: return
        try:
            a=float(self.start.get()); b=float(self.end.get())
            if a<0 or b<=a: raise ValueError("El tiempo final debe ser mayor que el inicial.")
            self.run_ff(["-ss",str(a),"-i",p,"-t",str(b-a),"-vn","-codec:a","libmp3lame","-q:a","2",out])
            self.status.set("Fragmento guardado.")
            messagebox.showinfo("Terminado","El fragmento MP3 se guardó correctamente.")
        except Exception as e: messagebox.showerror("No se pudo cortar",str(e))

    def join(self):
        if len(self.files)<2:
            messagebox.showinfo("Unir","Agregá al menos dos canciones."); return
        out=self.output("canciones_unidas.mp3")
        if not out: return
        try:
            listing=os.path.join(self.tempdir,"lista.txt")
            with open(listing,"w",encoding="utf-8") as f:
                for p in self.files:
                    safe=os.path.abspath(p).replace("\\","/").replace("'","'\\''")
                    f.write("file '"+safe+"'\n")
            self.run_ff(["-f","concat","-safe","0","-i",listing,"-c:a","libmp3lame","-q:a","2",out])
            self.status.set("Canciones unidas.")
            messagebox.showinfo("Terminado","Las canciones se unieron correctamente.")
        except Exception as e: messagebox.showerror("No se pudo unir",str(e))

    def mix(self):
        if len(self.files)<2:
            messagebox.showinfo("Mezclar","Agregá al menos dos canciones."); return
        out=self.output("mezcla.mp3")
        if not out: return
        try:
            v1=float(self.vol1.get()); v2=float(self.vol2.get())
            if not (0<=v1<=200 and 0<=v2<=200): raise ValueError("Los volúmenes deben estar entre 0 y 200.")
            filt=f"[0:a]volume={v1/100}[a0];[1:a]volume={v2/100}[a1];[a0][a1]amix=inputs=2:duration=longest:dropout_transition=2[a]"
            self.run_ff(["-i",self.files[0],"-i",self.files[1],"-filter_complex",filt,"-map","[a]","-codec:a","libmp3lame","-q:a","2",out])
            self.status.set("Mezcla guardada.")
            messagebox.showinfo("Terminado","Las dos canciones se mezclaron correctamente.")
        except Exception as e: messagebox.showerror("No se pudo mezclar",str(e))

    def close(self):
        try:
            import winsound; winsound.PlaySound(None,winsound.SND_PURGE)
        except: pass
        shutil.rmtree(self.tempdir,ignore_errors=True)
        self.root.destroy()

if __name__=="__main__":
    root=tk.Tk()
    try:
        s=ttk.Style()
        if "vista" in s.theme_names(): s.theme_use("vista")
    except: pass
    Editor(root)
    root.mainloop()
