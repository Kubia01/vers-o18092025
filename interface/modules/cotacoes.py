import tkinter as tk
from tkinter import ttk

from .base_module import BaseModule


class CotacoesModule(BaseModule):
	def setup_ui(self):
		# Importar e instanciar o módulo original de cotações (compra)
		from .cotacoes_backup import CotacoesModule as _CotacoesModule
		self.inner_frame = tk.Frame(self.frame, bg='#f8fafc')
		self.inner_frame.pack(fill='both', expand=True)
		self._compras = _CotacoesModule(self.inner_frame, self.user_id, self.role, self.main_window)
		# Forçar modo Compra e remover campo "Tipo de Cotação"
		try:
			if hasattr(self._compras, 'tipo_cotacao_var'):
				self._compras.tipo_cotacao_var.set('Compra')
				if hasattr(self._compras, 'on_tipo_cotacao_changed'):
					self._compras.on_tipo_cotacao_changed()
			# Remover combobox e label "Tipo de Cotação" de forma segura após a construção do layout
			self.frame.after_idle(self._remove_tipo_cotacao_widgets_safe)
		except Exception as e:
			print(f"CotacoesModule: erro ao configurar modo Compra: {e}")

	def _remove_tipo_cotacao_widgets_safe(self):
		# Coletar todas as combobox e labels candidatas primeiro
		candidates_combo = []
		candidates_label = []
		self._collect_tipo_widgets(self._compras.frame, candidates_combo, candidates_label)
		# Destruir com segurança
		for w in candidates_combo + candidates_label:
			try:
				w.destroy()
			except Exception:
				pass

	def _collect_tipo_widgets(self, root_widget, out_combo_list, out_label_list):
		for child in root_widget.winfo_children():
			try:
				if isinstance(child, ttk.Combobox):
					values = child.cget('values') if 'values' in child.keys() else ()
					vals = tuple(values) if isinstance(values, (list, tuple)) else ()
					if ('Compra' in vals and ('Locação' in vals or 'Locacao' in vals)):
						out_combo_list.append(child)
				# Remover labels que aparentem o rótulo "Tipo de Cotação"
				if isinstance(child, tk.Label):
					text = child.cget('text') if 'text' in child.keys() else ''
					if isinstance(text, str) and ('Tipo de Cotação' in text or 'Tipo de Cotacao' in text):
						out_label_list.append(child)
			except Exception:
				pass
			self._collect_tipo_widgets(child, out_combo_list, out_label_list)

	def handle_event(self, event_type, data=None):
		if hasattr(self, '_compras') and hasattr(self._compras, 'handle_event'):
			self._compras.handle_event(event_type, data)