import sqlite3

def clear_all_data():
    """ล้างข้อมูลทั้งหมดจาก orders และ stock"""
    conn = sqlite3.connect("bot_system.db")
    cursor = conn.cursor()

    # ลบข้อมูลจาก orders และ stock
    cursor.execute("DELETE FROM orders")

    # รีเซ็ตค่า ID
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='orders'")

    conn.commit()
    conn.close()

    print("✅ ล้างข้อมูลสินค้าทั้งหมด และออเดอร์ทั้งหมดเรียบร้อย!")

# รันฟังก์ชัน
clear_all_data()