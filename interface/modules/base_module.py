import tkinter as tk
from tkinter import ttk
from utils.theme import PALETTE, FONTS

class BaseModule:
    """Classe base para todos os módulos do sistema com controle de permissões robusto"""
    
    def __init__(self, parent, user_id, role, main_window):
        self.parent = parent
        self.user_id = user_id
        self.role = role
        self.main_window = main_window
        
        # Registrar para receber eventos
        if hasattr(main_window, 'register_listener'):
            print(f"DEBUG BASE_MODULE: Registrando listener para {self.__class__.__name__}")
            main_window.register_listener(self.handle_event)
        
        # Frame principal do módulo (container visual)
        self.frame = tk.Frame(parent, bg=PALETTE["bg_app"])
        self.frame.pack(fill="both", expand=True)
        
        # Configurar UI específica do módulo
        self.setup_ui()
        
        # Aplicar modo readonly automaticamente baseado nas permissões
        self._apply_permissions_automatically()
    
    def _apply_permissions_automatically(self):
        """Aplica automaticamente as permissões baseado no nível de acesso do usuário"""
        if not hasattr(self.main_window, 'can_edit'):
            return
            
        # Determinar qual módulo baseado em override opcional ou nome da classe
        module_key = getattr(self, 'module_key', self.__class__.__name__.lower().replace('module', ''))
        
        # Se o usuário não pode editar, aplicar modo somente leitura
        if not self.main_window.can_edit(module_key):
            self.set_read_only(True)
            print(f"🔒 Módulo {module_key} configurado como somente leitura para usuário {self.user_id}")
        
    def setup_ui(self):
        """Método a ser implementado pelos módulos filhos"""
        pass
        
    def handle_event(self, event_type, data=None):
        """Manipular eventos recebidos do sistema"""
        pass
        
    def emit_event(self, event_type, data=None):
        """Emitir evento para outros módulos"""
        if hasattr(self.main_window, 'emit_event'):
            self.main_window.emit_event(event_type, data)
    
    def has_role(self, role_name: str) -> bool:
        """Verifica se o usuário possui o perfil informado (suporta múltiplos perfis separados por vírgula)."""
        try:
            roles = [r.strip().lower() for r in (self.role or '').split(',') if r.strip()]
            return role_name.lower() in roles
        except Exception:
            return self.role == role_name
    
    def can_edit(self, module_key: str = None) -> bool:
        """Verifica se o usuário pode editar o módulo atual"""
        if self.has_role('admin'):
            return True
        
        if not hasattr(self.main_window, 'can_edit'):
            return True
            
        # Se não especificar módulo, tentar inferir do nome da classe ou usar override
        if module_key is None:
            module_key = getattr(self, 'module_key', self.__class__.__name__.lower().replace('module', ''))
            
        return self.main_window.can_edit(module_key)
    
    def can_add(self, module_key: str = None) -> bool:
        """Verifica se o usuário pode adicionar itens no módulo atual"""
        return self.can_edit(module_key)
    
    def can_delete(self, module_key: str = None) -> bool:
        """Verifica se o usuário pode deletar itens no módulo atual"""
        return self.can_edit(module_key)
    
    def set_read_only(self, read_only: bool = True):
        """Define o módulo como somente leitura"""
        self.read_only = read_only
        
        if read_only:
            print(f"🔒 Aplicando modo somente leitura para {self.__class__.__name__}")
            # Aplicar proteção imediatamente
            self._apply_read_only_state()
            
            # Aplicar proteção adicional após um breve delay para garantir que todos os widgets estejam prontos
            if hasattr(self, 'frame'):
                self.frame.after(100, self._apply_read_only_state)
                self.frame.after(500, self._apply_read_only_state)  # Proteção dupla
                self.frame.after(1000, self._apply_read_only_state)  # Proteção tripla
        else:
            print(f"✏️ Removendo modo somente leitura para {self.__class__.__name__}")
            # Implementar lógica para reativar campos se necessário
            
    def apply_readonly_for_visualization(self):
        """Aplica modo readonly apenas para visualização - mantém campos visíveis mas não editáveis"""
        if not self.can_edit():
            print(f"🔍 Aplicando modo visualização para {self.__class__.__name__}")
            self._apply_visualization_readonly()
            
    def _apply_visualization_readonly(self):
        """Aplica readonly apenas em botões de ação, mantendo campos visíveis"""
        try:
            # Desabilitar apenas botões de ação (salvar, excluir, adicionar, etc.)
            for widget in self.frame.winfo_children():
                self._disable_action_buttons_recursive(widget)
                
        except Exception as e:
            print(f"⚠️ Erro ao aplicar modo visualização: {e}")
            
    def _disable_action_buttons_recursive(self, widget):
        """Desabilita apenas botões de ação, mantendo campos de visualização"""
        try:
            if isinstance(widget, tk.Button):
                button_text = widget.cget('text').lower()
                # Lista de botões que devem ser desabilitados (ações de modificação)
                # NOTA: Removemos 'editar' da lista para permitir visualização
                action_buttons = ['salvar', 'excluir', 'adicionar', 'remover', 'inserir', 'deletar', 'criar', 'novo', 'alterar', 'modificar']
                if any(action in button_text for action in action_buttons):
                    widget.config(state='disabled')
                    print(f"   🔒 Botão desabilitado: {button_text}")
                elif 'editar' in button_text:
                    # Manter botão Editar habilitado para visualização
                    widget.config(state='normal')
                    print(f"   👁️ Botão Editar mantido habilitado para visualização: {button_text}")
                    
            elif isinstance(widget, (tk.Entry, tk.Text)):
                # Para campos de texto, aplicar readonly mas manter visível
                try:
                    if isinstance(widget, tk.Entry):
                        # Usar readonly para Entry - mantém o texto visível
                        widget.config(state='readonly', readonlybackground='#f8f8f8')
                        print(f"   🔍 Campo Entry em modo readonly: {widget.get()[:30]}...")
                    else:  # tk.Text
                        # Para Text, usar normal primeiro para garantir que o conteúdo seja visível
                        widget.config(state='normal')
                        widget.config(state='disabled', bg='#f8f8f8')
                        print(f"   🔍 Campo Text em modo readonly")
                except Exception as e:
                    print(f"   ⚠️ Erro ao configurar campo: {e}")
                    pass
                    
            elif isinstance(widget, ttk.Entry):
                # Para ttk.Entry
                try:
                    widget.config(state='readonly')
                except:
                    pass
                    
            elif isinstance(widget, ttk.Combobox):
                # Para combobox, bloquear completamente para usuários com permissão "Consultar"
                try:
                    widget.config(state='disabled')
                    # Bloquear todos os eventos de interação
                    widget.unbind('<Key>')
                    widget.unbind('<Button-1>')
                    widget.unbind('<ButtonRelease-1>')
                    widget.unbind('<Double-Button-1>')
                    widget.unbind('<Return>')
                    widget.unbind('<Tab>')
                    widget.unbind('<Down>')
                    widget.unbind('<Up>')
                    widget.unbind('<Button-3>')
                    widget.unbind('<B1-Motion>')
                    widget.unbind('<FocusIn>')
                    widget.unbind('<FocusOut>')
                    # Bloquear eventos de teclado específicos para combobox
                    widget.bind('<Key>', lambda e: 'break')
                    widget.bind('<Button-1>', lambda e: 'break')
                    widget.bind('<ButtonRelease-1>', lambda e: 'break')
                    widget.bind('<Double-Button-1>', lambda e: 'break')
                    widget.bind('<Return>', lambda e: 'break')
                    widget.bind('<Tab>', lambda e: 'break')
                    widget.bind('<Down>', lambda e: 'break')
                    widget.bind('<Up>', lambda e: 'break')
                    widget.bind('<Button-3>', lambda e: 'break')
                    widget.bind('<B1-Motion>', lambda e: 'break')
                    widget.bind('<FocusIn>', lambda e: 'break')
                    widget.bind('<FocusOut>', lambda e: 'break')
                    # Bloquear evento de seleção
                    widget.bind('<<ComboboxSelected>>', lambda e: 'break')
                except:
                    pass
                    
            elif isinstance(widget, (tk.Checkbutton, tk.Radiobutton)):
                # Para checkboxes e radiobuttons
                try:
                    widget.config(state='disabled')
                except:
                    pass
                    
            # Recursão para widgets filhos
            try:
                for child in widget.winfo_children():
                    self._disable_action_buttons_recursive(child)
            except:
                pass
                
        except Exception as e:
            pass  # Ignorar erros em widgets específicos
    
    def _apply_read_only_state(self):
        """Aplica o estado de somente leitura aos widgets"""
        if not hasattr(self, 'read_only') or not self.read_only:
            return
            
        try:
            print(f"🔒🔒🔒 APLICANDO proteção TOTAL para {self.__class__.__name__}")
            
            # Desabilitar todos os campos de entrada
            for widget in self.frame.winfo_children():
                self._disable_widget_recursive(widget)
                
            # Proteção adicional para campos específicos que podem ter sido criados dinamicamente
            self._protect_specific_widgets()
            
            print(f"✅ Proteção aplicada com sucesso para {self.__class__.__name__}")
            
        except Exception as e:
            print(f"⚠️ Erro ao aplicar proteção: {e}")
    
    def _disable_widget_recursive(self, widget):
        """Desabilita um widget e seus filhos recursivamente de forma COMPLETA e AGGRESSIVA"""
        try:
            # Desabilitar TODOS os tipos de widgets de entrada
            if isinstance(widget, (tk.Entry, tk.Text, tk.Spinbox)):
                widget.config(state='disabled')
                # Bloquear eventos de teclado e mouse
                widget.unbind('<Key>')
                widget.unbind('<Button-1>')
                widget.unbind('<Double-Button-1>')
                widget.unbind('<Return>')
                widget.unbind('<Tab>')
                widget.unbind('<Control-a>')
                widget.unbind('<Control-c>')
                widget.unbind('<Control-v>')
                widget.unbind('<Control-x>')
                widget.unbind('<Delete>')
                widget.unbind('<BackSpace>')
                widget.unbind('<F2>')
                widget.unbind('<Button-3>')
                
            elif isinstance(widget, ttk.Entry):
                widget.config(state='disabled')
                # Mesmo bloqueio para ttk.Entry
                widget.unbind('<Key>')
                widget.unbind('<Button-1>')
                widget.unbind('<Double-Button-1>')
                widget.unbind('<Return>')
                widget.unbind('<Tab>')
                widget.unbind('<Control-a>')
                widget.unbind('<Control-c>')
                widget.unbind('<Control-v>')
                widget.unbind('<Control-x>')
                widget.unbind('<Delete>')
                widget.unbind('<BackSpace>')
                widget.unbind('<F2>')
                widget.unbind('<Button-3>')
                
            elif isinstance(widget, (tk.Checkbutton, tk.Radiobutton)):
                widget.config(state='disabled')
                widget.unbind('<Button-1>')
                widget.unbind('<Button-3>')
                widget.unbind('<Return>')
                widget.unbind('<Space>')
                
            elif isinstance(widget, ttk.Combobox):
                # Bloquear completamente as listas suspensas para usuários com permissão "Consultar"
                widget.config(state='disabled')
                # Bloquear todos os eventos de interação
                widget.unbind('<Key>')
                widget.unbind('<Button-1>')
                widget.unbind('<ButtonRelease-1>')
                widget.unbind('<Double-Button-1>')
                widget.unbind('<Return>')
                widget.unbind('<Tab>')
                widget.unbind('<Down>')
                widget.unbind('<Up>')
                widget.unbind('<Button-3>')
                widget.unbind('<B1-Motion>')
                widget.unbind('<FocusIn>')
                widget.unbind('<FocusOut>')
                # Bloquear eventos de teclado específicos para combobox
                widget.bind('<Key>', lambda e: 'break')
                widget.bind('<Button-1>', lambda e: 'break')
                widget.bind('<ButtonRelease-1>', lambda e: 'break')
                widget.bind('<Double-Button-1>', lambda e: 'break')
                widget.bind('<Return>', lambda e: 'break')
                widget.bind('<Tab>', lambda e: 'break')
                widget.bind('<Down>', lambda e: 'break')
                widget.bind('<Up>', lambda e: 'break')
                widget.bind('<Button-3>', lambda e: 'break')
                widget.bind('<B1-Motion>', lambda e: 'break')
                widget.bind('<FocusIn>', lambda e: 'break')
                widget.bind('<FocusOut>', lambda e: 'break')
                # Bloquear evento de seleção
                widget.bind('<<ComboboxSelected>>', lambda e: 'break')
                
            elif isinstance(widget, tk.Button):
                # Desabilitar TODOS os botões exceto os de consulta/navegação
                button_text = widget.cget('text').lower()
                # Lista muito restritiva de botões permitidos
                allowed_buttons = ['buscar', 'pesquisar', 'filtrar', 'visualizar', 'ver', 'consultar', 'imprimir', 'exportar', 'pdf', 'voltar', 'anterior', 'próximo', 'primeiro', 'último', 'editar']
                if not any(allowed in button_text for allowed in allowed_buttons):
                    widget.config(state='disabled')
                    # Bloquear completamente o botão
                    widget.unbind('<Button-1>')
                    widget.unbind('<Return>')
                    widget.unbind('<Space>')
                    
            elif isinstance(widget, ttk.Treeview):
                # Modo consulta: permitir seleção/visualização, bloquear edição e remoção
                widget.config(selectmode='browse')
                # Bloquear ações de edição/inserção/remoção
                widget.unbind('<Return>')
                widget.unbind('<F2>')
                widget.unbind('<Delete>')
                widget.unbind('<Key>')
                
            elif isinstance(widget, tk.Listbox):
                # Permitir rolagem/seleção para consulta, sem edição
                widget.config(state='disabled')
                
            elif isinstance(widget, (tk.Scale, ttk.Scale)):
                widget.config(state='disabled')
                widget.unbind('<Button-1>')
                widget.unbind('<B1-Motion>')
                widget.unbind('<ButtonRelease-1>')
                
            # Bloquear TODOS os bindings de teclado e mouse para edição
            if hasattr(widget, 'bind'):
                # Remover TODOS os bindings de edição
                widget.unbind('<Key>')
                widget.unbind('<Button-1>')
                widget.unbind('<ButtonRelease-1>')
                widget.unbind('<B1-Motion>')
                widget.unbind('<Return>')
                widget.unbind('<Tab>')
                widget.unbind('<Shift-Tab>')
                widget.unbind('<Control-a>')
                widget.unbind('<Control-c>')
                widget.unbind('<Control-v>')
                widget.unbind('<Control-x>')
                widget.unbind('<Control-z>')
                widget.unbind('<Control-y>')
                widget.unbind('<Delete>')
                widget.unbind('<BackSpace>')
                widget.unbind('<F2>')
                widget.unbind('<F5>')
                widget.unbind('<F9>')
                widget.unbind('<Button-3>')  # Botão direito
                widget.unbind('<Button-2>')  # Botão do meio
                widget.unbind('<B2-Motion>')
                widget.unbind('<ButtonRelease-2>')
                widget.unbind('<Shift-Button-1>')
                widget.unbind('<Control-Button-1>')
                widget.unbind('<Up>')
                widget.unbind('<Down>')
                widget.unbind('<Left>')
                widget.unbind('<Right>')
                widget.unbind('<Home>')
                widget.unbind('<End>')
                widget.unbind('<Page_Up>')
                widget.unbind('<Page_Down>')
                widget.unbind('<Insert>')
                widget.unbind('<Space>')
            
            # Processar filhos recursivamente
            for child in widget.winfo_children():
                self._disable_widget_recursive(child)
                
        except Exception as e:
            # Log silencioso de erros para não interromper o processo
            pass
    
    def _protect_specific_widgets(self):
        """Proteção adicional para widgets específicos que podem ter sido criados dinamicamente"""
        try:
            # Proteger campos de entrada específicos que podem ter sido criados após a inicialização
            for widget_name in dir(self):
                widget = getattr(self, widget_name, None)
                if widget and hasattr(widget, 'config'):
                    if isinstance(widget, (tk.Entry, tk.Text, tk.Spinbox, ttk.Entry)):
                        widget.config(state='disabled')
                    elif isinstance(widget, ttk.Combobox):
                        # Bloquear completamente as listas suspensas
                        widget.config(state='disabled')
                        # Bloquear todos os eventos de interação
                        widget.unbind('<Key>')
                        widget.unbind('<Button-1>')
                        widget.unbind('<ButtonRelease-1>')
                        widget.unbind('<Double-Button-1>')
                        widget.unbind('<Return>')
                        widget.unbind('<Tab>')
                        widget.unbind('<Down>')
                        widget.unbind('<Up>')
                        widget.unbind('<Button-3>')
                        widget.unbind('<B1-Motion>')
                        widget.unbind('<FocusIn>')
                        widget.unbind('<FocusOut>')
                        # Bloquear eventos de teclado específicos para combobox
                        widget.bind('<Key>', lambda e: 'break')
                        widget.bind('<Button-1>', lambda e: 'break')
                        widget.bind('<ButtonRelease-1>', lambda e: 'break')
                        widget.bind('<Double-Button-1>', lambda e: 'break')
                        widget.bind('<Return>', lambda e: 'break')
                        widget.bind('<Tab>', lambda e: 'break')
                        widget.bind('<Down>', lambda e: 'break')
                        widget.bind('<Up>', lambda e: 'break')
                        widget.bind('<Button-3>', lambda e: 'break')
                        widget.bind('<B1-Motion>', lambda e: 'break')
                        widget.bind('<FocusIn>', lambda e: 'break')
                        widget.bind('<FocusOut>', lambda e: 'break')
                        # Bloquear evento de seleção
                        widget.bind('<<ComboboxSelected>>', lambda e: 'break')
                    elif isinstance(widget, (tk.Checkbutton, tk.Radiobutton)):
                        widget.config(state='disabled')
                        
        except Exception as e:
            print(f"⚠️ Erro na proteção específica: {e}")
    
    def create_section_frame(self, parent, title, padx=10, pady=10):
        """Criar frame de seção com título (compatível com uso anterior).

        Retorna um Frame que o chamador pode `pack` normalmente e adicionar
        widgets filhos dentro. O próprio frame já contém um cabeçalho e
        área de conteúdo, mas para manter compatibilidade, o conteúdo
        também pode ser adicionado diretamente no frame retornado.
        """
        container = tk.Frame(parent, bg='#ffffff', highlightthickness=1, highlightbackground=PALETTE["border"]) 
        # Header
        header = tk.Label(container, text=title, font=FONTS["subtitle"], bg='#ffffff', fg=PALETTE["text_primary"])
        header.pack(anchor="w", padx=12, pady=(12, 6))
        # Inner content holder (optional use)
        content = tk.Frame(container, bg='#ffffff')
        content.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        # For backward compatibility, allow adding directly to container
        container.content = content
        return container
    
    def create_button(self, parent, text, command, variant='primary', **kwargs):
        """Criar botão estilizado (mantém assinatura compatível por kwargs).
        Remove opções não suportadas por ttk.Button (ex.: bg, fg, relief...).
        """
        style = {
            'primary': 'Secondary.TButton',
            'success': 'Secondary.TButton',
            'danger': 'Secondary.TButton',
            'secondary': 'Secondary.TButton',
            'ghost': 'Secondary.TButton',
        }.get(variant, 'Secondary.TButton')

        # Sanitize unsupported ttk options passed from legacy calls
        unsupported = {
            'bg', 'background', 'fg', 'foreground', 'relief', 'bd', 'borderwidth',
            'highlightthickness', 'cursor', 'padx', 'pady'
        }
        safe_kwargs = {k: v for k, v in kwargs.items() if k not in unsupported}

        button = ttk.Button(parent, text=text, command=command, style=style, **safe_kwargs)
        return button
    
    def create_search_frame(self, parent, placeholder="Buscar...", command=None):
        """Criar frame de busca padronizado"""
        search_frame = tk.Frame(parent, bg='#ffffff', highlightthickness=1, highlightbackground=PALETTE["border"]) 
        
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(8, 0), pady=6)
        search_entry.insert(0, placeholder)

        def _on_focus_in(_e):
            if search_entry.get() == placeholder:
                search_entry.delete(0, 'end')
        def _on_focus_out(_e):
            if not search_entry.get().strip():
                search_entry.insert(0, placeholder)
        search_entry.bind('<FocusIn>', _on_focus_in)
        search_entry.bind('<FocusOut>', _on_focus_out)
        
        if command:
            search_btn = self.create_button(search_frame, "Buscar", command, variant='primary')
            search_btn.pack(side="right", padx=8, pady=6)
            search_entry.bind('<Return>', lambda e: command())
        
        return search_frame, search_var
    
    def show_success(self, message):
        """Mostrar mensagem de sucesso"""
        from tkinter import messagebox
        messagebox.showinfo("Sucesso", message)
        
    def show_error(self, message):
        """Mostrar mensagem de erro"""
        from tkinter import messagebox
        messagebox.showerror("Erro", message)
        
    def show_warning(self, message):
        """Mostrar mensagem de aviso"""
        from tkinter import messagebox
        messagebox.showwarning("Aviso", message)
        
    def show_info(self, title, message):
        """Mostrar mensagem informativa"""
        from tkinter import messagebox
        messagebox.showinfo(title, message)
