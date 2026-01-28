import sqlite3
import uuid

from database import connect_db

try:
    from PyQt5.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QTableWidget,
        QTableWidgetItem,
        QPushButton,
        QMessageBox,
        QLabel,
        QHBoxLayout,
        QLineEdit,
        QGroupBox,
        QFormLayout,
        QComboBox,
        QGridLayout,
    )
    from PyQt5.QtGui import QColor
    from PyQt5.QtCore import pyqtSignal, QTimer
except ModuleNotFoundError as e:
    if getattr(e, "name", "") == "PyQt5":
        raise SystemExit(
            "ไม่พบ PyQt5 ใน interpreter ที่กำลังรันอยู่\n"
            "ให้รันด้วย venv ของโปรเจกต์นี้แทน:\n"
            "  C:\\Users\\tao\\Desktop\\Stock_PRO\\.venv\\Scripts\\python.exe main.py\n"
        ) from e
    raise


class StockWindow(QWidget):
    product_added = pyqtSignal()  # ✅ เพิ่ม signal แจ้งเตือนเมื่อมีสินค้าใหม่

    def __init__(self):
        super().__init__()
        self.setWindowTitle("📦 จัดการสต็อกสินค้า")
        self.setGeometry(300, 200, 1000, 600)

        # ✅ เช็คและเพิ่มคอลัมน์ unit_per_item ถ้ายังไม่มี
        self.ensure_unit_per_item_column()

        # ✅ Layout หลัก
        self.layout = QVBoxLayout()

        # ✅ สร้าง UI สำหรับเพิ่มสินค้า
        self.create_add_product_ui()

        # ✅ สร้าง UI สำหรับแสดงสต็อกสินค้า
        self.create_stock_table_ui()
        self.create_product_categories_table_ui()  # ✅ เพิ่มตาราง product_categories

        # ✅ ปุ่มปิดหน้าต่าง
        self.close_btn = QPushButton("❌ ปิดหน้าสต็อก")
        self.close_btn.clicked.connect(self.close)
        self.layout.addWidget(self.close_btn)

        self.setLayout(self.layout)
        self.update_stock_from_orders()  # ✅ ให้ทำงานทันทีเมื่อเปิด StockWindow
        self.load_stock_data()
        # ✅ ตั้งค่า Timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.load_product_categories_data)
        self.update_timer.start(10000)  # 10 วินาที

    def ensure_unit_per_item_column(self):
        """ตรวจสอบและเพิ่มคอลัมน์ unit_per_item ในตาราง stock, product_categories และ orders ถ้ายังไม่มี"""
        conn = connect_db()
        cursor = conn.cursor()

        try:
            ### ✅ ตรวจสอบและเพิ่ม unit_per_item ใน stock ###
            cursor.execute("PRAGMA table_info(stock);")
            stock_columns = [row[1] for row in cursor.fetchall()]
            if "unit_per_item" not in stock_columns:
                print("⚠️ กำลังเพิ่ม unit_per_item ใน stock...")
                cursor.execute("ALTER TABLE stock ADD COLUMN unit_per_item INTEGER DEFAULT 1;")
                conn.commit()
                cursor.execute("VACUUM;")  # ✅ รีเฟรช schema
                conn.commit()
                print("✅ เพิ่มคอลัมน์ 'unit_per_item' ใน stock สำเร็จ!")

            ### ✅ ตรวจสอบและเพิ่ม unit_per_item ใน product_categories ###
            cursor.execute("PRAGMA table_info(product_categories);")
            product_columns = [row[1] for row in cursor.fetchall()]
            if "unit_per_item" not in product_columns:
                print("⚠️ กำลังเพิ่ม unit_per_item ใน product_categories...")
                cursor.execute("ALTER TABLE product_categories ADD COLUMN unit_per_item INTEGER DEFAULT 1;")
                conn.commit()
                cursor.execute("VACUUM;")  # ✅ รีเฟรช schema
                conn.commit()
                print("✅ เพิ่มคอลัมน์ 'unit_per_item' ใน product_categories สำเร็จ!")

            ### ✅ ตรวจสอบและเพิ่ม unit_per_item ใน orders ###
            cursor.execute("PRAGMA table_info(orders);")
            orders_columns = [row[1] for row in cursor.fetchall()]
            if "unit_per_item" not in orders_columns:
                print("⚠️ กำลังเพิ่ม unit_per_item ใน orders...")
                cursor.execute("ALTER TABLE orders ADD COLUMN unit_per_item INTEGER DEFAULT 1;")
                conn.commit()
                cursor.execute("VACUUM;")  # ✅ รีเฟรช schema
                conn.commit()
                print("✅ เพิ่มคอลัมน์ 'unit_per_item' ใน orders สำเร็จ!")

            # ✅ Debug Schema หลังอัปเดต
            cursor.execute("PRAGMA table_info(stock);")


            cursor.execute("PRAGMA table_info(product_categories);")


            cursor.execute("PRAGMA table_info(orders);")


        except sqlite3.Error as e:
            print(f"❌ Error: {e}")

        finally:
            conn.close()

    def update_stock_from_orders(self):
        """อัปเดตสินค้าจากออเดอร์ที่จัดส่งสำเร็จ"""
        conn = self.connect_db()
        cursor = conn.cursor()

        try:
            print("🔄 update_stock_from_orders() ถูกเรียกแล้ว!")

            # ✅ ดึงออเดอร์ที่จัดส่งพัสดุสำเร็จ แต่ยังไม่ processed
            cursor.execute("""
                SELECT id, product, unit_per_item
                FROM orders
                WHERE status = 'จัดส่งพัสดุสำเร็จ' 
                AND processed = 0 
                AND tracking IS NOT NULL
            """)
            orders = cursor.fetchall()

            if not orders:
                print("ℹ️ ไม่มีออเดอร์ใหม่ที่ต้องเพิ่มเข้าสต็อก")
                return

            updated_orders = []

            for order_id, product, unit_per_item in orders:
                # ✅ ดึงข้อมูล unit_conversion จาก `product_categories`
                cursor.execute("""
                    SELECT sell_price_retail, sell_price_wholesale, barcode, unit_conversion 
                    FROM product_categories 
                    WHERE product_name = ?
                """, (product,))
                product_data = cursor.fetchone()

                if product_data:
                    sell_price_retail, sell_price_wholesale, barcode, unit_conversion = product_data
                else:
                    sell_price_retail = sell_price_wholesale = 0
                    barcode = "ไม่พบข้อมูล"
                    unit_conversion = "1:1"

                # ✅ แปลง unit_conversion (1:3:24) → [1, 3, 24]
                unit_values = list(map(int, unit_conversion.split(":")))

                if len(unit_values) == 3:
                    unit_per_pack, unit_per_carton = unit_values[1], unit_values[2]
                else:
                    unit_per_pack, unit_per_carton = 1, 1

                    # ✅ คำนวณจำนวนชิ้นจากจำนวนลังที่สั่งเข้า
                total_units = unit_per_item * unit_per_carton  # ✅ คูณจำนวนลังด้วยจำนวนชิ้นต่อลัง

                # ✅ ตรวจสอบว่าสินค้ามีอยู่ในสต็อกหรือยัง
                cursor.execute("SELECT id, quantity FROM stock WHERE product = ?", (product,))
                existing_stock = cursor.fetchone()

                if existing_stock:
                    stock_id, current_quantity = existing_stock
                    new_quantity = current_quantity + total_units
                    print(f"🔄 อัปเดต {product}: {current_quantity} → {new_quantity} ชิ้น")

                    cursor.execute("""
                        UPDATE stock 
                        SET quantity = ?, date_received = CURRENT_TIMESTAMP, 
                            sell_price_retail = ?, sell_price_wholesale = ?, barcode = ?, unit_conversion = ?
                        WHERE id = ?;
                    """, (new_quantity, sell_price_retail, sell_price_wholesale, barcode, unit_conversion, stock_id))

                else:
                    cursor.execute("""
                        INSERT INTO stock (product, quantity, date_received, sell_price_retail, sell_price_wholesale, barcode, unit_conversion)
                        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?);
                    """, (product, total_units, sell_price_retail, sell_price_wholesale, barcode, unit_conversion))
                    print(f"✅ เพิ่มสินค้าใหม่ {product} จำนวน {total_units} ใน stock")

                updated_orders.append(order_id)

            if updated_orders:
                cursor.executemany("UPDATE orders SET processed = 1 WHERE id = ?",
                                   [(order_id,) for order_id in updated_orders])
                print(f"✅ อัปเดต processed = 1 ให้ {len(updated_orders)} ออเดอร์")

            conn.commit()
            print("✅ Commit ฐานข้อมูลสำเร็จ!")

        except sqlite3.Error as e:
            print(f"❌ Error อัปเดต stock: {e}")

        finally:
            conn.close()

        self.load_stock_data()

    def create_add_product_ui(self):
        """สร้าง UI สำหรับเพิ่มสินค้า"""
        add_product_group = QGroupBox("➕ เพิ่มสินค้าใหม่")
        add_product_layout = QGridLayout()

        # ✅ ช่องกรอกข้อมูล
        self.new_product_name = QLineEdit()
        self.new_barcode = QLineEdit()
        self.new_sku_prefix = QLineEdit()
        self.new_sell_price_retail = QLineEdit()
        self.new_sell_price_wholesale = QLineEdit()
        self.new_unit_per_pack = QLineEdit()  # ✅ กลับมาแล้ว!
        self.new_unit_per_carton = QLineEdit()  # ✅ กลับมาแล้ว!

        self.new_product_name.setPlaceholderText("ชื่อสินค้า")
        self.new_barcode.setPlaceholderText("📌 ยิงบาร์โค้ดที่นี่...")
        self.new_sku_prefix.setPlaceholderText("รหัส SKU")
        self.new_sell_price_retail.setPlaceholderText("ราคาปลีกต่อลัง")
        self.new_sell_price_wholesale.setPlaceholderText("ราคาส่งต่อลัง")
        self.new_unit_per_pack.setPlaceholderText("กี่ชิ้นต่อแพ็ค")
        self.new_unit_per_carton.setPlaceholderText("กี่ชิ้นต่อลัง")

        # ✅ ช่องแสดงราคาต่อชิ้น (แสดงอัตโนมัติ)
        self.price_per_unit_retail = QLabel("📌 ราคาปลีกต่อชิ้น: - บาท")
        self.price_per_unit_wholesale = QLabel("📌 ราคาส่งต่อชิ้น: - บาท")

        # ✅ คำนวณราคาทุกครั้งที่เปลี่ยนค่า
        self.new_sell_price_retail.textChanged.connect(self.calculate_price_per_unit)
        self.new_sell_price_wholesale.textChanged.connect(self.calculate_price_per_unit)
        self.new_unit_per_pack.textChanged.connect(self.calculate_price_per_unit)
        self.new_unit_per_carton.textChanged.connect(self.calculate_price_per_unit)

        # ✅ ปุ่มบันทึกสินค้า
        self.add_product_btn = QPushButton("📌 บันทึกสินค้า")
        self.add_product_btn.clicked.connect(self.add_new_product_category)

        # ✅ จัดวาง UI
        add_product_layout.addWidget(QLabel("ชื่อสินค้า:"), 0, 0)
        add_product_layout.addWidget(self.new_product_name, 0, 1)

        add_product_layout.addWidget(QLabel("บาร์โค้ด:"), 1, 0)
        add_product_layout.addWidget(self.new_barcode, 1, 1)

        add_product_layout.addWidget(QLabel("รหัส SKU:"), 2, 0)
        add_product_layout.addWidget(self.new_sku_prefix, 2, 1)

        add_product_layout.addWidget(QLabel("ราคาปลีก (ลัง):"), 3, 0)
        add_product_layout.addWidget(self.new_sell_price_retail, 3, 1)

        add_product_layout.addWidget(QLabel("ราคาส่ง (ลัง):"), 4, 0)
        add_product_layout.addWidget(self.new_sell_price_wholesale, 4, 1)

        add_product_layout.addWidget(QLabel("กี่ชิ้นต่อแพ็ค:"), 5, 0)  # ✅ กลับมาแล้ว!
        add_product_layout.addWidget(self.new_unit_per_pack, 5, 1)  # ✅ กลับมาแล้ว!

        add_product_layout.addWidget(QLabel("กี่ชิ้นต่อลัง:"), 6, 0)  # ✅ กลับมาแล้ว!
        add_product_layout.addWidget(self.new_unit_per_carton, 6, 1)  # ✅ กลับมาแล้ว!

        add_product_layout.addWidget(self.price_per_unit_retail, 7, 0, 1, 2)
        add_product_layout.addWidget(self.price_per_unit_wholesale, 8, 0, 1, 2)

        add_product_layout.addWidget(self.add_product_btn, 9, 0, 1, 2)

        add_product_group.setLayout(add_product_layout)
        self.layout.addWidget(add_product_group)

    def create_product_categories_table_ui(self):
        """สร้าง UI สำหรับแสดงรายการ product_categories"""
        product_group = QGroupBox("📦 รายการหมวดหมู่สินค้า")
        product_layout = QVBoxLayout()

        # ✅ ตารางแสดงข้อมูล product_categories
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(6)
        self.product_table.setHorizontalHeaderLabels([
            "ID", "ชื่อสินค้า", "บาร์โค้ด", "ราคาปลีก", "ราคาส่ง", "หน่วยต่อรายการ"
        ])

        product_layout.addWidget(self.product_table)
        product_group.setLayout(product_layout)
        self.layout.addWidget(product_group)

        # ✅ โหลดข้อมูลทันที
        self.load_product_categories_data()

    def load_product_categories_data(self):
        """โหลดข้อมูล product_categories และเรียงเฉพาะตามชื่อสินค้า (ก - ฮ | A-Z)"""
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, product_name, barcode, sell_price_retail, sell_price_wholesale, unit_conversion
            FROM product_categories
            ORDER BY product_name COLLATE NOCASE ASC
        """)
        rows = cursor.fetchall()
        conn.close()

        self.product_table.setRowCount(len(rows))
        self.product_table.setColumnCount(6)  # ✅ ไม่มีหมวดหมู่
        self.product_table.setHorizontalHeaderLabels([
            "ID", "ชื่อสินค้า", "บาร์โค้ด", "ราคาปลีก", "ราคาส่ง", "หน่วยต่อรายการ"
        ])

        for row_idx, row_data in enumerate(rows):
            for col_idx, cell_value in enumerate(row_data):
                item = QTableWidgetItem(str(cell_value) if cell_value else "-")
                self.product_table.setItem(row_idx, col_idx, item)

    def calculate_price_per_unit(self):
        """คำนวณราคาปลีก/ส่งต่อชิ้นจากราคาลังอัตโนมัติ"""
        try:
            retail_price = float(self.new_sell_price_retail.text()) if self.new_sell_price_retail.text() else 0
            wholesale_price = float(self.new_sell_price_wholesale.text()) if self.new_sell_price_wholesale.text() else 0
            unit_per_pack = int(self.new_unit_per_pack.text()) if self.new_unit_per_pack.text() else 1
            unit_per_carton = int(self.new_unit_per_carton.text()) if self.new_unit_per_carton.text() else 1

            if unit_per_carton > 0:
                price_per_unit_retail = retail_price / unit_per_carton
                price_per_unit_wholesale = wholesale_price / unit_per_carton
            else:
                price_per_unit_retail = 0
                price_per_unit_wholesale = 0

            self.price_per_unit_retail.setText(f"📌 ราคาปลีกต่อชิ้น: {price_per_unit_retail:.2f} บาท")
            self.price_per_unit_wholesale.setText(f"📌 ราคาส่งต่อชิ้น: {price_per_unit_wholesale:.2f} บาท")

        except ValueError:
            self.price_per_unit_retail.setText("📌 ราคาปลีกต่อชิ้น: - บาท")
            self.price_per_unit_wholesale.setText("📌 ราคาส่งต่อชิ้น: - บาท")

    def add_new_product_category(self):
        """เพิ่มสินค้าใหม่ลงในฐานข้อมูล หรืออัปเดตข้อมูลถ้ามีอยู่แล้ว"""
        product_name = self.new_product_name.text().strip()
        barcode = self.new_barcode.text().strip()
        sku_prefix = self.new_sku_prefix.text().strip()
        sell_price_retail = self.new_sell_price_retail.text().strip()
        sell_price_wholesale = self.new_sell_price_wholesale.text().strip()
        unit_per_pack = self.new_unit_per_pack.text().strip()
        unit_per_carton = self.new_unit_per_carton.text().strip()

        if not product_name or not barcode or not sell_price_retail or not sell_price_wholesale or not unit_per_pack or not unit_per_carton:
            QMessageBox.warning(self, "แจ้งเตือน", "❗ กรุณากรอกข้อมูลให้ครบถ้วน!")
            return

        if not sku_prefix:
            sku_prefix = "-"

        try:
            sell_price_retail = float(sell_price_retail)
            sell_price_wholesale = float(sell_price_wholesale)
            unit_per_pack = int(unit_per_pack)
            unit_per_carton = int(unit_per_carton)

            if unit_per_carton <= 0:
                QMessageBox.warning(self, "แจ้งเตือน", "❗ จำนวนชิ้นต่อลังต้องมากกว่า 0!")
                return

            # ✅ คำนวณราคาต่อชิ้น
            price_per_unit_retail = sell_price_retail / unit_per_carton
            price_per_unit_wholesale = sell_price_wholesale / unit_per_carton

        except ValueError:
            QMessageBox.warning(self, "แจ้งเตือน", "❗ กรุณากรอกข้อมูลที่ถูกต้อง!")
            return

        unit_conversion = f"1:{unit_per_pack}:{unit_per_carton}"

        conn = None  # ป้องกันการใช้งาน conn ที่ผิดพลาด
        try:
            conn = sqlite3.connect("bot_system.db")
            cursor = conn.cursor()

            # ✅ ตรวจสอบว่าสินค้ามีอยู่แล้วหรือไม่
            cursor.execute("SELECT COUNT(*) FROM product_categories WHERE product_name = ?", (product_name,))
            exists = cursor.fetchone()[0]

            if exists:
                cursor.execute("""
                    UPDATE product_categories 
                    SET sell_price_retail = ?, sell_price_wholesale = ?, sku_prefix = ?, barcode = ?, unit_conversion = ?
                    WHERE product_name = ?;
                """, (
                price_per_unit_retail, price_per_unit_wholesale, sku_prefix, barcode, unit_conversion, product_name))
                conn.commit()
                QMessageBox.information(self, "สำเร็จ", f"✅ อัปเดตข้อมูลสินค้า '{product_name}' สำเร็จ!")
            else:
                cursor.execute("""
                    INSERT INTO product_categories (product_name, barcode, sku_prefix, sell_price_retail, sell_price_wholesale, unit_conversion)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (
                product_name, barcode, sku_prefix, price_per_unit_retail, price_per_unit_wholesale, unit_conversion))
                conn.commit()
                QMessageBox.information(self, "สำเร็จ", f"✅ เพิ่มสินค้า '{product_name}' สำเร็จ!")

            # ✅ รีโหลดตาราง
            self.load_product_categories_data()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "ข้อผิดพลาด", f"❌ เกิดข้อผิดพลาด: {e}")

        finally:
            if conn:
                conn.close()  # ✅ ปิดฐานข้อมูลเสมอ

        # ✅ เคลียร์ข้อมูลหลังบันทึก
        self.new_product_name.clear()
        self.new_barcode.clear()
        self.new_sku_prefix.clear()
        self.new_sell_price_retail.clear()
        self.new_sell_price_wholesale.clear()
        self.new_unit_per_pack.clear()
        self.new_unit_per_carton.clear()

    def sync_product_with_stock(product_name):
        """อัปเดตข้อมูลสต็อกให้ตรงกับ product_categories"""
        conn = connect_db()
        cursor = conn.cursor()

        # ✅ ดึงข้อมูลสินค้าจาก product_categories
        cursor.execute("""
            SELECT sell_price_retail, sell_price_wholesale, unit_conversion
            FROM product_categories WHERE product_name = ?;
        """, (product_name,))
        product_data = cursor.fetchone()

        if product_data:
            sell_price_retail, sell_price_wholesale, unit_conversion = product_data

            # ✅ ตรวจสอบว่าสินค้านี้มีอยู่ใน stock หรือยัง
            cursor.execute("SELECT COUNT(*) FROM stock WHERE product = ?", (product_name,))
            exists = cursor.fetchone()[0]

            if exists:
                # ✅ ถ้ามีอยู่แล้ว → อัปเดตข้อมูล
                cursor.execute("""
                    UPDATE stock 
                    SET sell_price_retail = ?, sell_price_wholesale = ?, unit_conversion = ?
                    WHERE product = ?;
                """, (sell_price_retail, sell_price_wholesale, unit_conversion, product_name))
                print(f"🔄 อัปเดตสินค้า {product_name} ในสต็อกให้ตรงกับ product_categories")

            else:
                # ✅ ถ้ายังไม่มี → เพิ่มสินค้าใหม่เข้า stock พร้อม unit_conversion ที่ถูกต้อง
                cursor.execute("""
                    INSERT INTO stock (product, quantity, sell_price_retail, sell_price_wholesale, unit_conversion)
                    VALUES (?, 0, ?, ?, ?);
                """, (product_name, sell_price_retail, sell_price_wholesale, unit_conversion))
                print(f"✅ เพิ่มสินค้า {product_name} ในสต็อกใหม่")

            conn.commit()

        conn.close()

    def create_stock_table_ui(self):
        """สร้าง UI สำหรับแสดงสต็อกสินค้า"""
        stock_group = QGroupBox("📦 รายการสต็อกสินค้า")
        stock_layout = QVBoxLayout()

        # ✅ ช่องค้นหาสินค้า
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 ค้นหาสินค้า...")
        self.search_btn = QPushButton("🔎 ค้นหา")
        self.search_btn.clicked.connect(self.load_stock_data)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        stock_layout.addLayout(search_layout)

        # ✅ ตารางสินค้า
        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(12)
        self.stock_table.setHorizontalHeaderLabels([
            "ID", "สินค้า", "SKU", "จำนวน", "หน่วยต่อรายการ", "ราคาทุน", "ราคาขายปลีก", "ราคาขายส่ง",
            "จำนวนที่ขายออก", "ยอดขายรวม", "กำไร", "วันที่รับเข้า"
        ])
        stock_layout.addWidget(self.stock_table)

        self.stock_table.setColumnHidden(2, True)  # ✅ ซ่อน SKU (ตำแหน่งเดิม)
        self.stock_table.setColumnHidden(5, True)  # ✅ ซ่อน ราคาทุน (เลื่อนไป 1 ตำแหน่ง)
        self.stock_table.setColumnHidden(10, True)  # ✅ ซ่อน กำไร (เลื่อนไป 1 ตำแหน่ง)
        self.stock_table.setColumnHidden(4, True)
        stock_group.setLayout(stock_layout)
        self.layout.addWidget(stock_group)

    def connect_db(self):
        """เชื่อมต่อฐานข้อมูล (ใช้ helper กลางเพื่อ path ชัวร์)"""
        return connect_db()

    def load_stock_data(self):
        """โหลดข้อมูลสต็อกสินค้าทั้งหมด และแสดงจำนวนที่ขายออก + ยอดขายรวม"""
        conn = self.connect_db()
        cursor = conn.cursor()

        # ✅ ดึงข้อมูลสต็อกจากฐานข้อมูล
        query = """
            SELECT id, product, sku, quantity, 
                   COALESCE(unit_per_item, 1), COALESCE(cost_price, 0), 
                   sell_price_retail, sell_price_wholesale, 
                   COALESCE(sold_quantity, 0), COALESCE(sold_revenue, 0), 
                   COALESCE(sold_revenue - (COALESCE(cost_price, 0) * COALESCE(sold_quantity, 0)), 0) AS profit, 
                   date_received
            FROM stock
            ORDER BY date_received DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        # ✅ กำหนดจำนวนคอลัมน์ให้ตรงกับตารางเดิม
        self.stock_table.setRowCount(len(rows))
        self.stock_table.setColumnCount(12)  # 🔥 คงจำนวนคอลัมน์เท่าของเดิม
        self.stock_table.setHorizontalHeaderLabels([
            "ID", "สินค้า", "SKU", "คงเหลือ/ชิ้น", "หน่วยต่อรายการ",
            "ราคาทุน", "ราคาปลีก", "ราคาส่ง",
            "จำนวนที่ขายออก", "ยอดขายรวม", "กำไร", "วันที่รับเข้า"
        ])

        # ✅ ใส่ข้อมูลลงในตาราง
        for row_idx, row_data in enumerate(rows):
            for col_idx, cell_value in enumerate(row_data):
                item = QTableWidgetItem(str(cell_value) if cell_value is not None else "")

                # ✅ ถ้าสต็อกเหลือน้อยกว่า 5 ชิ้น ให้เปลี่ยนพื้นหลังเป็นสีแดง
                if col_idx == 3 and int(row_data[col_idx]) < 5:
                    item.setBackground(QColor("#FF6666"))  # สีแดง
                    item.setForeground(QColor("#FFFFFF"))  # ตัวหนังสือสีขาว

                self.stock_table.setItem(row_idx, col_idx, item)

        print("✅ โหลดข้อมูลสต็อกเสร็จสิ้น!")
