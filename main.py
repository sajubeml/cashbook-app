"""
main.py - Kivy CashBook Application.
Manages UI architecture, ScreenManager (DashboardScreen, HeaderScreen),
transaction modals, and real-time financial tracking.
"""

import os
import sys
from datetime import datetime

# Configure Kivy environment before importing kivy modules
os.environ["KIVY_NO_ARGS"] = "1"

import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.properties import (
    StringProperty,
    NumericProperty,
    ListProperty,
    ObjectProperty,
    BooleanProperty
)
from kivy.core.window import Window

import database
import pdf_generator

class ModernButton(Button):
    bg_color = ListProperty([0.23, 0.51, 0.96, 1])
    bg_color_down = ListProperty([0.15, 0.35, 0.75, 1])

class OutlineButton(Button):
    border_color = ListProperty([0.28, 0.33, 0.41, 1])
    bg_color = ListProperty([0.12, 0.16, 0.23, 1])
    bg_color_down = ListProperty([0.20, 0.25, 0.33, 1])

from kivy.utils import platform

# Set default window size for desktop testing (mobile portrait aspect ratio)
if platform not in ('android', 'ios'):
    Window.size = (420, 720)

KV_DESIGN = """
#:import hex kivy.utils.get_color_from_hex

<CardLayout@BoxLayout>:
    padding: [14, 12, 14, 12]
    canvas.before:
        Color:
            rgba: hex('#1E293B')
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [12, 12, 12, 12]

<StatCard@BoxLayout>:
    orientation: 'vertical'
    title: ''
    value: '0.00'
    val_color: hex('#F8FAFC')
    padding: [10, 8, 10, 8]
    spacing: 3
    canvas.before:
        Color:
            rgba: hex('#1E293B')
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10, 10, 10, 10]
    Label:
        text: root.title
        font_size: '11sp'
        bold: True
        color: hex('#94A3B8')
        size_hint_y: 0.35
        halign: 'center'
        valign: 'middle'
        text_size: self.size
    Label:
        text: root.value
        font_size: '15sp'
        bold: True
        color: root.val_color
        size_hint_y: 0.65
        halign: 'center'
        valign: 'middle'
        text_size: self.size

<ModernButton>:
    background_color: (0, 0, 0, 0)
    background_normal: ''
    background_down: ''
    bold: True
    font_size: '14sp'
    color: (1, 1, 1, 1)
    canvas.before:
        Color:
            rgba: self.bg_color_down if self.state == 'down' else self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [10, 10, 10, 10]

<OutlineButton>:
    background_color: (0, 0, 0, 0)
    background_normal: ''
    background_down: ''
    font_size: '12sp'
    bold: True
    color: hex('#E2E8F0')
    canvas.before:
        Color:
            rgba: self.bg_color_down if self.state == 'down' else self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8, 8, 8, 8]
        Color:
            rgba: self.border_color
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, 8)
            width: 1


<DashboardScreen>:
    name: 'dashboard'
    canvas.before:
        Color:
            rgba: hex('#0F172A')
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'vertical'
        spacing: 10
        padding: [14, 14, 14, 14]

        # Top App Bar
        BoxLayout:
            size_hint_y: None
            height: '46dp'
            spacing: 8

            BoxLayout:
                orientation: 'vertical'
                Label:
                    text: 'CashBook'
                    font_size: '20sp'
                    bold: True
                    color: hex('#F8FAFC')
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                Label:
                    text: 'Financial Ledger & Cash Tracker'
                    font_size: '10sp'
                    color: hex('#94A3B8')
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size

            OutlineButton:
                text: 'Settings'
                size_hint_x: None
                width: '64dp'
                on_release: root.open_settings_modal()

            OutlineButton:
                text: 'Categories'
                size_hint_x: None
                width: '72dp'
                on_release: app.go_to_categories()

            OutlineButton:
                text: 'Import'
                size_hint_x: None
                width: '62dp'
                border_color: hex('#10B981')
                on_release: root.open_excel_import()

            OutlineButton:
                text: 'PDF'
                size_hint_x: None
                width: '46dp'
                on_release: root.open_pdf_modal()

        # Financial Summary Cards (In, Out, Net)
        BoxLayout:
            size_hint_y: None
            height: '76dp'
            spacing: 8

            StatCard:
                title: 'TOTAL IN'
                value: root.summary_in
                val_color: hex('#10B981')

            StatCard:
                title: 'TOTAL OUT'
                value: root.summary_out
                val_color: hex('#EF4444')

            StatCard:
                title: 'NET BALANCE'
                value: root.summary_net
                val_color: hex('#38BDF8')

        # Filter and Search Row
        BoxLayout:
            size_hint_y: None
            height: '38dp'
            spacing: 8

            TextInput:
                id: search_input
                hint_text: 'Search remark, category...'
                multiline: False
                background_normal: ''
                background_active: ''
                background_color: hex('#1E293B')
                foreground_color: hex('#F8FAFC')
                cursor_color: hex('#38BDF8')
                font_size: '13sp'
                padding: [10, 8, 10, 8]
                on_text: root.filter_transactions(self.text)

            Spinner:
                id: filter_type_spinner
                text: 'All Types'
                values: ['All Types', 'Cash In', 'Cash Out']
                size_hint_x: None
                width: '105dp'
                background_normal: ''
                background_color: hex('#334155')
                color: hex('#F8FAFC')
                font_size: '12sp'
                on_text: root.filter_by_type(self.text)

        # Transaction Ledger List
        BoxLayout:
            orientation: 'vertical'
            spacing: 6

            BoxLayout:
                size_hint_y: None
                height: '24dp'
                Label:
                    text: 'RECENT TRANSACTIONS'
                    font_size: '11sp'
                    bold: True
                    color: hex('#94A3B8')
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.size
                Label:
                    id: count_label
                    text: root.transaction_count_text
                    font_size: '11sp'
                    color: hex('#64748B')
                    halign: 'right'
                    valign: 'middle'
                    text_size: self.size

            ScrollView:
                id: trans_scroll
                do_scroll_x: False
                do_scroll_y: True
                bar_width: '4dp'
                bar_color: hex('#475569')

                BoxLayout:
                    id: trans_container
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: 8
                    padding: [0, 2, 0, 4]

        # Bottom Action Floating Buttons (Cash In / Cash Out)
        BoxLayout:
            size_hint_y: None
            height: '52dp'
            spacing: 12
            padding: [0, 4, 0, 0]

            ModernButton:
                text: '+ CASH IN'
                bg_color: hex('#10B981')
                bg_color_down: hex('#059669')
                font_size: '15sp'
                bold: True
                color: (1, 1, 1, 1)
                on_release: root.open_transaction_modal('IN')

            ModernButton:
                text: '- CASH OUT'
                bg_color: hex('#EF4444')
                bg_color_down: hex('#DC2626')
                font_size: '15sp'
                bold: True
                color: (1, 1, 1, 1)
                on_release: root.open_transaction_modal('OUT')

<HeaderScreen>:
    name: 'headers'
    canvas.before:
        Color:
            rgba: hex('#0F172A')
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        orientation: 'vertical'
        spacing: 12
        padding: [14, 14, 14, 14]

        # Header Bar
        BoxLayout:
            size_hint_y: None
            height: '46dp'
            spacing: 10

            OutlineButton:
                text: '< Back'
                size_hint_x: None
                width: '58dp'
                on_release: app.go_to_dashboard()

            Label:
                text: 'Categories'
                font_size: '17sp'
                bold: True
                color: hex('#F8FAFC')
                halign: 'left'
                valign: 'middle'
                text_size: self.size

            OutlineButton:
                text: 'Clear Data'
                size_hint_x: None
                width: '78dp'
                border_color: hex('#EF4444')
                color: hex('#F87171')
                on_release: root.confirm_clear_data()

            ModernButton:
                text: '+ Add'
                size_hint_x: None
                width: '58dp'
                bg_color: hex('#3B82F6')
                bg_color_down: hex('#2563EB')
                on_release: root.open_add_category_modal()

        # Type Toggle Tabs
        BoxLayout:
            size_hint_y: None
            height: '36dp'
            spacing: 8

            OutlineButton:
                id: tab_all
                text: 'All Categories'
                on_release: root.switch_tab('ALL')
            OutlineButton:
                id: tab_in
                text: 'Cash In'
                on_release: root.switch_tab('IN')
            OutlineButton:
                id: tab_out
                text: 'Cash Out'
                on_release: root.switch_tab('OUT')

        # Categories Scroll List
        ScrollView:
            do_scroll_x: False
            do_scroll_y: True
            bar_width: '4dp'

            BoxLayout:
                id: category_container
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: 6
                padding: [0, 4, 0, 4]
"""

Builder.load_string(KV_DESIGN)


# ==========================================
# TRANSACTION ITEM CARD COMPONENT
# ==========================================
class TransactionCard(BoxLayout):
    """Visual card widget for individual transactions in the ledger."""
    def __init__(self, item, on_delete_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 72
        self.padding = [12, 8, 12, 8]
        self.spacing = 3

        is_in = item["type"] == "IN"
        amt_color = "#10B981" if is_in else "#EF4444"
        sign = "+" if is_in else "-"

        # Top Row: Category badge, date, and amount
        top_row = BoxLayout(size_hint_y=0.55, spacing=6)

        cat_lbl = Label(
            text=f"[{item['category']}]",
            font_size='13sp',
            bold=True,
            color=(0.95, 0.96, 0.98, 1),
            halign='left',
            valign='middle',
            size_hint_x=0.45
        )
        cat_lbl.bind(size=cat_lbl.setter('text_size'))

        date_lbl = Label(
            text=f"{item['date']}  {item['time'][:5]}",
            font_size='10sp',
            color=(0.58, 0.64, 0.72, 1),
            halign='center',
            valign='middle',
            size_hint_x=0.25
        )
        date_lbl.bind(size=date_lbl.setter('text_size'))

        amt_lbl = Label(
            text=f"{sign} {float(item['amount']):,.2f}",
            font_size='14sp',
            bold=True,
            color=kivy.utils.get_color_from_hex(amt_color),
            halign='right',
            valign='middle',
            size_hint_x=0.30
        )
        amt_lbl.bind(size=amt_lbl.setter('text_size'))

        top_row.add_widget(cat_lbl)
        top_row.add_widget(date_lbl)
        top_row.add_widget(amt_lbl)

        # Bottom Row: Payment mode, remarks, running balance, delete button
        bottom_row = BoxLayout(size_hint_y=0.45, spacing=6)

        mode_text = f"Mode: {item['payment_mode']}"
        remarks_text = f" • {item['remarks']}" if item.get('remarks') else ""
        desc_lbl = Label(
            text=f"{mode_text}{remarks_text}",
            font_size='11sp',
            color=(0.7, 0.75, 0.82, 1),
            halign='left',
            valign='middle',
            size_hint_x=0.60
        )
        desc_lbl.bind(size=desc_lbl.setter('text_size'))

        bal_lbl = Label(
            text=f"Bal: {float(item['running_balance']):,.2f}",
            font_size='11sp',
            bold=True,
            color=(0.22, 0.74, 0.97, 1),
            halign='right',
            valign='middle',
            size_hint_x=0.30
        )
        bal_lbl.bind(size=bal_lbl.setter('text_size'))

        del_btn = Button(
            text="✕",
            font_size='11sp',
            bold=True,
            size_hint=(None, 1),
            width=24,
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=(0.9, 0.4, 0.4, 1)
        )
        if on_delete_callback:
            del_btn.bind(on_release=lambda btn: on_delete_callback(item["id"]))

        bottom_row.add_widget(desc_lbl)
        bottom_row.add_widget(bal_lbl)
        bottom_row.add_widget(del_btn)

        self.add_widget(top_row)
        self.add_widget(bottom_row)

        # Background canvas styling
        with self.canvas.before:
            kivy.graphics.Color(*kivy.utils.get_color_from_hex('#1E293B'))
            self.rect = kivy.graphics.RoundedRectangle(pos=self.pos, size=self.size, radius=[8, 8, 8, 8])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


# ==========================================
# TRANSACTION MODAL VIEW
# ==========================================
class TransactionModal(ModalView):
    """Interactive modal view for logging Cash In and Cash Out."""
    def __init__(self, trans_type="IN", on_success_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.92, None)
        self.height = 430
        self.auto_dismiss = False
        self.trans_type = trans_type.upper()
        self.on_success_callback = on_success_callback

        bg_color = '#0F172A'
        title_color = '#10B981' if self.trans_type == 'IN' else '#EF4444'
        title_text = "Add Cash In (+)" if self.trans_type == 'IN' else "Add Cash Out (-)"

        container = BoxLayout(orientation='vertical', padding=[16, 16, 16, 16], spacing=10)

        # Modal Title
        title_lbl = Label(
            text=title_text,
            font_size='18sp',
            bold=True,
            color=kivy.utils.get_color_from_hex(title_color),
            size_hint_y=None,
            height=30
        )
        container.add_widget(title_lbl)

        # Amount Input
        self.amount_input = TextInput(
            hint_text='Amount (e.g. 1500.00)',
            multiline=False,
            input_filter='float',
            background_normal='',
            background_active='',
            background_color=kivy.utils.get_color_from_hex('#1E293B'),
            foreground_color=kivy.utils.get_color_from_hex('#F8FAFC'),
            font_size='15sp',
            size_hint_y=None,
            height=40,
            padding=[10, 10, 10, 10]
        )
        container.add_widget(self.amount_input)

        # Category Spinner
        categories = database.get_categories(self.trans_type)
        cat_names = [c["name"] for c in categories] if categories else ["General"]
        self.cat_spinner = Spinner(
            text=cat_names[0],
            values=cat_names,
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=kivy.utils.get_color_from_hex('#F8FAFC'),
            size_hint_y=None,
            height=40,
            font_size='14sp'
        )
        container.add_widget(self.cat_spinner)

        # Payment Mode Spinner
        payment_modes = ['Cash', 'Online / UPI', 'Bank Transfer', 'Cheque', 'Credit / Debit Card']
        self.mode_spinner = Spinner(
            text=payment_modes[0],
            values=payment_modes,
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=kivy.utils.get_color_from_hex('#F8FAFC'),
            size_hint_y=None,
            height=40,
            font_size='14sp'
        )
        container.add_widget(self.mode_spinner)

        # Date Input
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.date_input = TextInput(
            text=today_str,
            hint_text='Date (YYYY-MM-DD)',
            multiline=False,
            background_normal='',
            background_active='',
            background_color=kivy.utils.get_color_from_hex('#1E293B'),
            foreground_color=kivy.utils.get_color_from_hex('#F8FAFC'),
            font_size='14sp',
            size_hint_y=None,
            height=40,
            padding=[10, 10, 10, 10]
        )
        container.add_widget(self.date_input)

        # Remarks Input
        self.remarks_input = TextInput(
            hint_text='Remarks / Description (optional)',
            multiline=False,
            background_normal='',
            background_active='',
            background_color=kivy.utils.get_color_from_hex('#1E293B'),
            foreground_color=kivy.utils.get_color_from_hex('#F8FAFC'),
            font_size='14sp',
            size_hint_y=None,
            height=40,
            padding=[10, 10, 10, 10]
        )
        container.add_widget(self.remarks_input)

        # Error label
        self.err_lbl = Label(
            text='',
            color=kivy.utils.get_color_from_hex('#EF4444'),
            font_size='12sp',
            size_hint_y=None,
            height=20
        )
        container.add_widget(self.err_lbl)

        # Buttons (Cancel & Save)
        btn_box = BoxLayout(spacing=10, size_hint_y=None, height=44)
        cancel_btn = Button(
            text='Cancel',
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=kivy.utils.get_color_from_hex('#E2E8F0'),
            font_size='14sp',
            bold=True
        )
        cancel_btn.bind(on_release=self.dismiss)

        save_btn = Button(
            text='Save Transaction',
            background_normal='',
            background_color=kivy.utils.get_color_from_hex(title_color),
            color=kivy.utils.get_color_from_hex('#FFFFFF'),
            font_size='14sp',
            bold=True
        )
        save_btn.bind(on_release=self.save_transaction)

        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(save_btn)
        container.add_widget(btn_box)

        self.add_widget(container)

    def save_transaction(self, *args):
        amt_text = self.amount_input.text.strip()
        if not amt_text:
            self.err_lbl.text = "Please enter a valid amount."
            return

        try:
            amount = float(amt_text)
            if amount <= 0:
                self.err_lbl.text = "Amount must be greater than zero."
                return
        except ValueError:
            self.err_lbl.text = "Invalid amount format."
            return

        date_val = self.date_input.text.strip() or datetime.now().strftime("%Y-%m-%d")
        time_val = datetime.now().strftime("%H:%M:%S")
        category_val = self.cat_spinner.text
        mode_val = self.mode_spinner.text
        remarks_val = self.remarks_input.text.strip()

        try:
            database.add_transaction(
                date_str=date_val,
                time_str=time_val,
                category=category_val,
                trans_type=self.trans_type,
                amount=amount,
                payment_mode=mode_val,
                remarks=remarks_val
            )
            self.dismiss()
            if self.on_success_callback:
                self.on_success_callback()
        except Exception as e:
            self.err_lbl.text = str(e)


# ==========================================
# MONTHLY PDF EXPORT MODAL VIEW
# ==========================================
class PDFExportModal(ModalView):
    """Modal for selecting year and month to generate and export a ledger statement."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.90, None)
        self.height = 320
        self.auto_dismiss = True

        container = BoxLayout(orientation='vertical', padding=[16, 16, 16, 16], spacing=12)

        title_lbl = Label(
            text="Export Monthly PDF Statement",
            font_size='16sp',
            bold=True,
            color=kivy.utils.get_color_from_hex('#38BDF8'),
            size_hint_y=None,
            height=28
        )
        container.add_widget(title_lbl)

        # Month Selector
        now = datetime.now()
        month_names = [
            "01 - January", "02 - February", "03 - March", "04 - April",
            "05 - May", "06 - June", "07 - July", "08 - August",
            "09 - September", "10 - October", "11 - November", "12 - December"
        ]
        self.month_spinner = Spinner(
            text=month_names[now.month - 1],
            values=month_names,
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=kivy.utils.get_color_from_hex('#F8FAFC'),
            size_hint_y=None,
            height=40,
            font_size='14sp'
        )
        container.add_widget(self.month_spinner)

        # Year Input
        self.year_input = TextInput(
            text=str(now.year),
            hint_text='Year (YYYY)',
            multiline=False,
            input_filter='int',
            background_normal='',
            background_active='',
            background_color=kivy.utils.get_color_from_hex('#1E293B'),
            foreground_color=kivy.utils.get_color_from_hex('#F8FAFC'),
            font_size='14sp',
            size_hint_y=None,
            height=40,
            padding=[10, 10, 10, 10]
        )
        container.add_widget(self.year_input)

        # Status Label
        self.status_lbl = Label(
            text='',
            color=kivy.utils.get_color_from_hex('#10B981'),
            font_size='11sp',
            size_hint_y=None,
            height=34,
            halign='center'
        )
        self.status_lbl.bind(size=self.status_lbl.setter('text_size'))
        container.add_widget(self.status_lbl)

        # Actions
        btn_box = BoxLayout(spacing=10, size_hint_y=None, height=44)
        close_btn = Button(
            text='Close',
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=kivy.utils.get_color_from_hex('#E2E8F0'),
            font_size='14sp',
            bold=True
        )
        close_btn.bind(on_release=self.dismiss)

        gen_btn = Button(
            text='Generate PDF',
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#2563EB'),
            color=kivy.utils.get_color_from_hex('#FFFFFF'),
            font_size='14sp',
            bold=True
        )
        gen_btn.bind(on_release=self.generate_pdf)

        btn_box.add_widget(close_btn)
        btn_box.add_widget(gen_btn)
        container.add_widget(btn_box)

        self.add_widget(container)

    def generate_pdf(self, *args):
        try:
            month_idx = int(self.month_spinner.text.split(" - ")[0])
            year_val = int(self.year_input.text.strip())
            pdf_path = pdf_generator.generate_monthly_pdf(year_val, month_idx)
            self.status_lbl.color = kivy.utils.get_color_from_hex('#10B981')
            self.status_lbl.text = f"Saved: {os.path.basename(pdf_path)}"
            
            # Auto-open PDF
            try:
                from kivy.utils import platform
                if platform == 'win':
                    os.startfile(pdf_path)
                elif platform == 'macosx':
                    import subprocess
                    subprocess.call(['open', pdf_path])
                elif platform == 'linux':
                    import subprocess
                    subprocess.call(['xdg-open', pdf_path])
                else:
                    import webbrowser
                    webbrowser.open(f"file://{pdf_path}")
            except Exception as e:
                print(f"Could not open PDF automatically: {e}")
                
        except Exception as e:
            self.status_lbl.color = kivy.utils.get_color_from_hex('#EF4444')
            self.status_lbl.text = f"Error: {str(e)}"


# ==========================================
# SETTINGS & MULTIPLE BOOKS MODALS
# ==========================================
class SettingsModal(ModalView):
    """Modal for managing multiple books/ledgers."""
    def __init__(self, on_switch_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.88, None)
        self.height = 280
        self.auto_dismiss = True
        self.on_switch_callback = on_switch_callback

        container = BoxLayout(orientation='vertical', padding=[16, 16, 16, 16], spacing=12)

        title_lbl = Label(
            text="Settings / Multiple Books",
            font_size='16sp',
            bold=True,
            color=kivy.utils.get_color_from_hex('#38BDF8'),
            size_hint_y=None,
            height=28
        )
        container.add_widget(title_lbl)

        # Book Selector
        books = database.get_all_books()
        active = database.get_active_book()
        self.book_spinner = Spinner(
            text=active,
            values=books,
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=kivy.utils.get_color_from_hex('#F8FAFC'),
            size_hint_y=None,
            height=44,
            font_size='14sp'
        )
        container.add_widget(self.book_spinner)

        # Actions
        btn_box = BoxLayout(spacing=10, size_hint_y=None, height=44)
        add_btn = OutlineButton(
            text='New Book',
            border_color=kivy.utils.get_color_from_hex('#10B981'),
            color=kivy.utils.get_color_from_hex('#10B981')
        )
        add_btn.bind(on_release=self.open_add_book)

        switch_btn = ModernButton(
            text='Switch Book',
            bg_color=kivy.utils.get_color_from_hex('#2563EB')
        )
        switch_btn.bind(on_release=self.switch_book)

        btn_box.add_widget(add_btn)
        btn_box.add_widget(switch_btn)
        container.add_widget(btn_box)

        # Close
        close_btn = Button(
            text='Close',
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=kivy.utils.get_color_from_hex('#E2E8F0'),
            size_hint_y=None,
            height=40,
            font_size='14sp',
            bold=True
        )
        close_btn.bind(on_release=self.dismiss)
        container.add_widget(close_btn)

        self.add_widget(container)

    def switch_book(self, *args):
        selected = self.book_spinner.text
        database.set_active_book(selected)
        if self.on_switch_callback:
            self.on_switch_callback()
        self.dismiss()

    def open_add_book(self, *args):
        self.dismiss()
        modal = AddBookModal(on_success_callback=self.on_switch_callback)
        modal.open()


class AddBookModal(ModalView):
    """Modal for creating a new book."""
    def __init__(self, on_success_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.88, None)
        self.height = 230
        self.auto_dismiss = False
        self.on_success_callback = on_success_callback

        container = BoxLayout(orientation='vertical', padding=[16, 16, 16, 16], spacing=10)

        title_lbl = Label(
            text="Create New Book",
            font_size='16sp',
            bold=True,
            color=kivy.utils.get_color_from_hex('#10B981'),
            size_hint_y=None,
            height=26
        )
        container.add_widget(title_lbl)

        self.name_input = TextInput(
            hint_text='Book Name (e.g. Business)',
            multiline=False,
            background_normal='',
            background_active='',
            background_color=kivy.utils.get_color_from_hex('#1E293B'),
            foreground_color=kivy.utils.get_color_from_hex('#F8FAFC'),
            font_size='14sp',
            size_hint_y=None,
            height=44,
            padding=[10, 12, 10, 10]
        )
        container.add_widget(self.name_input)

        self.err_lbl = Label(text='', color=kivy.utils.get_color_from_hex('#EF4444'), font_size='12sp', size_hint_y=None, height=20)
        container.add_widget(self.err_lbl)

        btn_box = BoxLayout(spacing=10, size_hint_y=None, height=44)
        cancel_btn = Button(
            text='Cancel',
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            font_size='14sp', bold=True
        )
        cancel_btn.bind(on_release=self.dismiss)

        save_btn = Button(
            text='Create',
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#10B981'),
            font_size='14sp', bold=True
        )
        save_btn.bind(on_release=self.save_book)

        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(save_btn)
        container.add_widget(btn_box)
        self.add_widget(container)

    def save_book(self, *args):
        name = self.name_input.text.strip()
        if not name:
            self.err_lbl.text = "Please enter a book name."
            return
        
        safe_name = "".join([c for c in name if c.isalnum() or c in " _-"])
        if not safe_name:
            self.err_lbl.text = "Invalid name."
            return

        database.create_book(safe_name)
        if self.on_success_callback:
            self.on_success_callback()
        self.dismiss()


# ==========================================
# ADD CATEGORY MODAL VIEW
# ==========================================
class AddCategoryModal(ModalView):
    """Modal for creating new custom category headers."""
    def __init__(self, on_success_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.88, None)
        self.height = 290
        self.auto_dismiss = False
        self.on_success_callback = on_success_callback

        container = BoxLayout(orientation='vertical', padding=[16, 16, 16, 16], spacing=10)

        title_lbl = Label(
            text="Add Category Header",
            font_size='16sp',
            bold=True,
            color=kivy.utils.get_color_from_hex('#38BDF8'),
            size_hint_y=None,
            height=26
        )
        container.add_widget(title_lbl)

        self.name_input = TextInput(
            hint_text='Category Name (e.g. Freelance)',
            multiline=False,
            background_normal='',
            background_active='',
            background_color=kivy.utils.get_color_from_hex('#1E293B'),
            foreground_color=kivy.utils.get_color_from_hex('#F8FAFC'),
            font_size='14sp',
            size_hint_y=None,
            height=40,
            padding=[10, 10, 10, 10]
        )
        container.add_widget(self.name_input)

        self.type_spinner = Spinner(
            text='Cash Out (Expense)',
            values=['Cash Out (Expense)', 'Cash In (Income)', 'Both (In & Out)'],
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=kivy.utils.get_color_from_hex('#F8FAFC'),
            size_hint_y=None,
            height=40,
            font_size='14sp'
        )
        container.add_widget(self.type_spinner)

        self.err_lbl = Label(
            text='',
            color=kivy.utils.get_color_from_hex('#EF4444'),
            font_size='12sp',
            size_hint_y=None,
            height=20
        )
        container.add_widget(self.err_lbl)

        btn_box = BoxLayout(spacing=10, size_hint_y=None, height=44)
        cancel_btn = Button(
            text='Cancel',
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#334155'),
            color=kivy.utils.get_color_from_hex('#E2E8F0'),
            font_size='14sp',
            bold=True
        )
        cancel_btn.bind(on_release=self.dismiss)

        save_btn = Button(
            text='Save Category',
            background_normal='',
            background_color=kivy.utils.get_color_from_hex('#10B981'),
            color=kivy.utils.get_color_from_hex('#FFFFFF'),
            font_size='14sp',
            bold=True
        )
        save_btn.bind(on_release=self.save_category)

        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(save_btn)
        container.add_widget(btn_box)

        self.add_widget(container)

    def save_category(self, *args):
        name = self.name_input.text.strip()
        if not name:
            self.err_lbl.text = "Please enter category name."
            return

        choice = self.type_spinner.text
        if "Income" in choice:
            cat_type = "IN"
        elif "Expense" in choice:
            cat_type = "OUT"
        else:
            cat_type = "BOTH"

        try:
            database.add_category(name, cat_type)
            self.dismiss()
            if self.on_success_callback:
                self.on_success_callback()
        except Exception as e:
            self.err_lbl.text = str(e)


class NoticeModal(ModalView):
    """Clean modern notification alert modal."""
    def __init__(self, message="", **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.85, None)
        self.height = 180
        self.auto_dismiss = True
        self.background_color = [0, 0, 0, 0.6]

        box = BoxLayout(orientation='vertical', padding=18, spacing=14)
        with box.canvas.before:
            kivy.graphics.Color(*kivy.utils.get_color_from_hex('#1E293B'))
            self.bg_rect = kivy.graphics.RoundedRectangle(pos=box.pos, size=box.size, radius=[14, 14, 14, 14])
        box.bind(pos=lambda obj, val: setattr(self.bg_rect, 'pos', val))
        box.bind(size=lambda obj, val: setattr(self.bg_rect, 'size', val))

        lbl = Label(
            text=message,
            font_size='14sp',
            bold=True,
            color=kivy.utils.get_color_from_hex('#F8FAFC'),
            halign='center',
            valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))
        box.add_widget(lbl)

        btn = ModernButton(text='OK', size_hint_y=None, height=40, bg_color=kivy.utils.get_color_from_hex('#3B82F6'))
        btn.bind(on_release=self.dismiss)
        box.add_widget(btn)
        self.add_widget(box)


class ConfirmModal(ModalView):
    """Confirmation modal for actions like clearing all data."""
    def __init__(self, title="Confirmation", message="", on_confirm_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.85, None)
        self.height = 200
        self.auto_dismiss = False
        self.background_color = [0, 0, 0, 0.65]

        box = BoxLayout(orientation='vertical', padding=18, spacing=12)
        with box.canvas.before:
            kivy.graphics.Color(*kivy.utils.get_color_from_hex('#1E293B'))
            self.bg_rect = kivy.graphics.RoundedRectangle(pos=box.pos, size=box.size, radius=[14, 14, 14, 14])
        box.bind(pos=lambda obj, val: setattr(self.bg_rect, 'pos', val))
        box.bind(size=lambda obj, val: setattr(self.bg_rect, 'size', val))

        t_lbl = Label(
            text=title,
            font_size='16sp',
            bold=True,
            color=kivy.utils.get_color_from_hex('#EF4444'),
            size_hint_y=None,
            height=26
        )
        box.add_widget(t_lbl)

        m_lbl = Label(
            text=message,
            font_size='13sp',
            color=kivy.utils.get_color_from_hex('#CBD5E1'),
            halign='center',
            valign='middle'
        )
        m_lbl.bind(size=m_lbl.setter('text_size'))
        box.add_widget(m_lbl)

        btn_row = BoxLayout(spacing=10, size_hint_y=None, height=42)
        cancel_btn = OutlineButton(text='Cancel')
        cancel_btn.bind(on_release=self.dismiss)

        def handle_confirm(*args):
            self.dismiss()
            if on_confirm_callback:
                on_confirm_callback()

        confirm_btn = ModernButton(
            text='Clear All Data',
            bg_color=kivy.utils.get_color_from_hex('#EF4444'),
            bg_color_down=kivy.utils.get_color_from_hex('#DC2626')
        )
        confirm_btn.bind(on_release=handle_confirm)

        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(confirm_btn)
        box.add_widget(btn_row)
        self.add_widget(box)


# ==========================================
# SCREENS IMPLEMENTATION
# ==========================================
class DashboardScreen(Screen):
    """Main cashbook overview dashboard screen."""
    summary_in = StringProperty("0.00")
    summary_out = StringProperty("0.00")
    summary_net = StringProperty("0.00")
    transaction_count_text = StringProperty("0 records")

    def on_enter(self, *args):
        self.refresh_data()

    def refresh_data(self):
        """Re-query database for summary statistics and transactions."""
        summary = database.get_financial_summary()
        self.summary_in = f"+ {summary['total_in']:,.2f}"
        self.summary_out = f"- {summary['total_out']:,.2f}"
        self.summary_net = f"{summary['net_balance']:,.2f}"

        self.apply_current_filters()

    def apply_current_filters(self):
        search_kw = self.ids.search_input.text.strip() if hasattr(self.ids, 'search_input') else ""
        type_filter = self.ids.filter_type_spinner.text if hasattr(self.ids, 'filter_type_spinner') else "All Types"

        t_type = None
        if type_filter == "Cash In":
            t_type = "IN"
        elif type_filter == "Cash Out":
            t_type = "OUT"

        transactions = database.get_transactions(trans_type=t_type, search=search_kw)
        self.populate_transactions(transactions)

    def populate_transactions(self, transactions):
        container = self.ids.trans_container
        container.clear_widgets()

        self.transaction_count_text = f"{len(transactions)} record(s)"

        if not transactions:
            empty_lbl = Label(
                text="No transactions found.\nTap '+ CASH IN' or '- CASH OUT' to add an entry.",
                color=kivy.utils.get_color_from_hex('#64748B'),
                font_size='13sp',
                size_hint_y=None,
                height=120,
                halign='center'
            )
            empty_lbl.bind(size=empty_lbl.setter('text_size'))
            container.add_widget(empty_lbl)
            return

        for t in transactions:
            card = TransactionCard(t, on_delete_callback=self.delete_item)
            container.add_widget(card)

    def delete_item(self, item_id):
        database.delete_transaction(item_id)
        self.refresh_data()

    def filter_transactions(self, text):
        self.apply_current_filters()

    def filter_by_type(self, text):
        self.apply_current_filters()

    def open_transaction_modal(self, trans_type):
        modal = TransactionModal(trans_type=trans_type, on_success_callback=self.refresh_data)
        modal.open()

    def open_pdf_modal(self):
        modal = PDFExportModal()
        modal.open()

    def open_settings_modal(self):
        modal = SettingsModal(on_switch_callback=self.refresh_data)
        modal.open()

    def open_excel_import(self):
        """Open native file dialog to import transactions from Excel or CSV."""
        from kivy.utils import platform
        if platform == 'android':
            self.show_notice("Import XL is currently a Desktop-only feature.")
            return
            
        import threading
        def do_import():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                file_path = filedialog.askopenfilename(
                    title="Select Excel or CSV File to Import",
                    filetypes=[
                        ("Excel & CSV Files", "*.xlsx;*.xls;*.csv"),
                        ("Excel Workbook (*.xlsx)", "*.xlsx"),
                        ("Excel 97-2003 (*.xls)", "*.xls"),
                        ("CSV Files (*.csv)", "*.csv"),
                        ("All Files", "*.*")
                    ]
                )
                root.destroy()
                if not file_path:
                    return

                res = database.import_transactions_from_excel(file_path)
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: self.on_import_completed(res, file_path))
            except Exception as e:
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: self.show_notice(f"Import Error: {str(e)}"))

        threading.Thread(target=do_import, daemon=True).start()

    def on_import_completed(self, res, file_path):
        self.refresh_data()
        filename = os.path.basename(file_path)
        if res.get("success"):
            self.show_notice(f"Successfully imported {res.get('count', 0)} transactions from '{filename}'!")
        else:
            self.show_notice(res.get("message", "Import failed."))

    def show_notice(self, message):
        modal = NoticeModal(message=message)
        modal.open()


class HeaderScreen(Screen):
    """Category headers management screen."""
    current_tab = "ALL"

    def on_enter(self, *args):
        self.refresh_categories()

    def switch_tab(self, tab_type):
        self.current_tab = tab_type
        self.refresh_categories()

    def refresh_categories(self):
        container = self.ids.category_container
        container.clear_widgets()

        cat_filter = None if self.current_tab == "ALL" else self.current_tab
        categories = database.get_categories(category_type=cat_filter)

        if not categories:
            lbl = Label(
                text="No categories found.",
                color=kivy.utils.get_color_from_hex('#64748B'),
                size_hint_y=None,
                height=80
            )
            container.add_widget(lbl)
            return

        for c in categories:
            row = BoxLayout(size_hint_y=None, height=44, spacing=8, padding=[10, 4, 10, 4])

            # Tag color
            tag_color = '#10B981' if c['type'] == 'IN' else ('#EF4444' if c['type'] == 'OUT' else '#38BDF8')
            type_tag = f"[{c['type']}]"

            lbl_name = Label(
                text=f"{c['name']}  [color={tag_color}]{type_tag}[/color]",
                markup=True,
                font_size='14sp',
                color=kivy.utils.get_color_from_hex('#F8FAFC'),
                halign='left',
                valign='middle',
                size_hint_x=0.85
            )
            lbl_name.bind(size=lbl_name.setter('text_size'))

            del_btn = Button(
                text="Delete",
                font_size='12sp',
                bold=True,
                size_hint=(None, 1),
                width=65,
                background_normal='',
                background_color=kivy.utils.get_color_from_hex('#EF4444'),
                color=(1, 1, 1, 1)
            )
            del_btn.bind(on_release=lambda b, cid=c['id']: self.delete_category_item(cid))

            row.add_widget(lbl_name)
            row.add_widget(del_btn)

            with row.canvas.before:
                kivy.graphics.Color(*kivy.utils.get_color_from_hex('#1E293B'))
                r = kivy.graphics.RoundedRectangle(pos=row.pos, size=row.size, radius=[8, 8, 8, 8])
            row.bind(pos=lambda obj, val, rect=r: setattr(rect, 'pos', val))
            row.bind(size=lambda obj, val, rect=r: setattr(rect, 'size', val))

            container.add_widget(row)

    def delete_category_item(self, category_id):
        database.delete_category(category_id)
        self.refresh_categories()

    def open_add_category_modal(self):
        modal = AddCategoryModal(on_success_callback=self.refresh_categories)
        modal.open()

    def confirm_clear_data(self):
        def do_clear():
            database.clear_all_transactions()
            app = App.get_running_app()
            if app and hasattr(app, 'dashboard_screen'):
                app.dashboard_screen.refresh_data()
            modal = NoticeModal(message="All transactions have been cleared.\nDatabase is reset for fresh entry!")
            modal.open()

        modal = ConfirmModal(
            title="Clear All Transactions?",
            message="This will delete all existing income & expense entries\nand reset your running balance to zero.\n\nCategory headers will be preserved.",
            on_confirm_callback=do_clear
        )
        modal.open()


# ==========================================
# MAIN APPLICATION
# ==========================================
class CashBookApp(App):
    """Main CashBook Kivy application instance."""
    def build(self):
        self.title = "CashBook - Cash Flow & Ledger"
        database.init_db()

        self.sm = ScreenManager(transition=SlideTransition(duration=0.2))
        self.dashboard_screen = DashboardScreen(name='dashboard')
        self.header_screen = HeaderScreen(name='headers')

        self.sm.add_widget(self.dashboard_screen)
        self.sm.add_widget(self.header_screen)

        # Hook hardware back button (Android / Escape)
        Window.bind(on_keyboard=self.on_key_down)

        # Request Android runtime storage permissions if applicable
        self.request_android_permissions()

        return self.sm

    def request_android_permissions(self):
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE
                ])
            except Exception as e:
                print(f"[Android Permissions] Notice: {e}")

    def on_key_down(self, window, key, *args):
        # Key 27 is Escape / Android Back button
        if key == 27:
            if self.sm.current != 'dashboard':
                self.go_to_dashboard()
                return True
        return False

    def go_to_categories(self):
        self.sm.transition.direction = 'left'
        self.sm.current = 'headers'

    def go_to_dashboard(self):
        self.sm.transition.direction = 'right'
        self.sm.current = 'dashboard'


if __name__ == "__main__":
    CashBookApp().run()
