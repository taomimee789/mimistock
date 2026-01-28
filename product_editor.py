from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from database import connect_db


@dataclass
class ProductFormData:
    name: str
    barcode: str
    sku: str
    retail: float
    wholesale: float
    unit_conversion: str


class ProductEditorDialog(QDialog):
    """Simple dialog to add/update product_categories in bot_system.db."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("เพิ่ม/แก้ไขสินค้า")
        self.setModal(True)
        self.setMinimumWidth(520)

        root = QVBoxLayout()

        hint = QLabel(
            "กรอกข้อมูลสินค้าแล้วกด 'บันทึก'\n"
            "- ถ้ามีชื่อสินค้านี้อยู่แล้ว จะเป็นการอัปเดต\n"
            "- หน่วย: รูปแบบ 1:แพ็ค:ลัง (เช่น 1:6:24)"
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        form = QFormLayout()

        # ✅ ชื่อสินค้า: เลือกจากลิสต์ได้ + พิมพ์ค้นหาได้
        self.name = QComboBox()
        self.name.setEditable(True)
        self.name.setInsertPolicy(QComboBox.NoInsert)
        self.name.setPlaceholderText("พิมพ์เพื่อค้นหา/เลือกสินค้า")
        self._reload_product_names()

        self.barcode = QLineEdit()
        self.barcode.setPlaceholderText("เช่น 885xxxxxxxxxx")

        self.sku = QLineEdit()
        self.sku.setPlaceholderText("เช่น CHA")

        self.retail = QLineEdit()
        self.retail.setPlaceholderText("เช่น 25")
        self.retail.setValidator(QDoubleValidator(0.0, 1_000_000.0, 2))

        self.wholesale = QLineEdit()
        self.wholesale.setPlaceholderText("เช่น 20")
        self.wholesale.setValidator(QDoubleValidator(0.0, 1_000_000.0, 2))

        self.unit = QLineEdit()
        self.unit.setPlaceholderText("เช่น 1:6:24")

        form.addRow("ชื่อสินค้า:", self.name)
        form.addRow("บาร์โค้ด:", self.barcode)
        form.addRow("SKU:", self.sku)
        form.addRow("ปลีก:", self.retail)
        form.addRow("ส่ง:", self.wholesale)
        form.addRow("หน่วย:", self.unit)

        root.addLayout(form)

        btns = QHBoxLayout()
        btns.setAlignment(Qt.AlignRight)

        self.load_btn = QPushButton("โหลดตามชื่อ")
        self.load_btn.clicked.connect(self.load_by_name)

        self.save_btn = QPushButton("บันทึก")
        self.save_btn.clicked.connect(self.save)

        self.close_btn = QPushButton("ปิด")
        self.close_btn.clicked.connect(self.close)

        btns.addWidget(self.load_btn)
        btns.addWidget(self.save_btn)
        btns.addWidget(self.close_btn)

        root.addLayout(btns)

        self.setLayout(root)

    def _reload_product_names(self) -> None:
        """โหลดรายชื่อสินค้าในระบบมาให้เลือก/ค้นหาได้เร็ว"""
        try:
            conn = connect_db()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT product_name
                FROM product_categories
                ORDER BY product_name COLLATE NOCASE ASC
                """
            )
            names = [r[0] for r in cur.fetchall()]
            conn.close()
        except Exception:
            names = []

        current = self.name.currentText().strip() if self.name.currentText() else ""

        self.name.blockSignals(True)
        self.name.clear()
        self.name.addItems(names)

        # completer แบบค้นหาบางส่วนของคำ
        comp = QCompleter(names, self)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        self.name.setCompleter(comp)

        if current:
            idx = self.name.findText(current)
            if idx >= 0:
                self.name.setCurrentIndex(idx)
            else:
                self.name.setEditText(current)
        self.name.blockSignals(False)

    def _read(self) -> ProductFormData | None:
        name = self.name.currentText().strip()
        barcode = self.barcode.text().strip()
        sku = self.sku.text().strip() or "-"
        unit_conversion = self.unit.text().strip() or "1:1"

        if not name:
            QMessageBox.warning(self, "แจ้งเตือน", "กรุณากรอก 'ชื่อสินค้า'")
            return None

        try:
            retail = float(self.retail.text().strip() or 0)
            wholesale = float(self.wholesale.text().strip() or 0)
        except ValueError:
            QMessageBox.warning(self, "แจ้งเตือน", "ราคา (ปลีก/ส่ง) ต้องเป็นตัวเลข")
            return None

        # Validate unit_conversion (allow 1:6:24 etc.)
        try:
            parts = [int(p) for p in unit_conversion.split(":") if p != ""]
            if len(parts) < 2:
                raise ValueError
            if any(p <= 0 for p in parts):
                raise ValueError
        except Exception:
            QMessageBox.warning(self, "แจ้งเตือน", "หน่วยต้องเป็นรูปแบบตัวเลขคั่นด้วย ':' เช่น 1:6:24")
            return None

        return ProductFormData(
            name=name,
            barcode=barcode,
            sku=sku,
            retail=retail,
            wholesale=wholesale,
            unit_conversion=unit_conversion,
        )

    def load_by_name(self) -> None:
        name = self.name.currentText().strip()
        if not name:
            QMessageBox.information(self, "แจ้งเตือน", "พิมพ์ชื่อสินค้าก่อน แล้วค่อยกด 'โหลดตามชื่อ'")
            return

        conn = connect_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT barcode, sku_prefix, sell_price_retail, sell_price_wholesale, unit_conversion
            FROM product_categories
            WHERE product_name = ?
            """,
            (name,),
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            QMessageBox.information(self, "ไม่พบ", "ยังไม่มีสินค้านี้ในฐานข้อมูล (ถ้ากดบันทึก จะเป็นการเพิ่มใหม่)")
            return

        barcode, sku, retail, wholesale, unit_conversion = row
        self.barcode.setText(barcode or "")
        self.sku.setText(sku or "")
        self.retail.setText(str(retail or 0))
        self.wholesale.setText(str(wholesale or 0))
        self.unit.setText(unit_conversion or "1:1")

    def save(self) -> None:
        data = self._read()
        if not data:
            return

        conn = connect_db()
        cur = conn.cursor()

        # Upsert by product_name
        cur.execute("SELECT COUNT(*) FROM product_categories WHERE product_name = ?", (data.name,))
        exists = cur.fetchone()[0] or 0

        if exists:
            cur.execute(
                """
                UPDATE product_categories
                SET barcode = ?, sku_prefix = ?, sell_price_retail = ?, sell_price_wholesale = ?, unit_conversion = ?
                WHERE product_name = ?
                """,
                (data.barcode, data.sku, data.retail, data.wholesale, data.unit_conversion, data.name),
            )
        else:
            cur.execute(
                """
                INSERT INTO product_categories (product_name, barcode, sku_prefix, sell_price_retail, sell_price_wholesale, unit_conversion)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (data.name, data.barcode, data.sku, data.retail, data.wholesale, data.unit_conversion),
            )

        # ✅ ซิงค์ราคากับ stock ด้วย (SellWindow ใช้ราคาจาก stock ตอนขายจริง)
        cur.execute(
            """
            UPDATE stock
            SET sell_price_retail = ?,
                sell_price_wholesale = ?,
                barcode = COALESCE(NULLIF(?, ''), barcode),
                unit_conversion = COALESCE(NULLIF(?, ''), unit_conversion)
            WHERE product = ?
            """,
            (data.retail, data.wholesale, data.barcode, data.unit_conversion, data.name),
        )

        conn.commit()
        conn.close()

        # รีโหลดรายชื่อหลังบันทึก เผื่อเพิ่มสินค้าใหม่
        self._reload_product_names()

        QMessageBox.information(self, "สำเร็จ", "บันทึกสินค้าเรียบร้อย")
