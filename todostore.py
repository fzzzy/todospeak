

import unittest
import sqlite3
import os


class Lists(object):
    def __init__(self, sqlitepath):
        self.path = sqlitepath
        self.db = sqlite3.connect(sqlitepath)
        self.cursor = self.db.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS lists
                              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                               name TEXT NOT NULL,
                               created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS todos
                              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                               todo TEXT NOT NULL,
                               complete BOOLEAN NOT NULL CHECK (complete IN (0, 1)),
                               list_id INTEGER,
                               created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                               completed_at DATETIME DEFAULT NULL,
                               FOREIGN KEY(list_id) REFERENCES lists(id))''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS metadata
                              (id INTEGER PRIMARY KEY AUTOINCREMENT,
                               selected_list INTEGER NOT NULL)''')
        self.db.commit()
        self.cursor.execute("SELECT id FROM lists")
        results = self.cursor.fetchall()
        if not len(results):
            self.add_list("Default")
        self.cursor.execute("SELECT id FROM metadata")
        results = self.cursor.fetchall()
        if not len(results):
            self.cursor.execute(
                "INSERT INTO metadata (selected_list) VALUES (1)")
            self.db.commit()
        self.cursor.execute("SELECT selected_list FROM metadata WHERE id = 1")
        result = self.cursor.fetchone()
        self.selected_list = result[0]
        print("SELECTED LIST", self.selected_list)

    def add_list(self, name):
        self.cursor.execute("INSERT INTO lists (name) VALUES (?)", (name, ))
        self.cursor.execute("SELECT id FROM lists")
        results = self.cursor.fetchall()
        self.selected_list = len(results)
        self.cursor.execute(
            "UPDATE metadata SET selected_list = ? WHERE id = 1",
            (self.selected_list, ))
        self.db.commit()
        return self.cursor.lastrowid

    def del_list(self, index):
        self.cursor.execute("SELECT id FROM lists LIMIT ?", (index, ))
        results = self.cursor.fetchall()
        self.cursor.execute("DELETE FROM lists WHERE id=?", (results[-1][0], ))
        self.db.commit()
        return self.cursor.rowcount > 0

    def list_lists(self):
        self.cursor.execute("SELECT id, name FROM lists")
        return self.cursor.fetchall()

    def select_list(self, index):
        self.cursor.execute("SELECT id, name FROM lists LIMIT ?", (index, ))
        results = self.cursor.fetchall()
        self.selected_list = index
        self.selected_list_id = results[-1][0]
        self.cursor.execute(
            "UPDATE metadata SET selected_list = ? WHERE id = 1",
            (self.selected_list_id, ))
        self.db.commit()
        return Todos(self.db, self.selected_list_id, results[-1][1])


class Todos(object):
    def __init__(self, db, selected_list, name):
        self.db = db
        self.cursor = self.db.cursor()
        self.selected_list = selected_list
        self.name = name

    def add_todo(self, todo):
        self.cursor.execute(
            "INSERT INTO todos (todo, list_id, complete) VALUES (?, ?, 0)",
            (todo, self.selected_list))
        self.db.commit()
        return self.cursor.lastrowid

    def del_todo(self, index):
        self.cursor.execute(
            "SELECT id FROM todos WHERE list_id=? AND complete=0 LIMIT ?",
            (self.selected_list, index))
        results = self.cursor.fetchall()
        if results:
            self.cursor.execute(
                "DELETE FROM todos WHERE id=?",
                (results[-1][0],))
            self.db.commit()
            if self.cursor.rowcount > 0:
                self.selected_list = 1
                return True
        return False

    def read_todo(self, index):
        self.cursor.execute(
            "SELECT id, todo FROM todos WHERE list_id=? AND complete=0 LIMIT ?", 
            (self.selected_list, index))
        results = self.cursor.fetchall()
        if results:
            return results[-1]
        return None

    def read_all(self):
        self.cursor.execute(
            "SELECT id, todo FROM todos WHERE list_id=? AND complete=0",
            (self.selected_list,))
        return self.cursor.fetchall()

    def read_complete(self):
        self.cursor.execute(
            "SELECT id, todo FROM todos WHERE list_id=? AND complete=1",
            (self.selected_list, ))
        return self.cursor.fetchall()

    def mark_complete(self, index):
        self.cursor.execute(
            "SELECT id FROM todos WHERE list_id=? AND complete=0 LIMIT ?", 
            (self.selected_list, index))
        result = self.cursor.fetchall()
        self.cursor.execute(
            "UPDATE todos SET complete = 1, completed_at = CURRENT_TIMESTAMP WHERE id=?",
            (result[-1][0], ))
        self.db.commit()

    def mark_incomplete(self, index):
        self.cursor.execute(
            "SELECT id FROM todos WHERE list_id=? AND complete=1 LIMIT ?", 
            (self.selected_list, index))
        result = self.cursor.fetchall()
        self.cursor.execute(
            "UPDATE todos SET complete = 0, completed_at = NULL WHERE id=?",
            (result[-1][0], ))
        self.db.commit()


class TestLists(unittest.TestCase):
    def setUp(self):
        self.db_path = 'test_database.db'
        self.lists = Lists(self.db_path)

    def tearDown(self):
        self.lists.db.close()
        os.remove(self.db_path)

    def test_add_list(self):
        list_id = self.lists.add_list("Test List")
        self.assertIsNotNone(list_id)

    def test_del_list(self):
        self.lists.add_list("Test List")
        result = self.lists.del_list(1)
        self.assertTrue(result)

    def test_list_lists(self):
        self.lists.add_list("Test List 1")
        self.lists.add_list("Test List 2")
        lists = self.lists.list_lists()
        self.assertEqual(len(lists), 2)

    def test_select_list(self):
        self.lists.add_list("Test List")
        todos = self.lists.select_list(1)
        self.assertIsInstance(todos, Todos)


class TestTodos(unittest.TestCase):
    def setUp(self):
        self.db_path = 'test_database.db'
        self.lists = Lists(self.db_path)
        self.list_id = self.lists.add_list("Test List")
        self.todos = self.lists.select_list(1)

    def tearDown(self):
        self.lists.db.close()
        os.remove(self.db_path)

    def test_add_todo(self):
        todo_id = self.todos.add_todo("Test Todo")
        self.assertIsNotNone(todo_id)

    def test_del_todo(self):
        self.todos.add_todo("Test Todo")
        result = self.todos.del_todo(1)
        self.assertTrue(result)

    def test_read_todo(self):
        self.todos.add_todo("Test Todo")
        todo = self.todos.read_todo(1)
        self.assertIsNotNone(todo)
        self.assertEqual(todo[1], "Test Todo")

    def test_read_all(self):
        self.todos.add_todo("Test Todo 1")
        self.todos.add_todo("Test Todo 2")
        todos = self.todos.read_all()
        self.assertEqual(len(todos), 2)


if __name__ == '__main__':
    unittest.main()

