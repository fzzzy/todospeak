

import sqlite3


class Accounts(object):
    def __init__(self):
        self.path = "accounts.db"
        self.db = sqlite3.connect(self.path)
        self.cursor = self.db.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS accounts
                              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                               name TEXT NOT NULL,
                               uuid TEXT NOT NULL,
                               created_at DATETIME DEFAULT CURRENT_TIMESTAMP)
                            ''')
        self.db.commit()

    def add_account(self, name, uuid):
        try:
            self.cursor.execute('''INSERT INTO accounts (name, uuid)
                                   VALUES (?, ?)''', (name, uuid))
            self.db.commit()
            return True
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return False

    def get_account(self, uuid):
        try:
            self.cursor.execute('''SELECT * FROM accounts
                                   WHERE uuid = ?''', (uuid,))
            account = self.cursor.fetchone()
            if account:
                return {
                    'id': account[0],
                    'name': account[1],
                    'uuid': account[2],
                    'created_at': account[3]
                }
            else:
                return None
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            return None
