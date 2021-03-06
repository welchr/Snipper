#!/usr/bin/env python
import os
import sys
import webbrowser
import time
import multiprocessing as mp
from threading import Thread
from Queue import Empty as QueueEmpty
from settings import *
from main import run_snipper
from functools import partial
from shutil import rmtree

py2 = py30 = py31 = False
version = sys.hexversion
if version >= 0x020600F0 and version < 0x03000000 :
  py2 = True    # Python 2.6 or 2.7
  from Tkinter import *
  import ttk
elif version >= 0x03000000 and version < 0x03010000 :
  py30 = True
  from tkinter import *
  import ttk
elif version >= 0x03010000:
  py31 = True
  from tkinter import *
  import tkinter.ttk as ttk
else:
  raise ImportError, "Could not import Tkinter - see documentation for more info.";

from tkFileDialog import *
from tkMessageBox import *
    
def todo():
  print >> sys.stderr, "Not yet implemented..";
  
class SnipperUI():
  def __init__(self,root=None):
    root = Tk();
    self.root = root;
    root.geometry('460x635+50+50');
    root.minsize(460,635);
    
    style = ttk.Style();
    theme = style.theme_use();
    default = style.lookup(theme,'background');
    root.configure(background=default);
    
    menubar = Menu(root);
    
    filemenu = Menu(menubar,tearoff=0);
    filemenu.add_command(label="Run Snipper..",command=self.run);
    filemenu.add_separator();
    filemenu.add_command(label="Exit",command=root.destroy);
    menubar.add_cascade(label="File",menu=filemenu);
    
    helpmenu = Menu(menubar,tearoff=0);
    helpmenu.add_command(label="Documentation",command=self.launch_docs);
    helpmenu.add_separator();
    helpmenu.add_command(label="About..",command=self.show_about);
    menubar.add_cascade(label="Help",menu=helpmenu);
    
    root.config(menu=menubar);
    
    root.title("Snipper");
    
    notebook = ttk.Notebook(root);
    notebook.pack(anchor=CENTER,expand=True,fill=BOTH,padx=3,pady=3);
    
    genome_tab = Frame(notebook);
    notebook.add(genome_tab,padding=3);
    notebook.tab(0,text="Genome",underline="-1");
    
    label1 = Label(genome_tab,text="Enter a list of SNPs, genes, and chromosomal regions (one per line):");
    label1.pack(side=TOP,anchor=W,padx=3,pady=5);
    
    self.textRegions = Text(genome_tab);
    self.textRegions.pack(side=TOP,expand=True,fill=BOTH,padx=3,pady=3);
    
    def select_all(event):
      event.widget.tag_add('sel',1.0,'end');
      return "break";
    
    self.textRegions.bind("<Control-a>",select_all)
    
    buttonFrame = Frame(genome_tab);
    buttonFrame.pack(side=TOP,fill=X,padx=3,pady=3);
    
    buttonLoad = ttk.Button(buttonFrame,text="Load from file..",width=17,command=self.load_regions);
    buttonLoad.pack(side=LEFT,anchor=W,padx=3,pady=3);
    
    buttonClear = ttk.Button(buttonFrame,text="Clear",command=self.clear_regions);
    buttonClear.pack(side=LEFT,anchor=W,padx=3,pady=3);
    
    genome_frame = Frame(genome_tab);
    genome_frame.pack(side=BOTTOM,anchor=W,padx=3,pady=3);
    
    labelBuild = Label(genome_frame,text="Genome build:");
    labelBuild.grid(row=0,column=0,sticky=W,padx=3,pady=3);
    
    self.comboBuild = ttk.Combobox(genome_frame);
    self.comboBuild.grid(row=0,column=1,sticky=W,padx=3,pady=3);
    
    labelDist = Label(genome_frame,text="Distance to search from each SNP:");
    labelDist.grid(row=1,column=0,sticky=W,padx=3,pady=3);
    
    self.entryDist = ttk.Entry(genome_frame);
    self.entryDist.grid(row=1,column=1,sticky=W,padx=3,pady=3);
    
    labelNumGenes = Label(genome_frame,text="Max number of genes per SNP:");
    labelNumGenes.grid(row=2,column=0,sticky=W,padx=3,pady=3);
    
    self.entryNumGenes = ttk.Entry(genome_frame);
    self.entryNumGenes.grid(row=2,column=1,sticky=W,padx=3,pady=3);
    
    db_tab = Frame(notebook);
    notebook.add(db_tab,padding=3);
    notebook.tab(1,text="Databases",underline="-1");
    
    dblabel = Label(db_tab,text="Change settings for each database supported by Snipper below.");
    dblabel.pack(anchor=W,padx=3,pady=5);
    
    dbnotebook = ttk.Notebook(db_tab);
    dbnotebook.pack(expand=True,fill=BOTH,padx=3,pady=3);
    
    pubmed_tab = Frame(dbnotebook);
    dbnotebook.add(pubmed_tab,padding=3);
    dbnotebook.tab(0,text="PubMed",underline="-1");
    
    self.bCheckPubmed = BooleanVar();
    checkPubmed = ttk.Checkbutton(pubmed_tab,text="Enabled",variable=self.bCheckPubmed);
    checkPubmed.pack(padx=7,pady=7,anchor=W);
    
    pubmedFrame = Frame(pubmed_tab);
    pubmedFrame.pack(padx=3,pady=3,anchor=W);
    
    labelArticles = Label(pubmedFrame,text="Number of recent PubMed articles to return:");
    labelArticles.grid(row=0,column=0,padx=3,pady=5,sticky=W);
    
    self.entryNumArticles = ttk.Entry(pubmedFrame);
    self.entryNumArticles.grid(row=0,column=1,padx=3,pady=3,sticky=W);
    
    labelEach = Label(pubmedFrame,text="Search for each gene/term combination?");
    labelEach.grid(row=1,column=0,padx=3,pady=5,sticky=W);
    
    self.bCheckEachCombo = BooleanVar();
    checkEachCombo = ttk.Checkbutton(pubmedFrame,text="Yes",variable=self.bCheckEachCombo);
    checkEachCombo.grid(row=1,column=1,padx=3,pady=3,sticky=W);
    
    mimi_tab = Frame(dbnotebook);
    dbnotebook.add(mimi_tab,padding=3);
    dbnotebook.tab(1,text="MiMI",underline="-1");
    
    self.bCheckMimi = BooleanVar();
    checkMimi = ttk.Checkbutton(mimi_tab,text="Enabled",variable=self.bCheckMimi);
    checkMimi.pack(padx=7,pady=7,anchor=W);
    
    scan_tab = Frame(dbnotebook);
    dbnotebook.add(scan_tab,padding=3);
    dbnotebook.tab(2,text="SCAN",underline="-1");
    
    self.bCheckScan = BooleanVar();
    checkScan = ttk.Checkbutton(scan_tab,text="Enabled",onvalue=True,offvalue=False,variable=self.bCheckScan);
    checkScan.pack(padx=7,pady=7,anchor=W);
    
    scanFrame = Frame(scan_tab);
    scanFrame.pack(padx=3,pady=3,anchor=W);
    
    pvalLabel = Label(scanFrame,text="P-value threshold:");
    pvalLabel.grid(row=0,column=0,padx=3,pady=3,sticky=W);
    
    self.entryScanPval = ttk.Entry(scanFrame);
    self.entryScanPval.grid(row=0,column=1,padx=3,pady=3,sticky=W);
    
    search_tab = Frame(notebook);
    notebook.add(search_tab,padding=3);
    notebook.tab(2,text="Search Terms",underline="-1");
    
    labelSearch = Label(search_tab,text="Enter list of search terms, one per line:");
    labelSearch.pack(side=TOP,padx=3,pady=5,anchor=W);
    
    self.textSearch = Text(search_tab);
    self.textSearch.pack(side=TOP,padx=3,pady=3,expand=True,fill=BOTH,anchor=W);
    self.textSearch.bind("<Control-a>",select_all);
    
    buttonClearSearch = ttk.Button(search_tab,text="Clear",command=self.clear_search);
    buttonClearSearch.pack(side=TOP,padx=3,pady=3,anchor=W);
    
    style.configure("Imp.TButton",foreground='red',font='TkDefaultFont 9 bold');
    #run_button = ttk.Button(root,text="Run Snipper",width=15,style="Imp.TButton");
    run_button = Button(root,text="Run Snipper",fg="red",font="TkDefaultFont 12 bold",relief="groove",padx=2,pady=2,justify=CENTER,command=self.run);
    run_button.pack(anchor=CENTER,padx=3,pady=7);
    
    output_tab = Frame(notebook);
    notebook.add(output_tab,padding=3);
    notebook.tab(3,text="Output",underline="-1");
    
    output_frame = Frame(output_tab);
    output_frame.pack(side=TOP,anchor=W,padx=5,pady=5,fill=X);
    
    outdirLabel = Label(output_frame,text="Output directory:");
    outdirLabel.pack(side=LEFT,padx=3);
    
    self.entryOutdir = ttk.Entry(output_frame);
    self.entryOutdir.pack(side=LEFT,padx=3,fill=X,expand=True);
    
    buttonOutdir = ttk.Button(output_frame,text="Select directory..",command=self.select_outdir);
    buttonOutdir.pack(side=LEFT,padx=3);
    
    # check_frame = Frame(output_tab);
    # check_frame.pack(side=TOP,anchor=W,padx=5,pady=5,fill=X);
    
    # self.checkHTML = ttk.Checkbutton(check_frame,text="Write HTML");
    # self.checkHTML.pack(side=TOP,anchor=W,padx=3,pady=3);
    
    # self.checkRST = ttk.Checkbutton(check_frame,text="Write ReST");
    # self.checkRST.pack(side=TOP,anchor=W,padx=3,pady=3);
    
    # self.checkText = ttk.Checkbutton(check_frame,text="Write text");
    # self.checkText.pack(side=TOP,anchor=W,padx=3,pady=3);
    
    self.init_defaults();
    root.mainloop();
  
  def select_outdir(self):
    current_dir = self.entryOutdir.get();
    dir = askdirectory();
    
    if dir == None or dir == "":
      dir = current_dir;
    else:
      if os.path.exists(dir):
        if not self.settings.overwrite:
          showerror(title="Error",message="Directory already exists - please specify a directory that does not exist.");
          dir = current_dir;

    self.entryOutdir.delete(0,END);
    self.entryOutdir.insert(0,dir);
    
  def init_defaults(self):
    s = Settings();
    self.settings = s;
    
    self.entryOutdir.insert(0,s.outdir);
    self.comboBuild.configure(values=list(s.valid_builds));
    self.comboBuild.set(s.build);
    self.entryNumGenes.insert(0,s.num_genes);
    self.entryDist.insert(0,s.distance);
    self.entryNumArticles.insert(0,s.pnum);
    self.entryScanPval.insert(0,s.scandb_pval);
    
    self.bCheckScan.set(s.scandb);
    self.bCheckEachCombo.set(s.per_term);
    self.bCheckPubmed.set(s.pubmed);
    self.bCheckMimi.set(s.mimi);
  
  def launch_docs(self):
    webbrowser.open("http://csg.sph.umich.edu/boehnke/snipper/");
    
  def show_about(self):
    dialog = AboutDialog(self.root);
    dialog.focus_set();
    
  def clear_regions(self):
    self.textRegions.delete(1.0,END);
    self.textRegions.focus_set();
  
  def clear_search(self):
    self.textSearch.delete(1.0,END);
    self.textSearch.focus_set();
  
  def load_regions(self):
    regions_file = askopenfilename();
    
    if regions_file == None or regions_file == "":
      return;
    
    if not os.path.isfile(regions_file):
      showerror(title="Error",message="Could not open file: %s" % regions_file);
      return;
    elif not os.access(regions_file,os.R_OK):
      showerror(title="Error",message="Could not access file: %s" % regions_file);
      return;
    
    self.settings.parseGenericFile(regions_file);
    
    items = [];
    items += list(self.settings.snpset);
    items += list(self.settings.genes);
    items += [str(i) for i in self.settings.regions];
    joined_list = "\n".join(items);
    
    self.textRegions.delete(1.0,END);
    self.textRegions.insert(END,joined_list);

  def update_settings(self):
    try:
      self.settings.parseGenericString(self.textRegions.get(1.0,END));
      self.settings.parseTerms(self.textSearch.get(1.0,END));
      self.settings.build = self.comboBuild.get();
      self.settings.distance = self.entryDist.get();
      self.settings.num_genes = self.entryNumGenes.get();
      self.settings.pubmed = self.bCheckPubmed.get();
      self.settings.mimi = self.bCheckMimi.get();
      self.settings.scandb = self.bCheckScan.get();
      self.settings.outdir = self.entryOutdir.get();
      self.settings.per_term = self.bCheckEachCombo.get();
      self.settings.scandb_pval = self.entryScanPval.get();
    except:
      import traceback
      msg = traceback.format_exc();
      #msg = sys.exc_value;
      showerror(title="Error",message=msg);
      return False;
    
    return True;
    
  def run(self):
    bSetOK = self.update_settings();
    if not bSetOK:
      return;
    
    if os.path.isdir(self.settings.outdir) and self.settings.overwrite:
      if self.settings.warn_overwrite:
        del_dir = askyesno(title="Message",message="Directory exists: %s. Are you sure you want to delete it?" % self.settings.outdir);
        if del_dir:
          rmtree(self.settings.outdir);
        else:
          return;
      else:
        rmtree(self.settings.outdir);
    
    try:
      os.makedirs(self.settings.outdir);
    except:
      msg = ("Snipper output directory already exists: %(dir)s. %(sep)sPlease remove "
            "this directory, or change your output directory in the "
            "'Output' tab. " % {'dir':self.settings.outdir,'sep':os.linesep});
      showerror(title="Output directory exists!",message=msg);
      return;
    
    eventBusy = mp.Event();
    eventStopped = mp.Event();
    msgQueue = mp.Queue();
    
    p = mp.Process(target=snipper_thread,args=(self.settings,msgQueue,eventBusy,eventStopped));
    con = Console(self.root,msgQueue,eventBusy,eventStopped,p);
    con.html_index = os.path.join(self.settings.outdir,"html","index.html");
    
    p.start();
    
def snipper_thread(settings,queue,busy,stop):
  redir = IOQueueRedirect(queue);
  redir.start();

  busy.set();
  
  try:
    run_snipper(settings);
    queue.put(os.linesep + "Snipper has completed! Click the 'Open browser..' button to open the report in your web browser.");
  except:
    stop.set();
    if _SNIPPER_DEBUG:
      raise;
    else:
      print sys.exc_value;
      
  busy.clear();
  
  redir.stop();

class AboutDialog(Toplevel):
  def __init__(self,root):
    Toplevel.__init__(self,root);
    self.root = root;
    
    self.title("About Snipper");
    
    label1 = Label(self,text="Snipper v1.2",fg="red");
    label1.pack(padx=3,pady=3,anchor=W);
    
    label2 = Label(self,text="Coded by: Ryan Welch (welchr@umich.edu)");
    label2.pack(padx=3,pady=3,anchor=W);
    
    label3 = Label(self,text="Design and methodology by: ");
    label3.pack(padx=3,pady=3,anchor=W);
    
    authors = [
      'Ryan Welch',
      'Tanya Teslovich',
      'Michael Boehnke',
      'Laura Scott',
      'Cristen Willer'
    ];
    author_text = ", ".join(authors);
    label4 = Label(self,text=author_text,justify=LEFT);
    label4.pack(padx=3,pady=3,anchor=W);
    
    self.bind("<Return>",self.cancel);
    self.bind("<Escape>",self.cancel);
    self.resizable(0,0);
    self.grab_set();
   
  def cancel(self,event=None):
    self.root.focus_set();
    self.destroy();

class IOQueueRedirect:
  def __init__(self,queue):
    self.queue = queue;

  def start(self):
    sys.stdout = self;
    sys.stderr = self;

  def stop(self):
    sys.stdout = sys.__stdout__;
    sys.stderr = sys.__stderr__;

  def write(self,s):
    self.queue.put(s);

  def flush(self):
    pass

class Console(Toplevel):
  def __init__(self,master,queue,busy,stopped,proc):
    Toplevel.__init__(self,master);
    self.master = master;
    self.queue = queue;
    self.html_index = None;
    self.busy_state = busy;
    self.proc = proc;
    self.stopped = stopped;
    
    # Set style. 
    style = ttk.Style()
    theme = style.theme_use()
    default = style.lookup(theme, 'background')
    self.configure(background=default)

    self.textFrame = Frame(self);
    self.textFrame.pack(fill=BOTH,expand=True);
    
    self.sbar = Scrollbar(self.textFrame);
    self.sbar.pack(side=RIGHT,fill=Y);
    
    self.text = Text(self.textFrame,wrap=WORD,yscrollcommand=self.sbar.set,padx=3,pady=3);
    self.text.pack(fill=BOTH,expand=True);
    self.text.configure(background="white");
    self.sbar.config(command=self.text.yview);

    self.buttonOpenBrowser = ttk.Button(self,command=self.open_browser);
    self.buttonOpenBrowser.pack(side=LEFT,anchor=W,padx=4,pady=4);
    self.buttonOpenBrowser.configure(takefocus="");
    self.buttonOpenBrowser.configure(text="Open browser..")

    self.buttonSaveLog = ttk.Button(self,command=self.save_log);
    self.buttonSaveLog.pack(side=LEFT,anchor=W,padx=4,pady=4);
    self.buttonSaveLog.configure(takefocus="");
    self.buttonSaveLog.configure(text="Save log..")

    self.buttonCancel = ttk.Button(self,command=self.stop);
    self.buttonCancel.pack(side=RIGHT,anchor=E,padx=4,pady=4);
    self.buttonCancel.configure(takefocus="");
    self.buttonCancel.configure(text="Stop");
    
    self.protocol("WM_DELETE_WINDOW",self.cancel);
    
    self.grab_set();
    self.update_me();

  def update_me(self):
    try:
      while 1:
        line = self.queue.get_nowait();
        
        if line is None:
          self.text.delete(1.0,END);
        else:
          self.text.insert(END,str(line));
        
        self.text.see(END);
        self.text.update_idletasks();

    except QueueEmpty:
      pass   
    
    if self.busy_state.is_set():
      self.busy();
    else:
      self.not_busy();
    
    self.after(100,self.update_me);
  
  def cancel(self,event=None):
    self.stop();
    self.master.focus_set();
    self.destroy();
  
  def stop(self):
    self.queue.put(os.linesep + "Current run terminated. You can close the console at any time.");
    self.proc.terminate();
    self.proc.join();
    self.busy_state.clear();
    self.stopped.set();

  def destroy(self):
    self.stop();
    Toplevel.destroy(self);

  def save_log(self):
    fname = asksaveasfilename();
    try:
      f = open(fname,"w");
      print >> f, self.text.get(1.0,END);
      f.close();
      self.queue.put(os.linesep + "Wrote log file to: %s" % fname);
    except:
      self.queue.put(os.linesep + "Error writing log file: ");
      self.queue.put(sys.exc_value);

  def busy(self):
    self.config(cursor="watch");
    self.text.config(cursor="watch");
    self.buttonOpenBrowser.config(state=DISABLED);
    self.buttonSaveLog.config(state=DISABLED);
    self.buttonCancel.config(state=NORMAL);
    
  def not_busy(self):
    self.config(cursor="");
    self.text.config(cursor="xterm");
    
    if not self.stopped.is_set():
      self.buttonOpenBrowser.config(state=NORMAL);
    else:
      self.buttonOpenBrowser.config(state=DISABLED);
    
    self.buttonSaveLog.config(state=NORMAL);
    self.buttonCancel.config(state=DISABLED);

  def open_browser(self):
    if os.path.exists(self.html_index):
      webbrowser.open(self.html_index);
    else:
      pass

def main():
  SnipperUI();
  
if __name__ == "__main__":
  try:
    main();
  except:
    import traceback
    traceback.print_exc();
    
    print "Press any key to continue..";
    raw_input();