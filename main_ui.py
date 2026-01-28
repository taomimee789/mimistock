import sqlite3
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QFormLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHBoxLayout, QComboBox, QDialog, QLayout, QSplitter,
    QHeaderView, QScrollArea
)
from PyQt5.QtGui import QFont, QColor, QIntValidator
from PyQt5.QtCore import QTimer, Qt, QUrl
from datetime import datetime
import pytz
from StockWindow import StockWindow
from database import init_db, connect_db
from product_editor import ProductEditorDialog
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from SellWindow import SellWindow
from PyQt5.QtWidgets import QCompleter, QDesktopWidget, QSizePolicy
import winsound
import threading
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# หมายเหตุ: ห้าม init DB ตอน import โมดูล (จะทำใน main.py/ตอนรันโปรแกรม)

CREDENTIALS_FILE = "gen-lang-client-0301147324-8f1c9d568355.json"
SHEET_ID = "1T-wLeIpBrm75PfV7O7eOUJY5dxlUPp_AbCSMNuYyFZ4"
SHEET_NAME = "ฐานข้อมูล"

# ธีมสี
THEME_DARK = """
    QWidget { background-color: #1A1D2D; color: #A5D8FF; }
    QLabel, QLineEdit, QPushButton, QTableWidget { font-size: 14px; }
    QLineEdit { background-color: #2B2F44; border: 2px solid #5E92C2; color: #A5D8FF; padding: 8px; border-radius: 5px; }
    QPushButton { background-color: #5E92C2; color: #1A1D2D; font-weight: bold; padding: 10px; border-radius: 8px; box-shadow: 2px 2px 5px #000000; }
    QPushButton:hover { background-color: #A5D8FF; }
    QTableWidget { background-color: #2B2F44; border: 2px solid #5E92C2; color: #A5D8FF; }
"""

THEME_NEON = """
    QWidget { background-color: #23213D; color: #D4A5FF; }
    QLabel, QLineEdit, QPushButton, QTableWidget { font-size: 14px; }
    QLineEdit { background-color: #3A3753; border: 2px solid #9C6BFF; color: #D4A5FF; padding: 8px; border-radius: 5px; }
    QPushButton { background-color: #9C6BFF; color: #23213D; font-weight: bold; padding: 10px; border-radius: 8px; box-shadow: 2px 2px 5px #000000; }
    QPushButton:hover { background-color: #D4A5FF; }
    QTableWidget { background-color: #3A3753; border: 2px solid #9C6BFF; color: #D4A5FF; }
"""


class SQLiteApp(QWidget):
    def __init__(self):
        super().__init__()
        self.theme = "dark"
        self.initUI()

    def sync_data_to_sheets(self):
        """ซิงค์ข้อมูลจาก SQLite ไป Google Sheets เมื่อกดปุ่ม"""
        print("🟡 กดปุ่มซิงค์แล้ว! เริ่มซิงค์ข้อมูลไป Google Sheets...")  # ✅ Debug Log
        try:
            sync_sqlite_to_sheets()  # ✅ เรียกฟังก์ชันซิงค์ข้อมูล
            print("✅ ซิงค์เสร็จแล้ว! แสดงข้อความแจ้งเตือน...")
            QMessageBox.information(self, "✅ สำเร็จ", "ซิงค์ข้อมูลไปยัง Google Sheets เรียบร้อยแล้ว!")
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดขณะซิงค์: {e}")
            QMessageBox.critical(self, "❌ ข้อผิดพลาด", f"เกิดข้อผิดพลาด: {e}")

    def initUI(self):
        self.setWindowTitle("🚀 SQLite Manager - Real-time Update")

        # ✅ ใช้ขนาดเต็มจอ
        screen = QDesktopWidget().screenGeometry()
        width, height = screen.width(), screen.height()
        self.setGeometry(0, 0, width, height)

        self.setStyleSheet(THEME_DARK)

        layout = QVBoxLayout()  # ✅ Layout หลัก

        # ✅ Layout สำหรับปุ่มซิงค์ (อยู่ฝั่งซ้าย)
        sync_layout = QHBoxLayout()
        sync_layout.setAlignment(Qt.AlignLeft)

        self.sync_btn = QPushButton("🔄 ซิงค์ไป Google Sheets", self)
        self.sync_btn.setFont(QFont("Arial", 12))
        self.sync_btn.clicked.connect(self.sync_data_to_sheets)  # ✅ เชื่อมปุ่มกับฟังก์ชันซิงค์
        sync_layout.addWidget(self.sync_btn)

        #        self.auto_reset_cod()  # ✅ เรียกให้รีเซ็ตค่า COD อัตโนมัติ

        # ✅ Layout สำหรับปุ่มจัดการสินค้า (อยู่ฝั่งขวา)
        stock_sell_layout = QHBoxLayout()
        stock_sell_layout.setAlignment(Qt.AlignRight)

        self.sell_btn = QPushButton("🛒 ขายสินค้า", self)
        self.sell_btn.setFont(QFont("Arial", 12))
        self.sell_btn.clicked.connect(self.open_sell_window)
        stock_sell_layout.addWidget(self.sell_btn)

        self.import_orders_btn = QPushButton("📥 นำเข้าออเดอร์", self)
        self.import_orders_btn.setFont(QFont("Arial", 12))
        self.import_orders_btn.clicked.connect(self.show_import_dialog)
        stock_sell_layout.addWidget(self.import_orders_btn)

        self.stock_btn = QPushButton("📦 จัดการสต็อกสินค้า")
        self.stock_btn.setFont(QFont("Arial", 12))
        self.stock_btn.clicked.connect(self.open_stock_window)
        stock_sell_layout.addWidget(self.stock_btn)

        # ✅ ปุ่มเพิ่ม/แก้ไขสินค้า (แก้ข้อมูลใน bot_system.db ตาราง product_categories)
        self.product_editor_btn = QPushButton("📝 เพิ่ม/แก้สินค้า")
        self.product_editor_btn.setFont(QFont("Arial", 12))
        self.product_editor_btn.clicked.connect(self.open_product_editor)
        stock_sell_layout.addWidget(self.product_editor_btn)

        # ✅ รวม Layout ซิงค์ (ซ้าย) และ Layout สินค้า (ขวา) ให้อยู่ในแถวเดียวกัน
        top_layout = QHBoxLayout()
        top_layout.addLayout(sync_layout)  # ✅ ปุ่มซิงค์ (ซ้าย)
        top_layout.addStretch()  # ✅ ให้ซิงค์ชิดซ้าย และสินค้าไปชิดขวา
        top_layout.addLayout(stock_sell_layout)  # ✅ ปุ่มสินค้า (ขวา)

        layout.addLayout(top_layout)  # ✅ เพิ่มทั้งหมดเข้า Layout หลัก

        self.setLayout(layout)  # ✅ กำหนด Layout ให้ Widget นี้ใช้

        stock_sell_layout.setSizeConstraint(QLayout.SetMinimumSize)  # ✅ ปรับขนาดอัตโนมัติ
        layout.addLayout(stock_sell_layout)

        form_layout = QFormLayout()
        font = QFont("Arial", 12)

        self.id_input = self.create_input("ID:", form_layout, font)
        self.password_input = self.create_input("Password:", form_layout, font, True)
        self.f2a_input = self.create_input("F2A:", form_layout, font)

        self.product_input = QComboBox()
        self.load_product_categories()
        self.product_input.setFixedHeight(30)
        form_layout.addRow("สินค้า:", self.product_input)

        self.unit_per_item_input = QLineEdit()
        self.unit_per_item_input.setPlaceholderText("ใส่จำนวนหน่วยต่อรายการ (เช่น 2)")
        self.unit_per_item_input.setValidator(QIntValidator(1, 9999))
        form_layout.addRow("หน่วยต่อรายการ:", self.unit_per_item_input)

        self.shop_input = self.create_input("ร้านค้า:", form_layout, font)
        self.load_shop_history()
        self.price_input = self.create_input("ราคาสินค้า:", form_layout, font)
        self.load_price_history()
        self.price_input.textChanged.connect(self.format_price_input)

        self.payment_input = QComboBox()
        self.payment_input.addItems(["COD", "Prompt Pay", "Truemoney Wallet"])
        self.payment_input.setFixedHeight(30)
        form_layout.addRow(QLabel("ชำระผ่าน:"), self.payment_input)

        self.tracking_input = QLineEdit()
        self.tracking_input.setFont(font)
        form_layout.addRow(QLabel("เลขพัสดุ:"), self.tracking_input)

        self.shipping_label = QLabel("ขนส่ง: (อัปเดตอัตโนมัติ)")
        self.shipping_input = QLabel("-")
        form_layout.addRow(self.shipping_label, self.shipping_input)

        self.status_label = QLabel("สถานะจัดส่ง: (อัปเดตอัตโนมัติ)")
        self.status_input = QLabel("-")
        form_layout.addRow(self.status_label, self.status_input)

        layout.addLayout(form_layout)

        self.submit_btn = QPushButton("📥 บันทึกข้อมูล", self)
        self.submit_btn.setFont(font)
        self.submit_btn.clicked.connect(self.add_data)

        # ✅ ปุ่มอัปเดตสถานะ, เปลี่ยนธีม และ บันทึกข้อมูล (เรียงกันในบรรทัดเดียว)
        self.update_status_btn = QPushButton("📦 อัปเดตสถานะพัสดุ", self)
        self.update_status_btn.setFont(font)
        self.update_status_btn.clicked.connect(self.update_tracking_ui)

        self.theme_btn = QPushButton("🌓 เปลี่ยนธีม", self)
        self.theme_btn.setFont(font)
        self.theme_btn.clicked.connect(self.toggle_theme)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.submit_btn)  # ✅ ใส่ปุ่มบันทึกในบรรทัดเดียวกัน
        btn_layout.addWidget(self.update_status_btn)
        btn_layout.addWidget(self.theme_btn)

        layout.addLayout(btn_layout)  # ✅ ใส่ Layout ที่มี 3 ปุ่มเข้าไป

        # ✅ ปุ่มค้นหา
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 ค้นหาสินค้า ร้านค้า เลขพัสดุ ฯลฯ")

        self.start_search_btn = QPushButton("🔍 เริ่มค้นหา")
        self.start_search_btn.setFont(font)
        self.start_search_btn.clicked.connect(self.search_data)

        self.stop_search_btn = QPushButton("🛑 หยุดค้นหา")
        self.stop_search_btn.setFont(font)
        self.stop_search_btn.clicked.connect(self.stop_search)
        self.stop_search_btn.setEnabled(False)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.start_search_btn)
        search_layout.addWidget(self.stop_search_btn)

        layout.addLayout(search_layout)

        # ✅ แสดงยอด COD รายวัน + จำนวนพัสดุในบรรทัดเดียวกัน (จัดกลาง-ขวา)
        summary_layout = QHBoxLayout()
        self.cod_expense_label = QLabel("💰 ค่าใช้จ่าย COD วันนี้: ฿0")
        self.cod_expense_label.setFont(QFont("Arial", 12))

        self.status_summary_label = QLabel("📦 รอจัดส่ง: 0 | 🚚 อยู่ระหว่างการจัดส่ง: 0 | ✅ จัดส่งสำเร็จ: 0")
        self.status_summary_label.setFont(QFont("Arial", 12))

        summary_layout.addWidget(self.cod_expense_label)  # ✅ แสดง "ค่าใช้จ่าย COD วันนี้"
        summary_layout.addStretch()  # ✅ ดันให้ไปชิดขวา
        summary_layout.addWidget(self.status_summary_label)  # ✅ แสดง "สถานะพัสดุ"

        layout.addLayout(summary_layout)  # ✅ ใส่เข้า Layout หลัก

        # ✅ กลุ่มปุ่มล้างข้อมูล & รีเซ็ต COD (อยู่ในแถวเดียวกัน)
        clear_cod_layout = QHBoxLayout()

        self.clear_shipped_btn = QPushButton("🧹 ล้างข้อมูลพัสดุที่จัดส่งสำเร็จ")
        self.clear_shipped_btn.setFont(font)
        self.clear_shipped_btn.clicked.connect(self.clear_shipped_data)
        clear_cod_layout.addWidget(self.clear_shipped_btn)

        self.reset_cod_btn = QPushButton("🔄 รีเซ็ตค่าใช้จ่าย COD รายวัน")
        self.reset_cod_btn.setFont(font)
        self.reset_cod_btn.clicked.connect(self.reset_cod_expense)
        clear_cod_layout.addWidget(self.reset_cod_btn)

        # ✅ เพิ่ม Layout ปุ่มเข้าไปใน UI
        layout.addLayout(clear_cod_layout)

        self.table = QTableWidget()
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setFont(font)
        self.table.setColumnCount(11)  # ตั้งค่าจำนวนคอลัมน์
        self.table.setHorizontalHeaderLabels([
            "วันที่บันทึก", "สินค้า", "ร้านค้า", "ราคา", "ชำระผ่าน",
            "ขนส่ง", "สถานะจัดส่ง", "เลขพัสดุ", "ID", "Password", "F2A"
        ])

        # ✅ ปุ่ม "แสดง/ซ่อน ID, Password, F2A"
        toggle_sensitive_layout = QHBoxLayout()
        self.show_sensitive_data_btn = QPushButton("👁️ แสดง ID, Password, F2A")
        self.show_sensitive_data_btn.setCheckable(True)
        self.show_sensitive_data_btn.setFont(QFont("Arial", 12))
        self.show_sensitive_data_btn.clicked.connect(self.toggle_sensitive_columns)
        toggle_sensitive_layout.addWidget(self.show_sensitive_data_btn)

        # ✅ ซ่อน "ID", "Password", "F2A" ไว้ก่อน
        self.hidden_columns = [8, 9, 10]
        for col in self.hidden_columns:
            self.table.setColumnHidden(col, True)

        layout.addLayout(toggle_sensitive_layout)

        # ✅ เปิดใช้งานการเรียงลำดับคอลัมน์
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.table.horizontalHeader().setStyleSheet("color: #000000; font-size: 14px; font-weight: bold;")
        self.table.cellChanged.connect(self.edit_data)
        self.table.itemSelectionChanged.connect(self.load_tracking_from_db)

        # ✅ ขยายคอลัมน์ที่ต้องการให้ใหญ่ขึ้น
        columns_to_expand = [0, 1, 6, 7]  # "วันที่บันทึก", "สินค้า", "สถานะจัดส่ง", "เลขพัสดุ"
        for col in columns_to_expand:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

        layout.addWidget(self.table)

        # ✅ คำนวณค่าใช้จ่าย COD ครั้งแรกเมื่อเปิดโปรแกรม
        self.calculate_cod_expense()

        self.setLayout(layout)
        # ✅ อัปเดตสถานะพัสดุทุกครั้งที่โหลด UI
        self.update_status_summary()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_table)
        self.timer.start(3000)

    def update_status_summary(self):
        """อัปเดตจำนวนพัสดุในแต่ละสถานะ"""
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM orders GROUP BY status")
        data = cursor.fetchall()
        conn.close()

        # ✅ นับจำนวนสถานะพัสดุ
        status_counts = {"รอจัดส่ง": 0, "อยู่ระหว่างการจัดส่ง": 0, "จัดส่งพัสดุสำเร็จ": 0}
        for status, count in data:
            if status in status_counts:
                status_counts[status] = count

        # ✅ อัปเดตข้อความใน QLabel
        self.status_summary_label.setText(
            f"📦 รอจัดส่ง: {status_counts['รอจัดส่ง']} | 🚚 อยู่ระหว่างการจัดส่ง: {status_counts['อยู่ระหว่างการจัดส่ง']} | ✅ จัดส่งสำเร็จ: {status_counts['จัดส่งพัสดุสำเร็จ']}"
        )

    def toggle_sensitive_columns(self):
        """เปิด/ปิดการแสดงคอลัมน์ 'ID', 'Password', 'F2A'"""
        is_checked = self.show_sensitive_data_btn.isChecked()
        for col in self.hidden_columns:
            self.table.setColumnHidden(col, not is_checked)

        # ✅ เปลี่ยนข้อความปุ่มให้เข้าใจง่าย
        if is_checked:
            self.show_sensitive_data_btn.setText("🙈 ซ่อน ID, Password, F2A")
        else:
            self.show_sensitive_data_btn.setText("👁️ แสดง ID, Password, F2A")

    def clear_shipped_data(self):
        """ซ่อนข้อมูลพัสดุที่จัดส่งสำเร็จ โดยไม่ลบออกจากฐานข้อมูล"""
        conn = connect_db()
        cursor = conn.cursor()

        # ✅ อัปเดตให้ซ่อนแถวที่จัดส่งสำเร็จ (ไม่ลบจริง)
        cursor.execute("""
            UPDATE orders SET hidden = 1 WHERE status = 'จัดส่งพัสดุสำเร็จ';
        """)
        conn.commit()
        conn.close()

        self.update_table()  # ✅ อัปเดตตารางใหม่
        QMessageBox.information(self, "✅ สำเร็จ", "ซ่อนข้อมูลพัสดุที่จัดส่งสำเร็จแล้ว!")

    def show_import_dialog(self):
        """แสดงหน้าต่างให้วางข้อมูลออเดอร์ในรูปแบบตาราง"""
        dialog = QDialog(self)
        dialog.setWindowTitle("📥 นำเข้าออเดอร์แบบตาราง")

        # ✅ ปรับให้เต็มจอ 80% ตามขนาดหน้าจอ
        screen = QDesktopWidget().screenGeometry()
        width, height = screen.width(), screen.height()
        dialog.setGeometry(int(width * 0.1), int(height * 0.1), int(width * 0.8), int(height * 0.8))

        layout = QVBoxLayout()

        # ✅ ทำให้ตารางปรับขนาดอัตโนมัติ
        self.import_table = QTableWidget()
        self.import_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.import_table.setColumnCount(9)
        self.import_table.setHorizontalHeaderLabels([
            "ID ผู้ใช้", "รหัสผ่าน", "F2A", "สินค้า", "เลขพัสดุ", "จำนวนสินค้า", "ราคา", "ช่องทางชำระเงิน", "ร้านค้า"
        ])
        self.import_table.setRowCount(100)  # ✅ ตั้งค่าเริ่มต้น 100 แถวเลย
        # ✅ ปรับให้หัวตารางตัวหนังสือเป็นสีดำ
        header = self.import_table.horizontalHeader()
        for col in range(self.import_table.columnCount()):
            item = self.import_table.horizontalHeaderItem(col)
            if item:
                item.setForeground(QColor("black"))
        # ✅ ปุ่มวางข้อมูลจาก Clipboard (Google ชีต / Excel)
        paste_btn = QPushButton("📋 วางข้อมูล (Ctrl+V)")
        paste_btn.clicked.connect(self.paste_data_from_clipboard)
        layout.addWidget(paste_btn)

        # ✅ ปุ่มตรวจสอบข้อมูลก่อนนำเข้า
        check_btn = QPushButton("🔍 ตรวจสอบข้อมูล")
        check_btn.clicked.connect(self.validate_import_data)
        layout.addWidget(check_btn)

        # ✅ ปุ่มนำเข้าออเดอร์
        import_btn = QPushButton("✅ นำเข้าออเดอร์")
        import_btn.clicked.connect(self.import_orders_from_table)
        import_btn.setEnabled(False)  # ❌ เริ่มต้นปิดปุ่มนำเข้าไว้ก่อน
        self.import_btn = import_btn
        layout.addWidget(import_btn)

        layout.addWidget(self.import_table)
        dialog.setLayout(layout)
        dialog.exec_()

    def paste_data_from_clipboard(self):
        """วางข้อมูลจาก Clipboard ลงในตาราง"""
        clipboard = QApplication.clipboard()
        data = clipboard.text()

        if not data:
            QMessageBox.warning(self, "⚠️ ข้อผิดพลาด", "ไม่มีข้อมูลใน Clipboard!")
            return

        rows = data.strip().split("\n")
        row_count = len(rows)

        # ✅ ถ้าแถวที่มีอยู่ไม่พอ ให้เพิ่มแถวใหม่
        if row_count > self.import_table.rowCount():
            self.import_table.setRowCount(row_count)

        for row_idx, row in enumerate(rows):
            cells = row.split("\t")  # ✅ แยกข้อมูลตาม Tab (จาก Google ชีต/Excel)
            for col_idx, cell in enumerate(cells):
                if col_idx < self.import_table.columnCount():
                    self.import_table.setItem(row_idx, col_idx, QTableWidgetItem(cell.strip()))

        self.import_btn.setEnabled(True)  # ✅ เปิดปุ่มนำเข้าเมื่อมีข้อมูล

    def import_orders_from_table(self):
        """นำเข้าข้อมูลออเดอร์จากตาราง"""
        timezone = pytz.timezone("Asia/Bangkok")
        current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")

        conn = self.connect_db()
        cursor = conn.cursor()

        for row in range(self.import_table.rowCount()):
            user_id = self.import_table.item(row, 0)
            product = self.import_table.item(row, 3)
            price = self.import_table.item(row, 6)

            # ✅ ข้ามแถวที่ไม่มี ID ผู้ใช้, สินค้า และราคา
            if not user_id or not product or not price:
                continue

            password = self.import_table.item(row, 1)
            f2a = self.import_table.item(row, 2)
            tracking = self.import_table.item(row, 4)
            quantity = self.import_table.item(row, 5)
            payment = self.import_table.item(row, 7)
            shop = self.import_table.item(row, 8)

            user_id = user_id.text().strip()
            password = password.text().strip() if password else ""
            f2a = f2a.text().strip() if f2a else ""
            product = product.text().strip()
            tracking = tracking.text().strip() if tracking else ""
            price = float(price.text().replace("฿", "").replace(",", ""))  # ✅ แปลงราคาเป็นตัวเลข
            payment = payment.text().strip()
            shop = shop.text().strip() if shop else "-"

            # ✅ ถ้าไม่ได้ใส่จำนวน หรือใส่ 1 ให้เป็น 1
            quantity = int(quantity.text().strip()) if quantity and quantity.text().strip().isdigit() else 1

            status = "รอจัดส่ง" if tracking == "" else "อยู่ระหว่างการจัดส่ง"
            cod_expense = price if payment == "COD" else 0

            cursor.execute("""
                INSERT INTO orders (date_recorded, product, shop, price, payment, tracking, shipping, status, user_id, password, f2a, cod_expense, unit_per_item)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                current_time, product, shop, price, payment, tracking, self.detect_shipping_provider(tracking), status,
                user_id, password, f2a, cod_expense, quantity))

        conn.commit()
        conn.close()

        self.update_table()
        self.calculate_cod_expense()
        QMessageBox.information(self, "✅ สำเร็จ", "นำเข้าออเดอร์เรียบร้อย!")
        print(f"🟡 DEBUG: Payment Method -> '{payment}'")

    def validate_import_data(self):
        """ตรวจสอบข้อมูลในตารางก่อนนำเข้า"""
        for row in range(self.import_table.rowCount()):
            user_id = self.import_table.item(row, 0)
            product = self.import_table.item(row, 3)
            price = self.import_table.item(row, 6)

            if user_id and product and price:
                continue  # ✅ ข้อมูลสมบูรณ์ ข้ามไปตรวจสอบแถวถัดไป
            elif not user_id and not product and not price:
                break  # ✅ เจอแถวว่าง ให้หยุดตรวจสอบได้เลย
            else:
                QMessageBox.warning(self, "⚠️ ข้อผิดพลาด", f"แถวที่ {row + 1} ข้อมูลไม่ครบถ้วน!")
                return

        self.import_btn.setEnabled(True)  # ✅ เปิดปุ่มนำเข้า
        QMessageBox.information(self, "✅ ตรวจสอบแล้ว", "ข้อมูลถูกต้อง พร้อมนำเข้า!")

    def load_shop_history(self):
        """โหลดประวัติร้านค้าเพื่อใช้เป็น AutoComplete"""
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT shop FROM orders ORDER BY date_recorded DESC LIMIT 50")
            shop_list = [row[0] for row in cursor.fetchall()]
            conn.close()

            completer = QCompleter(shop_list, self)
            completer.setCaseSensitivity(False)  # ไม่ต้องสนใจตัวพิมพ์ใหญ่-เล็ก
            completer.setFilterMode(Qt.MatchContains)  # แสดงผลแม้พิมพ์บางคำ
            self.shop_input.setCompleter(completer)

    def load_price_history(self):
        """โหลดประวัติราคาสินค้าเพื่อใช้เป็น AutoComplete"""
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT price FROM orders ORDER BY date_recorded DESC LIMIT 50")
            price_list = [str(row[0]) for row in cursor.fetchall()]
            conn.close()

            completer = QCompleter(price_list, self)
            completer.setCaseSensitivity(False)
            completer.setFilterMode(Qt.MatchContains)
            self.price_input.setCompleter(completer)

    def open_sell_window(self):
        """เปิดหน้าต่างขายสินค้า"""
        self.sell_window = SellWindow()
        self.sell_window.show()

    def detect_shipping_provider(self, tracking_no):
        tracking_no = (tracking_no or "").strip().upper()
        if tracking_no.startswith("TH"):
            return "Flash Express"
        elif tracking_no.startswith("TIK"):
            return "Kerry"
        return "J&T Express"

    def connect_db(self):
        """เชื่อมต่อกับฐานข้อมูล SQLite (ใช้ helper กลางเพื่อ path ชัวร์)"""
        return connect_db()

    def load_product_categories(self):
        """โหลดชื่อสินค้าตามออเดอร์ล่าสุดเข้า Dropdown"""
        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT p.product_name 
                FROM product_categories p
                LEFT JOIN orders o ON p.product_name = o.product
                ORDER BY o.date_recorded DESC, p.id DESC
            """)  # ✅ เรียงตามออเดอร์ล่าสุด
            products = [p[0] for p in cursor.fetchall()]
            conn.close()

            # ✅ บันทึกค่าที่เลือกอยู่ปัจจุบัน
            current_selection = self.product_input.currentText()

            self.product_input.clear()
            self.product_input.addItems(products)

            # ✅ ถ้าค่าก่อนหน้านี้ยังอยู่ ให้เลือกค่าเดิมกลับมา
            if current_selection in products:
                self.product_input.setCurrentText(current_selection)

    def open_stock_window(self):
        """เปิดหน้าต่างสต็อกสินค้า"""
        try:
            if hasattr(self, 'stock_window') and self.stock_window.isVisible():
                self.stock_window.activateWindow()
            else:
                self.stock_window = StockWindow()
                self.stock_window.product_added.connect(self.load_product_categories)  # ✅ เชื่อมสัญญาณ
                self.stock_window.show()
        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดขณะเปิดหน้าสต็อกสินค้า: {e}")

    def open_product_editor(self):
        """เปิดหน้าต่างเพิ่ม/แก้ไขสินค้า (แก้ product_categories ใน bot_system.db)"""
        dlg = ProductEditorDialog(self)
        dlg.exec_()

        # รีโหลด dropdown สินค้าในหน้าหลักหลังแก้ไข
        try:
            self.load_product_categories()
        except Exception:
            pass

    cod_updated = pyqtSignal()  # ✅ Signal แจ้งว่า ค่าใช้จ่าย COD อัปเดตแล้ว

    def calculate_cod_expense(self):
        """คำนวณค่าใช้จ่าย COD รายวันโดยใช้ date_recorded"""
        today = datetime.now().strftime("%Y-%m-%d")

        conn = connect_db()
        if conn:
            cursor = conn.cursor()

            # ✅ คำนวณค่า COD ใหม่
            cursor.execute("""
                SELECT SUM(cod_expense) FROM orders 
                WHERE payment = 'COD' 
                AND status = 'จัดส่งพัสดุสำเร็จ'
                AND date_recorded LIKE ?;
            """, (f"{today}%",))
            total_cod = cursor.fetchone()[0] or 0
            conn.close()

            # ✅ **อัปเดต Label ใน UI**
            self.cod_expense_label.setText(f"💰 ค่าใช้จ่าย COD วันนี้: ฿{total_cod:,.2f}")

            print(f"🔄 อัปเดตค่าใช้จ่าย COD ใน UI: ฿{total_cod:,.2f}")

    def reset_cod_expense(self):
        """รีเซ็ตค่าใช้จ่าย COD เฉพาะของวันนี้"""
        try:
            reply = QMessageBox.question(
                self, "ยืนยัน", "⚠ ต้องการรีเซ็ตค่าใช้จ่าย COD วันนี้หรือไม่?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                conn = connect_db()
                if conn:
                    cursor = conn.cursor()
                    today = datetime.now().strftime("%Y-%m-%d")

                    # ✅ ตรวจสอบจำนวนออเดอร์ที่ควรถูกรีเซ็ต
                    cursor.execute("""
                        SELECT COUNT(*) FROM orders 
                        WHERE payment = 'COD' 
                        AND status = 'จัดส่งพัสดุสำเร็จ'
                        AND date_recorded LIKE ?;
                    """, (f"{today}%",))
                    count_before = cursor.fetchone()[0]
                    print(f"📊 จำนวนออเดอร์ของวันนี้ที่ควรรีเซ็ต: {count_before}")

                    # ✅ รีเซ็ตเฉพาะออเดอร์ของวันนี้
                    cursor.execute("""
                        UPDATE orders 
                        SET cod_expense = 0 
                        WHERE payment = 'COD' 
                        AND status = 'จัดส่งพัสดุสำเร็จ'
                        AND date_recorded LIKE ?;
                    """, (f"{today}%",))
                    conn.commit()

                    # ✅ ตรวจสอบจำนวนออเดอร์ที่ถูกรีเซ็ตแล้ว
                    cursor.execute("""
                        SELECT COUNT(*) FROM orders 
                        WHERE payment = 'COD' 
                        AND status = 'จัดส่งพัสดุสำเร็จ'
                        AND date_recorded LIKE ? 
                        AND cod_expense = 0;
                    """, (f"{today}%",))
                    count_after = cursor.fetchone()[0]
                    print(f"✅ จำนวนออเดอร์ที่ถูกรีเซ็ตแล้ว: {count_after}")

                    if count_after == count_before:
                        print("🎯 ค่า COD ถูกรีเซ็ตเรียบร้อย! (เฉพาะของวันนี้)")
                    else:
                        print("⚠️ บางออเดอร์ไม่ได้ถูกรีเซ็ต กรุณาตรวจสอบฐานข้อมูล!")

                    conn.commit()
                    cursor.close()
                    conn.close()

                    # ✅ โหลดค่าล่าสุดใหม่ และอัปเดตตารางทันที
                    self.calculate_cod_expense()
                    self.update_table()

                    QMessageBox.information(
                        self, "✅ สำเร็จ",
                        f"รีเซ็ตค่าใช้จ่าย COD วันนี้เรียบร้อย! ({count_after}/{count_before} ออเดอร์)"
                    )
                    print("🔄 รีเซ็ตค่าใช้จ่าย COD เสร็จแล้ว! (เฉพาะของวันนี้)")

        except Exception as e:
            QMessageBox.critical(self, "❌ ข้อผิดพลาด", f"เกิดข้อผิดพลาด: {e}")

    def edit_data(self, row, column):
        """อัปเดตข้อมูลที่แก้ไขในตารางลง SQLite"""
        new_value = self.table.item(row, column).text()
        conn = connect_db()
        updated_stock = False  # ✅ ป้องกันการเรียกซ้ำ

        if conn:
            cursor = conn.cursor()
            order_id = self.table.item(row, 8).text()  # ID ผู้ใช้

            column_mapping = {
                0: "date_recorded",
                1: "product",
                2: "shop",
                3: "price",
                4: "payment",
                5: "shipping",
                6: "status",
                7: "tracking",
                8: "user_id",
                9: "password",
                10: "f2a"
            }

            if column not in column_mapping:
                print(f"⚠️ คอลัมน์ {column} ไม่สามารถอัปเดตได้!")
                return

            column_name = column_mapping[column]

            # ✅ ถ้าเป็น "เลขพัสดุ" ให้เปลี่ยนสถานะ
            if column == 7:  # ช่องเลขพัสดุ
                status = "อยู่ระหว่างการจัดส่ง" if new_value.strip() else "รอจัดส่ง"
                try:
                    cursor.execute(f"""
                        UPDATE orders SET {column_name} = ?, status = ? WHERE user_id = ?
                    """, (new_value, status, order_id))
                    conn.commit()
                except sqlite3.Error as e:
                    print(f"❌ เกิดข้อผิดพลาดขณะอัปเดตข้อมูล: {e}")


            elif column == 6:  # อัปเดตสถานะ

                if new_value == "จัดส่งพัสดุสำเร็จ":

                    try:

                        timezone = pytz.timezone("Asia/Bangkok")

                        current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")

                        cursor.execute("""

                            UPDATE orders 

                            SET status = ?, cod_expense = price, processed = 1, 

                                date_recorded = ?, status_updated_at = ?

                            WHERE user_id = ?;

                        """, (new_value, current_time, current_time, order_id))

                        conn.commit()

                        print(
                            f"✅ อัปเดต processed = 1, date_recorded และ status_updated_at ให้ user_id {order_id} ทันที")

                        # ✅ เพิ่มตรงนี้เพื่ออัปเดตค่า COD ทันที

                        self.calculate_cod_expense()

                        if hasattr(self, 'stock_window') and not updated_stock:
                            print("🔄 update_stock_from_orders() ถูกเรียกใช้งาน! (จาก edit_data())")

                            self.stock_window.update_stock_from_orders()

                            updated_stock = True

                        # ✅ คำนวณค่า COD ใหม่ทุกครั้งที่มีการจัดส่งสำเร็จ

                        self.calculate_cod_expense()


                    except sqlite3.Error as e:

                        print(f"❌ เกิดข้อผิดพลาดขณะอัปเดตค่าใช้จ่าย COD: {e}")



                else:
                    try:
                        # ✅ ถ้าสถานะยังไม่เป็น "จัดส่งพัสดุสำเร็จ" ให้ตรวจสอบ `cod_expense`
                        cursor.execute("""
                            UPDATE orders 
                            SET status = ?, cod_expense = CASE 
                                WHEN payment = 'COD' AND cod_expense = 0 THEN price 
                                ELSE cod_expense END
                            WHERE user_id = ?;
                        """, (new_value, order_id))
                        conn.commit()
                        print(f"✅ อัปเดตสถานะ {new_value} และตรวจสอบ cod_expense ให้ user_id {order_id}")

                    except sqlite3.Error as e:
                        print(f"❌ เกิดข้อผิดพลาดขณะอัปเดตค่าใช้จ่าย COD: {e}")

                if not updated_stock:
                    print("✅ คำนวณค่า COD ตามปกติ")
                    self.calculate_cod_expense()
                else:
                    print("⚠️ ข้าม `calculate_cod_expense()` เพราะอัปเดตสต็อกแล้ว")

                self.update_table()  # ✅ อัปเดต UI ให้ข้อมูลใหม่แสดง

    def add_product_category(self):
        """เพิ่มสินค้าใหม่ลงใน `product_categories`"""
        product_name = self.new_product_name.text().strip()
        sell_price_retail = self.new_sell_price_retail.text().strip()
        sell_price_wholesale = self.new_sell_price_wholesale.text().strip()

        if not product_name or not sell_price_retail or not sell_price_wholesale:
            QMessageBox.warning(self, "แจ้งเตือน", "❗ กรุณากรอกข้อมูลให้ครบถ้วน!")
            return

        try:
            sell_price_retail = float(sell_price_retail)
            sell_price_wholesale = float(sell_price_wholesale)
        except ValueError:
            QMessageBox.warning(self, "แจ้งเตือน", "❗ ราคาต้องเป็นตัวเลข!")
            return

        conn = self.connect_db()
        if conn:
            cursor = conn.cursor()
            try:
                sku_prefix = product_name[:3].upper()

                cursor.execute("""
                    INSERT INTO product_categories (product_name, sku_prefix, sell_price_retail, sell_price_wholesale)
                    VALUES (?, ?, ?, ?)
                """, (product_name, sku_prefix, sell_price_retail, sell_price_wholesale))

                conn.commit()
                QMessageBox.information(self, "สำเร็จ", f"✅ เพิ่มสินค้า '{product_name}' สำเร็จ!")

                # ✅ โหลดข้อมูลใหม่หลังจากเพิ่มสินค้า
                self.load_stock_data()

            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "แจ้งเตือน", f"❗ สินค้า '{product_name}' มีอยู่แล้ว!")
            finally:
                conn.close()

            self.new_product_name.clear()
            self.new_sell_price_retail.clear()
            self.new_sell_price_wholesale.clear()

    def search_data(self):
        search_text = self.search_input.text().strip().lower()  # แปลงเป็น lower case

        if not search_text:
            QMessageBox.warning(self, "แจ้งเตือน", "กรุณากรอกคำค้นหา!")
            return

        # ตัด "฿" ออกจากการค้นหาถ้าผู้ใช้ค้นหาด้วยราคา
        if search_text.startswith("฿"):
            search_text = search_text[1:]

        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date_recorded, product, shop, price, payment, shipping, status, tracking, user_id, password, f2a 
                FROM orders 
                WHERE 
                    LOWER(product) LIKE ? OR 
                    LOWER(shop) LIKE ? OR 
                    LOWER(tracking) LIKE ? OR 
                    LOWER(user_id) LIKE ? OR
                    LOWER(status) LIKE ? OR
                    price LIKE ?
            """, (f"%{search_text}%", f"%{search_text}%", f"%{search_text}%", f"%{search_text}%", f"%{search_text}%",
                  f"%{search_text}%"))

            search_results = cursor.fetchall()
            conn.close()

            if not search_results:
                QMessageBox.warning(self, "แจ้งเตือน", "ไม่พบข้อมูลที่เกี่ยวข้อง!")
                return

            self.show_search_results(search_results)

            self.timer.stop()
            self.start_search_btn.setEnabled(False)
            self.stop_search_btn.setEnabled(True)

    def stop_search(self):
        self.search_input.clear()
        self.update_table()
        self.timer.start(5000)
        self.start_search_btn.setEnabled(True)
        self.stop_search_btn.setEnabled(False)

    def show_search_results(self, results):
        self.table.blockSignals(True)
        self.table.setRowCount(len(results))
        self.table.setColumnCount(11)

        for row_idx, row_data in enumerate(results):
            for col_idx, cell_value in enumerate(row_data):
                item = QTableWidgetItem(str(cell_value))
                self.table.setItem(row_idx, col_idx, item)

        self.table.blockSignals(False)

    def load_tracking_from_db(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            return

        tracking_number = self.table.item(selected_row, 7).text()
        if tracking_number.strip():
            self.tracking_input.setText(tracking_number)

    def update_table(self):
        """โหลดข้อมูลจากฐานข้อมูล และซ่อนรายการที่ถูกซ่อนไว้"""
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            # ✅ โหลดเฉพาะออเดอร์ที่ไม่ได้ถูกซ่อน (hidden = 0)
            cursor.execute("""
                SELECT date_recorded, product, shop, price, payment, shipping, status, tracking, user_id, password, f2a 
                FROM orders WHERE hidden = 0 ORDER BY date_recorded DESC
            """)
            all_data = cursor.fetchall()
            conn.close()

            self.table.blockSignals(True)  # ปิดการส่งสัญญาณชั่วคราว (ป้องกัน loop update)

            self.table.setRowCount(len(all_data))  # ✅ ปรับจำนวนแถวตามข้อมูลใหม่

            from datetime import datetime
            today = datetime.now()

            for row_idx, row_data in enumerate(all_data):
                date_recorded = datetime.strptime(row_data[0], "%Y-%m-%d %H:%M:%S")
                tracking = row_data[7].strip()
                status = row_data[6]

                # ✅ **อัปเดตสถานะตามเงื่อนไขเดิม**
                if not tracking:
                    new_status = "รอจัดส่ง"
                elif status != "จัดส่งพัสดุสำเร็จ":
                    new_status = "อยู่ระหว่างการจัดส่ง"
                else:
                    new_status = status  # ไม่เปลี่ยนแปลงถ้าส่งสำเร็จแล้ว

                if (today - date_recorded).days > 3 and new_status != "จัดส่งพัสดุสำเร็จ":
                    new_status = "ตรวจสอบพัสดุ"

                row_data = list(row_data)
                row_data[6] = new_status  # ✅ อัปเดตสถานะใหม่

                # ✅ **ถ้าสถานะเป็น "จัดส่งพัสดุสำเร็จ" ให้คำนวณค่า COD**
                if new_status == "จัดส่งพัสดุสำเร็จ":
                    self.calculate_cod_expense()

                # ✅ ใส่ข้อมูลลงตาราง
                for col_idx, cell_value in enumerate(row_data):
                    item = QTableWidgetItem(str(cell_value))

                    # ✅ **จัดสีตามสถานะการจัดส่ง**
                    if col_idx == 6:  # คอลัมน์สถานะ
                        if new_status == "รอจัดส่ง":
                            item.setBackground(QColor("#FFD700"))  # พื้นเหลือง
                            item.setForeground(QColor("#000000"))  # ตัวหนังสือดำ
                        elif new_status == "อยู่ระหว่างการจัดส่ง":
                            item.setBackground(QColor("#87CEEB"))  # พื้นฟ้า
                            item.setForeground(QColor("#000000"))  # ตัวหนังสือดำ
                        elif new_status == "ตรวจสอบพัสดุ":
                            item.setBackground(QColor("#DC143C"))  # พื้นแดง
                            item.setForeground(QColor("#FFFFFF"))  # ตัวหนังสือขาว
                        elif new_status == "จัดส่งพัสดุสำเร็จ":
                            item.setBackground(QColor("#32CD32"))  # พื้นเขียว
                            item.setForeground(QColor("#FFFFFF"))  # ตัวหนังสือขาว

                    self.table.setItem(row_idx, col_idx, item)

            self.table.blockSignals(False)  # ✅ เปิดการส่งสัญญาณกลับมา
            # ✅ อัปเดตสถานะพัสดุหลังโหลดข้อมูลใหม่
            self.update_status_summary()

    def format_price_input(self):
        text = self.price_input.text()
        if not text.startswith("฿"):
            text = "฿" + text

        if not text[1:].isdigit():
            text = "฿" + "".join(filter(str.isdigit, text))

        self.price_input.setText(text)

    def create_input(self, label_text, layout, font, is_password=False):
        label = QLabel(label_text)
        label.setFont(font)
        input_field = QLineEdit()
        input_field.setFont(font)
        if is_password:
            input_field.setEchoMode(QLineEdit.Password)
        layout.addRow(label, input_field)
        return input_field

    def add_data(self):
        conn = connect_db()
        if conn:
            cursor = conn.cursor()

            timezone = pytz.timezone("Asia/Bangkok")
            current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")

            product = self.product_input.currentText().strip()
            shop = self.shop_input.text().strip()
            price = self.price_input.text().replace("฿", "").strip()
            payment = self.payment_input.currentText().strip()
            tracking = self.tracking_input.text().strip()
            shipping = self.detect_shipping_provider(tracking)
            status = "รอจัดส่ง" if not tracking else "อยู่ระหว่างการจัดส่ง"
            user_id = self.id_input.text().strip()
            password = self.password_input.text().strip()
            f2a = self.f2a_input.text().strip()
            unit_per_item = self.unit_per_item_input.text().strip()
            unit_per_item = int(unit_per_item) if unit_per_item.isdigit() else 1  # ✅ ถ้าเว้นว่าง ให้เป็น 1

            # ✅ ถ้าเป็น COD ให้ใส่ราคาไปที่ cod_expense ด้วย
            cod_expense = float(price) if payment == "COD" else 0
            print(f"📝 บันทึกข้อมูล: {product}, unit_per_item = {unit_per_item}")

            cursor.execute("""
                INSERT INTO orders (date_recorded, product, shop, price, payment, tracking, shipping, status, user_id, password, f2a, cod_expense, unit_per_item)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (current_time, product, shop, price, payment, tracking, shipping, status, user_id, password, f2a,
                  cod_expense, unit_per_item))

            conn.commit()
            conn.close()

            self.update_table()
            self.update_status_summary()
            self.load_shop_history()
            self.load_price_history()
            self.clear_inputs()
            self.load_product_categories()
            self.calculate_cod_expense()  # ✅ อัปเดตค่าใช้จ่าย COD ทันที

            QMessageBox.information(self, "✅ สำเร็จ", "บันทึกข้อมูลเรียบร้อย!")

    def show_temp_message(self, message, color="black"):
        if not hasattr(self, "message_label"):
            self.message_label = QLabel(self)
            self.message_label.setStyleSheet(
                "font-size: 18px; font-weight: bold; border: 2px solid #333; border-radius: 10px; padding: 10px;"
            )
            self.message_label.setAlignment(Qt.AlignCenter)
            self.message_label.setGeometry(50, 50, 300, 50)

        self.message_label.setText(message)
        self.message_label.setStyleSheet(
            f"background-color: {color}; color: white; font-size: 18px; padding: 10px; border-radius: 10px;"
        )
        self.message_label.show()

        QTimer.singleShot(2000, self.message_label.hide)

    def clear_inputs(self):
        """เคลียร์ค่าทั้งหมดในช่องกรอกหลังบันทึก"""
        self.product_input.setCurrentIndex(0)  # รีเซ็ต ComboBox เป็นตัวเลือกแรก
        self.shop_input.clear()
        self.price_input.clear()
        self.tracking_input.clear()
        self.id_input.clear()
        self.password_input.clear()
        self.f2a_input.clear()
        self.unit_per_item_input.clear()
        self.payment_input.setCurrentIndex(0)  # รีเซ็ตเป็นตัวเลือกแรก (COD)

        # รีเฟรช UI หลังจากเคลียร์ค่า
        self.update()

        # ให้โฟกัสกลับไปที่ช่อง "สินค้า"
        self.product_input.setFocus()

    def update_tracking_ui(self):
        self.show_tracking_popup()

    def show_tracking_popup(self):
        self.tracking_popup = QDialog(self)
        self.tracking_popup.setWindowTitle("📦 ตรวจสอบเลขพัสดุ")
        self.tracking_popup.setGeometry(200, 200, 300, 150)

        layout = QVBoxLayout()

        self.tracking_input_popup = QLineEdit()
        self.tracking_input_popup.setPlaceholderText("🔍 ยิงบาร์โค้ดหรือพิมพ์เลขพัสดุ")
        layout.addWidget(self.tracking_input_popup)

        check_button = QPushButton("✅ ตรวจสอบ")
        check_button.clicked.connect(self.check_tracking_popup)
        layout.addWidget(check_button)

        self.tracking_popup.setLayout(layout)
        self.tracking_popup.exec_()

    def check_tracking_popup(self):
        """ตรวจสอบเลขพัสดุ และอัปเดตสถานะ + status_updated_at"""
        tracking_number = self.tracking_input_popup.text().strip()

        if not tracking_number:
            self.play_sound("tada.wav")
            self.show_temp_message("⚠️ กรุณากรอกเลขพัสดุ!", "red")
            return

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT status, payment, price FROM orders WHERE tracking = ?", (tracking_number,))
        result = cursor.fetchone()

        if result:
            current_status, payment, price = result

            if current_status == "จัดส่งพัสดุสำเร็จ":
                self.play_sound("Windows Notify Calendar.wav")
                self.show_temp_message("✅ พัสดุนี้จัดส่งสำเร็จแล้ว!", "orange")
            else:
                timezone = pytz.timezone("Asia/Bangkok")
                current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")

                cod_expense = price if payment == "COD" else 0  # อัปเดตค่า COD เฉพาะถ้าเป็น COD

                cursor.execute("""
                    UPDATE orders 
                    SET status = 'จัดส่งพัสดุสำเร็จ', status_updated_at = ?, cod_expense = ?, date_recorded = ?
                    WHERE tracking = ?;
                """, (current_time, cod_expense, current_time, tracking_number))

                conn.commit()

                self.play_sound("Windows Unlock.wav")
                self.show_temp_message("✅ จัดส่งพัสดุสำเร็จแล้ว!", "green")

                # ✅ อัปเดตยอด COD ทันที
                self.calculate_cod_expense()
                self.update_table()

        else:
            self.play_sound("tada.wav")
            self.show_temp_message(f"❌ ไม่พบพัสดุ: {tracking_number}!", "red")

        conn.close()
        self.tracking_input_popup.clear()
        self.tracking_input_popup.setFocus()

    def play_sound(self, sound_file):
        full_path = os.path.abspath(sound_file)
        print(f"กำลังเล่นไฟล์เสียง: {full_path}")

        if os.path.exists(full_path):
            # ✅ ใช้ Thread เพื่อให้เสียงเล่นพร้อมกับ UI
            threading.Thread(target=winsound.PlaySound, args=(full_path, winsound.SND_FILENAME)).start()
        else:
            print(f"❌ ไม่พบไฟล์เสียง: {full_path}")

    def toggle_theme(self):
        self.setStyleSheet(THEME_NEON if self.theme == "dark" else THEME_DARK)
        self.theme = "neon" if self.theme == "dark" else "dark"


def sync_sqlite_to_sheets():
    """ซิงค์ข้อมูลจาก SQLite ไปยัง Google Sheets"""
    try:
        print("🔄 เชื่อมต่อ Google Sheets...")  # ✅ Debug Log
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_FILE,
            ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

        print("✅ เชื่อมต่อ Google Sheets สำเร็จ!")  # ✅ Debug Log

        # เชื่อมต่อ SQLite
        conn = sqlite3.connect("bot_system.db")
        cursor = conn.cursor()

        print("🔄 ดึงข้อมูลจาก SQLite...")  # ✅ Debug Log
        cursor.execute(
            "SELECT product, shop, price, payment, tracking, status, user_id, password, f2a FROM orders WHERE hidden = 0")
        data = cursor.fetchall()

        conn.close()

        print(f"📊 จำนวนข้อมูลที่ต้องอัปโหลด: {len(data)} แถว")  # ✅ Debug Log

        # ล้างข้อมูลเดิมใน Google Sheets
        sheet.clear()
        sheet.append_row(["สินค้า", "ร้านค้า", "ราคา", "ชำระผ่าน", "เลขพัสดุ", "สถานะ", "ID", "รหัสผ่าน", "F2A"])

        if data:
            sheet.append_rows(data)
            print("✅ ซิงค์ข้อมูลจาก SQLite ไป Google Sheets สำเร็จ!")

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดขณะซิงค์ SQLite ไป Google Sheets:\n{e}")


if __name__ == "__main__":
    import sys
    import traceback
    from PyQt5.QtWidgets import QApplication

    try:
        # สร้างแอป PyQt
        app = QApplication(sys.argv)

        # เปิดหน้าต่างหลักของโปรแกรม
        window = SQLiteApp()
        window.show()

        # เริ่มการทำงานของแอป
        sys.exit(app.exec_())

    except Exception as e:
        print("❌ เกิดข้อผิดพลาดในโปรแกรมหลัก:")
        print(e)
        traceback.print_exc()  # แสดงรายละเอียดข้อผิดพลาดแบบเต็ม

