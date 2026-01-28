from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QFont, QFontDatabase

from database import init_db
from main_ui import SQLiteApp
from paths import user_db_path, templates_dir
import shutil
from pathlib import Path


def _ensure_user_db(app: QApplication) -> Path:
    """Ensure per-user DB exists. On first run, ask to start with Demo data or Empty."""
    dbp = user_db_path()
    if dbp.exists():
        return dbp

    tdir = templates_dir()
    demo = tdir / "demo.db"
    empty = tdir / "empty.db"

    # choose template
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Question)
    msg.setWindowTitle("เริ่มใช้งานครั้งแรก")
    msg.setText("ต้องการเริ่มต้นข้อมูลแบบไหน?")
    demo_btn = msg.addButton("โหมดตัวอย่าง (มีสินค้า/สต็อกเริ่มต้น)", QMessageBox.AcceptRole)
    empty_btn = msg.addButton("เริ่มใหม่ (ฐานข้อมูลว่าง)", QMessageBox.DestructiveRole)
    msg.setDefaultButton(demo_btn)
    msg.exec_()

    chosen = demo if msg.clickedButton() == demo_btn else empty
    if not chosen.exists():
        # fallback: create empty via init
        init_db(dbp)
        return dbp

    dbp.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(chosen), str(dbp))
    return dbp


def main() -> int:
    app = QApplication(sys.argv)

    # ตั้งฟอนต์ให้รองรับภาษาไทยใน UI
    try:
        font_id = QFontDatabase.addApplicationFont("THSarabunNew.ttf")
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                app.setFont(QFont(families[0], 12))
            else:
                app.setFont(QFont("Tahoma", 11))
        else:
            app.setFont(QFont("Tahoma", 11))
    except Exception:
        app.setFont(QFont("Tahoma", 11))

    # ensure db exists (copy demo/empty template on first run)
    dbp = _ensure_user_db(app)
    init_db(dbp)

    win = SQLiteApp()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
