import sqlite3

from database import connect_db

try:
    from PyQt5.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QComboBox,
        QMessageBox,
        QGridLayout,
        QSpacerItem,
        QSizePolicy,
        QGroupBox,
        QHBoxLayout,
        QTableWidget,
        QTableWidgetItem,
    )
    from PyQt5.QtGui import QFont, QIcon
    from PyQt5.QtCore import Qt
except ModuleNotFoundError as e:
    # มักเกิดจากรันด้วย interpreter/venv ผิดตัว (เช่น PyCharmMiscProject\.venv)
    if getattr(e, "name", "") == "PyQt5":
        raise SystemExit(
            "ไม่พบ PyQt5 ใน interpreter ที่กำลังรันอยู่\n"
            "ให้รันด้วย venv ของโปรเจกต์นี้แทน:\n"
            "  C:\\Users\\tao\\Desktop\\Stock_PRO\\.venv\\Scripts\\python.exe main.py\n"
        ) from e
    raise

from reportlab.lib.pagesizes import mm, portrait
import os
import sqlite3
from datetime import datetime
# (PyQt5 imports are consolidated above)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from paths import resource_path


class SellWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🛒 ขายสินค้า")
        self.setGeometry(400, 200, 700, 500)

        # ✅ สร้างตารางก่อนเรียก `initUI()`
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(5)
        self.sales_table.setHorizontalHeaderLabels(["สินค้า", "คงเหลือ", "จำนวน", "ราคาต่อหน่วย", "ราคารวม"])

        self.initUI()  # ✅ เรียก `initUI()` หลังสร้าง `sales_table`
        self.load_products()
        self.reset_daily_sales_if_needed()

    def initUI(self):
        """สร้าง UI สำหรับขายสินค้า"""
        layout = QVBoxLayout()
        font = QFont("Arial", 12)

        # ✅ หัวข้อใหญ่
        title_label = QLabel("📦 ระบบขายสินค้า")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # ✅ Grid Layout สำหรับ Barcode & รายละเอียดสินค้า
        grid_layout = QGridLayout()

        # ✅ ช่องยิงบาร์โค้ด (แยกออกจากช่องเลือกสินค้า)
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("📌 ยิงบาร์โค้ดที่นี่...")
        self.barcode_input.setFont(font)
        self.barcode_input.returnPressed.connect(self.search_product_by_barcode)  # ✅ ค้นหาทันทีเมื่อยิงบาร์โค้ด

        grid_layout.addWidget(QLabel("บาร์โค้ด:"), 0, 0)
        grid_layout.addWidget(self.barcode_input, 0, 1)

        # ✅ ช่องเลือกสินค้า (แยกจากบาร์โค้ด)
        self.product_input = QComboBox()
        self.product_input.setFont(font)
        self.product_input.currentIndexChanged.connect(self.update_price_display)

        grid_layout.addWidget(QLabel("สินค้า:"), 1, 0)
        grid_layout.addWidget(self.product_input, 1, 1)

        # ✅ เลือกประเภทลูกค้า (ปลีก / ส่ง)
        self.customer_type = QComboBox()
        self.customer_type.addItems(["ลูกค้าปลีก", "ลูกค้าส่ง"])
        self.customer_type.setFont(font)
        self.customer_type.currentIndexChanged.connect(self.update_price_display)

        grid_layout.addWidget(QLabel("ประเภทลูกค้า:"), 2, 0)
        grid_layout.addWidget(self.customer_type, 2, 1)

        # ✅ ช่องกรอกจำนวนสินค้า
        self.quantity_input = QLineEdit()
        self.quantity_input.setText("1")  # ✅ กำหนดค่าเริ่มต้นเป็น 1
        self.quantity_input.setFont(font)

        grid_layout.addWidget(QLabel("จำนวนที่ขาย:"), 3, 0)
        grid_layout.addWidget(self.quantity_input, 3, 1)

        # ✅ ตัวเลือกหน่วยสินค้า
        self.unit_type = QComboBox()
        self.unit_type.addItems(["ชิ้น", "แพ็ค", "ลัง"])  # ✅ ใช้ "ชิ้น" แทน "ถุง"
        grid_layout.addWidget(QLabel("ขายเป็น:"), 4, 0)
        grid_layout.addWidget(self.unit_type, 4, 1)
        self.unit_type.currentIndexChanged.connect(self.update_price_display)
        self.customer_type.currentIndexChanged.connect(self.update_price_display)

        # ✅ แสดงราคาขายในแถวใหม่ (แยกออก ไม่ทับซ้อน)
        self.price_label = QLabel("💲 ราคาขาย: ฿0")
        self.price_label.setFont(QFont("Arial", 12, QFont.Bold))
        grid_layout.addWidget(self.price_label, 5, 0, 1, 2)  # ✅ วางในแถวที่ 5


        # ✅ ใช้ QGroupBox แยกโซนข้อมูลสินค้า
        product_group = QGroupBox("📦 รายละเอียดสินค้า")
        product_group.setLayout(grid_layout)
        layout.addWidget(product_group)
        self.sales_table.setMinimumHeight(200)  # ✅ กำหนดความสูงขั้นต่ำของตาราง
        self.sales_table.setMinimumWidth(600)  # ✅ กำหนดความกว้างขั้นต่ำ
        self.sales_table.show()
        layout.addWidget(self.sales_table)  # ✅ ใส่ตารางลงใน U

        # ✅ ปุ่มขายสินค้า
        self.sell_btn = QPushButton("  💰 ขายสินค้า")
        self.sell_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.sell_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.sell_btn.setIcon(QIcon("icon/sell.png"))  # ใส่ไอคอนให้ปุ่ม
        self.sell_btn.clicked.connect(self.sell_product)
        layout.addWidget(self.sell_btn)

        # ✅ ปุ่มลบสินค้า
        self.delete_btn = QPushButton("🗑️ ลบสินค้า")
        self.delete_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.delete_btn.setStyleSheet("background-color: #F44336; color: white; padding: 10px; border-radius: 5px;")
        self.delete_btn.clicked.connect(self.delete_selected_product)  # เชื่อมไปยังฟังก์ชัน
        layout.addWidget(self.delete_btn)

        # ✅ แสดงผลรวมราคาทั้งหมด
        self.total_price_label = QLabel("💰 รวมทั้งหมด: ฿0.00")
        self.total_price_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(self.total_price_label)


        # ✅ ปุ่มบันทึกการขาย
        self.save_sales_btn = QPushButton("💾 บันทึกการขาย")
        self.save_sales_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.save_sales_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; border-radius: 5px;")
        self.save_sales_btn.clicked.connect(self.save_sales)  # เชื่อมไปยังฟังก์ชัน
        layout.addWidget(self.save_sales_btn)


        # ✅ ปุ่มปริ้นรายการ
        self.print_btn = QPushButton("🖨️ ปริ้นใบเสร็จ")
        self.print_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.print_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 10px; border-radius: 5px;")
        self.print_btn.clicked.connect(self.print_sales)
        layout.addWidget(self.print_btn)

        self.daily_sales_label = QLabel("📆 ยอดขายวันนี้: ฿0.00")
        layout.addWidget(self.daily_sales_label)

        # ✅ Spacer ให้ UI ดูสมดุล
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setLayout(layout)
        self.load_products()
        self.sales_table.setColumnCount(5)  # ✅ เปลี่ยนจาก 4 เป็น 5 คอลัมน์
        self.sales_table.setHorizontalHeaderLabels(["สินค้า", "คงเหลือ", "จำนวน", "ราคาต่อหน่วย", "ราคารวม"])

        # ✅ อนุญาตให้แก้ไขตาราง
        self.sales_table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.sales_table.itemChanged.connect(self.on_table_item_changed)  # ดักจับเมื่อมีการแก้ไขค่า

    def search_product_by_barcode(self):
        """ค้นหาสินค้าจากบาร์โค้ด"""
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return

        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product FROM stock WHERE barcode = ?
            UNION
            SELECT product_name FROM product_categories WHERE barcode = ?
        """, (barcode, barcode))

        product = cursor.fetchone()
        conn.close()

        if product:
            self.product_input.setCurrentText(product[0])  # ✅ อัปเดตช่องเลือกสินค้า
        else:
            QMessageBox.warning(self, "แจ้งเตือน", "❗ ไม่พบสินค้านี้!")

        self.barcode_input.clear()

    def connect_db(self):
        """เชื่อมต่อฐานข้อมูล (ใช้ helper กลางเพื่อ path ชัวร์)"""
        return connect_db()

    def delete_selected_product(self):
        """ลบสินค้าที่เลือกออกจากตารางขาย"""
        selected_row = self.sales_table.currentRow()

        if selected_row >= 0:  # ✅ ถ้ามีแถวที่ถูกเลือก
            product_name = self.sales_table.item(selected_row, 0).text()
            confirm = QMessageBox.question(self, "ยืนยันการลบ",
                                           f"ต้องการลบ '{product_name}' ออกจากตะกร้าหรือไม่?",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if confirm == QMessageBox.Yes:
                self.sales_table.removeRow(selected_row)  # ✅ ลบแถวที่เลือกออก
                self.update_total_price()  # ✅ อัปเดตราคารวม
                self.barcode_input.setFocus()  # ✅ โฟกัสกลับไปที่ช่องยิงบาร์โค้ด
                print(f"🗑️ ลบสินค้า '{product_name}' ออกจากตะกร้าสำเร็จ!")
        else:
            QMessageBox.warning(self, "⚠️ แจ้งเตือน", "กรุณาเลือกสินค้าที่ต้องการลบ!")

    def load_products(self):
        """โหลดสินค้าทั้งหมดจากสต็อก

        เรียงลำดับให้สินค้าที่ขายบ่อย (sold_quantity สูง) อยู่บนสุด
        """
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT product
            FROM stock
            WHERE quantity > 0
            ORDER BY COALESCE(sold_quantity, 0) DESC, product COLLATE NOCASE ASC
            """
        )
        products = cursor.fetchall()
        conn.close()

        current = self.product_input.currentText().strip() if self.product_input.currentText() else ""
        self.product_input.blockSignals(True)
        self.product_input.clear()
        for (name,) in products:
            self.product_input.addItem(name)
        # พยายามเลือกของเดิมกลับมา (ถ้ายังมี)
        if current:
            idx = self.product_input.findText(current)
            if idx >= 0:
                self.product_input.setCurrentIndex(idx)
        self.product_input.blockSignals(False)

    def reset_daily_sales_if_needed(self):
        """ รีเซ็ตยอดขายรายวันอัตโนมัติเมื่อถึงวันใหม่ """
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT last_reset FROM system_status")
        last_reset = cursor.fetchone()
        today = datetime.now().strftime("%Y-%m-%d")

        if last_reset is None or last_reset[0] != today:
            cursor.execute("UPDATE system_status SET daily_sales = 0, last_reset = ?", (today,))
            conn.commit()

        conn.close()
        self.update_daily_sales_label()

    def update_daily_sales_label(self):
        """ อัปเดตยอดขายรายวันบนหน้าจอ """
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT daily_sales FROM system_status")
        daily_sales = cursor.fetchone()[0]
        conn.close()
        self.daily_sales_label.setText(f"📆 ยอดขายวันนี้: ฿{daily_sales:,.2f}")

    def on_table_item_changed(self, item):
        """บันทึกการเปลี่ยนแปลงใน QTableWidget และคำนวณราคารวมใหม่"""
        try:
            row = item.row()
            column = item.column()

            if column not in [2, 3]:  # ✅ อนุญาตให้แก้เฉพาะ "จำนวน" และ "ราคาต่อหน่วย"
                return

            quantity_item = self.sales_table.item(row, 2)
            price_item = self.sales_table.item(row, 3)

            if any(i is None or i.text().strip() == "" for i in [quantity_item, price_item]):
                return

            # ✅ ลบ "ชิ้น", "แพ็ค", "ลัง" ออกจาก quantity ก่อนแปลงเป็น int
            raw_quantity = quantity_item.text().strip()
            quantity = int(''.join(filter(str.isdigit, raw_quantity)))  # ✅ แยกเอาแต่ตัวเลขออกมา

            unit_type = ''.join(filter(str.isalpha, raw_quantity))  # ✅ แยกเอาเฉพาะ "ชิ้น/แพ็ค/ลัง"
            print(f"🔍 DEBUG: Quantity = {quantity}, Unit = {unit_type}")  # ✅ Debug ดูค่าที่ได้

            unit_mapping = {"ชิ้น": 1, "แพ็ค": 3, "ลัง": 24}  # ✅ ใช้ค่าที่ตั้งไว้
            conversion_factor = unit_mapping.get(unit_type, 1)
            total_quantity = quantity * conversion_factor  # ✅ แปลงเป็นจำนวนชิ้นที่แท้จริง

            unit_price = float(price_item.text())
            total_price = total_quantity * unit_price

            self.sales_table.blockSignals(True)
            self.sales_table.setItem(row, 4, QTableWidgetItem(f"{total_price:,.2f}"))
            self.sales_table.blockSignals(False)

            self.update_total_price()  # ✅ คำนวณราคารวมใหม่

        except Exception as e:
            print(f"❌ ERROR ใน on_table_item_changed(): {e}")
            self.sales_table.blockSignals(False)

    def update_total_price(self):
        """คำนวณราคารวมทั้งหมด"""
        total_amount = 0
        for row in range(self.sales_table.rowCount()):
            total_item = self.sales_table.item(row, 4)
            if total_item and total_item.text().strip():
                total_amount += float(total_item.text().replace(",", ""))

        self.total_price_label.setText(f"💰 รวมทั้งหมด: ฿{total_amount:,.2f}")

    def update_price_display(self):
        """อัปเดตราคาขายเมื่อเลือกสินค้า"""
        product_name = self.product_input.currentText()
        customer_type = self.customer_type.currentText()
        unit_type = self.unit_type.currentText()

        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sell_price_retail, sell_price_wholesale, unit_conversion
            FROM product_categories WHERE product_name = ?;
        """, (product_name,))
        product_data = cursor.fetchone()
        conn.close()

        if product_data:
            price_retail, price_wholesale, unit_conversion = product_data
            price_per_unit = price_retail if customer_type == "ลูกค้าปลีก" else price_wholesale

            # ✅ แปลง unit_conversion (1:3:24) → [1, 3, 24]
            unit_values = list(map(int, unit_conversion.split(":")))

            if len(unit_values) == 3:
                unit_per_pack, unit_per_carton = unit_values[1], unit_values[2]
            else:
                unit_per_pack, unit_per_carton = 1, 1

                # ✅ คำนวณราคาตามประเภทการขาย
            unit_mapping = {"ชิ้น": 1, "แพ็ค": unit_per_pack, "ลัง": unit_per_carton}
            price_display = price_per_unit * unit_mapping.get(unit_type, 1)

            self.price_label.setText(f"💲 ราคาขาย: ฿{price_display:,.2f} ({unit_type})")

    def sell_product(self):
        """เพิ่มรายการขายลงตาราง โดยไม่ตัดสต็อกทันที"""
        try:
            print("🛒 sell_product() ถูกเรียกแล้ว!")

            product_name = self.product_input.currentText()
            quantity_input = self.quantity_input.text().strip()
            unit_type = self.unit_type.currentText()
            customer_type = self.customer_type.currentText()

            if not product_name:
                QMessageBox.warning(self, "⚠️ แจ้งเตือน", "กรุณาเลือกสินค้า!")
                return

            conn = self.connect_db()
            cursor = conn.cursor()

            # ✅ ดึงจำนวนคงเหลือ + unit_conversion จาก stock
            cursor.execute(
                """
                SELECT quantity, unit_conversion
                FROM stock
                WHERE product = ?;
                """,
                (product_name,),
            )
            stock_data = cursor.fetchone()

            # ✅ ดึงราคาต่อชิ้นจาก product_categories (เป็นแหล่งข้อมูลหลัก)
            cursor.execute(
                """
                SELECT sell_price_retail, sell_price_wholesale
                FROM product_categories
                WHERE product_name = ?;
                """,
                (product_name,),
            )
            price_data = cursor.fetchone()
            conn.close()

            if not stock_data:
                QMessageBox.warning(self, "❌ ผิดพลาด", "ไม่พบสินค้าในสต็อก!")
                return

            stock_quantity, unit_conversion = stock_data

            # fallback เผื่อไม่มีใน product_categories
            if price_data:
                price_retail, price_wholesale = price_data
            else:
                conn2 = self.connect_db()
                cur2 = conn2.cursor()
                cur2.execute(
                    "SELECT sell_price_retail, sell_price_wholesale FROM stock WHERE product = ?;",
                    (product_name,),
                )
                row2 = cur2.fetchone() or (0, 0)
                conn2.close()
                price_retail, price_wholesale = row2

            price_per_unit = price_retail if customer_type == "ลูกค้าปลีก" else price_wholesale

            # ✅ ดึงค่า unit_conversion (1:3:24)
            unit_values = list(map(int, unit_conversion.split(":")))
            unit_per_pack = unit_values[1]
            unit_per_carton = unit_values[2]

            # ✅ ตรวจสอบค่า quantity_input
            if quantity_input.isdigit():
                quantity = int(quantity_input)
            else:
                quantity = 1  # ✅ ตั้งค่าเริ่มต้นเป็น 1

            # ✅ แปลงจำนวนขายเป็น "ชิ้น"
            unit_mapping = {"ชิ้น": 1, "แพ็ค": unit_per_pack, "ลัง": unit_per_carton}
            total_units_sold = quantity * unit_mapping.get(unit_type, 1)

            # ✅ ตรวจสอบว่าสต็อกพอไหม
            if total_units_sold > stock_quantity:
                QMessageBox.critical(self, "❌ ข้อผิดพลาด",
                                     f"สินค้า '{product_name}' มีไม่พอในสต็อก!\nคงเหลือ {stock_quantity} ชิ้น")
                return  # ✅ หยุดทันทีหากสต็อกไม่พอ

            # ✅ เพิ่มข้อมูลลงตารางขาย
            self.update_sales_table(product_name, quantity, unit_type, price_per_unit)
            QMessageBox.information(self, "✅ สำเร็จ", f"เพิ่มสินค้า '{product_name}' ในรายการขายสำเร็จ!")

            self.quantity_input.setText("1")  # ✅ รีเซ็ตค่าเป็น 1 ทุกครั้งหลังขายเสร็จ
            self.barcode_input.setFocus()  # ✅ โฟกัสกลับไปที่ช่องยิงบาร์โค้ด

        except Exception as e:
            print(f"❌ ERROR ใน sell_product(): {e}")

    def update_sales_table(self, product_name, quantity, unit_type, price_per_unit):
        """เพิ่มรายการขายลงตาราง และอัปเดตจำนวนคงเหลือให้ตรงกับรายการที่มีอยู่"""
        try:
            if not hasattr(self, "sales_table") or self.sales_table is None:
                print("❌ ERROR: self.sales_table ไม่มีอยู่แล้ว!")
                return

            conn = self.connect_db()
            cursor = conn.cursor()

            # ✅ ดึง unit_conversion
            cursor.execute("SELECT unit_conversion FROM stock WHERE product = ?", (product_name,))
            unit_conversion_data = cursor.fetchone()

            if unit_conversion_data:
                unit_values = list(map(int, unit_conversion_data[0].split(":")))
                unit_per_pack = unit_values[1]
                unit_per_carton = unit_values[2]
            else:
                unit_per_pack, unit_per_carton = 1, 1

                # ✅ คำนวณจำนวนที่ขายเป็น "ชิ้น"
            unit_mapping = {"ชิ้น": 1, "แพ็ค": unit_per_pack, "ลัง": unit_per_carton}
            total_units_sold = quantity * unit_mapping.get(unit_type, 1)

            # ✅ คำนวณราคาต่อหน่วยให้ถูกต้อง
            price_mapping = {"ชิ้น": price_per_unit, "แพ็ค": price_per_unit * unit_per_pack,
                             "ลัง": price_per_unit * unit_per_carton}
            price_display = price_mapping[unit_type]

            # ✅ คำนวณราคารวม
            total_price = quantity * price_display

            # ✅ ตรวจสอบคงเหลือล่าสุดจาก `sales_table` ถ้ามีสินค้าอยู่ก่อนแล้ว
            current_stock_remaining = None
            for row in range(self.sales_table.rowCount()):
                item = self.sales_table.item(row, 0)
                if item and item.text() == product_name:
                    current_stock_remaining = int(self.sales_table.item(row, 1).text())  # ค่าคงเหลือจากตาราง

            if current_stock_remaining is None:
                # ✅ ถ้ายังไม่มีสินค้าใน `sales_table` ใช้ค่าจากฐานข้อมูล
                cursor.execute("SELECT quantity FROM stock WHERE product = ?", (product_name,))
                stock_quantity_data = cursor.fetchone()
                current_stock_remaining = stock_quantity_data[0] if stock_quantity_data else 0

            conn.close()

            new_stock_remaining = current_stock_remaining - total_units_sold

            # ✅ ถ้าจำนวนสินค้าที่ต้องการขายมากกว่าคงเหลือ → แจ้งเตือนและไม่ให้เพิ่มสินค้าเข้าตาราง
            if new_stock_remaining < 0:
                QMessageBox.critical(self, "❌ ข้อผิดพลาด",
                                     f"สินค้า '{product_name}' มีไม่พอในสต็อก!\n"
                                     f"คงเหลือ {current_stock_remaining} ชิ้น แต่ต้องการ {total_units_sold} ชิ้น!")
                return  # ✅ หยุดการทำงาน ไม่ให้เพิ่มสินค้าเข้าตาราง

            row_position = self.sales_table.rowCount()
            self.sales_table.insertRow(row_position)

            # ✅ ใส่ข้อมูลในตาราง
            self.sales_table.setItem(row_position, 0, QTableWidgetItem(str(product_name)))
            self.sales_table.setItem(row_position, 1,
                                     QTableWidgetItem(str(new_stock_remaining)))  # ✅ อัปเดตคงเหลือล่าสุด
            self.sales_table.setItem(row_position, 2, QTableWidgetItem(f"{quantity} {unit_type}"))
            self.sales_table.setItem(row_position, 3, QTableWidgetItem(f"{price_display:,.2f}"))
            self.sales_table.setItem(row_position, 4, QTableWidgetItem(f"{total_price:,.2f}"))

            self.sales_table.scrollToBottom()
            self.sales_table.repaint()

            # ✅ DEBUG LOG
            print(f"🛒 DEBUG: ขาย {quantity} {unit_type} → ลดสต็อก {total_units_sold} ชิ้น")
            print(f"🛒 DEBUG: ราคาต่อ {unit_type} = {price_display}")
            print(f"🛒 DEBUG: ราคารวม = {total_price}")
            print(f"🛒 DEBUG: คงเหลือใหม่ในตารางขาย = {new_stock_remaining}")

        except Exception as e:
            print(f"❌ ERROR ใน update_sales_table: {e}")

    def save_sales(self):
        """บันทึกข้อมูลการขายลงฐานข้อมูล และอัปเดตสต็อก"""
        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            total_sales = 0  # ยอดขายรวมของรอบนี้
            sales_data = []  # เก็บข้อมูลสำหรับอัปเดตสต็อก

            for row in range(self.sales_table.rowCount()):
                product_item = self.sales_table.item(row, 0)  # สินค้า
                quantity_item = self.sales_table.item(row, 2)  # จำนวน
                total_price_item = self.sales_table.item(row, 4)  # ราคารวม

                if not all([product_item, quantity_item, total_price_item]):
                    continue  # ข้ามแถวที่ไม่มีข้อมูลครบ

                product = product_item.text()
                raw_quantity = quantity_item.text().strip()
                total_price = float(total_price_item.text().replace(",", ""))

                # ✅ แยกจำนวนและหน่วยสินค้าออกจากกัน
                quantity = int(''.join(filter(str.isdigit, raw_quantity)))  # แยกตัวเลขออกจากข้อความ
                if "ลัง" in raw_quantity:
                    unit_type = "ลัง"
                elif "แพ็ค" in raw_quantity:
                    unit_type = "แพ็ค"
                else:
                    unit_type = "ชิ้น"

                # ✅ ดึงค่าหน่วยต่อลังจากฐานข้อมูล
                cursor.execute("SELECT unit_conversion FROM stock WHERE product = ?", (product,))
                unit_conversion_data = cursor.fetchone()

                if unit_conversion_data:
                    unit_values = list(map(int, unit_conversion_data[0].split(":")))  # แปลง "1:3:24" → [1,3,24]
                    unit_per_pack = unit_values[1]
                    unit_per_carton = unit_values[2]
                else:
                    unit_per_pack, unit_per_carton = 1, 1  # ตั้งค่าเริ่มต้น

                # ✅ แปลงจำนวนให้เป็น "ชิ้น"
                unit_mapping = {"ชิ้น": 1, "แพ็ค": unit_per_pack, "ลัง": unit_per_carton}
                total_units_sold = quantity * unit_mapping[unit_type]

                # ✅ อัปเดตสต็อกให้ลดลง
                cursor.execute("""
                    UPDATE stock 
                    SET quantity = quantity - ?, 
                        sold_quantity = COALESCE(sold_quantity, 0) + ?, 
                        sold_revenue = COALESCE(sold_revenue, 0) + ?
                    WHERE product = ? AND quantity >= ?;
                """, (total_units_sold, total_units_sold, total_price, product, total_units_sold))

                total_sales += total_price
                sales_data.append((product, quantity, unit_type, total_price))

            # ✅ อัปเดตยอดขายรายวัน
            cursor.execute("UPDATE system_status SET daily_sales = daily_sales + ?", (total_sales,))
            conn.commit()
            conn.close()

            # ✅ อัปเดตแสดงผลยอดขายรายวัน และจำนวนที่ขายออก
            self.update_daily_sales_label()
            self.update_stock_display()  # โหลดข้อมูลใหม่จากฐานข้อมูล
            self.load_products()  # ✅ รีเรียง dropdown ตามสินค้าขายบ่อย

            QMessageBox.information(self, "✅ สำเร็จ", "บันทึกข้อมูลการขายและอัปเดตสต็อกเรียบร้อยแล้ว!")

        except Exception as e:
            print(f"❌ ERROR ใน save_sales(): {e}")

    def update_stock_display(self):
        """โหลดข้อมูลสต็อกใหม่และอัปเดตจำนวนคงเหลือในตาราง"""
        try:
            conn = self.connect_db()
            cursor = conn.cursor()

            for row in range(self.sales_table.rowCount()):
                product_name = self.sales_table.item(row, 0).text()

                # ✅ ดึงข้อมูลสต็อกปัจจุบันจากฐานข้อมูล
                cursor.execute("SELECT quantity FROM stock WHERE product = ?", (product_name,))
                stock_data = cursor.fetchone()

                if stock_data:
                    new_stock = stock_data[0]
                    self.sales_table.setItem(row, 1, QTableWidgetItem(str(new_stock)))  # ✅ อัปเดตคงเหลือในตารางขาย

            conn.close()
            print("✅ อัปเดตข้อมูลสต็อกเรียบร้อยแล้ว!")

        except Exception as e:
            print(f"❌ ERROR ใน update_stock_display(): {e}")

    def print_sales(self):
        """บันทึกใบเสร็จ PDF แยกเก็บเป็น receipts/ใบเสร็จ_YYYY-MM-DD_HH-MM-SS.pdf"""

        if self.sales_table.rowCount() == 0:
            QMessageBox.warning(self, "⚠️ แจ้งเตือน", "ไม่มีรายการขาย!")
            return

        # ✅ ตรวจสอบและสร้างโฟลเดอร์ receipts ถ้ายังไม่มี
        receipts_dir = "receipts"
        if not os.path.exists(receipts_dir):
            os.makedirs(receipts_dir)

        # ✅ เปลี่ยน `:` เป็น `-` ในชื่อไฟล์ (Windows รองรับ)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pdf_filename = f"{receipts_dir}/ใบเสร็จ_{timestamp}.pdf"

        # ✅ ปรับขนาดกระดาษให้เหมาะกับเครื่องพิมพ์ใบเสร็จ
        page_width = 80 * mm
        page_height = 120 * mm

        doc = SimpleDocTemplate(
            pdf_filename,
            pagesize=portrait((page_width, page_height)),
            leftMargin=1 * mm,
            rightMargin=1 * mm,
            topMargin=0 * mm,
            bottomMargin=0 * mm
        )

        # ✅ โหลดฟอนต์ภาษาไทย (รองรับทั้งรันจากซอร์ส และตอนเป็นไฟล์ .exe ของ PyInstaller)
        font_path = resource_path("THSarabunNew.ttf")
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("THSarabunNew", str(font_path)))
            font_name = "THSarabunNew"
        else:
            # ถ้าไม่เจอฟอนต์ไทย จะทำให้ภาษาไทยเพี้ยน/เป็นต่างดาวได้
            font_name = "Helvetica"

        styles = getSampleStyleSheet()
        styles["Normal"].fontName = font_name
        styles["Normal"].fontSize = 14
        styles["Normal"].leading = 16

        # ✅ บรรทัดแรก: "ใบเสร็จรับเงิน" อยู่ตรงกลาง
        header_table = Table([
            [Paragraph("<b>ใบเสร็จรับเงิน</b>", styles["Normal"])]
        ], colWidths=[30 * mm])

        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # ใบเสร็จรับเงิน อยู่ตรงกลาง
        ]))

        # ✅ บรรทัดที่สอง: "ร้านค้า Mimee_shop" อยู่ซ้าย + "วันที่และเวลา" อยู่ขวา
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        shop_date_table = Table([
            [Paragraph("<b>ร้านค้า Mimee_shop</b>", styles["Normal"]),  # ร้านค้า Mimee_shop ชิดซ้าย
             Paragraph(f"<b>วันที่:</b> {now}", styles["Normal"])]  # วันที่+เวลา ชิดขวา
        ], colWidths=[35 * mm, 45 * mm])

        shop_date_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # ร้านค้า Mimee_shop ชิดซ้าย
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),  # วันที่ + เวลา ชิดขวา
        ]))

        # ✅ ตารางสินค้า
        data = [
            [Paragraph("<b>สินค้า</b>", styles["Normal"]),
             Paragraph("<b>จำนวน</b>", styles["Normal"]),
             Paragraph("<b>ราคาต่อหน่วย</b>", styles["Normal"]),
             Paragraph("<b>ราคารวม</b>", styles["Normal"])]
        ]
        total_amount = 0

        for row in range(self.sales_table.rowCount()):
            product_name = self.sales_table.item(row, 0).text()
            quantity = self.sales_table.item(row, 2).text()
            unit_price = self.sales_table.item(row, 3).text()
            total_price = self.sales_table.item(row, 4).text()

            data.append([
                Paragraph(product_name, styles["Normal"]),
                Paragraph(quantity, styles["Normal"]),
                Paragraph(f"฿{unit_price}", styles["Normal"]),
                Paragraph(f"฿{total_price}", styles["Normal"])
            ])
            total_amount += float(total_price.replace(",", ""))

        # ✅ ปรับขนาดตารางให้เหมาะกับใบเสร็จ (70 mm)
        table = Table(data, colWidths=[30 * mm, 10 * mm, 15 * mm, 15 * mm])
        table.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ]))

        # ✅ สรุปราคารวม
        total_table = Table([[Paragraph(f"<b>รวมทั้งหมด:</b> ฿{total_amount:,.2f}", styles["Normal"])]],
                            colWidths=[70 * mm])
        total_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))

        # ✅ รวม Layout ทั้งหมด
        elements = [
            header_table,
            shop_date_table,
            table,total_table
        ]

        # ✅ บันทึก PDF แยกไฟล์ตามวันเวลา
        doc.build(elements)

        # ✅ เปิดไฟล์ PDF อัตโนมัติ
        os.system(f"start {pdf_filename}")

        QMessageBox.information(self, "✅ สำเร็จ", f"บันทึกใบเสร็จที่ {pdf_filename} สำเร็จ!")

    def closeEvent(self, event):
        """ล้างตารางเมื่อปิดหน้าต่าง"""
        self.sales_table.setRowCount(0)
        event.accept()



if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = SellWindow()
    window.show()
    sys.exit(app.exec_())



