import sqlite3

conn = sqlite3.connect('example/tracking_orders.sqlite')
cursor = conn.cursor()

# 查询 2026-05-31 当天是否有数据
cursor.execute("""
    SELECT COUNT(*) 
    FROM Orders 
    WHERE date_order_placed >= '2026-05-31 00:00:00' 
      AND date_order_placed < '2026-06-01 00:00:00'
""")
print("2026-05-31 当天的订单数:", cursor.fetchone()[0])

# 查看最后 10 条订单的日期
cursor.execute("""
    SELECT date_order_placed 
    FROM Orders 
    ORDER BY date_order_placed DESC 
    LIMIT 10
""")
print("最后 10 条订单日期:", cursor.fetchall())

conn.close()