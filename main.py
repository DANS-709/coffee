import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QHeaderView
)
from PyQt6 import uic


class CoffeeApp(QMainWindow):
    """
    Основной класс приложения для отображения информации о кофе из SQLite.
    """

    def __init__(self):
        super().__init__()
        self.DB_NAME = 'coffee.sqlite'

        # Загрузка интерфейса из файла .ui
        try:
            uic.loadUi('main.ui', self)
        except FileNotFoundError:
            self._show_error_box("Ошибка файла UI",
                                 "Не найден файл 'main.ui'. Убедитесь, что он находится в той же папке.")
            sys.exit(1)

        self.setWindowTitle("Каталог Кофе")

        # Установка обработчиков событий
        self.refreshButton.clicked.connect(self.load_coffee_data)

        # Настройка заголовков таблицы (для удобства)
        self.coffeeTable.setHorizontalHeaderLabels([
            "ID", "Сорт", "Обжарка", "Вид", "Описание вкуса", "Цена (₽)", "Объем (г)"
        ])

        # Растягиваем последний столбец (Описание вкуса) на всю ширину
        self.coffeeTable.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.Stretch
        )

        # Загрузка данных при старте
        self.load_coffee_data()

    def _get_db_connection(self):
        """Пытается установить соединение с базой данных."""
        try:
            conn = sqlite3.connect(self.DB_NAME)
            return conn
        except sqlite3.Error as e:
            self._show_error_box("Ошибка базы данных",
                                 f"Не удалось подключиться к базе данных '{self.DB_NAME}'.\nОшибка: {e}")
            return None

    def _show_error_box(self, title, message):
        """Отображает стандартное окно сообщения об ошибке."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

    def load_coffee_data(self):
        """Извлекает данные о кофе из базы данных и отображает их в таблице."""
        conn = self._get_db_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            # Выборка всех данных из таблицы
            query = "SELECT ID, sort_name, roast_degree, state, flavor_description, price, package_volume FROM coffee"
            cursor.execute(query)
            rows = cursor.fetchall()

            # Очистка таблицы перед заполнением
            self.coffeeTable.setRowCount(0)

            # Заполнение таблицы данными
            self.coffeeTable.setRowCount(len(rows))
            for row_index, row_data in enumerate(rows):
                for col_index, data in enumerate(row_data):
                    item = QTableWidgetItem(str(data))
                    self.coffeeTable.setItem(row_index, col_index, item)

            self.statusBar().showMessage(f"Загружено {len(rows)} записей.", 3000)

        except sqlite3.Error as e:
            self._show_error_box("Ошибка SQL",
                                 f"Не удалось выполнить запрос к базе данных.\nОшибка: {e}")
        finally:
            conn.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CoffeeApp()
    window.show()
    sys.exit(app.exec())