import sqlite3

class Database:
    def __init__(self, db_name='shop.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, role TEXT DEFAULT 'user')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, parent_id INTEGER)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_categories_parent ON categories (parent_id)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, price REAL, category_id INTEGER, stock INTEGER, photo TEXT)''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_products_category ON products (category_id)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS carts (user_id INTEGER, product_id INTEGER, quantity INTEGER, PRIMARY KEY (user_id, product_id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, products TEXT, total REAL, delivery TEXT, payment TEXT, status TEXT DEFAULT 'new', address TEXT)''')
        self.conn.commit()

    def get_categories(self, parent_id=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM categories WHERE parent_id IS ?", (parent_id,))
        return cursor.fetchall()

    def get_products(self, category_id: int):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, description, price, stock, photo FROM products WHERE category_id = ?", (category_id,))
        return cursor.fetchall()

    def get_cart(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.price, c.quantity, p.photo 
            FROM carts c JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = ?
        """, (user_id,))
        return cursor.fetchall()

    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1):
        cursor = self.conn.cursor()
        cursor.execute("SELECT quantity FROM carts WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE carts SET quantity = quantity + ? WHERE user_id = ? AND product_id = ?", (quantity, user_id, product_id))
        else:
            cursor.execute("INSERT INTO carts (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, quantity))
        self.conn.commit()

    def remove_from_cart(self, user_id: int, product_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM carts WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        self.conn.commit()

    def clear_cart(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM carts WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def create_order(self, user_id: int, products: str, total: float, delivery: str, payment: str, address: str):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO orders (user_id, products, total, delivery, payment, address) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, products, total, delivery, payment, address))
        order_id = cursor.lastrowid
        self.conn.commit()
        return order_id

    def update_product_stock(self, product_id: int, quantity: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
        self.conn.commit()

    def add_user(self, user_id, role='user'):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, role) VALUES (?, ?)", (user_id, role))
        self.conn.commit()

    def is_admin(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result and result[0] == 'admin'

    def set_admin(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET role = 'admin' WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def add_category(self, name, parent_id=None):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO categories (name, parent_id) VALUES (?, ?)", (name, parent_id))
        self.conn.commit()

    def get_product(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        return cursor.fetchone()

    def delete_product(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        self.conn.commit()

    def get_orders(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,))
        return cursor.fetchall()

    def get_all_orders(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM orders")
        return cursor.fetchall()

    def update_order_status(self, order_id, status):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        self.conn.commit()

    def add_product(self, name, description, price, category_id, stock, photo):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO products (name, description, price, category_id, stock, photo) VALUES (?, ?, ?, ?, ?, ?)",
                       (name, description, price, category_id, stock, photo))
        self.conn.commit()