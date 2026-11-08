"""Native settings, organizer and local conversation-history windows."""
import json
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, simpledialog, scrolledtext
from reactor_ui import BG, PANEL, TEXT, MUTED, ACCENT


def window_for(app,attribute,title,geometry='800x650'):
    existing = getattr(app,attribute,None)
    if existing and existing.winfo_exists():
        existing.lift()
        return existing,False
    window = tk.Toplevel(app.root)
    window.title('ASUNA — '+title)
    window.geometry(geometry)
    window.minsize(650,480)
    window.configure(bg=BG)
    setattr(app,attribute,window)
    return window,True


def allowed(app):
    if app.busy or app.voice.input_busy or app.restoring:
        messagebox.showinfo('ASUNA','Finish or stop the current request before changing saved data.',parent=app.root)
        return False
    return True


def explain_error(window,operation):
    try:
        return operation()
    except (OSError,ValueError,KeyError,RuntimeError) as exc:
        messagebox.showerror('ASUNA',str(exc),parent=window)
        return None


def title(parent,text):
    tk.Label(parent,text=text,bg=BG,fg=TEXT,font=('Segoe UI',14,'bold'),anchor='w').pack(fill='x',padx=16,pady=(14,8))


def notebook(parent):
    style = ttk.Style(parent)
    style.configure('Asuna.TNotebook',background=BG,borderwidth=0)
    style.configure('Asuna.TNotebook.Tab',background=PANEL,foreground=TEXT,padding=(15,9))
    style.map('Asuna.TNotebook.Tab',background=[('selected','#234b5b')])
    book = ttk.Notebook(parent,style='Asuna.TNotebook')
    book.pack(fill='both',expand=True,padx=14,pady=12)
    return book


def tree(parent,columns):
    holder = tk.Frame(parent,bg=BG)
    holder.pack(fill='both',expand=True,padx=12,pady=8)
    view = ttk.Treeview(holder,columns=[c[0] for c in columns],show='headings',style='Work.Treeview',selectmode='browse',height=8)
    for name,label,width in columns:
        view.heading(name,text=label)
        view.column(name,width=width,minwidth=60)
    view.pack(side='left',fill='both',expand=True)
    scroll = ttk.Scrollbar(holder,orient='vertical',command=view.yview)
    scroll.pack(side='right',fill='y')
    view.configure(yscrollcommand=scroll.set)
    return view


def buttons(app,parent,items):
    bar = tk.Frame(parent,bg=BG)
    bar.pack(fill='x',padx=12,pady=8)
    for index,(label,command) in enumerate(items):
        app.button(bar,label,command).grid(row=index//4,column=index%4,sticky='w',padx=(0,6),pady=3)
    return bar


def show_settings(app,section='general'):
    window,created = window_for(app,'settings_window','Settings','830x700')
    if not created:
        if hasattr(app,'settings_tabs'):
            app.settings_book.select(app.settings_tabs.get(section,app.settings_tabs['general']))
        return
    window.minsize(700,620)
    title(window,'Make ASUNA yours')
    book = app.settings_book = notebook(window)
    tabs = app.settings_tabs = {key:tk.Frame(book,bg=BG) for key in ('general','shortcuts','health','data')}
    for key,label in (('general','Assistant'),('shortcuts','Shortcuts'),('health','Check setup'),('data','Data & history')):
        book.add(tabs[key],text=label)
    values = app.preferences.values
    controls = {}
    for row,(key,label,options) in enumerate((
            ('fast_model','Fast model',list(app.models.values())),('deep_model','Deep model',list(app.models.values())),
            ('default_mode','Start in',('Fast','Deep')),('reply_style','Reply style',('Brief','Balanced','Detailed')),
            ('context_tokens','Context size',(2048,4096,8192,16384)),('reply_tokens','Response limit',(512,1024,2048,4096)))):
        tk.Label(tabs['general'],text=label,bg=BG,fg=TEXT).grid(row=row,column=0,sticky='w',padx=18,pady=10)
        variable = controls[key] = tk.StringVar(master=window,value=str(values[key]))
        widget = ttk.Combobox(tabs['general'],textvariable=variable,values=options,width=43,
                              state='normal' if key.endswith('_model') else 'readonly')
        widget.grid(row=row,column=1,sticky='ew',padx=18,pady=10)
        if key.endswith('_model'):
            setattr(app,key+'_choice',widget)
    tabs['general'].columnconfigure(1,weight=1)
    auto = tk.BooleanVar(master=window,value=values['auto_backup'])
    tk.Checkbutton(tabs['general'],text='Create one local data backup each day I open ASUNA',variable=auto,
                   bg=BG,fg=TEXT,selectcolor=PANEL,activebackground=BG,activeforeground=TEXT).grid(row=6,column=0,columnspan=2,sticky='w',padx=18,pady=12)
    saved = tk.StringVar(master=window,value='Model changes apply to your next request. Larger context uses more memory.')
    tk.Label(tabs['general'],textvariable=saved,bg=BG,fg=MUTED,wraplength=680,justify='left').grid(row=7,column=0,columnspan=2,sticky='w',padx=18,pady=12)

    def save_preferences():
        if not allowed(app): return
        def apply():
            changed = {key:(int(v.get()) if key in ('context_tokens','reply_tokens') else v.get().strip()) for key,v in controls.items()}
            changed['auto_backup'] = auto.get()
            app.preferences.save(changed)
            app.models = app.preferences.models
            app.mode.set(changed['default_mode'])
            saved.set('Saved. Your next request will use these settings.')
        explain_error(window,apply)
    bar = tk.Frame(tabs['general'],bg=BG)
    bar.grid(row=8,column=0,columnspan=2,sticky='w',padx=18,pady=8)
    app.button(bar,'Save settings',save_preferences).pack(side='left',padx=(0,8))
    app.button(bar,'Voice settings',app.show_voice_settings).pack(side='left')

    title(tabs['shortcuts'],'Your apps, websites and folders')
    shortcut_tree = tree(tabs['shortcuts'],(('name','Name',170),('kind','Type',70),('target','Location',390),('enabled','Enabled',70)))
    def refresh_shortcuts():
        shortcut_tree.delete(*shortcut_tree.get_children())
        for index,item in enumerate(app.actions.shortcuts.state['items']):
            shortcut_tree.insert('','end',iid=str(index),values=(item['name'],item['kind'],item['target'],'Yes' if item['enabled'] else 'No'))
    def add_shortcut(kind):
        if not allowed(app): return
        if kind=='site':
            target = simpledialog.askstring('Website shortcut','Website address (https://…):',parent=window)
        elif kind=='folder':
            target = filedialog.askdirectory(parent=window,title='Choose a shortcut folder')
        else:
            target = filedialog.askopenfilename(parent=window,title='Choose an installed app',filetypes=[('Windows apps','*.exe')])
        if not target: return
        name = simpledialog.askstring('Shortcut name','What should ASUNA call it? For example: Spotify or Work files',parent=window)
        if not name: return
        def save():
            if not allowed(app):return
            app.actions.shortcuts.set(name,kind,target)
            refresh_shortcuts()
        explain_error(window,save)
    def selected_shortcut():
        selection = shortcut_tree.selection()
        return app.actions.shortcuts.state['items'][int(selection[0])] if selection else None
    def toggle_shortcut():
        item = selected_shortcut()
        if item and allowed(app):
            explain_error(window,lambda:app.actions.shortcuts.toggle(item['name']))
            refresh_shortcuts()
    def open_shortcut():
        item = selected_shortcut()
        if item and allowed(app): app.submit('open '+item['name'])
    buttons(app,tabs['shortcuts'],[('Add app',lambda:add_shortcut('app')),('Add website',lambda:add_shortcut('site')),
                                  ('Add folder',lambda:add_shortcut('folder')),('Enable / disable',toggle_shortcut),('Open selected',open_shortcut)])
    tk.Label(tabs['shortcuts'],text='Say “open” followed by a shortcut name. App shortcuts select an installed .exe; arguments and scripts are not accepted.',bg=BG,fg=MUTED,wraplength=680,justify='left').pack(fill='x',padx=16,pady=(0,12))
    refresh_shortcuts()

    title(tabs['health'],'Check ASUNA’s local setup')
    app.health_tree = tree(tabs['health'],(('component','Component',150),('status','Status',190),('help','Next step',390)))
    app.health_detail = tk.StringVar(master=window,value='These checks never record audio or change your accounts.')
    app.health_check_running = False
    tk.Label(tabs['health'],textvariable=app.health_detail,bg=BG,fg=MUTED,wraplength=680,justify='left').pack(fill='x',padx=16,pady=8)
    def refresh_health():
        if app.health_check_running:return
        app.health_check_running = True
        app.health_detail.set('Checking local services…')
        events,data,models = app.events,app.actions.data,dict(app.models)
        def work():
            try:
                from diagnostics import setup_report
                events.put(('setup_health',setup_report(data,models)))
            except Exception as exc:
                events.put(('setup_health',([('Setup check','Needs attention',str(exc))],[])))
        threading.Thread(target=work,daemon=True).start()
    def choose_profile():
        if not allowed(app): return
        def choose():
            from browser_profile import profiles,save
            _,options = profiles()
            if not options: raise ValueError('No Chrome profiles were found. Open Chrome once, then try again.')
            dialog = tk.Toplevel(window)
            dialog.title('Choose Chrome profile')
            dialog.configure(bg=BG)
            tk.Label(dialog,text='ASUNA will open links in this profile.',bg=BG,fg=TEXT).pack(padx=18,pady=12)
            labels = [p['profile_name']+' ('+p['profile_directory']+')' for p in options]
            choice = tk.StringVar(master=dialog,value=labels[0])
            ttk.Combobox(dialog,textvariable=choice,values=labels,state='readonly',width=45).pack(padx=18,pady=8)
            def apply():
                def commit():
                    if not allowed(app):return
                    save(options[labels.index(choice.get())],app.actions.data)
                    from browser_control import session
                    session.reset_profile()
                    dialog.destroy()
                    app.health_detail.set('Profile saved. Type connect browser to pair the extension in that profile.')
                    refresh_health()
                explain_error(dialog,commit)
            app.button(dialog,'Use this profile',apply).pack(pady=14)
        explain_error(window,choose)
    buttons(app,tabs['health'],[('Refresh checks',refresh_health),('Choose Chrome profile',choose_profile),
                               ('Connect browser',lambda:app.submit('connect browser')),('Voice settings',app.show_voice_settings)])
    app.refresh_health = refresh_health
    def check_selected_tab(event=None):
        if book.select()==str(tabs['health']) and not app.health_tree.get_children():
            refresh_health()
    book.bind('<<NotebookTabChanged>>',check_selected_tab)

    title(tabs['data'],'Your data stays on this computer')
    tk.Label(tabs['data'],text='Backups contain personal chats, notes, tasks, memories and settings. Browser cookies, model weights and extension pairing secrets are excluded.\n\nRestore replaces the state files in the selected archive, makes a safety backup first, and closes ASUNA so restored data loads cleanly.',bg=BG,fg=MUTED,justify='left',wraplength=690).pack(fill='x',padx=18,pady=10)
    def export_backup():
        if not allowed(app): return
        filename = filedialog.asksaveasfilename(parent=window,title='Save a personal data backup',defaultextension='.zip',initialfile='ASUNA-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip',filetypes=[('ASUNA backup','*.zip')])
        if not filename:return
        def export():
            from backups import create_backup
            app.persist()
            create_backup(app.actions.data,filename,overwrite=True)
            messagebox.showinfo('ASUNA','Backup saved.',parent=window)
        explain_error(window,export)
    def restore():
        if not allowed(app):return
        filename = filedialog.askopenfilename(parent=window,title='Choose an ASUNA backup',filetypes=[('ASUNA backup','*.zip')])
        if not filename:return
        def apply():
            from backups import inspect_backup,restore_backup
            payload = inspect_backup(filename)
            if not messagebox.askyesno('Restore personal data','Replace these saved files from the backup?\n\n'+'\n'.join(sorted(payload))+'\n\nA safety backup will be created. ASUNA will then close.',parent=window):return
            app.restoring = True
            try:
                safety = restore_backup(app.actions.data,filename)
            except Exception:
                app.restoring = False
                raise
            messagebox.showinfo('ASUNA','Restore complete. Reopen Start ASUNA.bat.\nSafety backup: '+str(safety),parent=window)
            app.close()
        explain_error(window,apply)
    def export_chat():
        if not allowed(app):return
        filename = filedialog.asksaveasfilename(parent=window,title='Export current chat',defaultextension='.txt',filetypes=[('Text','*.txt')])
        if filename:
            explain_error(window,lambda:Path(filename).write_text('\n\n'.join(m['role'].upper()+'\n'+m['content'] for m in app.history),encoding='utf-8'))
    def open_data():
        import os
        os.startfile(str(app.actions.data))
    buttons(app,tabs['data'],[('Save backup',export_backup),('Restore backup',restore),('Export current chat',export_chat),
                             ('View chat history',app.show_history),('Open data folder',open_data)])
    book.select(tabs.get(section,tabs['general']))


def update_health(app,value):
    app.health_check_running = False
    if not app.settings_window or not app.settings_window.winfo_exists():return
    rows,names = value
    app.health_tree.delete(*app.health_tree.get_children())
    for index,row in enumerate(rows):app.health_tree.insert('','end',iid=str(index),values=row)
    app.health_detail.set('Checks complete. Select a row to read the next step.')
    app.health_tree.bind('<<TreeviewSelect>>',lambda e:app.health_detail.set(app.health_tree.item(app.health_tree.selection()[0],'values')[2]) if app.health_tree.selection() else None)
    for key in ('fast_model','deep_model'):
        getattr(app,key+'_choice').configure(values=names or list(app.models.values()))


def show_organizer(app):
    window,created = window_for(app,'organizer_window','Organizer','850x680')
    if not created:return
    window.minsize(700,560)
    title(window,'Tasks, notes and daily routines')
    buttons(app,window,[('Daily overview',lambda:app.submit('daily overview')),('Chat history',app.show_history)])
    book = notebook(window)
    panels = [tk.Frame(book,bg=BG) for _ in range(3)]
    for panel,label in zip(panels,('Tasks','Notes','Routines')):book.add(panel,text=label)
    from everyday import TaskService
    task_service = TaskService(app.actions)
    archived = tk.BooleanVar(master=window,value=False)
    task_tree = tree(panels[0],(('id','ID',40),('text','Task',370),('status','Status',90),('due','Due',100),('priority','Priority',90)))
    def refresh_tasks():
        selected = task_tree.selection()
        task_tree.delete(*task_tree.get_children())
        for t in app.actions.state['tasks']:
            if t.get('archived') and not archived.get():continue
            task_tree.insert('','end',iid=str(t['id']),values=(t['id'],t['text'],'Archived' if t.get('archived') else 'Done' if t['done'] else 'Open',t.get('due',''),t.get('priority','normal')))
        if selected and task_tree.exists(selected[0]):task_tree.selection_set(selected[0])
    def selected_task():
        chosen = task_tree.selection()
        return next((t for t in app.actions.state['tasks'] if chosen and t['id']==int(chosen[0])),None)
    def task_change(field=None):
        if not allowed(app):return
        item = selected_task()
        if field is None:
            text = simpledialog.askstring('New task','Task:',parent=window)
            if text:explain_error(window,lambda:task_service.add(text))
        elif item:
            if field=='done':value = not item['done']
            elif field=='archived':value = not item.get('archived',False)
            else:
                label = {'text':'Task text:','due':'Due date YYYY-MM-DD (blank clears it):','priority':'Priority: low, normal or high'}[field]
                value = simpledialog.askstring('Edit task',label,initialvalue=item.get(field,'normal' if field=='priority' else ''),parent=window)
                if value is None:return
            explain_error(window,lambda:task_service.edit(item['id'],{field:value}))
        refresh_tasks()
    buttons(app,panels[0],[('Add task',task_change),('Edit',lambda:task_change('text')),('Done / reopen',lambda:task_change('done')),
                          ('Due date',lambda:task_change('due')),('Priority',lambda:task_change('priority')),('Archive / restore',lambda:task_change('archived')),
                          ('Refresh',refresh_tasks)])
    tk.Checkbutton(panels[0],text='Include archived tasks',variable=archived,command=refresh_tasks,bg=BG,fg=TEXT,selectcolor=PANEL,activebackground=BG).pack(anchor='w',padx=16,pady=6)
    refresh_tasks()
    note_tree = tree(panels[1],(('id','ID',40),('title','Note',480),('status','Status',90)))
    note_archived = tk.BooleanVar(master=window,value=False)
    query = tk.StringVar(master=window)
    search_bar = tk.Frame(panels[1],bg=BG)
    search_bar.pack(fill='x',padx=12,pady=5)
    tk.Entry(search_bar,textvariable=query,bg=PANEL,fg=TEXT,insertbackground=ACCENT).pack(side='left',fill='x',expand=True)
    def refresh_notes():
        selected = note_tree.selection()
        note_tree.delete(*note_tree.get_children())
        for n in app.notes.state['notes']:
            if n['archived'] and not note_archived.get() or query.get().casefold() not in n['text'].casefold():continue
            note_tree.insert('','end',iid=str(n['id']),values=(n['id'],n['text'].split('\n')[0][:160],'Archived' if n['archived'] else 'Active'))
        if selected and note_tree.exists(selected[0]):note_tree.selection_set(selected[0])
    def selected_note():
        chosen = note_tree.selection()
        return next((n for n in app.notes.state['notes'] if chosen and n['id']==int(chosen[0])),None)
    def edit_note(new=False):
        if not allowed(app):return
        item = None if new else selected_note()
        if not new and item is None:return
        editor = tk.Toplevel(window)
        editor.title('ASUNA — Note')
        editor.geometry('650x470')
        editor.configure(bg=BG)
        body = scrolledtext.ScrolledText(editor,wrap='word',bg=PANEL,fg=TEXT,insertbackground=ACCENT,font=('Segoe UI',11))
        body.pack(fill='both',expand=True,padx=14,pady=14)
        if item:body.insert('1.0',item['text'])
        if item and item['archived']:
            body.configure(state='disabled')
            tk.Label(editor,text='Archived note. Restore it in Organizer to edit.',bg=BG,fg=MUTED).pack(pady=(0,14))
            return
        def save():
            if not allowed(app):return
            def commit():
                app.notes.save(body.get('1.0','end-1c'),item['id'] if item else 0)
                refresh_notes()
                editor.destroy()
            explain_error(editor,commit)
        app.button(editor,'Save note',save).pack(pady=(0,14))
    def archive_note():
        item = selected_note()
        if item and allowed(app):
            explain_error(window,lambda:app.notes.archive(item['id'],restore=item['archived']))
            refresh_notes()
    app.button(search_bar,'Search',refresh_notes).pack(side='right',padx=(8,0))
    buttons(app,panels[1],[('Add note',lambda:edit_note(True)),('Read / edit',edit_note),('Archive / restore',archive_note),('Refresh',refresh_notes)])
    tk.Checkbutton(panels[1],text='Include archived notes',variable=note_archived,command=refresh_notes,bg=BG,fg=TEXT,selectcolor=PANEL,activebackground=BG).pack(anchor='w',padx=16,pady=6)
    refresh_notes()
    routine_tree = tree(panels[2],(('id','ID',40),('text','Routine',330),('schedule','Schedule',170),('active','Active',70)))
    def refresh_routines():
        from personal import schedule_label
        routine_tree.delete(*routine_tree.get_children())
        for r in app.personal.state['routines']:
            routine_tree.insert('','end',iid=str(r['id']),values=(r['id'],r['text'],schedule_label(r['repeat']),'Yes' if r['active'] else 'No'))
    def toggle_routine():
        if not allowed(app):return
        chosen = routine_tree.selection()
        item = next((r for r in app.personal.state['routines'] if chosen and r['id']==int(chosen[0])),None)
        if item:
            explain_error(window,lambda:app.personal.pause_routine(item['id'],resume=not item['active']))
            refresh_routines()
    buttons(app,panels[2],[('Pause / resume',toggle_routine),('Refresh',refresh_routines),('Show reminder commands',lambda:app.submit('help'))])
    tk.Label(panels[2],text='Create routines in chat, for example: daily reminder at 20:00: stretch. ASUNA must stay open for reminders and timers.',bg=BG,fg=MUTED,wraplength=700,justify='left').pack(fill='x',padx=16,pady=10)
    refresh_routines()


def show_history(app):
    window,created = window_for(app,'history_window','Chat history','860x650')
    if not created:return
    title(window,'Archived conversations')
    query = tk.StringVar(master=window)
    top = tk.Frame(window,bg=BG)
    top.pack(fill='x',padx=16,pady=8)
    tk.Entry(top,textvariable=query,bg=PANEL,fg=TEXT,insertbackground=ACCENT).pack(side='left',fill='x',expand=True)
    view = tree(window,(('date','Saved',190),('title','Conversation',570)))
    body = scrolledtext.ScrolledText(window,height=12,wrap='word',bg=PANEL,fg=TEXT,font=('Segoe UI',10),state='disabled')
    body.pack(fill='both',expand=True,padx=14,pady=8)
    records = []
    def refresh():
        from chat_history import archived_chats
        records[:] = archived_chats(app.actions.data,query.get())
        view.delete(*view.get_children())
        for index,(path,label,_) in enumerate(records):
            view.insert('','end',iid=str(index),values=(path.stem[:15],label))
    def select(event=None):
        chosen = view.selection()
        if not chosen:return
        messages = records[int(chosen[0])][2]
        body.configure(state='normal')
        body.delete('1.0','end')
        body.insert('end','\n\n'.join(m['role'].upper()+'\n'+m['content'] for m in messages))
        body.configure(state='disabled')
    app.button(top,'Search history',refresh).pack(side='right',padx=(8,0))
    view.bind('<<TreeviewSelect>>',select)
    tk.Label(window,text='New chat archives the previous conversation. Viewing history does not send it back to a model.',bg=BG,fg=MUTED).pack(pady=(0,10))
    refresh()
