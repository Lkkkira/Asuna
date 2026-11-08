"""Native Reactor interface and lightweight event-driven canvas animation."""
import math
import time
import tkinter as tk
from tkinter import ttk, scrolledtext

BG = '#080e17'
PANEL = '#101b28'
LINE = '#25384a'
TEXT = '#edf5ff'
MUTED = '#9fadc1'
ACCENT = '#68e7ec'

PRESENCE = {
    'idle': ('Right here with you.', 'Ready for whatever comes next.', 'READY'),
    'listening': ('I’m listening.', 'Speak, then stop recording to review your words.', 'LISTENING'),
    'thinking': ('Let me work that out.', 'Understanding your request.', 'THINKING'),
    'speaking': ('Here’s what I found.', 'Speaking the response.', 'SPEAKING'),
    'working': ('On it.', 'You can follow every step in Activity.', 'WORKING'),
    'waiting': ('Your turn.', 'Review the request or answer my question.', 'WAITING FOR YOU'),
    'error': ('Something needs attention.', 'The details are in the conversation and Activity.', 'NEEDS ATTENTION'),
}


class ReactorCore(tk.Canvas):
    def __init__(self, parent, motion):
        super().__init__(parent, bg=BG, highlightthickness=0, width=470, height=360)
        self.motion = motion
        self.scheduler = self.winfo_toplevel()
        self.mode = 'idle'
        self.level = 0.0
        self.phase = 0.0
        self.items_ready = False
        self.closed = False
        self.after_id = None
        self.last_tick = time.monotonic()
        self.bind('<Configure>', self.resize)
        self.bind('<Destroy>', self.dispose, add='+')
        self.after_id = self.scheduler.after(40, self.animate)

    def resize(self, event=None):
        width, height = self.winfo_width(), self.winfo_height()
        if width < 10 or height < 10:
            return
        self.delete('all')
        self.cx, self.cy = width / 2, (height - 35) / 2
        self.radius = max(35, min(width * .40, (height - 55) * .43))
        r, x, y = self.radius, self.cx, self.cy
        # Static grid and calibration ticks are redrawn only on resize.
        for offset in range(-3, 4):
            d = offset * r / 3
            self.create_line(x-r, y+d, x+r, y+d, fill='#101f2d')
            self.create_line(x+d, y-r, x+d, y+r, fill='#101f2d')
        self.ticks = []
        for angle in range(0, 360, 6):
            a = math.radians(angle)
            inner = r * (.96 if angle % 30 else .93)
            self.ticks.append(self.create_line(x+inner*math.cos(a), y+inner*math.sin(a),
                x+r*math.cos(a), y+r*math.sin(a), fill='#285b68', width=1))
        self.outer = []
        for start, extent in [(5, 67), (92, 12), (170, 74), (290, 13)]:
            self.outer.append((self.create_arc(*self.bounds(.88), start=start, extent=extent,
                style='arc', outline=ACCENT, width=4), start))
        self.create_oval(*self.bounds(.70), outline='#244654', width=1)
        self.middle = [(self.create_arc(*self.bounds(.67), start=start, extent=90,
            style='arc', outline='#81dfe5', width=2), start) for start in (0, 180)]
        self.inner = [(self.create_arc(*self.bounds(.50), start=start, extent=9,
            style='arc', outline='#397981', width=2), start) for start in range(0, 360, 24)]
        self.glow = []
        for scale, color in [(.43, '#102b37'), (.40, '#12313d'), (.37, '#153746')]:
            self.glow.append(self.create_oval(*self.bounds(scale), fill=color, outline=''))
        self.disc = self.create_oval(*self.bounds(.34), fill='#102631', outline='#55b9c3', width=1)
        self.letter = self.create_text(x, y, text='A', fill='#c8f9ff', font=('Segoe UI', max(22, int(r*.35))))
        for sign in (-1, 1):
            bx, by = x+sign*r*1.12, y+sign*r*1.03
            self.create_line(bx, by-sign*13, bx, by, bx-sign*13, by, fill='#668895')
        self.create_text(x, max(10, y-r-17), text='ASUNA / LOCAL', fill=MUTED, font=('Segoe UI', 8))
        self.caption = self.create_text(x, y+r+19, text='LOCAL INTELLIGENCE', fill=MUTED, font=('Segoe UI', 8))
        self.bars = []
        for index in range(31):
            bx = x+(index-15)*6
            self.bars.append(self.create_line(bx, height-13, bx, height-17, fill=ACCENT, width=3, capstyle='round'))
        self.items_ready = True
        self.paint()

    def bounds(self, scale):
        r = self.radius * scale
        return self.cx-r, self.cy-r, self.cx+r, self.cy+r

    def set_mode(self, mode):
        self.mode = mode if mode in PRESENCE else 'idle'
        self.paint()

    def set_level(self, level):
        self.level = max(0.0, min(1.0, float(level)))

    def paint(self):
        if not self.items_ready or self.closed:
            return
        active = self.mode in ('listening', 'thinking', 'speaking', 'working')
        color = '#ef9b90' if self.mode == 'error' else '#e9c18b' if self.mode == 'waiting' else ACCENT
        for item, start in self.outer:
            self.itemconfigure(item, start=(start+self.phase) % 360, outline=color)
        for item, start in self.middle:
            self.itemconfigure(item, start=(start-self.phase*1.6) % 360)
        for item, start in self.inner:
            self.itemconfigure(item, start=(start+self.phase*.45) % 360)
        pulse = math.sin(self.phase*.12) if self.motion.get() else 0
        strength = self.level if self.mode == 'listening' else .5+.3*pulse if self.mode == 'speaking' else .2
        self.coords(self.disc, *self.bounds(.34+strength*.025))
        self.itemconfigure(self.disc, outline=color)
        self.itemconfigure(self.caption, text=PRESENCE[self.mode][2])
        height = self.winfo_height()
        for index, bar in enumerate(self.bars):
            envelope = math.sin((index+1)/32*math.pi)
            if self.mode == 'listening':
                amplitude = 2 + strength*24*envelope*(.45+.55*abs(math.sin(index*.93+self.phase*.04)))
            elif self.mode == 'speaking':
                amplitude = 3 + (11+7*pulse)*envelope*abs(math.sin(index*1.23+self.phase*.06))
            elif active:
                amplitude = 2 + 3*envelope*abs(math.sin(index*.8+self.phase*.05))
            else:
                amplitude = 2
            bx = self.cx+(index-15)*6
            self.coords(bar, bx, height-15-amplitude/2, bx, height-15+amplitude/2)
            self.itemconfigure(bar, fill=color)

    def animate(self):
        if self.closed:
            return
        now = time.monotonic()
        elapsed = min(.2, now-self.last_tick)
        self.last_tick = now
        visible = self.winfo_ismapped() and self.winfo_toplevel().state() != 'iconic'
        if visible:
            if self.motion.get():
                speed = {'idle': 7, 'listening': 17, 'thinking': 48, 'speaking': 20, 'working': 26}.get(self.mode, 4)
                self.phase = (self.phase + elapsed*speed) % 360
            self.paint()
        self.after_id = self.scheduler.after(40 if visible and self.motion.get() else 200, self.animate)

    def dispose(self, event=None):
        if event is not None and event.widget is not self:
            return
        self.closed = True
        if self.after_id:
            try:
                self.scheduler.after_cancel(self.after_id)
            except (tk.TclError, ValueError):
                pass
        self.after_id = None


def build_reactor(app):
    root = app.root
    from version import __version__
    root.title('ASUNA — Reactor · Repo edition · '+__version__)
    root.geometry('1100x800')
    root.minsize(720, 680)
    root.configure(bg=BG)
    root.protocol('WM_DELETE_WINDOW', app.close)
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TCombobox', padding=6, fieldbackground=PANEL, background=PANEL,
                    foreground=TEXT, arrowcolor=ACCENT, bordercolor=LINE)
    style.map('TCombobox', fieldbackground=[('readonly', PANEL)], foreground=[('readonly', TEXT)])
    style.configure('Work.Treeview', background=PANEL, fieldbackground=PANEL,
                    foreground=TEXT, rowheight=22, borderwidth=0)
    style.configure('Work.Treeview.Heading', background='#142333', foreground=MUTED, relief='flat')
    style.map('Work.Treeview', background=[('selected', '#214554')])
    top = tk.Frame(root, bg=BG)
    top.pack(fill='x', padx=22, pady=(18, 10))
    tk.Label(top, text='A', bg=BG, fg=ACCENT, font=('Segoe UI', 20)).pack(side='left', padx=(0, 14))
    brand = tk.Frame(top, bg=BG)
    brand.pack(side='left')
    tk.Label(brand, text='A S U N A', bg=BG, fg=TEXT, font=('Segoe UI', 20, 'bold')).pack(anchor='w')
    tk.Label(brand, text='H A L O  /  R E A C T O R', bg=BG, fg=MUTED, font=('Segoe UI', 8)).pack(anchor='w')
    app.mode = tk.StringVar(value=app.preferences.values['default_mode'])
    app.selector = ttk.Combobox(top, textvariable=app.mode, values=['Fast', 'Deep'], state='readonly', width=8)
    app.selector.pack(side='right', padx=(12, 0))
    app.selector.bind('<<ComboboxSelected>>', lambda e: app.log('Mode selected: '+app.mode.get()+'. Applies to your next message.'))
    app.button(top,'Settings',app.show_settings).pack(side='right',padx=(8,0))
    app.button(top,'Organizer',app.show_organizer).pack(side='right',padx=(8,0))
    tk.Checkbutton(top, text='Motion', variable=app.motion_enabled, command=app.save_ui_settings,
                   bg=BG, fg=MUTED, selectcolor=PANEL, activebackground=BG, activeforeground=TEXT).pack(side='right')
    tk.Frame(root, bg=LINE, height=1).pack(fill='x', padx=22)
    tools = tk.Frame(root, bg=BG)
    tools.pack(fill='x', padx=22, pady=8)
    app.toolbar_buttons = []
    for name, command in [('Activity', app.toggle_activity), ('New chat', app.clear),
                          ('My day', lambda: app.submit('daily overview')), ('Memory', lambda: app.submit('show memories')),
                          ('Document', app.attach_document), ('Commands', lambda: app.submit('help'))]:
        app.toolbar_buttons.append(app.button(tools, name, command))
    tools.bind('<Configure>', app.layout_toolbar)
    voice = tk.Frame(root, bg=BG)
    voice.pack(fill='x', padx=22, pady=(0, 4))
    app.record_button = app.button(voice, 'Record', app.toggle_recording)
    app.record_button.pack(side='left', padx=(0, 6))
    app.button(voice, 'Stop speaking', app.stop_speaking).pack(side='left', padx=(0, 6))
    tk.Checkbutton(voice, text='Speak replies', variable=app.speak_replies, command=app.toggle_speech,
                   bg=BG, fg=TEXT, selectcolor=PANEL, activebackground=BG, activeforeground=TEXT).pack(side='left', padx=4)
    app.button(voice, 'Voice settings', app.show_voice_settings).pack(side='left', padx=6)
    profile = {'en': 'English', 'hi': 'Hindi', 'mixed': 'English + Hindi', 'auto': 'Auto (all languages)'}[app.voice_language]
    app.voice_status = tk.StringVar(value=f'{profile} · Whisper {app.voice.model_name} · Record, review, then Send' if app.voice.ready() else 'Run Setup Voice.bat to enable microphone input')
    tk.Label(root, textvariable=app.voice_status, bg=BG, fg=MUTED, anchor='w', font=('Segoe UI', 9)).pack(fill='x', padx=24)
    bottom = tk.Frame(root, bg=BG)
    bottom.pack(side='bottom', fill='x', padx=22, pady=(10, 16))
    app.entry = tk.Entry(bottom, bg=PANEL, fg=TEXT, insertbackground=ACCENT, relief='flat',
                         highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT, font=('Segoe UI', 12))
    app.entry.pack(side='left', fill='x', expand=True, ipady=13, padx=(0, 10))
    app.entry.bind('<Return>', lambda e: app.send())
    app.send_button = app.button(bottom, 'Send  →', app.send)
    app.send_button.pack(side='right', ipady=6)
    app.stop_button = app.button(bottom,'Stop',app.cancel_request)
    app.stop_button.configure(state='disabled')
    app.stop_button.pack(side='right',ipady=6,padx=(0,8))
    main = tk.Frame(root, bg=BG)
    main.pack(fill='both', expand=True, padx=22, pady=(14, 0))
    main.columnconfigure(0, weight=3, minsize=230)
    main.columnconfigure(1, weight=2, minsize=300)
    main.rowconfigure(0, weight=1)
    hero = tk.Frame(main, bg=BG)
    hero.grid(row=0, column=0, sticky='nsew', padx=(0, 24))
    tk.Label(hero, text='P E R S O N A L  A S S I S T A N T  /  L O C A L', bg=BG, fg=MUTED, font=('Segoe UI', 8)).pack(pady=(8, 4))
    app.presence_title = tk.StringVar(value=PRESENCE['idle'][0])
    app.presence_caption = tk.StringVar(value=PRESENCE['idle'][1])
    caption = tk.Label(hero, textvariable=app.presence_caption, bg=BG, fg=MUTED, font=('Segoe UI', 10), wraplength=400)
    caption.pack(side='bottom', pady=(0, 15))
    heading = tk.Label(hero, textvariable=app.presence_title, bg=BG, fg=TEXT, font=('Segoe UI', 21), wraplength=450)
    heading.pack(side='bottom', pady=(0, 7))
    app.reactor = ReactorCore(hero, app.motion_enabled)
    app.reactor.pack(fill='both', expand=True)
    hero.bind('<Configure>', lambda e: (heading.configure(wraplength=max(180, e.width-8)), caption.configure(wraplength=max(180, e.width-8))))
    aside = app.activity_host = tk.Frame(main, bg=BG, highlightbackground=LINE, highlightthickness=1)
    aside.grid(row=0, column=1, sticky='nsew')
    tk.Label(aside, text='L I V E  A C T I V I T Y', bg=BG, fg=MUTED, font=('Segoe UI', 9), anchor='w').pack(fill='x', padx=12, pady=(12, 5))
    app.presence_badge = tk.StringVar(value='READY')
    tk.Label(aside, textvariable=app.presence_badge, bg=BG, fg=ACCENT, font=('Segoe UI', 9), anchor='w').pack(fill='x', padx=12)
    app.reactor_task = tk.StringVar(value='Waiting for your request')
    focus_fields = tk.Frame(aside, bg=BG)
    focus_fields.pack(fill='x')
    task = tk.Label(focus_fields, textvariable=app.reactor_task, bg=BG, fg=TEXT, font=('Segoe UI', 11, 'bold'), anchor='w', justify='left', wraplength=320)
    task.pack(fill='x', padx=12, pady=(5, 2))
    app.status = tk.StringVar(value='Ready · Local models')
    detail = tk.Label(focus_fields, textvariable=app.status, bg=BG, fg=MUTED, font=('Segoe UI', 9), anchor='w', justify='left', wraplength=320)
    detail.pack(fill='x', padx=12, pady=(0, 8))
    divider = tk.Frame(aside, bg=LINE, height=1)
    divider.pack(fill='x', padx=12)
    tk.Label(aside, text='CONVERSATION', bg=BG, fg=MUTED, font=('Segoe UI', 8), anchor='w').pack(fill='x', padx=12, pady=(8, 4))
    app.activity_panel = tk.Frame(aside, bg=BG)
    tree_frame = tk.Frame(app.activity_panel, bg=BG)
    tree_frame.pack(fill='x')
    app.work_tree = ttk.Treeview(tree_frame, columns=('status',), height=3, style='Work.Treeview')
    app.work_tree.heading('#0', text='Work / action')
    app.work_tree.heading('status', text='Status')
    app.work_tree.column('#0', width=170, minwidth=90)
    app.work_tree.column('status', width=105, minwidth=90, stretch=False)
    app.work_tree.pack(side='left', fill='both', expand=True)
    scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=app.work_tree.yview)
    scrollbar.pack(side='right', fill='y')
    app.work_tree.configure(yscrollcommand=scrollbar.set)
    app.work_tree.bind('<<TreeviewSelect>>', app.select_work)
    app.work_detail = scrolledtext.ScrolledText(app.activity_panel, width=1, height=2, wrap='word', bg=PANEL, fg=TEXT, relief='flat', font=('Segoe UI', 9), state='disabled')
    app.work_detail.pack(fill='x', pady=4)
    app.activity = scrolledtext.ScrolledText(app.activity_panel, width=1, height=2, bg=BG, fg=MUTED, relief='flat', font=('Consolas', 8), state='disabled')
    app.activity.pack(fill='x')
    app.chat = scrolledtext.ScrolledText(aside, width=1, height=6, wrap='word', bg=PANEL, fg=TEXT,
            insertbackground=ACCENT, relief='flat', padx=12, pady=12, font=('Segoe UI', 10), state='disabled')
    app.chat.pack(fill='both', expand=True, padx=10, pady=(0, 10))
    app.chat.tag_config('speaker', foreground=ACCENT, font=('Segoe UI', 9, 'bold'))

    def layout_activity(event=None):
        compact = aside.winfo_height() < 450
        task.configure(wraplength=max(180, aside.winfo_width()-26))
        detail.configure(wraplength=max(180, aside.winfo_width()-26))
        app.work_tree.configure(height=2 if compact else 3)
        app.work_detail.configure(height=1 if compact else 2)
        app.activity.configure(height=1 if compact else 2)
        # The work tree already shows the request; reserve room for conversation.
        if compact and app.activity_visible:
            focus_fields.pack_forget()
        elif not focus_fields.winfo_manager():
            focus_fields.pack(fill='x', before=divider)

    app.layout_activity = layout_activity
    aside.bind('<Configure>', layout_activity)
