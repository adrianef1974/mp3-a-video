# -*- coding: utf-8 -*-
"""
VideoClip Maker - editor sencillo de videoclips para Windows.
Genera un videoclip 2D animado a partir de escenas, imágenes opcionales y una canción.
No genera animación 3D mediante IA: crea animaciones gráficas sencillas y monta el audio.
"""
import os, sys, math, threading, subprocess, tempfile, shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from mutagen import File as MutagenFile

W, H = 854, 480
FPS = 15

PRESET = [
    ("Charly sentado a la mesa", "Charly está sentado tranquilamente a una mesa en su trabajo.", 7, "sitting"),
    ("La urgencia", "Charly se sobresalta, se levanta rápidamente y empieza a correr.", 5, "surprise"),
    ("Corre por el pasillo", "La cámara lo sigue desde atrás mientras corre con pasos cortitos y rápidos.", 8, "running"),
    ("Llega al baño", "Charly llega al fondo del pasillo, entra al baño y cierra la puerta de golpe.", 6, "door"),
    ("Tarjeta roja", "Justo después aparece un árbitro con silbato y levanta una tarjeta roja.", 6, "referee"),
]

def get_font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def rounded(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def draw_person(draw, cx, cy, scale=1.0, pose="sitting", back=False):
    # Personaje 2D genérico basado en la descripción: bajo, rellenito,
    # pelo corto/escaso arriba, anteojos y guardapolvo azul.
    s=scale
    skin=(224,174,137); blue=(35,91,166); dark=(35,38,45)
    if pose=="running":
        # piernas en zancada
        draw.line((cx-13*s,cy+65*s,cx-42*s,cy+103*s), fill=(38,42,52), width=max(5,int(13*s)))
        draw.line((cx+10*s,cy+65*s,cx+40*s,cy+91*s), fill=(38,42,52), width=max(5,int(13*s)))
        draw.ellipse((cx-53*s,cy+96*s,cx-28*s,cy+108*s), fill=(25,25,28))
        draw.ellipse((cx+28*s,cy+85*s,cx+53*s,cy+98*s), fill=(25,25,28))
    else:
        draw.line((cx-12*s,cy+62*s,cx-16*s,cy+108*s), fill=(38,42,52), width=max(5,int(14*s)))
        draw.line((cx+12*s,cy+62*s,cx+16*s,cy+108*s), fill=(38,42,52), width=max(5,int(14*s)))
    # torso/guardapolvo
    draw.polygon([(cx-25*s,cy+5*s),(cx+25*s,cy+5*s),(cx+34*s,cy+72*s),(cx-34*s,cy+72*s)], fill=blue, outline=(15,48,99))
    draw.line((cx,cy+10*s,cx,cy+68*s), fill=(210,220,238), width=max(1,int(2*s)))
    # arms
    if pose=="running":
        draw.line((cx-23*s,cy+18*s,cx-48*s,cy+42*s), fill=blue, width=max(5,int(12*s)))
        draw.line((cx+23*s,cy+18*s,cx+47*s,cy-2*s), fill=blue, width=max(5,int(12*s)))
    else:
        draw.line((cx-23*s,cy+18*s,cx-42*s,cy+50*s), fill=blue, width=max(5,int(12*s)))
        draw.line((cx+23*s,cy+18*s,cx+42*s,cy+50*s), fill=blue, width=max(5,int(12*s)))
    # head
    draw.ellipse((cx-25*s,cy-48*s,cx+25*s,cy+8*s), fill=skin, outline=(95,63,49), width=max(1,int(2*s)))
    # short sparse hair
    draw.arc((cx-24*s,cy-50*s,cx+24*s,cy-10*s), 185, 350, fill=(65,48,38), width=max(2,int(5*s)))
    if not back:
        # glasses
        draw.ellipse((cx-19*s,cy-25*s,cx-2*s,cy-11*s), outline=(25,25,25), width=max(1,int(2*s)))
        draw.ellipse((cx+2*s,cy-25*s,cx+19*s,cy-11*s), outline=(25,25,25), width=max(1,int(2*s)))
        draw.line((cx-2*s,cy-18*s,cx+2*s,cy-18*s), fill=(25,25,25), width=max(1,int(2*s)))
        draw.ellipse((cx-10*s,cy-8*s,cx-7*s,cy-5*s), fill=(55,35,30))
        draw.ellipse((cx+7*s,cy-8*s,cx+10*s,cy-5*s), fill=(55,35,30))

def background(scene_type, frame_index, total_frames):
    im=Image.new("RGB",(W,H),(225,231,238)); d=ImageDraw.Draw(im)
    # suelo y pared
    d.rectangle((0,0,W,340), fill=(225,231,238))
    d.rectangle((0,340,W,H), fill=(166,174,183))
    d.line((0,340,W,340), fill=(120,130,140), width=3)
    if scene_type in ("sitting","surprise"):
        # mesa
        d.rectangle((115,265,600,292), fill=(120,75,45))
        d.rectangle((145,292,165,430), fill=(85,53,35))
        d.rectangle((545,292,565,430), fill=(85,53,35))
        d.rectangle((0,430,W,480), fill=(130,140,150))
        if scene_type=="sitting":
            draw_person(d,365,200,1.25,"sitting")
            d.text((25,25),"EN EL TRABAJO",font=get_font(23,True),fill=(55,65,78))
        else:
            draw_person(d,365,180,1.25,"running")
            d.text((25,25),"¡DE REPENTE!",font=get_font(25,True),fill=(175,35,35))
            d.line((420,175,475,150),fill=(180,45,35),width=4)
            d.line((420,190,490,190),fill=(180,45,35),width=4)
    elif scene_type=="running":
        # pasillo en perspectiva
        d.polygon([(0,0),(W,0),(610,340),(244,340)],fill=(235,238,242))
        d.polygon([(0,480),(W,480),(610,340),(244,340)],fill=(150,160,170))
        d.line((244,340,0,480),fill=(105,115,125),width=4)
        d.line((610,340,W,480),fill=(105,115,125),width=4)
        for x in (80,220,634,774):
            d.rectangle((x,75,x+35,245),fill=(190,205,218),outline=(115,130,145),width=3)
        draw_person(d,427,210,1.35,"running",back=True)
        d.text((22,22),"¡A TODA VELOCIDAD!",font=get_font(24,True),fill=(165,40,40))
        # líneas de movimiento
        for k in range(4):
            y=200+k*27
            d.line((250,y,310,y-8),fill=(120,130,140),width=3)
    elif scene_type=="door":
        d.rectangle((0,0,W,H),fill=(220,226,232))
        d.rectangle((0,340,W,480),fill=(155,164,174))
        d.rectangle((330,55,535,370),fill=(105,72,48),outline=(55,40,30),width=8)
        d.rectangle((350,75,515,350),fill=(145,103,70))
        d.ellipse((485,205,500,220),fill=(225,190,80))
        d.text((370,95),"BAÑO",font=get_font(25,True),fill=(255,255,255))
        d.text((25,25),"¡JUSTO A TIEMPO!",font=get_font(24,True),fill=(55,65,78))
    elif scene_type=="referee":
        d.rectangle((0,0,W,H),fill=(222,231,220))
        d.rectangle((0,350,W,480),fill=(105,145,95))
        # puerta al fondo
        d.rectangle((75,95,275,355),fill=(105,72,48),outline=(55,40,30),width=7)
        d.text((105,125),"BAÑO",font=get_font(22,True),fill="white")
        # árbitro
        d.ellipse((510,95,590,180),fill=(220,170,135),outline=(70,50,40),width=3)
        d.rectangle((500,175,600,330),fill=(30,30,35))
        d.line((520,320,505,425),fill=(30,30,35),width=18)
        d.line((580,320,595,425),fill=(30,30,35),width=18)
        # brazo y tarjeta roja
        d.line((510,205,455,140),fill=(30,30,35),width=17)
        d.polygon([(420,75),(470,75),(470,145),(420,145)],fill=(210,20,30),outline=(100,0,0))
        d.text((30,25),"¡TARJETA ROJA!",font=get_font(28,True),fill=(170,20,25))
        d.arc((595,65,650,120),180,330,fill=(30,30,30),width=4)
        d.ellipse((612,85,622,95),fill=(30,30,30))
    return im

def add_caption(im, title, description, progress):
    d=ImageDraw.Draw(im)
    # banda inferior
    d.rectangle((0,425,W,480),fill=(15,20,28))
    d.text((22,433),title[:65],font=get_font(19,True),fill=(255,255,255))
    # progreso decorativo
    d.rectangle((0,474,int(W*progress),480),fill=(45,150,230))
    return im

def render_video(audio_path, output_path, scenes, progress_cb):
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    duration=0
    try:
        af=MutagenFile(audio_path)
        duration=float(af.info.length)
    except Exception:
        duration=sum(max(1,int(s["duration"])) for s in scenes)
    if duration<=0: duration=sum(max(1,int(s["duration"])) for s in scenes)
    total_scene=sum(max(1,int(s["duration"])) for s in scenes)
    # Distribuir cada escena según duración indicada y repetir secuencia si la canción es más larga
    plan=[]
    remaining=duration
    while remaining>0:
        for s in scenes:
            if remaining<=0: break
            seg=min(max(1,int(s["duration"])),remaining)
            plan.append((s,seg))
            remaining-=seg
    total_frames=max(1,int(duration*FPS))
    temp=os.path.splitext(output_path)[0]+"_video_sin_audio.mp4"
    cmd=[ffmpeg,"-y","-f","rawvideo","-vcodec","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-movflags","+faststart",temp]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    frame_no=0
    try:
        for scene,seg in plan:
            n=max(1,int(seg*FPS))
            for j in range(n):
                t=j/max(1,n-1)
                im=background(scene["kind"],j,n)
                # movimiento de cámara sutil (zoom/paneo) simulado con variación de encuadre
                if scene["kind"]=="running":
                    shift=int(math.sin(t*math.pi*6)*5)
                    im=im.transform((W,H),Image.Transform.AFFINE,(1,0,shift,0,1,0))
                im=add_caption(im,scene["title"],scene["description"],frame_no/total_frames)
                proc.stdin.write(im.tobytes())
                frame_no+=1
                if frame_no%max(1,FPS*2)==0:
                    progress_cb(min(90,int(frame_no/total_frames*90)))
        proc.stdin.close()
        err=proc.stderr.read().decode("utf-8","ignore")
        code=proc.wait()
        if code!=0: raise RuntimeError("No se pudo generar el video: "+err[-1200:])
    except Exception:
        try: proc.kill()
        except: pass
        raise
    # Mezclar el MP3 con el video
    mux=[ffmpeg,"-y","-i",temp,"-i",audio_path,"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",output_path]
    result=subprocess.run(mux,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try: os.remove(temp)
    except: pass
    if result.returncode!=0:
        raise RuntimeError("No se pudo agregar el audio: "+result.stderr.decode("utf-8","ignore")[-1200:])
    progress_cb(100)

class App:
    def __init__(self, root):
        self.root=root
        root.title("VideoClip Maker - creador de videoclips")
        root.geometry("900x690")
        root.minsize(780,600)
        self.audio=None
        self.scenes=[]
        self.build()
        self.load_preset()

    def build(self):
        top=ttk.Frame(self.root,padding=12); top.pack(fill="x")
        ttk.Label(top,text="VIDEOCLIP MAKER",font=("Segoe UI",20,"bold")).pack(anchor="w")
        ttk.Label(top,text="Crea un videoclip animado 2D con tu música y una secuencia de escenas.",foreground="#555").pack(anchor="w")
        audio=ttk.LabelFrame(self.root,text="1. Canción",padding=10); audio.pack(fill="x",padx=12,pady=6)
        self.audio_label=ttk.Label(audio,text="No hay canción seleccionada")
        self.audio_label.pack(side="left",fill="x",expand=True)
        ttk.Button(audio,text="Cargar MP3",command=self.choose_audio).pack(side="right")
        body=ttk.LabelFrame(self.root,text="2. Escenas del videoclip",padding=10); body.pack(fill="both",expand=True,padx=12,pady=6)
        columns=("title","duration","kind")
        self.tree=ttk.Treeview(body,columns=columns,show="headings",height=10)
        self.tree.heading("title",text="Escena"); self.tree.heading("duration",text="Duración (seg.)"); self.tree.heading("kind",text="Tipo visual")
        self.tree.column("title",width=430); self.tree.column("duration",width=120,anchor="center"); self.tree.column("kind",width=160,anchor="center")
        self.tree.pack(fill="both",expand=True)
        controls=ttk.Frame(body); controls.pack(fill="x",pady=(8,0))
        ttk.Button(controls,text="Agregar escena",command=self.add_scene).pack(side="left",padx=3)
        ttk.Button(controls,text="Editar seleccionada",command=self.edit_scene).pack(side="left",padx=3)
        ttk.Button(controls,text="Eliminar",command=self.delete_scene).pack(side="left",padx=3)
        ttk.Button(controls,text="Cargar ejemplo Charly",command=self.load_preset).pack(side="right",padx=3)
        bottom=ttk.LabelFrame(self.root,text="3. Exportar",padding=10); bottom.pack(fill="x",padx=12,pady=6)
        self.status=ttk.Label(bottom,text="Listo. Cargá una canción para comenzar.")
        self.status.pack(anchor="w")
        self.progress=ttk.Progressbar(bottom,maximum=100); self.progress.pack(fill="x",pady=7)
        row=ttk.Frame(bottom); row.pack(fill="x")
        ttk.Label(row,text="El video se guarda en MP4, 854×480, 15 fps.").pack(side="left")
        ttk.Button(row,text="GENERAR VIDEO MP4",command=self.export).pack(side="right")

    def refresh(self):
        for x in self.tree.get_children(): self.tree.delete(x)
        for i,s in enumerate(self.scenes):
            self.tree.insert("","end",iid=str(i),values=(s["title"],s["duration"],s["kind"]))

    def load_preset(self):
        self.scenes=[{"title":a,"description":b,"duration":c,"kind":d} for a,b,c,d in PRESET]
        self.refresh()

    def choose_audio(self):
        p=filedialog.askopenfilename(filetypes=[("Audio MP3","*.mp3"),("Todos los archivos","*.*")])
        if p:
            self.audio=p; self.audio_label.config(text=os.path.basename(p))
            self.status.config(text="Canción cargada. Podés generar el videoclip.")

    def add_scene(self):
        self.scene_dialog()

    def edit_scene(self):
        sel=self.tree.selection()
        if not sel: messagebox.showinfo("Escenas","Seleccioná una escena."); return
        self.scene_dialog(int(sel[0]))

    def delete_scene(self):
        sel=self.tree.selection()
        if not sel: return
        del self.scenes[int(sel[0])]
        self.refresh()

    def scene_dialog(self,index=None):
        old=self.scenes[index] if index is not None else {"title":"","description":"","duration":6,"kind":"running"}
        win=tk.Toplevel(self.root); win.title("Escena"); win.transient(self.root); win.grab_set()
        frm=ttk.Frame(win,padding=14); frm.pack(fill="both",expand=True)
        ttk.Label(frm,text="Título").pack(anchor="w")
        title=tk.StringVar(value=old["title"]); ttk.Entry(frm,textvariable=title,width=60).pack(fill="x",pady=3)
        ttk.Label(frm,text="Descripción").pack(anchor="w")
        desc=tk.Text(frm,width=60,height=5,wrap="word"); desc.pack(fill="both",expand=True,pady=3); desc.insert("1.0",old["description"])
        ttk.Label(frm,text="Duración en segundos").pack(anchor="w")
        dur=tk.StringVar(value=str(old["duration"])); ttk.Entry(frm,textvariable=dur,width=10).pack(anchor="w",pady=3)
        ttk.Label(frm,text="Tipo de animación").pack(anchor="w")
        kind=tk.StringVar(value=old["kind"])
        ttk.Combobox(frm,textvariable=kind,state="readonly",values=["sitting","surprise","running","door","referee"]).pack(anchor="w",pady=3)
        ttk.Label(frm,text="Tipos: sentado, sorpresa, correr, puerta, árbitro.").pack(anchor="w")
        def save():
            try: seconds=max(1,min(300,int(dur.get())))
            except: messagebox.showerror("Duración","Ingresá segundos válidos.",parent=win); return
            item={"title":title.get().strip() or "Escena","description":desc.get("1.0","end").strip(),"duration":seconds,"kind":kind.get()}
            if index is None: self.scenes.append(item)
            else: self.scenes[index]=item
            self.refresh(); win.destroy()
        ttk.Button(frm,text="Guardar escena",command=save).pack(anchor="e",pady=8)

    def export(self):
        if not self.audio:
            messagebox.showwarning("Falta canción","Primero cargá un archivo MP3."); return
        if not self.scenes:
            messagebox.showwarning("Faltan escenas","Agregá al menos una escena."); return
        out=filedialog.asksaveasfilename(defaultextension=".mp4",filetypes=[("Video MP4","*.mp4")],initialfile="mi_videoclip.mp4")
        if not out: return
        self.progress["value"]=0
        self.status.config(text="Generando video. En esta PC puede tardar...")
        for child in self.root.winfo_children(): pass
        threading.Thread(target=self.worker,args=(out,),daemon=True).start()

    def worker(self,out):
        try:
            render_video(self.audio,out,list(self.scenes),lambda v:self.root.after(0,lambda:self.progress.configure(value=v)))
            self.root.after(0,lambda:(self.status.config(text="¡Video terminado!"),messagebox.showinfo("Terminado","Videoclip creado:\n"+out)))
        except Exception as e:
            self.root.after(0,lambda:(self.status.config(text="Error al generar el video."),messagebox.showerror("Error",str(e))))

def main():
    root=tk.Tk()
    try:
        style=ttk.Style()
        if "vista" in style.theme_names(): style.theme_use("vista")
    except: pass
    App(root)
    root.mainloop()

if __name__=="__main__":
    main()
