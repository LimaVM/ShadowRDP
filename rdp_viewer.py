import sys
import os
import ctypes
import subprocess
import re
import psutil
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime
import threading
import json
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# Configuração de cores e temas
COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72', 
    'success': '#28A745',
    'warning': '#FFC107',
    'danger': '#DC3545',
    'info': '#17A2B8',
    'light': '#F8F9FA',
    'dark': '#343A40',
    'white': '#FFFFFF',
    'gray': '#6C757D'
}

# — UAC Elevation + SeDebugPrivilege —
def is_admin():
    """Verifica se o programa está sendo executado como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate():
    """Eleva os privilégios do programa para administrador"""
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, __file__, None, 1
        )
        sys.exit()
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível elevar privilégios: {e}")
        sys.exit()

# Verificação de privilégios administrativos
if not is_admin():
    elevate()

# Configuração de privilégios de debug
try:
    import win32api, win32con, win32security
    hToken = win32security.OpenProcessToken(
        win32api.GetCurrentProcess(),
        win32con.TOKEN_ADJUST_PRIVILEGES | win32con.TOKEN_QUERY
    )
    luid = win32security.LookupPrivilegeValue(None, win32con.SE_DEBUG_NAME)
    win32security.AdjustTokenPrivileges(
        hToken, False, [(luid, win32con.SE_PRIVILEGE_ENABLED)]
    )
except ImportError:
    messagebox.showwarning("Aviso", "pywin32 não encontrado. Algumas funcionalidades podem não funcionar corretamente.\nInstale com: pip install pywin32")

class RDPSessionViewer:
    """Gerenciador Avançado de Sessões RDP - Versão Final"""
    
    WIDTH, HEIGHT = 1400, 900
    REFRESH_INTERVAL = 2000  # ms
    CONFIG_FILE = "rdp_viewer_config.json"
    LOG_FILE = "rdp_viewer.log"
    
    def __init__(self, master):
        self.root = master
        self.root.title("🖥️ Gerenciador Avançado de Sessões RDP - v3.0 Professional")
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.root.resizable(True, True)
        self.root.minsize(1200, 700)
        
        # Configurações
        self.config = self.load_config()
        
        # Dados
        self.sessions = []
        self.usage = {}
        self.history = []
        self.footer_dx = 3
        self.is_refreshing = False
        self.sort_column = None
        self.sort_reverse = False
        
        # Variáveis de controle
        self.auto_refresh_enabled = tk.BooleanVar(value=True)
        self.show_system_processes = tk.BooleanVar(value=False)
        self.dark_mode = tk.BooleanVar(value=self.config.get('dark_mode', False))
        self.show_notifications = tk.BooleanVar(value=True)
        self.sound_alerts = tk.BooleanVar(value=False)
        
        # Inicialização do psutil
        self.init_psutil()
        
        # Construção da interface
        self.setup_styles()
        self.build_ui()
        self.center_window()
        
        # Inicialização
        self.update_all()
        self.schedule_auto_refresh()
        self.animate_footer()
        
        # Bind para eventos
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<F5>", lambda e: self.update_all())
        self.root.bind("<Control-r>", lambda e: self.update_all())
        self.root.bind("<Control-q>", lambda e: self.on_closing())
    
    def load_config(self):
        """Carrega configurações do arquivo"""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log_error(f"Erro ao carregar configurações: {e}")
        return {}
    
    def save_config(self):
        """Salva configurações no arquivo"""
        try:
            config = {
                'dark_mode': self.dark_mode.get(),
                'auto_refresh': self.auto_refresh_enabled.get(),
                'show_system': self.show_system_processes.get(),
                'notifications': self.show_notifications.get(),
                'sound_alerts': self.sound_alerts.get(),
                'window_geometry': self.root.geometry(),
                'refresh_interval': self.REFRESH_INTERVAL
            }
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_error(f"Erro ao salvar configurações: {e}")
    
    def log_error(self, message):
        """Registra erros em arquivo de log"""
        try:
            with open(self.LOG_FILE, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {message}\n")
        except:
            pass
    
    def init_psutil(self):
        """Inicializa o psutil para medições de CPU"""
        def init_cpu():
            for p in psutil.process_iter():
                try:
                    p.cpu_percent(None)
                except:
                    pass
        
        thread = threading.Thread(target=init_cpu, daemon=True)
        thread.start()
    
    def setup_styles(self):
        """Configura estilos avançados da interface"""
        self.style = ttk.Style(self.root)
        
        # Tema base
        available_themes = self.style.theme_names()
        if 'vista' in available_themes:
            self.style.theme_use('vista')
        elif 'clam' in available_themes:
            self.style.theme_use('clam')
        
        # Estilos personalizados
        self.style.configure('Title.TLabel', 
                           font=('Segoe UI', 20, 'bold'),
                           foreground=COLORS['primary'])
        
        self.style.configure('Subtitle.TLabel', 
                           font=('Segoe UI', 12, 'bold'),
                           foreground=COLORS['dark'])
        
        self.style.configure('Info.TLabel', 
                           font=('Segoe UI', 9),
                           foreground=COLORS['gray'])
        
        self.style.configure('Custom.Treeview', 
                           rowheight=30, 
                           font=('Segoe UI', 10))
        
        self.style.configure('Custom.Treeview.Heading', 
                           font=('Segoe UI', 11, 'bold'),
                           background=COLORS['primary'],
                           foreground=COLORS['white'])
        
        # Botões com cores específicas
        self.style.configure('Primary.TButton', 
                           font=('Segoe UI', 9, 'bold'),
                           background=COLORS['primary'])
        
        self.style.configure('Success.TButton', 
                           font=('Segoe UI', 9, 'bold'),
                           background=COLORS['success'])
        
        self.style.configure('Danger.TButton', 
                           font=('Segoe UI', 9, 'bold'),
                           background=COLORS['danger'])
        
        self.style.configure('Warning.TButton', 
                           font=('Segoe UI', 9, 'bold'),
                           background=COLORS['warning'])
        
        self.apply_theme()
    
    def apply_theme(self):
        """Aplica tema claro ou escuro"""
        if self.dark_mode.get():
            # Tema escuro
            bg_color = '#2C3E50'
            fg_color = '#ECF0F1'
            self.root.configure(bg=bg_color)
            
            self.style.configure('TLabel', background=bg_color, foreground=fg_color)
            self.style.configure('TFrame', background=bg_color)
            self.style.configure('TLabelFrame', background=bg_color, foreground=fg_color)
            self.style.configure('Custom.Treeview', 
                               background='#34495E', 
                               foreground=fg_color,
                               fieldbackground='#34495E')
        else:
            # Tema claro
            bg_color = COLORS['light']
            fg_color = COLORS['dark']
            self.root.configure(bg=bg_color)
            
            self.style.configure('TLabel', background=bg_color, foreground=fg_color)
            self.style.configure('TFrame', background=bg_color)
            self.style.configure('TLabelFrame', background=bg_color, foreground=fg_color)
            self.style.configure('Custom.Treeview', 
                               background=COLORS['white'], 
                               foreground=fg_color,
                               fieldbackground=COLORS['white'])
    
    def build_ui(self):
        """Constrói a interface do usuário"""
        # Frame principal com padding
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Cabeçalho
        self.build_header(main_frame)
        
        # Barra de ferramentas
        self.build_toolbar(main_frame)
        
        # Área principal dividida
        self.build_main_area(main_frame)
        
        # Barra de status
        self.build_status_bar(main_frame)
        
        # Rodapé
        self.build_footer()
    
    def build_header(self, parent):
        """Constrói o cabeçalho aprimorado"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Frame esquerdo - Título e subtítulo
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title_label = ttk.Label(title_frame, 
                               text="🖥️ Gerenciador Avançado de Sessões RDP", 
                               style='Title.TLabel')
        title_label.pack(anchor='w')
        
        subtitle_label = ttk.Label(title_frame, 
                                  text="Controle total sobre sessões remotas do servidor", 
                                  style='Subtitle.TLabel')
        subtitle_label.pack(anchor='w')
        
        # Frame direito - Informações do sistema
        info_frame = ttk.Frame(header_frame)
        info_frame.pack(side=tk.RIGHT)
        
        self.system_info_label = ttk.Label(info_frame, text="", style='Info.TLabel')
        self.system_info_label.pack(anchor='e')
        
        self.server_info_label = ttk.Label(info_frame, text="", style='Info.TLabel')
        self.server_info_label.pack(anchor='e')
        
        self.update_system_info()
    
    def build_toolbar(self, parent):
        """Constrói a barra de ferramentas avançada"""
        toolbar_frame = ttk.LabelFrame(parent, text="🔧 Ferramentas", padding=10)
        toolbar_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Primeira linha - Pesquisa e filtros
        search_frame = ttk.Frame(toolbar_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Pesquisa
        ttk.Label(search_frame, text="🔍 Pesquisar:", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=('Segoe UI', 10), width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 20))
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())
        
        # Botão limpar pesquisa
        ttk.Button(search_frame, text="✖ Limpar", 
                  command=lambda: self.search_var.set("")).pack(side=tk.LEFT, padx=(0, 20))
        
        # Intervalo de atualização
        ttk.Label(search_frame, text="⏱️ Intervalo (s):", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        
        self.interval_var = tk.StringVar(value=str(self.REFRESH_INTERVAL // 1000))
        interval_spinbox = ttk.Spinbox(search_frame, from_=1, to=60, width=5, 
                                      textvariable=self.interval_var,
                                      command=self.update_refresh_interval)
        interval_spinbox.pack(side=tk.LEFT)
        
        # Segunda linha - Configurações
        config_frame = ttk.Frame(toolbar_frame)
        config_frame.pack(fill=tk.X)
        
        # Checkboxes organizados
        ttk.Checkbutton(config_frame, text="🔄 Auto-atualizar", 
                       variable=self.auto_refresh_enabled).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Checkbutton(config_frame, text="⚙️ Processos do sistema", 
                       variable=self.show_system_processes,
                       command=self.update_all).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Checkbutton(config_frame, text="🌙 Modo escuro", 
                       variable=self.dark_mode,
                       command=self.toggle_theme).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Checkbutton(config_frame, text="🔔 Notificações", 
                       variable=self.show_notifications).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Checkbutton(config_frame, text="🔊 Alertas sonoros", 
                       variable=self.sound_alerts).pack(side=tk.LEFT)
    
    def build_main_area(self, parent):
        """Constrói a área principal dividida"""
        # PanedWindow para divisão
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Frame esquerdo - Sessões
        sessions_frame = ttk.LabelFrame(paned, text="📋 Sessões Ativas", padding=10)
        paned.add(sessions_frame, weight=3)
        
        self.build_sessions_table(sessions_frame)
        self.build_action_buttons(sessions_frame)
        
        # Frame direito - Informações e estatísticas
        info_frame = ttk.LabelFrame(paned, text="📊 Informações e Estatísticas", padding=10)
        paned.add(info_frame, weight=1)
        
        self.build_info_panel(info_frame)
    
    def build_sessions_table(self, parent):
        """Constrói a tabela de sessões"""
        # Frame para tabela com scrollbars
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Colunas da tabela
        columns = ("Usuário", "ID", "Estado", "Idle", "Logon", "CPU %", "RAM (MB)", "Processos")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", 
                                style='Custom.Treeview', selectmode="extended")
        
        # Configuração das colunas
        column_config = {
            "Usuário": {"width": 120, "anchor": "w"},
            "ID": {"width": 50, "anchor": "center"},
            "Estado": {"width": 80, "anchor": "center"},
            "Idle": {"width": 80, "anchor": "center"},
            "Logon": {"width": 120, "anchor": "w"},
            "CPU %": {"width": 70, "anchor": "e"},
            "RAM (MB)": {"width": 80, "anchor": "e"},
            "Processos": {"width": 80, "anchor": "e"}
        }
        
        for col in columns:
            config = column_config.get(col, {"width": 100, "anchor": "w"})
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=config["width"], anchor=config["anchor"])
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Bind para duplo clique
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
    
    def build_action_buttons(self, parent):
        """Constrói os botões de ação organizados"""
        buttons_frame = ttk.LabelFrame(parent, text="🎮 Ações", padding=10)
        buttons_frame.pack(fill=tk.X)
        
        # Primeira linha - Ações principais
        row1_frame = ttk.Frame(buttons_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 8))
        
        buttons_row1 = [
            ("🔄 Atualizar", self.update_all, 'Primary.TButton'),
            ("❌ Desconectar", self.batch_logoff, 'Danger.TButton'),
            ("🚪 Logoff", self.logoff_user, 'Warning.TButton'),
            ("🖥️ Controlar", self.remote_control, 'Success.TButton')
        ]
        
        for text, command, style in buttons_row1:
            btn = ttk.Button(row1_frame, text=text, command=command, style=style)
            btn.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        
        # Segunda linha - Comunicação
        row2_frame = ttk.Frame(buttons_frame)
        row2_frame.pack(fill=tk.X, pady=(0, 8))
        
        buttons_row2 = [
            ("💬 Mensagem", self.send_message, 'Primary.TButton'),
            ("🖼️ Imagem", self.send_image, 'Primary.TButton'),
            ("🎥 Vídeo", self.send_video, 'Primary.TButton'),
            ("🔊 Áudio", self.play_audio, 'Primary.TButton')
        ]
        
        for text, command, style in buttons_row2:
            btn = ttk.Button(row2_frame, text=text, command=command, style=style)
            btn.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        
        # Terceira linha - Utilitários
        row3_frame = ttk.Frame(buttons_frame)
        row3_frame.pack(fill=tk.X)
        
        buttons_row3 = [
            ("📊 Gráficos", self.show_graph, 'Success.TButton'),
            ("📋 Exportar", self.export_data, 'Primary.TButton'),
            ("⚙️ Configurações", self.show_settings, 'Primary.TButton'),
            ("📖 Logs", self.show_logs, 'Primary.TButton')
        ]
        
        for text, command, style in buttons_row3:
            btn = ttk.Button(row3_frame, text=text, command=command, style=style)
            btn.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
    
    def build_info_panel(self, parent):
        """Constrói o painel de informações"""
        # Resumo de sessões
        summary_frame = ttk.LabelFrame(parent, text="📈 Resumo", padding=10)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.summary_labels = {}
        summary_items = [
            ("total_sessions", "Total de Sessões:"),
            ("active_sessions", "Sessões Ativas:"),
            ("total_cpu", "CPU Total:"),
            ("total_memory", "RAM Total:"),
            ("avg_idle", "Idle Médio:")
        ]
        
        for key, label in summary_items:
            frame = ttk.Frame(summary_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=label, font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT)
            self.summary_labels[key] = ttk.Label(frame, text="0", font=('Segoe UI', 9))
            self.summary_labels[key].pack(side=tk.RIGHT)
        
        # Usuários mais ativos
        active_frame = ttk.LabelFrame(parent, text="👥 Usuários Mais Ativos", padding=10)
        active_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.active_users_text = tk.Text(active_frame, height=6, font=('Segoe UI', 9))
        active_scrollbar = ttk.Scrollbar(active_frame, orient=tk.VERTICAL, command=self.active_users_text.yview)
        self.active_users_text.configure(yscrollcommand=active_scrollbar.set)
        
        self.active_users_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        active_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Alertas
        alerts_frame = ttk.LabelFrame(parent, text="⚠️ Alertas", padding=10)
        alerts_frame.pack(fill=tk.BOTH, expand=True)
        
        self.alerts_text = tk.Text(alerts_frame, height=8, font=('Segoe UI', 9))
        alerts_scrollbar = ttk.Scrollbar(alerts_frame, orient=tk.VERTICAL, command=self.alerts_text.yview)
        self.alerts_text.configure(yscrollcommand=alerts_scrollbar.set)
        
        self.alerts_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        alerts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def build_status_bar(self, parent):
        """Constrói a barra de status"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Status principal
        self.status_label = ttk.Label(status_frame, text="✅ Sistema pronto", 
                                     font=('Segoe UI', 10, 'bold'),
                                     foreground=COLORS['success'])
        self.status_label.pack(side=tk.LEFT)
        
        # Separador
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Última atualização
        self.last_update_label = ttk.Label(status_frame, text="", 
                                          font=('Segoe UI', 9),
                                          foreground=COLORS['gray'])
        self.last_update_label.pack(side=tk.LEFT)
        
        # Informações adicionais à direita
        self.connection_status = ttk.Label(status_frame, text="🔗 Conectado", 
                                          font=('Segoe UI', 9),
                                          foreground=COLORS['success'])
        self.connection_status.pack(side=tk.RIGHT)
    
    def build_footer(self):
        """Constrói o rodapé animado"""
        self.lbl_footer = tk.Label(self.root, 
                                  text="🚀 DESENVOLVIDO POR DEVLIMA - Gerenciador RDP Professional v3.0 🚀",
                                  font=("Segoe UI", 12, "bold"), 
                                  fg=COLORS['primary'], 
                                  bg=self.root.cget('bg'))
        self.lbl_footer.place(x=0, y=0)
    
    def center_window(self):
        """Centraliza a janela na tela"""
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = (sw - self.WIDTH) // 2
        y = (sh - self.HEIGHT) // 2
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")
        self.center_footer()
    
    def center_footer(self):
        """Centraliza o rodapé"""
        try:
            self.lbl_footer.update_idletasks()
            fw = self.lbl_footer.winfo_reqwidth()
            fh = self.lbl_footer.winfo_reqheight()
            x = (self.root.winfo_width() - fw) // 2
            y = self.root.winfo_height() - fh - 10
            self.lbl_footer.place(x=x, y=y)
        except:
            pass
    
    def animate_footer(self):
        """Anima o rodapé"""
        try:
            x, y = self.lbl_footer.winfo_x(), self.lbl_footer.winfo_y()
            window_width = self.root.winfo_width()
            footer_width = self.lbl_footer.winfo_reqwidth()
            
            if x + self.footer_dx < 0 or x + self.footer_dx + footer_width > window_width:
                self.footer_dx *= -1
            
            self.lbl_footer.place(x=x + self.footer_dx, y=y)
            self.root.after(150, self.animate_footer)
        except:
            pass
    
    def update_refresh_interval(self):
        """Atualiza intervalo de refresh"""
        try:
            new_interval = int(self.interval_var.get()) * 1000
            if 1000 <= new_interval <= 60000:
                self.REFRESH_INTERVAL = new_interval
                self.save_config()
        except:
            pass
    
    def update_system_info(self):
        """Atualiza informações do sistema"""
        try:
            # Informações básicas do sistema
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            info_text = f"💻 CPU: {cpu_percent:.1f}% | 🧠 RAM: {memory.percent:.1f}% ({memory.used // (1024**3):.1f}GB/{memory.total // (1024**3):.1f}GB)"
            self.system_info_label.config(text=info_text)
            
            # Informações do servidor
            import platform
            server_text = f"🖥️ {platform.node()} | {platform.system()} {platform.release()}"
            self.server_info_label.config(text=server_text)
            
        except Exception as e:
            self.system_info_label.config(text="❌ Erro ao obter informações do sistema")
            self.log_error(f"Erro ao atualizar info do sistema: {e}")
    
    def toggle_theme(self):
        """Alterna entre tema claro e escuro"""
        self.apply_theme()
        self.save_config()
        
        # Atualiza cores do footer
        self.lbl_footer.config(bg=self.root.cget('bg'))
    
    def sort_by_column(self, column):
        """Ordena a tabela por coluna"""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        items = []
        for item in self.tree.get_children(''):
            values = self.tree.item(item)["values"]
            if values:
                sort_value = values[list(self.tree["columns"]).index(column)]
                # Tenta converter para número se possível
                try:
                    if column in ["ID", "CPU %", "RAM (MB)", "Processos"]:
                        sort_value = float(sort_value.replace('%', '').replace(',', '.'))
                except:
                    pass
                items.append((sort_value, item))
        
        items.sort(reverse=self.sort_reverse)
        
        for index, (val, item) in enumerate(items):
            self.tree.move(item, '', index)
        
        # Atualiza indicador de ordenação no cabeçalho
        for col in self.tree["columns"]:
            heading_text = col
            if col == column:
                heading_text += " ↓" if self.sort_reverse else " ↑"
            self.tree.heading(col, text=heading_text)
    
    def update_all(self):
        """Atualiza todos os dados"""
        if self.is_refreshing:
            return
        
        self.is_refreshing = True
        self.status_label.config(text="🔄 Atualizando...", foreground=COLORS['warning'])
        
        try:
            self.update_sessions()
            self.update_usage()
            self.refresh_list()
            self.update_system_info()
            self.update_summary()
            self.update_active_users()
            self.check_alerts()
            
            # Adiciona ao histórico
            now = datetime.now()
            active_sessions = len([s for s in self.sessions if s.get("ID", "").isdigit()])
            total_cpu = sum(v.get("cpu", 0) for v in self.usage.values())
            total_mem = sum(v.get("mem", 0) for v in self.usage.values())
            
            self.history.append((now, active_sessions, total_cpu, total_mem))
            
            # Limita histórico
            if len(self.history) > 200:
                self.history = self.history[-200:]
            
            self.status_label.config(text=f"✅ Atualizado - {active_sessions} sessões ativas", 
                                   foreground=COLORS['success'])
            self.last_update_label.config(text=f"🕒 Última atualização: {now.strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.status_label.config(text=f"❌ Erro na atualização: {str(e)}", 
                                   foreground=COLORS['danger'])
            self.log_error(f"Erro na atualização: {e}")
        finally:
            self.is_refreshing = False
    
    def update_sessions(self):
        """Obtém sessões RDP ativas usando a lógica do script original"""
        self.sessions.clear()

        try:
            result = subprocess.run(
                "query user",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            out = result.stdout.strip()
        except Exception as e:
            out = ""
            self.log_error(f"Erro ao executar 'query user': {e}")

        if not out:
            self.sessions.append({
                "Usuário": "Erro",
                "ID": "",
                "Estado": "",
                "Idle": "",
                "Logon": "",
                "CPU %": "0.0",
                "RAM (MB)": "0.0",
                "Processos": "0",
            })
        else:
            for line in out.splitlines():
                if "Ativo" in line:
                    clean = line.strip().lstrip(">").rstrip()
                    parts = re.split(r"\s{2,}", clean)
                    if len(parts) >= 3 and parts[2].isdigit():
                        idle = parts[4] if len(parts) > 4 else ""
                        logon = parts[5] if len(parts) > 5 else ""
                        self.sessions.append({
                            "Usuário": parts[0],
                            "ID": parts[2],
                            "Estado": "Ativo",
                            "Idle": idle,
                            "Logon": logon,
                            "CPU %": "0.0",
                            "RAM (MB)": "0.0",
                            "Processos": "0",
                        })

        self.sessions.sort(key=lambda s: s["Usuário"].lower())
    
    def update_usage(self):
        """Atualiza uso de CPU, memória e contagem de processos"""
        usage = {}
        process_count = {}
        
        try:
            for proc in psutil.process_iter(['username', 'cpu_percent', 'memory_info']):
                try:
                    username = proc.info.get('username', '')
                    if not username:
                        continue
                    
                    # Remove domínio
                    username = username.split('\\')[-1].lower()
                    
                    # Filtra processos do sistema se necessário
                    system_users = ['system', 'local service', 'network service', 'dwm-1', 'dwm-2']
                    if not self.show_system_processes.get() and username in system_users:
                        continue
                    
                    cpu = proc.cpu_percent()
                    memory_mb = proc.memory_info().rss / (1024 * 1024)
                    
                    if username not in usage:
                        usage[username] = {'cpu': 0.0, 'mem': 0.0}
                        process_count[username] = 0
                    
                    usage[username]['cpu'] += cpu
                    usage[username]['mem'] += memory_mb
                    process_count[username] += 1
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception:
                    continue
            
            self.usage = usage
            
            # Atualiza dados nas sessões
            for session in self.sessions:
                username = session["Usuário"].lower()
                if username in usage:
                    session["CPU %"] = f"{usage[username]['cpu']:.1f}"
                    session["RAM (MB)"] = f"{usage[username]['mem']:.1f}"
                    session["Processos"] = str(process_count.get(username, 0))
                    
        except Exception as e:
            self.log_error(f"Erro ao atualizar uso: {e}")
    
    def refresh_list(self):
        """Atualiza a lista na interface"""
        # Salva seleções atuais
        selected_ids = {self.tree.item(item)["values"][1] for item in self.tree.selection() 
                       if self.tree.item(item)["values"]}
        
        # Filtro de pesquisa
        search_term = self.search_var.get().lower().strip()
        filtered_sessions = []
        
        for session in self.sessions:
            if not search_term or any(search_term in str(value).lower() 
                                    for value in session.values()):
                filtered_sessions.append(session)
        
        # Limpa e repopula
        self.tree.delete(*self.tree.get_children())
        
        for session in filtered_sessions:
            values = (
                session["Usuário"],
                session["ID"],
                session["Estado"],
                session["Idle"],
                session["Logon"],
                session["CPU %"],
                session["RAM (MB)"],
                session["Processos"]
            )
            
            item = self.tree.insert("", "end", values=values)
            
            # Coloração baseada no estado
            if session["Estado"] == "Ativo":
                self.tree.set(item, "Estado", "🟢 Ativo")
            elif session["Estado"] == "Disc":
                self.tree.set(item, "Estado", "🔴 Desconectado")
            
            # Restaura seleção
            if session["ID"] in selected_ids:
                self.tree.selection_add(item)
    
    def update_summary(self):
        """Atualiza resumo estatístico"""
        try:
            total_sessions = len(self.sessions)
            active_sessions = len([s for s in self.sessions if s.get("ID", "").isdigit()])
            total_cpu = sum(float(s.get("CPU %", 0)) for s in self.sessions if s.get("CPU %", "0").replace(".", "").isdigit())
            total_memory = sum(float(s.get("RAM (MB)", 0)) for s in self.sessions if s.get("RAM (MB)", "0").replace(".", "").isdigit())
            
            # Calcula idle médio
            idle_times = []
            for s in self.sessions:
                idle = s.get("Idle", "")
                if idle and idle != "." and idle != "none":
                    try:
                        if ":" in idle:
                            parts = idle.split(":")
                            minutes = int(parts[0]) * 60 + int(parts[1])
                            idle_times.append(minutes)
                    except:
                        pass
            
            avg_idle = sum(idle_times) / len(idle_times) if idle_times else 0
            
            # Atualiza labels
            self.summary_labels["total_sessions"].config(text=str(total_sessions))
            self.summary_labels["active_sessions"].config(text=str(active_sessions))
            self.summary_labels["total_cpu"].config(text=f"{total_cpu:.1f}%")
            self.summary_labels["total_memory"].config(text=f"{total_memory:.1f} MB")
            self.summary_labels["avg_idle"].config(text=f"{avg_idle:.0f} min")
            
        except Exception as e:
            self.log_error(f"Erro ao atualizar resumo: {e}")
    
    def update_active_users(self):
        """Atualiza lista de usuários mais ativos"""
        try:
            self.active_users_text.delete(1.0, tk.END)
            
            # Ordena usuários por uso de CPU
            user_usage = []
            for username, usage in self.usage.items():
                if usage['cpu'] > 0:
                    user_usage.append((username, usage['cpu'], usage['mem']))
            
            user_usage.sort(key=lambda x: x[1], reverse=True)
            
            if user_usage:
                self.active_users_text.insert(tk.END, "👥 Top Usuários por CPU:\n\n")
                for i, (user, cpu, mem) in enumerate(user_usage[:10], 1):
                    line = f"{i:2d}. {user:<15} CPU: {cpu:5.1f}% RAM: {mem:6.1f}MB\n"
                    self.active_users_text.insert(tk.END, line)
            else:
                self.active_users_text.insert(tk.END, "Nenhum usuário ativo no momento.")
                
        except Exception as e:
            self.log_error(f"Erro ao atualizar usuários ativos: {e}")
    
    def check_alerts(self):
        """Verifica e exibe alertas"""
        try:
            self.alerts_text.delete(1.0, tk.END)
            alerts = []
            
            # Verifica uso alto de CPU
            for session in self.sessions:
                try:
                    cpu = float(session.get("CPU %", 0))
                    if cpu > 80:
                        alerts.append(f"🔥 {session['Usuário']}: CPU alta ({cpu:.1f}%)")
                except:
                    pass
            
            # Verifica uso alto de memória
            for session in self.sessions:
                try:
                    mem = float(session.get("RAM (MB)", 0))
                    if mem > 2048:  # Mais de 2GB
                        alerts.append(f"🧠 {session['Usuário']}: RAM alta ({mem:.1f}MB)")
                except:
                    pass
            
            # Verifica sessões idle por muito tempo
            for session in self.sessions:
                idle = session.get("Idle", "")
                if idle and "+" in idle:  # Indica mais de 24h
                    alerts.append(f"😴 {session['Usuário']}: Idle há muito tempo ({idle})")
            
            # Exibe alertas
            if alerts:
                timestamp = datetime.now().strftime('%H:%M:%S')
                self.alerts_text.insert(tk.END, f"⚠️ Alertas ({timestamp}):\n\n")
                for alert in alerts:
                    self.alerts_text.insert(tk.END, f"{alert}\n")
            else:
                self.alerts_text.insert(tk.END, "✅ Nenhum alerta no momento.\nTodos os sistemas funcionando normalmente.")
                
        except Exception as e:
            self.log_error(f"Erro ao verificar alertas: {e}")
    
    def schedule_auto_refresh(self):
        """Agenda próxima atualização automática"""
        if self.auto_refresh_enabled.get():
            self.update_all()
        
        self.root.after(self.REFRESH_INTERVAL, self.schedule_auto_refresh)
    
    def get_selected_sessions(self):
        """Retorna sessões selecionadas"""
        selected = []
        for item in self.tree.selection():
            values = self.tree.item(item)["values"]
            if values and len(values) >= 2:
                selected.append({
                    "user": values[0],
                    "id": values[1],
                    "state": values[2],
                    "item": item
                })
        return selected
    
    def on_double_click(self, event):
        """Manipula duplo clique na tabela"""
        selected = self.get_selected_sessions()
        if selected:
            self.show_session_details(selected[0])
    
    def show_context_menu(self, event):
        """Mostra menu de contexto"""
        selected = self.get_selected_sessions()
        if not selected:
            return
        
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="📋 Detalhes da Sessão", command=lambda: self.show_session_details(selected[0]))
        context_menu.add_separator()
        context_menu.add_command(label="💬 Enviar Mensagem", command=self.send_message)
        context_menu.add_command(label="🖥️ Controlar Sessão", command=self.remote_control)
        context_menu.add_separator()
        context_menu.add_command(label="🚪 Fazer Logoff", command=self.logoff_user)
        context_menu.add_command(label="❌ Desconectar", command=self.batch_logoff)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def show_session_details(self, session):
        """Mostra detalhes da sessão"""
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Detalhes da Sessão - {session['user']}")
        details_window.geometry("500x400")
        details_window.resizable(False, False)
        
        # Frame principal
        main_frame = ttk.Frame(details_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(main_frame, text=f"👤 Detalhes de {session['user']}", 
                 font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))
        
        # Informações básicas
        info_frame = ttk.LabelFrame(main_frame, text="Informações Básicas", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Busca dados atualizados da sessão
        session_data = None
        for s in self.sessions:
            if s.get("ID") == session["id"]:
                session_data = s
                break
        
        if session_data:
            details = [
                ("Usuário:", session_data["Usuário"]),
                ("ID da Sessão:", session_data["ID"]),
                ("Estado:", session_data["Estado"]),
                ("Tempo Idle:", session_data["Idle"]),
                ("Logon:", session_data["Logon"]),
                ("Uso de CPU:", f"{session_data['CPU %']}%"),
                ("Uso de RAM:", f"{session_data['RAM (MB)']} MB"),
                ("Processos:", session_data["Processos"])
            ]
            
            for label, value in details:
                row_frame = ttk.Frame(info_frame)
                row_frame.pack(fill=tk.X, pady=2)
                
                ttk.Label(row_frame, text=label, font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT)
                ttk.Label(row_frame, text=value, font=('Segoe UI', 9)).pack(side=tk.RIGHT)
        
        # Botões de ação
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(buttons_frame, text="💬 Enviar Mensagem", 
                  command=lambda: [details_window.destroy(), self.send_message()]).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="🖥️ Controlar", 
                  command=lambda: [details_window.destroy(), self.remote_control()]).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="❌ Fechar", 
                  command=details_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def show_settings(self):
        """Mostra janela de configurações"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("⚙️ Configurações")
        settings_window.geometry("600x500")
        settings_window.resizable(False, False)
        
        # Frame principal
        main_frame = ttk.Frame(settings_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(main_frame, text="⚙️ Configurações do Sistema", 
                 font=('Segoe UI', 16, 'bold')).pack(pady=(0, 20))
        
        # Notebook para abas
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Aba Geral
        general_frame = ttk.Frame(notebook, padding=20)
        notebook.add(general_frame, text="Geral")
        
        ttk.Checkbutton(general_frame, text="🔄 Atualização automática", 
                       variable=self.auto_refresh_enabled).pack(anchor='w', pady=5)
        
        ttk.Checkbutton(general_frame, text="⚙️ Mostrar processos do sistema", 
                       variable=self.show_system_processes).pack(anchor='w', pady=5)
        
        ttk.Checkbutton(general_frame, text="🔔 Mostrar notificações", 
                       variable=self.show_notifications).pack(anchor='w', pady=5)
        
        ttk.Checkbutton(general_frame, text="🔊 Alertas sonoros", 
                       variable=self.sound_alerts).pack(anchor='w', pady=5)
        
        # Intervalo de atualização
        interval_frame = ttk.LabelFrame(general_frame, text="Intervalo de Atualização", padding=10)
        interval_frame.pack(fill=tk.X, pady=20)
        
        ttk.Label(interval_frame, text="Intervalo (segundos):").pack(side=tk.LEFT)
        interval_spinbox = ttk.Spinbox(interval_frame, from_=1, to=60, width=10,
                                      textvariable=self.interval_var)
        interval_spinbox.pack(side=tk.RIGHT)
        
        # Aba Aparência
        appearance_frame = ttk.Frame(notebook, padding=20)
        notebook.add(appearance_frame, text="Aparência")
        
        ttk.Checkbutton(appearance_frame, text="🌙 Modo escuro", 
                       variable=self.dark_mode,
                       command=self.toggle_theme).pack(anchor='w', pady=5)
        
        # Botões
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(buttons_frame, text="💾 Salvar", 
                  command=lambda: [self.save_config(), settings_window.destroy()]).pack(side=tk.LEFT)
        
        ttk.Button(buttons_frame, text="❌ Cancelar", 
                  command=settings_window.destroy).pack(side=tk.RIGHT)
    
    def show_logs(self):
        """Mostra janela de logs"""
        logs_window = tk.Toplevel(self.root)
        logs_window.title("📖 Logs do Sistema")
        logs_window.geometry("800x600")
        
        # Frame principal
        main_frame = ttk.Frame(logs_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(main_frame, text="📖 Logs do Sistema", 
                 font=('Segoe UI', 14, 'bold')).pack(pady=(0, 10))
        
        # Área de texto com scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        logs_text = tk.Text(text_frame, font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=logs_text.yview)
        logs_text.configure(yscrollcommand=scrollbar.set)
        
        logs_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Carrega logs
        try:
            if os.path.exists(self.LOG_FILE):
                with open(self.LOG_FILE, 'r', encoding='utf-8') as f:
                    logs_content = f.read()
                    logs_text.insert(tk.END, logs_content)
            else:
                logs_text.insert(tk.END, "Nenhum log encontrado.")
        except Exception as e:
            logs_text.insert(tk.END, f"Erro ao carregar logs: {e}")
        
        # Botões
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="🔄 Atualizar", 
                  command=lambda: self.refresh_logs(logs_text)).pack(side=tk.LEFT)
        
        ttk.Button(buttons_frame, text="🗑️ Limpar Logs", 
                  command=lambda: self.clear_logs(logs_text)).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(buttons_frame, text="❌ Fechar", 
                  command=logs_window.destroy).pack(side=tk.RIGHT)
    
    def refresh_logs(self, text_widget):
        """Atualiza logs na janela"""
        text_widget.delete(1.0, tk.END)
        try:
            if os.path.exists(self.LOG_FILE):
                with open(self.LOG_FILE, 'r', encoding='utf-8') as f:
                    logs_content = f.read()
                    text_widget.insert(tk.END, logs_content)
            else:
                text_widget.insert(tk.END, "Nenhum log encontrado.")
        except Exception as e:
            text_widget.insert(tk.END, f"Erro ao carregar logs: {e}")
    
    def clear_logs(self, text_widget):
        """Limpa arquivo de logs"""
        if messagebox.askyesno("Confirmar", "Deseja realmente limpar todos os logs?"):
            try:
                with open(self.LOG_FILE, 'w', encoding='utf-8') as f:
                    f.write("")
                text_widget.delete(1.0, tk.END)
                text_widget.insert(tk.END, "Logs limpos com sucesso.")
                messagebox.showinfo("Sucesso", "Logs limpos com sucesso.")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao limpar logs: {e}")
    
    # Métodos de ação (mantidos do código original com melhorias)
    def batch_logoff(self):
        """Desconecta sessões selecionadas"""
        selected = self.get_selected_sessions()
        
        if not selected:
            messagebox.showwarning("Atenção", "Selecione pelo menos uma sessão.")
            return
        
        valid_sessions = [s for s in selected if s["id"].isdigit()]
        if not valid_sessions:
            messagebox.showwarning("Atenção", "Nenhuma sessão válida selecionada.")
            return
        
        users = [s["user"] for s in valid_sessions]
        message = f"Desconectar {len(users)} sessão(ões):\n\n" + "\n".join(f"• {user}" for user in users)
        
        if not messagebox.askyesno("⚠️ Confirmar Desconexão", message):
            return
        
        success_count = 0
        errors = []
        
        for session in valid_sessions:
            try:
                result = subprocess.run(f"logoff {session['id']}", shell=True, 
                                      capture_output=True, timeout=10)
                if result.returncode == 0:
                    success_count += 1
                else:
                    errors.append(f"{session['user']}: {result.stderr.decode()}")
            except Exception as e:
                errors.append(f"{session['user']}: {str(e)}")
        
        # Relatório de resultado
        result_msg = f"✅ {success_count} sessão(ões) desconectada(s) com sucesso."
        if errors:
            result_msg += f"\n\n❌ Erros:\n" + "\n".join(errors[:5])
        
        messagebox.showinfo("Resultado da Operação", result_msg)
        self.update_all()
    
    def logoff_user(self):
        """Faz logoff de usuário selecionado"""
        selected = self.get_selected_sessions()
        
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma sessão.")
            return
        
        session = selected[0]
        if not session["id"].isdigit():
            messagebox.showwarning("Atenção", "ID de sessão inválido.")
            return
        
        if messagebox.askyesno("⚠️ Confirmar Logoff", 
                              f"Fazer logoff do usuário {session['user']}?\n\nEsta ação encerrará a sessão imediatamente."):
            try:
                result = subprocess.run(f"logoff {session['id']}", shell=True, 
                                      capture_output=True, timeout=10)
                if result.returncode == 0:
                    messagebox.showinfo("✅ Sucesso", f"Logoff realizado para {session['user']}")
                else:
                    messagebox.showerror("❌ Erro", f"Falha no logoff:\n{result.stderr.decode()}")
            except Exception as e:
                messagebox.showerror("❌ Erro", f"Erro ao executar logoff:\n{str(e)}")
            
            self.update_all()
    
    def show_graph(self):
        """Mostra gráficos avançados de histórico"""
        if not self.history:
            messagebox.showinfo("Informação", "Nenhum dado histórico disponível ainda.\nAguarde algumas atualizações.")
            return
        
        # Cria janela do gráfico
        graph_window = tk.Toplevel(self.root)
        graph_window.title("📊 Análise de Histórico - Sessões e Recursos")
        graph_window.geometry("1000x700")
        
        # Cria figura matplotlib
        fig = Figure(figsize=(12, 10))
        
        # Dados para os gráficos
        times = [entry[0] for entry in self.history]
        sessions = [entry[1] for entry in self.history]
        cpu_usage = [entry[2] for entry in self.history]
        mem_usage = [entry[3] for entry in self.history]
        
        # Gráfico 1: Sessões ativas
        ax1 = fig.add_subplot(2, 2, 1)
        ax1.plot(times, sessions, 'b-', linewidth=2, marker='o', markersize=3)
        ax1.set_title('📈 Sessões Ativas ao Longo do Tempo', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Número de Sessões')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(bottom=0)
        
        # Gráfico 2: Uso de CPU
        ax2 = fig.add_subplot(2, 2, 2)
        ax2.plot(times, cpu_usage, 'r-', linewidth=2, marker='s', markersize=3)
        ax2.set_title('🔥 Uso Total de CPU', fontsize=12, fontweight='bold')
        ax2.set_ylabel('CPU (%)')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(bottom=0)
        
        # Gráfico 3: Uso de Memória
        ax3 = fig.add_subplot(2, 2, 3)
        ax3.plot(times, mem_usage, 'g-', linewidth=2, marker='^', markersize=3)
        ax3.set_title('🧠 Uso Total de Memória', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Memória (MB)')
        ax3.set_xlabel('Horário')
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(bottom=0)
        
        # Gráfico 4: Correlação CPU vs Memória
        ax4 = fig.add_subplot(2, 2, 4)
        scatter = ax4.scatter(cpu_usage, mem_usage, c=range(len(cpu_usage)), 
                             cmap='viridis', alpha=0.6)
        ax4.set_title('🔄 Correlação CPU vs Memória', fontsize=12, fontweight='bold')
        ax4.set_xlabel('CPU (%)')
        ax4.set_ylabel('Memória (MB)')
        ax4.grid(True, alpha=0.3)
        
        # Colorbar para o scatter plot
        plt.colorbar(scatter, ax=ax4, label='Tempo (mais recente →)')
        
        # Formata datas no eixo X
        fig.autofmt_xdate()
        fig.tight_layout()
        
        # Adiciona canvas à janela
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Frame para botões
        buttons_frame = ttk.Frame(graph_window)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(buttons_frame, text="💾 Salvar Gráfico", 
                  command=lambda: self.save_graph(fig)).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(buttons_frame, text="🔄 Atualizar", 
                  command=lambda: [graph_window.destroy(), self.show_graph()]).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(buttons_frame, text="❌ Fechar", 
                  command=graph_window.destroy).pack(side=tk.RIGHT, padx=10)
    
    def save_graph(self, fig):
        """Salva gráfico em arquivo"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[
                ("PNG files", "*.png"),
                ("PDF files", "*.pdf"),
                ("SVG files", "*.svg"),
                ("All files", "*.*")
            ]
        )
        if filename:
            try:
                fig.savefig(filename, dpi=300, bbox_inches='tight', 
                           facecolor='white', edgecolor='none')
                messagebox.showinfo("✅ Sucesso", f"Gráfico salvo em:\n{filename}")
            except Exception as e:
                messagebox.showerror("❌ Erro", f"Erro ao salvar gráfico:\n{str(e)}")
    
    def play_audio(self):
        """Reproduz áudio na sessão selecionada"""
        selected = self.get_selected_sessions()
        
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma sessão.")
            return
        
        session = selected[0]
        if not session["id"].isdigit():
            messagebox.showwarning("Atenção", "ID de sessão inválido.")
            return
        
        # Seleciona arquivo de áudio
        audio_path = filedialog.askopenfilename(
            title="Selecione arquivo de áudio",
            filetypes=[
                ("Arquivos de áudio", "*.wav *.mp3 *.wma *.aac *.flac"),
                ("WAV files", "*.wav"),
                ("MP3 files", "*.mp3"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if not audio_path:
            return
        
        try:
            # Escapa aspas no caminho
            safe_path = audio_path.replace('"', '\\"')
            
            # Comando para reproduzir áudio na sessão
            cmd = f'psexec -accepteula -i {session["id"]} -d powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Item \\"{safe_path}\\""'
            
            subprocess.Popen(cmd, shell=True)
            messagebox.showinfo("✅ Sucesso", f"Áudio enviado para a sessão de {session['user']}")
            
        except Exception as e:
            messagebox.showerror("❌ Erro", f"Erro ao reproduzir áudio:\n{str(e)}")
    
    def send_message(self):
        """Envia mensagem para sessão selecionada"""
        selected = self.get_selected_sessions()
        
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma sessão.")
            return
        
        session = selected[0]
        if not session["id"].isdigit():
            messagebox.showwarning("Atenção", "ID de sessão inválido.")
            return
        
        # Dialog customizado para mensagem
        message_window = tk.Toplevel(self.root)
        message_window.title(f"💬 Enviar Mensagem para {session['user']}")
        message_window.geometry("500x300")
        message_window.resizable(False, False)
        
        # Frame principal
        main_frame = ttk.Frame(message_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text=f"Mensagem para {session['user']}:", 
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Área de texto
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        message_text = tk.Text(text_frame, font=('Segoe UI', 10), wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=message_text.yview)
        message_text.configure(yscrollcommand=scrollbar.set)
        
        message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botões
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
        
        def send_msg():
            message = message_text.get(1.0, tk.END).strip()
            if not message:
                messagebox.showwarning("Atenção", "Digite uma mensagem.")
                return
            
            try:
                cmd = f'msg {session["id"]} "{message}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
                
                if result.returncode == 0:
                    messagebox.showinfo("✅ Sucesso", f"Mensagem enviada para {session['user']}")
                    message_window.destroy()
                else:
                    messagebox.showerror("❌ Erro", f"Falha ao enviar mensagem:\n{result.stderr.decode()}")
                    
            except Exception as e:
                messagebox.showerror("❌ Erro", f"Erro ao enviar mensagem:\n{str(e)}")
        
        ttk.Button(buttons_frame, text="📤 Enviar", command=send_msg).pack(side=tk.LEFT)
        ttk.Button(buttons_frame, text="❌ Cancelar", command=message_window.destroy).pack(side=tk.RIGHT)
        
        # Foco no texto
        message_text.focus()
    
    def send_image(self):
        """Envia imagem para sessão selecionada"""
        selected = self.get_selected_sessions()
        
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma sessão.")
            return
        
        session = selected[0]
        if not session["id"].isdigit():
            messagebox.showwarning("Atenção", "ID de sessão inválido.")
            return
        
        # Seleciona arquivo de imagem
        image_path = filedialog.askopenfilename(
            title="Selecione imagem",
            filetypes=[
                ("Arquivos de imagem", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if not image_path:
            return
        
        try:
            # Escapa aspas no caminho
            safe_path = image_path.replace('"', '\\"')
            
            # Comando para abrir imagem na sessão
            cmd = f'psexec -accepteula -i {session["id"]} -d powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Item \\"{safe_path}\\""'
            
            subprocess.Popen(cmd, shell=True)
            messagebox.showinfo("✅ Sucesso", f"Imagem enviada para a sessão de {session['user']}")
            
        except Exception as e:
            messagebox.showerror("❌ Erro", f"Erro ao enviar imagem:\n{str(e)}")
    
    def send_video(self):
        """Envia vídeo para sessão selecionada"""
        selected = self.get_selected_sessions()
        
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma sessão.")
            return
        
        session = selected[0]
        if not session["id"].isdigit():
            messagebox.showwarning("Atenção", "ID de sessão inválido.")
            return
        
        # Seleciona arquivo de vídeo
        video_path = filedialog.askopenfilename(
            title="Selecione vídeo",
            filetypes=[
                ("Arquivos de vídeo", "*.mp4 *.avi *.wmv *.mkv *.mov *.flv *.webm"),
                ("MP4 files", "*.mp4"),
                ("AVI files", "*.avi"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if not video_path:
            return
        
        try:
            # Escapa aspas no caminho
            safe_path = video_path.replace('"', '\\"')
            
            # Comando para reproduzir vídeo na sessão
            cmd = f'psexec -accepteula -i {session["id"]} -d powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Item \\"{safe_path}\\""'
            
            subprocess.Popen(cmd, shell=True)
            messagebox.showinfo("✅ Sucesso", f"Vídeo enviado para a sessão de {session['user']}")
            
        except Exception as e:
            messagebox.showerror("❌ Erro", f"Erro ao enviar vídeo:\n{str(e)}")
    
    def remote_control(self):
        """Inicia controle remoto da sessão"""
        selected = self.get_selected_sessions()
        
        if not selected:
            messagebox.showwarning("Atenção", "Selecione uma sessão.")
            return
        
        session = selected[0]
        if not session["id"].isdigit():
            messagebox.showwarning("Atenção", "ID de sessão inválido.")
            return
        
        # Confirma ação
        if not messagebox.askyesno("⚠️ Confirmar Controle Remoto", 
                                  f"Iniciar controle remoto da sessão de {session['user']}?\n\nO usuário será notificado sobre o controle remoto."):
            return
        
        try:
            # Comando para controle remoto
            cmd = f"mstsc /shadow:{session['id']} /control"
            subprocess.Popen(cmd, shell=True)
            messagebox.showinfo("✅ Sucesso", f"Controle remoto iniciado para {session['user']}")
            
        except Exception as e:
            messagebox.showerror("❌ Erro", f"Erro ao iniciar controle remoto:\n{str(e)}")
    
    def export_data(self):
        """Exporta dados das sessões"""
        if not self.sessions:
            messagebox.showwarning("Atenção", "Nenhum dado para exportar.")
            return
        
        # Seleciona arquivo para salvar
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("Excel files", "*.xlsx"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if not filename:
            return
        
        try:
            if filename.endswith('.json'):
                # Exporta como JSON
                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'server_info': {
                        'hostname': os.environ.get('COMPUTERNAME', 'Unknown'),
                        'username': os.environ.get('USERNAME', 'Unknown')
                    },
                    'sessions': self.sessions,
                    'usage': self.usage,
                    'history': [(t.isoformat(), s, c, m) for t, s, c, m in self.history],
                    'summary': {
                        'total_sessions': len(self.sessions),
                        'active_sessions': len([s for s in self.sessions if s.get("ID", "").isdigit()]),
                        'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                    
            elif filename.endswith('.csv'):
                # Exporta como CSV
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    if self.sessions:
                        writer = csv.DictWriter(f, fieldnames=self.sessions[0].keys())
                        writer.writeheader()
                        writer.writerows(self.sessions)
                        
            elif filename.endswith('.xlsx'):
                # Exporta como Excel
                try:
                    import pandas as pd
                    df = pd.DataFrame(self.sessions)
                    df.to_excel(filename, index=False, engine='openpyxl')
                except ImportError:
                    messagebox.showerror("Erro", "pandas não está instalado.\nInstale com: pip install pandas openpyxl")
                    return
                    
            else:
                # Exporta como texto
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"RELATÓRIO DE SESSÕES RDP\n")
                    f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                    f.write(f"Servidor: {os.environ.get('COMPUTERNAME', 'Unknown')}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for i, session in enumerate(self.sessions, 1):
                        f.write(f"SESSÃO {i}\n")
                        f.write("-" * 40 + "\n")
                        for key, value in session.items():
                            f.write(f"{key}: {value}\n")
                        f.write("\n")
                    
                    f.write("\nRESUMO ESTATÍSTICO\n")
                    f.write("-" * 40 + "\n")
                    f.write(f"Total de sessões: {len(self.sessions)}\n")
                    f.write(f"Sessões ativas: {len([s for s in self.sessions if s.get('ID', '').isdigit()])}\n")
                    f.write(f"Dados históricos: {len(self.history)} registros\n")
            
            messagebox.showinfo("✅ Sucesso", f"Dados exportados com sucesso para:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("❌ Erro", f"Erro ao exportar dados:\n{str(e)}")
    
    def on_closing(self):
        """Chamado quando a janela é fechada"""
        if messagebox.askyesno("Confirmar Saída", "Deseja realmente sair do programa?"):
            self.save_config()
            self.root.destroy()


if __name__ == "__main__":
    try:
        # Configuração inicial
        root = tk.Tk()
        root.configure(bg=COLORS['light'])
        
        # Tenta configurar ícone
        try:
            # Se houver um arquivo icon.ico, usa ele
            if os.path.exists('icon.ico'):
                root.iconbitmap('icon.ico')
        except:
            pass
        
        # Inicia aplicação
        app = RDPSessionViewer(root)
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror("❌ Erro Fatal", f"Erro ao inicializar aplicação:\n{str(e)}")
        sys.exit(1)

