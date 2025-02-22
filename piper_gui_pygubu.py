#!/usr/bin/python3
import tkinter as tk
import tkinter.filedialog as fd
import pygubu
from piper_gui_pygubuui import piper_gui_pygubu_classUI
import pyperclip
import subprocess,shlex
from pathlib import Path
import math
import tomllib
from tkinter import messagebox

"""
gui for piper
v.2500222
"""

class config():
    #load toml config
    __slots__=("cfg",)
    def __init__(self):
        try:
            with open("piper_gui_config.toml", "rb") as f:
                self.cfg:dict= tomllib.load(f)
        except Exception as e:
            print('Caught this error: ' + repr(e))
            messagebox.showinfo("error", "failed to load piper_gui_config.toml, cf stderr in console")
            exit(-1)

class pipersay():
    #gère les interactions avec piper
    
    def piper_command_raw(self, debug:str="--debug")->str:
        try:
            vitesse:str=app.get_speed()  # lire vitesse de la gui
        except ValueError:
            return ""
        return f"""piper \
  --model {app.cfg.cfg["model"]} \
  --length-scale {vitesse} {debug} \
  --output-raw"""
    
    def piper_to_wav(self, texte:str,path:str,filename:str,vitesse:str,debug:str="--debug")->None:
        out_dir:Path=Path(path)
        if not out_dir.exists():
            app.set_bar("path doesn't exist")
            return
        out_file_path:Path=out_dir / filename
        if texte=="\n":#si le champ est vide
            app.set_bar("text is empty")
            return
        piper_command:str= f"""piper \
  --model {app.cfg.cfg["model"]} \
  --length-scale {vitesse} {debug} \
  --output_file {str(out_file_path)}"""
        if app.check_comma.instate(['selected']):
            texte=texte.replace(" ",", ")
        proc1_echo=subprocess.Popen(["echo",texte], stdout=subprocess.PIPE)
        proc2_piper = subprocess.Popen(shlex.split(piper_command), stdin=proc1_echo.stdout, stdout=subprocess.PIPE)
        proc1_echo.stdout.close()  # Close the input pipe of proc1_echo to let it terminate (honnêtement c'est de l'ia, je suis pas sûr de mon coup)
        proc2_piper.stdout.close() 

        try:
            proc1_echo.wait(1)  # Wait for command1 to terminate
            proc2_piper.wait(120) #c'est sensé gérer si ça plante... c'est un timeout 120'
            app.set_bar("piper ended")
        except TimeoutExpired :
            app.set_bar("time out!")
    
    def say(self,texte:str)->None:
        # lit texte
        if texte=="\n":#si le champ est vide
            return
        if app.check_comma.instate(['selected']):
            texte=texte.replace(" ",", ")
        proc1_echo=subprocess.Popen(["echo",texte], stdout=subprocess.PIPE)
        proc2_piper = subprocess.Popen(shlex.split(self.piper_command_raw()), stdin=proc1_echo.stdout, stdout=subprocess.PIPE)
        proc1_echo.stdout.close()  # Close the input pipe of proc1_echo to let it terminate (c'est de l'ia, admettons)
        proc3_aplay = subprocess.Popen(['aplay','-N', '-r', '22050', '-f', 'S16_LE', '-t', 'raw'], stdin=proc2_piper.stdout, stdout=subprocess.PIPE)
        proc2_piper.stdout.close() 
        proc3_aplay.stdout.close() 

        try:
            proc1_echo.wait(1)  # Wait for command1 to terminate
            proc2_piper.wait(120) #c'est sensé gérer si ça plante... c'est un timeout 120'
            proc3_aplay.wait(360)
            app.set_bar("piper ended")
            
        except TimeoutExpired :
            app.set_bar("time out!")

class piper_gui_pygubu_class(piper_gui_pygubu_classUI):
    __slots__=("texte","pipersay","label_text","entry_speed","entry_path","entry_filename","master","cfg")
    def __init__(self, master=None):
        super().__init__(master)
        self.master=master
        self.cfg:config=config()
        self.texte = self.builder.get_object("texte", master) #objet champ de texte
        self.pipersay=pipersay() #instantiation de la classe pipersay
        self.label_text=self.builder.get_object("statusbar", master)
        self.entry_speed=self.builder.get_object("entry_speed", master)
        self.entry_speed.insert(0,self.cfg.cfg["speed"])
        self.check_comma=self.builder.get_object("check_comma", master)
        self.check_comma.state(['!alternate']) # sans ça la case est dans l'état alternate au lancement ni oui ni non
        self.entry_path=self.builder.get_object("entry_path", master)
        self.entry_path.insert(0,self.cfg.cfg["path"])
        self.entry_filename=self.builder.get_object("entry_filename", master)
        
    
    def get_speed(self)->str:
        speed:str=self.entry_speed.get()
        try:
            assert float(speed)
        except:
            app.set_bar("speed must be float")
            raise ValueError
        return speed
    
    def get_filename(self)->str:
        outbasename:str=self.entry_filename.get()
        try:
            assert outbasename!=""
        except:
            self.set_bar("choose root name")
            raise ValueError
        return outbasename
    
    def paste(self)->None:
        #insère le presse papier dans le champ texte
        self.texte.insert("1.0",pyperclip.paste())
        
    def clipsay_method(self,widget_id:str)->None:
        #piper lit directement le presse papier
        self.set_bar("starting piper")
        self.pipersay.say(pyperclip.paste())
        # c'est sensé remédier au bouton coincé bas mais ça coince plus ??
        """a=self.builder.get_object(widget_id, self.master) #.config(relief="raised") une option tk qui existe en style en ttk
        style = tk.ttk.Style()
        style.configure('W.TButton', relief = 'raised')
        a.config(style="W.TButton")"""
        
    def flush(self)->None:
        #vide le champ de texte
        self.texte.delete("1.0",tk.END)
        self.set_bar("flush !")
        
    def read(self)->None:
        #lit le champ de texte dans piper
        self.pipersay.say(self.texte.get('1.0', 'end'))
        
    def set_bar(self,s:str)->None:
        #màj statusbar
        self.label_text.config(text=s)
        self.mainwindow.update() #sans ceci, si la tâche qui suit est intensive, la gui est gelée et le message passe pas
        
    def to_wav(self)->None:
        # exporte en wav
        self.set_bar("starting piper")
        try:
            self.pipersay.piper_to_wav(texte=self.texte.get('1.0', 'end'),path=self.entry_path.get(),filename=self.get_filename(),vitesse=self.get_speed())
        except ValueError as e:
            print('Caught this error: ' + repr(e))
            return
        #j'ai essayé avec multiprocessing mais ça crashe tkinter , on pourrait mettre config(relief="raised") pr contourner le pb ou faire des threads
        
    def batchwav(self)->None:
        try:
            outbasename:str=self.get_filename()
        except ValueError:
            return
        
        entry_path:Path=Path(self.entry_path.get())
        if not entry_path.exists():
            app.set_bar("path doesn't exist")
            entry_path=Path("/")
        file_path :tuple | str = fd.askopenfilename(title="select txt file list to convert to wav", initialdir=str(entry_path), filetypes=[("txt file", "*.txt")])
        Path_filename:Path = Path(file_path)
        if not Path_filename.exists():
            self.set_bar("no file chosen")
            return
        outpath:Path=Path(Path_filename.parent) / (outbasename +".csv")
        
        with open(Path_filename,encoding="utf8") as f:
            line_count:int = 0
            for line in f:
                line_count += 1
        nb_chiffres:int=int(math.log10(line_count))+1
        
        try:
            vitesse:str=self.get_speed()
        except ValueError:
            return
        
        with open(Path_filename, encoding="utf8") as finput:       
            i:int=1
            with open(outpath,"w", encoding="utf8") as f:
                for line in finput:
                    stri:str=str(i).zfill(nb_chiffres)
                    line=line.strip()
                    f.write (f"{line};{outbasename}{stri}.opus;{line}[sound:{outbasename}{stri}.opus]\n")
                    i+=1
                    self.pipersay.piper_to_wav(texte=line,path=str(Path(Path_filename.parent))+ "/" ,filename=outbasename +stri+".wav",vitesse=vitesse)
                    self.set_bar(outbasename +stri+".wav")

if __name__ == "__main__":
    app = piper_gui_pygubu_class()
    app.run()
