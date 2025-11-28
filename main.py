import sys
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QHeaderView, QDialog
)
from PyQt6 import uic


class AddEditCoffeeForm(QDialog):
    """
    Форма для добавления новой записи или редактирования существующей.
    Загружает интерфейс из addEditCoffeeForm.ui.
    """

    def __init__(self, db_name, coffee_id=None):
        super().__init__()
        self.DB_NAME = db_name
        self.coffee_id = coffee_id
        self.is_edit_mode = coffee_id is not None

        # Загрузка интерфейса формы
        try:
            uic.loadUi('addEditCoffeeForm.ui', self)
        except FileNotFoundError:
            self._show_error_box("Ошибка файла UI",
                                 "Не найден файл 'addEditCoffeeForm.ui'."
                                 " Убедитесь, что он находится в той же папке.")
            sys.exit(1)

        self.setWindowTitle("Редактирование записи" if self.is_edit_mode else "Добавление новой записи")

        # Настройка кнопок
        self.saveButton.clicked.connect(self.save_data)
        self.cancelButton.clicked.connect(self.reject)  # QDialog.reject() закрывает с кодом 0

        # Настройка поля ID
        self.idEdit.setEnabled(self.is_edit_mode)
        if not self.is_edit_mode:
            self.idEdit.setText("Автоматически")

        # Инициализация и загрузка данных для редактирования
        if self.is_edit_mode:
            self.load_coffee_details()

    def _show_error_box(self, title, message):
        """Отображает стандартное окно сообщения об ошибке."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

    def _get_db_connection(self):
        """Пытается установить соединение с базой данных."""
        try:
            conn = sqlite3.connect(self.DB_NAME)
            return conn
        except sqlite3.Error as e:
            self._show_error_box("Ошибка базы данных",
                                 f"Не удалось подключиться к базе данных '{self.DB_NAME}'.\nОшибка: {e}")
            return None

    def load_coffee_details(self):
        """Загружает данные выбранной записи для редактирования."""
        conn = self._get_db_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            query = ("SELECT ID, sort_name, roast_degree, state,"
                     " flavor_description, price, package_volume FROM coffee WHERE ID = ?")
            cursor.execute(query, (self.coffee_id,))
            data = cursor.fetchone()

            if data:
                self.idEdit.setText(str(data[0]))
                self.sortNameEdit.setText(data[1])
                self.roastDegreeCombo.setCurrentText(data[2])
                self.stateCombo.setCurrentText(data[3])
                self.flavorDescriptionEdit.setText(data[4])
                self.priceEdit.setText(str(data[5]))
                self.packageVolumeEdit.setText(str(data[6]))
            else:
                self._show_error_box("Ошибка", "Запись не найдена.")
                self.reject()

        except sqlite3.Error as e:
            self._show_error_box("Ошибка SQL", f"Ошибка загрузки данных: {e}")
            self.reject()
        finally:
            conn.close()

    def save_data(self):
        """Проверяет данные и сохраняет их в базу данных (INSERT или UPDATE)."""
        sort_name = self.sortNameEdit.text().strip()
        roast_degree = self.roastDegreeCombo.currentText()
        state = self.stateCombo.currentText()
        flavor_description = self.flavorDescriptionEdit.toPlainText().strip()
        price_text = self.priceEdit.text().strip()
        volume_text = self.packageVolumeEdit.text().strip()

        # 1. Валидация обязательных полей
        if not sort_name or not price_text:
            self._show_error_box("Ошибка валидации",
                                 "Поля 'Название сорта' и 'Цена' обязательны для заполнения.")
            return

        # 2. Валидация числовых полей
        try:
            price = float(price_text)
            if price <= 0:
                raise ValueError
        except ValueError:
            self._show_error_box("Ошибка валидации", "Цена должна быть положительным числом.")
            return

        package_volume = None
        if volume_text:
            try:
                package_volume = int(volume_text)
                if package_volume <= 0:
                    raise ValueError
            except ValueError:
                self._show_error_box("Ошибка валидации",
                                     "Объем упаковки должен быть целым положительным числом.")
                return

        # Подготовка данных
        data = (sort_name, roast_degree, state, flavor_description, price, package_volume)

        conn = self._get_db_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            if self.is_edit_mode:
                # UPDATE
                query = """
                    UPDATE coffee SET 
                        sort_name = ?, roast_degree = ?, state = ?,
                         flavor_description = ?, price = ?, package_volume = ?
                    WHERE ID = ?
                """
                cursor.execute(query, data + (self.coffee_id,))
            else:
                # INSERT
                query = """
                    INSERT INTO coffee (sort_name, roast_degree, state,
                     flavor_description, price, package_volume)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, data)

            conn.commit()
            self.accept()  # QDialog.accept() закрывает с кодом 1 (успех)

        except sqlite3.Error as e:
            self._show_error_box("Ошибка SQL", f"Ошибка сохранения данных: {e}")
        finally:
            conn.close()


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
        self.addButton.clicked.connect(self.open_add_dialog)
        self.editButton.clicked.connect(self.open_edit_dialog)

        self.setup_table()

        # Загрузка данных при старте
        self.load_coffee_data()

    def _show_error_box(self, title, message):
        """Отображает стандартное окно сообщения об ошибке."""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

    def _get_db_connection(self):
        """Пытается установить соединение с базой данных."""
        try:
            conn = sqlite3.connect(self.DB_NAME)
            return conn
        except sqlite3.Error as e:
            self._show_error_box("Ошибка базы данных",
                                 f"Не удалось подключиться к базе данных '{self.DB_NAME}'.\nОшибка: {e}")
            return None

    def setup_table(self):
        """Настраивает внешний вид таблицы."""
        self.coffeeTable.setHorizontalHeaderLabels([
            "ID", "Сорт", "Обжарка", "Вид", "Описание вкуса", "Цена (₽)", "Объем (г)"
        ])

        # Растягиваем столбец "Описание вкуса" (индекс 4) на всю ширину
        self.coffeeTable.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        # Устанавливаем режим автоматического изменения размера для остальных столбцов
        for i in range(self.coffeeTable.columnCount()):
            if i != 4:
                self.coffeeTable.horizontalHeader().setSectionResizeMode(
                    i, QHeaderView.ResizeMode.ResizeToContents
                )

    def load_coffee_data(self):
        """Извлекает данные о кофе из базы данных и отображает их в таблице."""
        conn = self._get_db_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            query = ("SELECT ID, sort_name, roast_degree, state,"
                     " flavor_description, price, package_volume FROM coffee")
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

    def open_add_dialog(self):
        """Открывает форму для добавления новой записи."""
        dialog = AddEditCoffeeForm(self.DB_NAME)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_coffee_data()
            self.statusBar().showMessage("Новая запись успешно добавлена.", 3000)

    def open_edit_dialog(self):
        """Открывает форму для редактирования выбранной записи."""
        selected_rows = self.coffeeTable.selectedItems()
        if not selected_rows:
            self.statusBar().showMessage("Выберите строку для редактирования.", 3000)
            return

        # ID находится в первом столбце (индекс 0) выбранной строки
        try:
            # Получаем ID из первой ячейки первой выбранной строки
            coffee_id = int(selected_rows[0].text())
        except ValueError:
            self._show_error_box("Ошибка", "Некорректный ID записи.")
            return

        dialog = AddEditCoffeeForm(self.DB_NAME, coffee_id=coffee_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_coffee_data()
            self.statusBar().showMessage(f"Запись ID {coffee_id} успешно обновлена.", 3000)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CoffeeApp()
    window.show()
    sys.exit(app.exec())