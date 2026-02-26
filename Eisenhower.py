import os
import sys
import json
from datetime import datetime

# ---------------- QtCore ---------------- #
from PySide6.QtCore import (
    Qt,
    QRect,
    QPoint,
    QSize,
    QDate,
)

# ---------------- QtGui ---------------- #
from PySide6.QtGui import (
    QAction,
    QIcon,
    QPalette,
    QColor,
    QTextCursor,
    QTextCharFormat,
    QTextDocument,
    QTextListFormat,
    QFont,
    QPixmap,
    QImage,
    QTextImageFormat,
)

# ---------------- QtWidgets ---------------- #
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QLineEdit,
    QDateEdit,
    QStackedWidget,
    QToolBar,
    QGridLayout,
    QDialog,
    QFormLayout,
    QComboBox,
    QTextEdit,
    QMessageBox,
    QFrame,
    QSizePolicy,
    QFileDialog,
    QTabWidget,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QRubberBand,
    QDialogButtonBox,
    QColorDialog,
    QCalendarWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
)

# ---------------- QtCharts ---------------- #
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
)



APP_DIR = os.path.join(os.getenv("APPDATA"), "Eisenhower")

if not os.path.exists(APP_DIR):
    os.makedirs(APP_DIR)

DATA_FILE = os.path.join(APP_DIR, "tasks.json")
NOTES_FILE = os.path.join(APP_DIR, "notes.json")
TOPICS_FILE = os.path.join(APP_DIR, "topics.json")



# ---------------------- Data model ---------------------- #

class Task:
    def __init__(
        self,
        title,
        category,
        due_date,
        status="open",
        created_at=None,
        completed_at=None,
        closing_comment=None,
        description=None,
    ):
        self.title = title
        self.category = category
        self.due_date = due_date  # stored as "yyyy-MM-dd"
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.completed_at = completed_at
        self.closing_comment = closing_comment
        self.description = description

    def to_dict(self):
        return {
            "title": self.title,
            "category": self.category,
            "due_date": self.due_date,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "closing_comment": self.closing_comment,
            "description": self.description,
        }

    @staticmethod
    def from_dict(d):
        return Task(
            title=d["title"],
            category=d.get("category", "plan"),
            due_date=d.get("due_date"),
            status=d.get("status", "open"),
            created_at=d.get("created_at"),
            completed_at=d.get("completed_at"),
            closing_comment=d.get("closing_comment"),
            description=d.get("description"),
        )

class TaskManager:
    def __init__(self):
        self.tasks = []
        self.load()

    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.tasks = [Task.from_dict(t) for t in data]
            except Exception:
                self.tasks = []
        else:
            self.tasks = []

    def save(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.tasks], f, indent=2)

    def add_task(self, task: Task):
        self.tasks.append(task)
        self.save()

    def all_open_tasks(self):
        return [t for t in self.tasks if t.status == "open"]

    def all_tasks(self):
        return self.tasks

    def archive_task(self, task: Task, comment: str | None):
        task.status = "done"

        # 🔥 FIX: preserve original category
        if not hasattr(task, "original_category") or not task.original_category:
            task.original_category = task.category

        task.completed_at = datetime.now().isoformat()
        task.closing_comment = comment
        self.save()

# ---------------------- Create Task Dialog ---------------------- #

class CalendarDialog(QDialog):
    def __init__(self, parent=None, initial_date=None):
        super().__init__(parent)
        self.setWindowTitle("Select Deadline")

        layout = QVBoxLayout(self)

        # --- Calendar ---
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setSelectionMode(QCalendarWidget.SelectionMode.SingleSelection)

        # Today highlight (yellow)
        today = QDate.currentDate()
        fmt_today = QTextCharFormat()
        fmt_today.setBackground(QColor("yellow"))
        self.calendar.setDateTextFormat(today, fmt_today)

        # Initial date
        if initial_date:
            self.calendar.setSelectedDate(initial_date)
        else:
            self.calendar.setSelectedDate(today)

        layout.addWidget(self.calendar)

        # --- Selected date label (your visual confirmation) ---
        self.selected_label = QLabel()
        self.update_selected_label(self.calendar.selectedDate())
        layout.addWidget(self.selected_label)

        # Update label whenever user clicks a date
        self.calendar.selectionChanged.connect(
            lambda: self.update_selected_label(self.calendar.selectedDate())
        )

        # Today button
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(lambda: self.calendar.setSelectedDate(today))
        layout.addWidget(today_btn)

        # OK / Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_selected_label(self, date):
        self.selected_label.setText(f"Selected date: {date.toString('dd.MM.yyyy')}")

    def selected_date(self):
        return self.calendar.selectedDate()


class CreateTaskDialog(QDialog):
    def __init__(self, manager: TaskManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Create Task")
        self.setMinimumWidth(450)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        # --- Title ---
        self.title_edit = QLineEdit()
        form.addRow("Title:", self.title_edit)

        # --- Description ---
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(80)
        form.addRow("Description:", self.description_edit)

        # --- Deadline (custom calendar dialog) ---
        deadline_container = QWidget()
        deadline_layout = QHBoxLayout(deadline_container)
        deadline_layout.setContentsMargins(0, 0, 0, 0)
        deadline_layout.setSpacing(4)

        self.due_date_edit = QDateEdit()
        self.due_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.due_date_edit.setDate(QDate.currentDate())
        self.due_date_edit.setMinimumHeight(28)
        self.due_date_edit.setCalendarPopup(False)  # we handle calendar ourselves

        calendar_btn = QPushButton("📅")
        calendar_btn.setFixedWidth(32)
        calendar_btn.clicked.connect(self.open_calendar_dialog)

        deadline_layout.addWidget(self.due_date_edit)
        deadline_layout.addWidget(calendar_btn)

        form.addRow("Deadline:", deadline_container)

        # --- Category ---
        self.category_combo = QComboBox()
        self.category_combo.addItem("")
        self.category_combo.addItem("Do")
        self.category_combo.addItem("Plan")
        self.category_combo.addItem("Delegate")
        self.category_combo.addItem("Wait")
        form.addRow("Category:", self.category_combo)

        layout.addLayout(form)

        # --- Buttons ---
        btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_task)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)

        layout.addLayout(btns)
        self.setLayout(layout)

    def open_calendar_dialog(self):
        dlg = CalendarDialog(self, self.due_date_edit.date())
        if dlg.exec() == QDialog.Accepted:
            self.due_date_edit.setDate(dlg.selected_date())

    def save_task(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing title", "Please enter a task title.")
            return

        category = self.category_combo.currentText().strip().lower()
        if category not in ("do", "plan", "delegate", "wait"):
            QMessageBox.warning(self, "Missing category", "Please choose a category.")
            return

        due_date_iso = self.due_date_edit.date().toString("yyyy-MM-dd")

        task = Task(
            title=title,
            category=category,
            due_date=due_date_iso,
            status="open",
            description=self.description_edit.toPlainText().strip(),
        )
        self.manager.add_task(task)
        self.accept()

# ---------------------- Edit Task Dialog ---------------------- #

class EditTaskDialog(QDialog):
    def __init__(self, manager: TaskManager, task: Task, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.task = task
        self.setWindowTitle("Edit Task")
        self.setMinimumWidth(500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        # --- Title ---
        self.title_edit = QLineEdit(self.task.title)
        form.addRow("Title:", self.title_edit)

        # --- Description ---
        self.description_edit = QTextEdit(self.task.description or "")
        self.description_edit.setFixedHeight(80)
        form.addRow("Description:", self.description_edit)

        expand_btn = QPushButton("Open full editor…")
        expand_btn.clicked.connect(self.open_full_editor)
        form.addRow("", expand_btn)

        # --- Deadline (custom calendar dialog) ---
        deadline_container = QWidget()
        deadline_layout = QHBoxLayout(deadline_container)
        deadline_layout.setContentsMargins(0, 0, 0, 0)
        deadline_layout.setSpacing(4)

        self.due_date_edit = QDateEdit()
        self.due_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.due_date_edit.setCalendarPopup(False)  # we use our own dialog

        # Load existing date
        if self.task.due_date:
            try:
                dt = datetime.strptime(self.task.due_date, "%Y-%m-%d")
                self.due_date_edit.setDate(dt)
            except Exception:
                self.due_date_edit.setDate(datetime.now())
        else:
            self.due_date_edit.setDate(datetime.now())

        # Calendar button
        calendar_btn = QPushButton("📅")
        calendar_btn.setFixedWidth(32)
        calendar_btn.clicked.connect(self.open_calendar_dialog)

        deadline_layout.addWidget(self.due_date_edit)
        deadline_layout.addWidget(calendar_btn)

        form.addRow("Deadline:", deadline_container)

        # --- Category ---
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Do", "Plan", "Delegate", "Wait"])
        if self.task.category in ("do", "plan", "delegate", "wait"):
            idx = {"do": 0, "plan": 1, "delegate": 2, "wait": 3}[self.task.category]
            self.category_combo.setCurrentIndex(idx)
        form.addRow("Category:", self.category_combo)

        layout.addLayout(form)

        # --- Closing comment ---
        self.comment_edit = QTextEdit()
        self.comment_edit.setPlaceholderText("Closing comment (only used when closing the task)...")
        layout.addWidget(QLabel("Closing comment (optional when closing):"))
        layout.addWidget(self.comment_edit)

        # --- Buttons ---
        btns = QHBoxLayout()
        save_btn = QPushButton("Save changes")
        save_btn.clicked.connect(self.save_changes)
        close_btn = QPushButton("Close task")
        close_btn.clicked.connect(self.close_task)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(save_btn)
        btns.addWidget(close_btn)
        btns.addWidget(cancel_btn)

        layout.addLayout(btns)
        self.setLayout(layout)

    # --- Calendar dialog ---
    def open_calendar_dialog(self):
        dlg = CalendarDialog(self, self.due_date_edit.date())
        if dlg.exec() == QDialog.Accepted:
            self.due_date_edit.setDate(dlg.selected_date())

    # --- Save changes ---
    def save_changes(self):
        self.task.title = self.title_edit.text().strip()
        self.task.description = self.description_edit.toPlainText().strip()
        self.task.due_date = self.due_date_edit.date().toString("yyyy-MM-dd")

        cat = self.category_combo.currentText().strip().lower()
        if cat in ("do", "plan", "delegate", "wait"):
            self.task.category = cat

        self.manager.save()
        self.accept()

    # --- Close task ---
    def close_task(self):
        comment = self.comment_edit.toPlainText().strip()
        self.manager.archive_task(self.task, comment if comment else None)
        self.accept()

    # --- Full editor for description ---
    def open_full_editor(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Description")
        layout = QVBoxLayout()

        big_edit = QTextEdit()
        big_edit.setPlainText(self.description_edit.toPlainText())
        layout.addWidget(big_edit)

        btns = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(lambda: (self.description_edit.setPlainText(big_edit.toPlainText()), dlg.accept()))
        cancel.clicked.connect(dlg.reject)
        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)

        layout.addLayout(btns)
        dlg.setLayout(layout)
        dlg.exec()

# ---------------------- Matrix + drag & drop ---------------------- #

class MatrixView(QWidget):
    def __init__(self, manager, refresh_all_callback):
        super().__init__()
        self.manager = manager
        self.refresh_all_callback = refresh_all_callback
        self.last_dragged_task = None
        self.init_ui()

    # ---------------------- Overdue Helper ---------------------- #
    def is_overdue(self, date_str):
        if not date_str:
            return False
        d = QDate.fromString(date_str, "yyyy-MM-dd")
        return d.isValid() and d < QDate.currentDate()

    # ---------------------- Due Soon Helper ---------------------- #
    def is_due_today_or_tomorrow(self, date_str):
        if not date_str:
            return False
        d = QDate.fromString(date_str, "yyyy-MM-dd")
        if not d.isValid():
            return False
        today = QDate.currentDate()
        return d == today or d == today.addDays(1)

    # ---------------------- UI SETUP ---------------------- #
    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Eisenhower Matrix")
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)

        self.q_do = CategoryList("do", self)
        self.q_plan = CategoryList("plan", self)
        self.q_delegate = CategoryList("delegate", self)
        self.q_wait = CategoryList("wait", self)

        def quadrant_frame(title_text, color, inner_widget):
            frame = QFrame()
            frame.setFrameShape(QFrame.StyledPanel)
            frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #bdc3c7;
                    border-radius: 6px;
                    background-color: #fdfdfd;
                }
            """)
            v = QVBoxLayout()
            header = QLabel(title_text)
            header.setStyleSheet(f"font-weight: bold; color: {color}; padding: 4px;")
            v.addWidget(header)
            v.addWidget(inner_widget)
            frame.setLayout(v)
            return frame

        grid.addWidget(quadrant_frame("Urgent + Important (Do)", "#e67e22", self.q_do), 0, 0)
        grid.addWidget(quadrant_frame("Not urgent + Important (Plan)", "#27ae60", self.q_plan), 0, 1)
        grid.addWidget(quadrant_frame("Urgent + Not important (Ask / Delegate)", "#8e44ad", self.q_delegate), 1, 0)
        grid.addWidget(quadrant_frame("Waiting / Blocked (Wait)", "#c0392b", self.q_wait), 1, 1)

        layout.addLayout(grid)
        self.setLayout(layout)
        self.refresh()

    # ---------------------- MAIN REFRESH ---------------------- #
    def refresh(self):
        # Clear all quadrants
        for lst in (self.q_do, self.q_plan, self.q_delegate, self.q_wait):
            lst.clear()

        # --- Helpers for sorting/grouping ---
        def parse_due(t):
            """Return datetime for due_date or None if missing/invalid."""
            ds = getattr(t, "due_date", None)
            if not ds:
                return None
            try:
                return datetime.strptime(ds, "%Y-%m-%d")
            except Exception:
                return None

        def parse_created_at(t):
            """Optional: provide stable tie-breaker if Task has created_at."""
            c = getattr(t, "created_at", None)
            if isinstance(c, datetime):
                return c
            if isinstance(c, str):
                try:
                    # Accept ISO-like strings
                    return datetime.fromisoformat(c)
                except Exception:
                    pass
            return datetime.min  # fallback

        def norm_cat(cat):
            c = (cat or "").strip().lower()
            if c == "ask":  # normalize legacy
                c = "delegate"
            if c not in ("do", "plan", "delegate", "wait"):
                c = "plan"
            return c

        # Group tasks by normalized category
        buckets = {"do": [], "plan": [], "delegate": [], "wait": []}
        for t in self.manager.all_open_tasks():
            c = norm_cat(getattr(t, "category", None))
            t.category = c  # ensure normalized
            buckets[c].append(t)

        # Sort each category by due date ascending; undated last
        def sort_key(t):
            d = parse_due(t)
            return (
                d is None,                  # dated first (False < True)
                d or datetime.max,          # actual due date (or max for undated)
                parse_created_at(t),        # tie-breaker if available
                getattr(t, "title", ""),    # final deterministic tie-breaker
            )

        for cat in buckets:
            buckets[cat].sort(key=sort_key)

        # Populate UI
        def add_task_to_widget(t, target_list):
            desc = (t.description or "").replace("\n", " ").strip()

            # Format date for display
            if t.due_date:
                try:
                    dt = datetime.strptime(t.due_date, "%Y-%m-%d")
                    date_str = dt.strftime("%d.%m.%Y")
                except Exception:
                    date_str = t.due_date
            else:
                date_str = "(no date)"

            # Build row widget
            widget = QWidget()
            h = QHBoxLayout(widget)
            h.setContentsMargins(4, 2, 4, 2)
            h.setSpacing(8)

            widget.setMaximumWidth(self.width() - 20)

            # --- TITLE ---
            title_label = QLabel(t.title)
            font = title_label.font()
            font.setBold(True)
            title_label.setFont(font)
            title_label.setMinimumWidth(100)
            title_label.setMaximumWidth(180)
            title_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

            # --- DATE ---
            date_label = QLabel(date_str)
            date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            date_label.setMinimumWidth(80)
            date_label.setMaximumWidth(80)
            date_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

            # --- DESCRIPTION ---
            desc_label = QLabel(desc)
            desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            desc_label.setMinimumWidth(0)

            h.addWidget(title_label)
            h.addWidget(date_label)
            h.addWidget(desc_label)

            h.setStretch(0, 0)
            h.setStretch(1, 0)
            h.setStretch(2, 1)

            # Update elision on resize
            widget.resizeEvent = lambda event, w=widget, task=t: self.update_elision(w, task)

            # Create list item
            item = QListWidgetItem()
            item.setData(Qt.UserRole, t)
            item.setSizeHint(widget.sizeHint())

            # Overdue / due-soon highlighting
            if self.is_overdue(t.due_date):
                color = "red"
            elif self.is_due_today_or_tomorrow(t.due_date):
                color = "#e67e22"  # orange
            else:
                color = "black"

            title_label.setStyleSheet(f"color: {color};")
            date_label.setStyleSheet(f"color: {color};")
            desc_label.setStyleSheet(f"color: {color};")

            target_list.addItem(item)
            target_list.setItemWidget(item, widget)

        for t in buckets["do"]:
            add_task_to_widget(t, self.q_do)
        for t in buckets["plan"]:
            add_task_to_widget(t, self.q_plan)
        for t in buckets["delegate"]:
            add_task_to_widget(t, self.q_delegate)
        for t in buckets["wait"]:
            add_task_to_widget(t, self.q_wait)

    # ---------------------- ELLIPSIZING ---------------------- #
    def update_elision(self, widget, task):
        layout = widget.layout()
        title_label = layout.itemAt(0).widget()
        date_label  = layout.itemAt(1).widget()
        desc_label  = layout.itemAt(2).widget()

        # Title
        fm_title = title_label.fontMetrics()
        title_label.setText(
            fm_title.elidedText(task.title, Qt.ElideRight, title_label.width())
        )

        # Description
        desc = (task.description or "").replace("\n", " ").strip()
        fm_desc = desc_label.fontMetrics()
        desc_label.setText(
            fm_desc.elidedText(desc, Qt.ElideRight, desc_label.width())
        )

    # ---------------------- RESIZE HANDLER ---------------------- #
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh()

    # ---------------------- EDIT TASK ---------------------- #
    def edit_task_from_item(self, item: QListWidgetItem):
        task = item.data(Qt.UserRole)
        dlg = EditTaskDialog(self.manager, task, self)
        if dlg.exec():
            self.refresh_all_callback()

    # ---------------------- DEADLINE UPDATE ---------------------- #
    def ask_deadline_update(self, task):
        dlg = QDialog(self)
        dlg.setWindowTitle("Choose new deadline")
        v = QVBoxLayout(dlg)

        # Calendar
        cal = QCalendarWidget()
        cal.setGridVisible(True)
        cal.setSelectionMode(QCalendarWidget.SelectionMode.SingleSelection)

        # Today highlight
        today = QDate.currentDate()
        fmt_today = QTextCharFormat()
        fmt_today.setBackground(QColor("yellow"))
        cal.setDateTextFormat(today, fmt_today)

        # Initial date
        if task.due_date:
            try:
                dt = datetime.strptime(task.due_date, "%Y-%m-%d")
                cal.setSelectedDate(QDate(dt.year, dt.month, dt.day))
            except Exception:
                cal.setSelectedDate(today)
        else:
            cal.setSelectedDate(today)

        v.addWidget(cal)

        # Selected date label
        selected_label = QLabel()
        selected_label.setText(f"Selected date: {cal.selectedDate().toString('dd.MM.yyyy')}")
        v.addWidget(selected_label)

        # Update label when user clicks a date
        cal.selectionChanged.connect(
            lambda: selected_label.setText(
                f"Selected date: {cal.selectedDate().toString('dd.MM.yyyy')}"
            )
        )

        # Today button
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(lambda: cal.setSelectedDate(today))
        v.addWidget(today_btn)

        # OK / Cancel
        btns = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(dlg.accept)
        cancel.clicked.connect(dlg.reject)
        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        v.addLayout(btns)

        if dlg.exec():
            selected = cal.selectedDate()
            task.due_date = selected.toString("yyyy-MM-dd")
            # Notify the outer UI to refresh if that's your pattern elsewhere
            if callable(self.refresh_all_callback):
                self.refresh_all_callback()


class CategoryList(QListWidget):
    def __init__(self, category_name, parent_matrix):
        super().__init__()
        self.category_name = category_name
        self.parent_matrix = parent_matrix

        self.setSelectionMode(QListWidget.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QListWidget.DragDrop)

        self.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                color: #000000;
            }
        """)

        self.itemDoubleClicked.connect(self.parent_matrix.edit_task_from_item)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            self.parent_matrix.last_dragged_task = item.data(Qt.UserRole)
        super().startDrag(supportedActions)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        super().dropEvent(event)
        event.acceptProposedAction()

        task = self.parent_matrix.last_dragged_task
        self.parent_matrix.last_dragged_task = None

        if not task:
            return

        old = task.category
        new = self.category_name

        if old == new:
            return

        # 🔥 FIX: update original_category so archive remembers the new quadrant
        task.original_category = new

        choice = QMessageBox.question(
            self,
            "Update deadline?",
            "You moved this task to a new category.\n"
            "Do you want to update the deadline?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        task.category = new

        if choice == QMessageBox.Yes:
            self.parent_matrix.ask_deadline_update(task)

        self.parent_matrix.manager.save()
        self.parent_matrix.refresh_all_callback()

# ---------------------- Timeline ---------------------- #

class TimelineView(QWidget):
    def __init__(self, manager: TaskManager, refresh_all_callback):
        super().__init__()
        self.manager = manager
        self.refresh_all_callback = refresh_all_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Timeline")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2980b9;")
        layout.addWidget(title)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.edit_task_from_item)
        layout.addWidget(self.list)

        self.setLayout(layout)
        self.refresh()

    def refresh(self):
        self.list.clear()
        tasks = [t for t in self.manager.all_open_tasks()]
        tasks.sort(key=lambda t: (t.due_date is None, t.due_date or ""))

        for t in tasks:
            desc = (t.description or "").replace("\n", " ").strip()
            max_len = 80
            if len(desc) > max_len:
                desc = desc[:max_len] + "…"

            if t.due_date:
                try:
                    dt = datetime.strptime(t.due_date, "%Y-%m-%d")
                    date_str = dt.strftime("%d.%m.%Y")
                except Exception:
                    date_str = t.due_date
            else:
                date_str = "(no date)"

            label = f"{date_str}   [{t.category.upper()}]   {t.title}"
            if desc:
                label += f" — {desc}"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, t)
            item.setForeground(Qt.black)

            if t.due_date:
                try:
                    due = datetime.strptime(t.due_date, "%Y-%m-%d")
                    if due < datetime.now():
                        item.setForeground(Qt.red)
                except Exception:
                    pass

            self.list.addItem(item)

    def edit_task_from_item(self, item: QListWidgetItem):
        task = item.data(Qt.UserRole)
        dlg = EditTaskDialog(self.manager, task, self)
        if dlg.exec():
            self.refresh_all_callback()

# ---------------------- Archive Task ---------------------- #

class ArchiveTaskDialog(QDialog):
    def __init__(self, task: Task, manager: TaskManager, parent=None):
        super().__init__(parent)
        self.task = task
        self.manager = manager

        # Preserve original category (normalize old values)
        original = (task.category or "").strip().lower()
        if original == "ask":
            original = "delegate"
        self.original_category = original or "plan"

        self.setWindowTitle("Archived Task")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel(f"<b>{task.title}</b>")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Category
        layout.addWidget(QLabel(f"Category: {self.original_category.capitalize()}"))

        # Deadline
        layout.addWidget(QLabel(f"Deadline: {task.due_date}"))

        # Description
        layout.addWidget(QLabel("<b>Description:</b>"))
        desc_label = QLabel(task.description or "(No description)")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # Closing comment
        if task.closing_comment:
            layout.addWidget(QLabel("<b>Closing Comment:</b>"))
            comment_label = QLabel(task.closing_comment)
            comment_label.setWordWrap(True)
            layout.addWidget(comment_label)

        # Buttons
        btns = QHBoxLayout()
        restore_btn = QPushButton("Restore to Matrix")
        restore_btn.clicked.connect(self.restore_task)

        delete_btn = QPushButton("Delete Permanently")
        delete_btn.clicked.connect(self.delete_task)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        btns.addStretch()
        btns.addWidget(restore_btn)
        btns.addWidget(delete_btn)
        btns.addWidget(close_btn)

        layout.addLayout(btns)

    def restore_task(self):
        # Restore original category
        cat = getattr(self.task, "original_category", None)
        if not cat:
            cat = self.task.category

        cat = (cat or "").strip().lower()

        # Normalize old values
        if cat == "ask":
            cat = "delegate"

        # Final safety
        if cat not in ("do", "plan", "delegate", "wait"):
            cat = "plan"

        self.task.category = cat
        self.task.status = "open"
        self.manager.save()
        self.accept()

    def delete_task(self):
        confirm = QMessageBox.question(
            self,
            "Delete Task?",
            f"Delete permanently:\n\n{self.task.title}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.manager.tasks.remove(self.task)
            self.manager.save()
            self.accept()

# ---------------------- Archive View ---------------------- #

class ArchiveView(QWidget):
    def __init__(self, manager: TaskManager):
        super().__init__()
        self.manager = manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Archive")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #7f8c8d;")
        layout.addWidget(title)

        # --- Buttons row ---
        btn_row = QHBoxLayout()

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected)
        btn_row.addWidget(delete_btn)

        clear_btn = QPushButton("Clear Archive")
        clear_btn.clicked.connect(self.clear_archive)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # --- List of archived tasks ---
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.open_archived_task)
        layout.addWidget(self.list)

        self.setLayout(layout)
        self.refresh()

    def refresh(self):
        self.list.clear()
        archive_tasks = [t for t in self.manager.all_tasks() if t.status == "done"]
        archive_tasks.sort(key=lambda t: t.completed_at or "")

        for t in archive_tasks:
            if t.completed_at:
                try:
                    dt = datetime.fromisoformat(t.completed_at)
                    date_str = dt.strftime("%d.%m.%Y")
                except Exception:
                    date_str = t.completed_at.split("T")[0]
            else:
                date_str = ""

            desc = (t.description or "").replace("\n", " ").strip()
            max_len = 80
            if len(desc) > max_len:
                desc = desc[:max_len] + "…"

            label = f"{date_str}   {t.title}"
            if desc:
                label += f" — {desc}"
            if t.closing_comment:
                label += f"   (Comment: {t.closing_comment})"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, t)
            item.setForeground(Qt.black)
            self.list.addItem(item)

    def _refresh_all_matrices(self):
        from PySide6.QtWidgets import QApplication

        def refresh_in_widget(w):
            # Direct MatrixView instances
            if isinstance(w, MatrixView):
                if hasattr(w, "refresh_all_callback") and w.refresh_all_callback:
                    w.refresh_all_callback()
                else:
                    w.refresh()

            # Any MatrixView children
            for child in w.findChildren(MatrixView):
                if hasattr(child, "refresh_all_callback") and child.refresh_all_callback:
                    child.refresh_all_callback()
                else:
                    child.refresh()

        for top in QApplication.topLevelWidgets():
            refresh_in_widget(top)

    def open_archived_task(self, item):
        task = item.data(Qt.UserRole)
        dlg = ArchiveTaskDialog(task, self.manager, self)

        if dlg.exec():
            self.refresh()
            self._refresh_all_matrices()

    def delete_selected(self):
        item = self.list.currentItem()
        if not item:
            QMessageBox.warning(self, "No selection", "Please select a task to delete.")
            return

        task = item.data(Qt.UserRole)

        confirm = QMessageBox.question(
            self,
            "Delete Task?",
            f"Are you sure you want to permanently delete:\n\n{task.title}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.manager.tasks.remove(task)
            self.manager.save()
            self.refresh()

    def clear_archive(self):
        confirm = QMessageBox.question(
            self,
            "Clear Archive?",
            "This will permanently delete ALL archived tasks.\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.manager.tasks = [t for t in self.manager.tasks if t.status != "done"]
            self.manager.save()
            self.refresh()
            self._refresh_all_matrices()

# ---------------------- Statistics ---------------------- #

class StatisticsView(QWidget):
    def __init__(self, manager: TaskManager):
        super().__init__()
        self.manager = manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Statistics")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #16a085;")
        layout.addWidget(title)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        self.chart_view = QChartView()
        layout.addWidget(self.chart_view)

        self.setLayout(layout)
        self.refresh()

    def refresh(self):
        tasks = self.manager.all_tasks()
        open_tasks = [t for t in tasks if t.status == "open"]
        done_tasks = [t for t in tasks if t.status == "done"]

        count_open = len(open_tasks)
        count_done = len(done_tasks)

        per_category = {"do": 0, "plan": 0, "delegate": 0, "wait": 0}
        for t in open_tasks:
            if t.category in per_category:
                per_category[t.category] += 1

        self.summary_label.setText(
            f"Open tasks: {count_open}   |   Archived tasks: {count_done}\n"
            f"Do: {per_category['do']}   Plan: {per_category['plan']}   "
            f"Delegate: {per_category['delegate']}   Wait: {per_category['wait']}"
        )

        bar_set = QBarSet("Open tasks")
        bar_set.append([
            per_category["do"],
            per_category["plan"],
            per_category["delegate"],
            per_category["wait"],
        ])

        series = QBarSeries()
        series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Open tasks per category")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        categories = ["Do", "Plan", "Delegate", "Wait"]
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        max_val = max(per_category.values()) if per_category.values() else 0
        axis_y = QValueAxis()
        axis_y.setRange(0, max_val + 1 if max_val > 0 else 1)
        axis_y.setLabelFormat("%d")
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        self.chart_view.setChart(chart)

# ------------------------- Image Resize -------------------------#
 
class ImageResizeDialog(QDialog):
    def __init__(self, current_width, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resize Image")

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("New width (px):"))
        self.width_edit = QLineEdit(str(int(current_width)))
        layout.addWidget(self.width_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_width(self):
        try:
            return int(self.width_edit.text())
        except:
            return None

# ------------------------- Image Crop ------------------------- #

class ImageCropDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crop Image")
        self.resize(600, 400)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)

        self.rubber = QRubberBand(QRubberBand.Rectangle, self.view)
        self.origin = QPoint()

        layout = QVBoxLayout(self)
        layout.addWidget(self.view)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.view.viewport().installEventFilter(self)

    def eventFilter(self, source, event):
        from PySide6.QtCore import QEvent

        if source is self.view.viewport():
            if event.type() == QEvent.MouseButtonPress:
                self.origin = event.pos()
                self.rubber.setGeometry(QRect(self.origin, QSize()))
                self.rubber.show()

            elif event.type() == QEvent.MouseMove:
                if self.rubber.isVisible():
                    rect = QRect(self.origin, event.pos()).normalized()
                    self.rubber.setGeometry(rect)

            elif event.type() == QEvent.MouseButtonRelease:
                self.rubber.hide()

        return super().eventFilter(source, event)

    def get_cropped_pixmap(self):
        rect = self.rubber.geometry()
        if rect.isNull():
            return None

        mapped = self.view.mapToScene(rect).boundingRect().toRect()
        return self.pixmap_item.pixmap().copy(mapped)

# ---------------------- Formatting Toolbar ---------------------- 

class FormattingToolbar(QWidget):
    def __init__(self, editor: QTextEdit, parent=None):
        super().__init__(parent)
        self.editor = editor

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # --- Bold ---
        bold_btn = QPushButton("B")
        bold_btn.setCheckable(True)
        bold_btn.clicked.connect(self.toggle_bold)
        bold_btn.setStyleSheet("font-weight: bold;")
        layout.addWidget(bold_btn)

        # --- Italic ---
        italic_btn = QPushButton("I")
        italic_btn.setCheckable(True)
        italic_btn.clicked.connect(self.toggle_italic)
        italic_btn.setStyleSheet("font-style: italic;")
        layout.addWidget(italic_btn)

        # --- Underline ---
        underline_btn = QPushButton("U")
        underline_btn.setCheckable(True)
        underline_btn.clicked.connect(self.toggle_underline)
        underline_btn.setStyleSheet("text-decoration: underline;")
        layout.addWidget(underline_btn)

        # --- Text color ---
        color_btn = QPushButton("A")
        color_btn.clicked.connect(self.set_text_color)
        layout.addWidget(color_btn)

        # --- Highlight ---
        highlight_btn = QPushButton("HL")
        highlight_btn.clicked.connect(self.set_highlight_color)
        layout.addWidget(highlight_btn)

        # --- Bullet list ---
        bullet_btn = QPushButton("• List")
        bullet_btn.clicked.connect(self.make_bullet_list)
        layout.addWidget(bullet_btn)

        # --- Numbered list ---
        num_btn = QPushButton("1. List")
        num_btn.clicked.connect(self.make_number_list)
        layout.addWidget(num_btn)

        # --- Headings ---
        normal_btn = QPushButton("Normal")
        normal_btn.clicked.connect(lambda: self.set_heading(0))
        layout.addWidget(normal_btn)

        h1_btn = QPushButton("H1")
        h1_btn.clicked.connect(lambda: self.set_heading(1))
        layout.addWidget(h1_btn)

        h2_btn = QPushButton("H2")
        h2_btn.clicked.connect(lambda: self.set_heading(2))
        layout.addWidget(h2_btn)

    # ---------------- Formatting actions ---------------- #

    def merge_format(self, fmt):
        cursor = self.editor.textCursor()
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def toggle_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if self.editor.fontWeight() != QFont.Bold else QFont.Normal)
        self.merge_format(fmt)

    def toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.fontItalic())
        self.merge_format(fmt)

    def toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.fontUnderline())
        self.merge_format(fmt)

    def set_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self.merge_format(fmt)

    def set_highlight_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            self.merge_format(fmt)

    def make_bullet_list(self):
        cursor = self.editor.textCursor()
        cursor.insertList(QTextListFormat.ListDisc)

    def make_number_list(self):
        cursor = self.editor.textCursor()
        cursor.insertList(QTextListFormat.ListDecimal)

    def set_heading(self, level):
        cursor = self.editor.textCursor()
        char_fmt = cursor.charFormat()

        if level == 0:
            char_fmt.setFontPointSize(12)
            char_fmt.setFontWeight(QFont.Normal)
        elif level == 1:
            char_fmt.setFontPointSize(22)
            char_fmt.setFontWeight(QFont.Bold)
        elif level == 2:
            char_fmt.setFontPointSize(18)
            char_fmt.setFontWeight(QFont.Bold)

        cursor.setCharFormat(char_fmt)

# ---------------------- Rich Text Edit ---------------------- #

class RichTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_view = parent

    def insertFromMimeData(self, source):
        # Prefer text over image (fixes OneNote paste issue)
        if source.hasText():
            super().insertFromMimeData(source)
            if self.parent_view:
                self.parent_view.on_note_changed()
            return

        # If no text but an image → insert image
        if source.hasImage():
            image = source.imageData()

            if isinstance(image, QImage):
                img_dir = os.path.join(APP_DIR, "note_images")
                os.makedirs(img_dir, exist_ok=True)

                filename = os.path.join(
                    img_dir,
                    f"img_{datetime.now().timestamp():.0f}.png"
                )
                image.save(filename)

                display_width = min(image.width(), 600)
                aspect = image.height() / image.width()
                display_height = int(display_width * aspect)

                cursor = self.textCursor()

                fmt = QTextImageFormat()
                fmt.setName(filename)
                fmt.setWidth(display_width)
                fmt.setHeight(display_height)

                cursor.insertImage(fmt)

                if self.parent_view:
                    self.parent_view.on_note_changed()
                return

        # Fallback
        super().insertFromMimeData(source)

# ------------------------- Notes ------------------------- #

class NotesView(QWidget):
    def __init__(self):
        super().__init__()

        self.loading_note = False
        self.search_text = ""

        main_layout = QHBoxLayout(self)

        # ---------------- Left Panel ---------------- #
        left_panel = QVBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search…")
        self.search_edit.textChanged.connect(self.search_notes)
        left_panel.addWidget(self.search_edit)

        # Fix placeholder visibility
        self.search_edit.setStyleSheet("""
            QLineEdit { color: black; }
            QLineEdit::placeholder { color: gray; }
        """)

        self.notes_list = QListWidget()
        self.notes_list.currentRowChanged.connect(self.load_selected_note)
        left_panel.addWidget(self.notes_list)

        new_btn = QPushButton("New Note")
        new_btn.clicked.connect(self.create_note)
        left_panel.addWidget(new_btn)

        main_layout.addLayout(left_panel, 1)

        # ---------------- Right Panel ---------------- #
        right_panel = QVBoxLayout()

        self.title_edit = QLineEdit()
        self.title_edit.textChanged.connect(self.on_note_changed)
        right_panel.addWidget(self.title_edit)

        # --- Formatting toolbar ---
        self.text_edit = RichTextEdit(self)
        self.toolbar = FormattingToolbar(self.text_edit)
        right_panel.addWidget(self.toolbar)

        self.text_edit.textChanged.connect(self.on_note_changed)
        self.text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self.open_context_menu)

        self.text_edit.setTextInteractionFlags(
            Qt.TextEditorInteraction |
            Qt.TextEditable |
            Qt.TextSelectableByMouse
        )

        right_panel.addWidget(self.text_edit)

        delete_btn = QPushButton("Delete Note")
        delete_btn.clicked.connect(self.delete_current_note)
        right_panel.addWidget(delete_btn)

        main_layout.addLayout(right_panel, 3)

        # Load notes
        self.notes = self.load_notes()
        self.refresh_list()

    # ---------------- Storage ---------------- #

    def load_notes(self):
        if not os.path.exists(NOTES_FILE):
            return []
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def save_notes(self):
        with open(NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.notes, f, indent=4)

    # ---------------- Autosave ---------------- #

    def on_note_changed(self):
        if self.loading_note:
            return

        item = self.notes_list.currentItem()
        if not item:
            return

        idx = item.data(Qt.UserRole)

        self.notes[idx]["title"] = self.title_edit.text().strip()
        self.notes[idx]["body_html"] = self.text_edit.toHtml()

        item.setText(self.notes[idx]["title"])
        self.save_notes()

    # ---------------- Search ---------------- #

    def search_notes(self, text):
        self.search_text = text.strip()
        self.refresh_list()
        self.highlight_text_in_editor(self.search_text)

    def highlight_text_in_editor(self, pattern):
        if not pattern:
            self.text_edit.setExtraSelections([])
            return

        doc = self.text_edit.document()
        cursor = QTextCursor(doc)

        extra = []
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#ffff66"))

        pos = 0
        while True:
            cursor = doc.find(pattern, pos)
            if cursor.isNull():
                break
            pos = cursor.position()

            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            extra.append(sel)

        self.text_edit.setExtraSelections(extra)

    # ---------------- List Handling ---------------- #

    def refresh_list(self):
        current_item = self.notes_list.currentItem()
        current_index = current_item.data(Qt.UserRole) if current_item else None

        self.notes_list.clear()
        visible = []

        for i, note in enumerate(self.notes):
            title = note.get("title", "Untitled")
            body = note.get("body_html", "")

            if self.search_text:
                haystack = (title + " " + body).lower()
                if self.search_text.lower() not in haystack:
                    continue

            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, i)
            self.notes_list.addItem(item)
            visible.append(i)

        if current_index in visible:
            for row in range(self.notes_list.count()):
                if self.notes_list.item(row).data(Qt.UserRole) == current_index:
                    self.notes_list.setCurrentRow(row)
                    break
        elif self.notes_list.count() > 0:
            self.notes_list.setCurrentRow(0)
        else:
            self.loading_note = True
            self.title_edit.setText("")
            self.text_edit.setHtml("")
            self.loading_note = False

    # ---------------- Note Actions ---------------- #

    def create_note(self):
        self.notes.append({"title": "Untitled", "body_html": ""})
        self.save_notes()
        self.refresh_list()
        self.notes_list.setCurrentRow(self.notes_list.count() - 1)

    def load_selected_note(self, index):
        item = self.notes_list.item(index)
        if not item:
            self.loading_note = True
            self.title_edit.setText("")
            self.text_edit.setHtml("")
            self.loading_note = False
            return

        idx = item.data(Qt.UserRole)
        note = self.notes[idx]

        self.loading_note = True
        self.title_edit.setText(note.get("title", "Untitled"))
        self.text_edit.setHtml(note.get("body_html", ""))
        self.loading_note = False

        self.highlight_text_in_editor(self.search_text)

    def delete_current_note(self):
        item = self.notes_list.currentItem()
        if not item:
            return

        idx = item.data(Qt.UserRole)
        del self.notes[idx]
        self.save_notes()
        self.refresh_list()

    # ---------------- Image insertion ---------------- #

    def insert_image_from_path(self, path):
        image = QImage(path)
        if image.isNull():
            return

        display_width = min(image.width(), 600)
        aspect = image.height() / image.width()
        display_height = int(display_width * aspect)

        cursor = self.text_edit.textCursor()

        fmt = QTextImageFormat()
        fmt.setName(path)
        fmt.setWidth(display_width)
        fmt.setHeight(display_height)

        cursor.insertImage(fmt)
        self.on_note_changed()

    def insert_image_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Insert Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.insert_image_from_path(path)

    # ---------------- Image resizing ---------------- #

    def resize_image_at_cursor(self, cursor):
        fmt = cursor.charFormat()
        if not fmt.isImageFormat():
            return

        img_fmt = QTextImageFormat(fmt)
        path = img_fmt.name()

        image = QImage(path)
        if image.isNull():
            return

        dlg = ImageResizeDialog(img_fmt.width(), self)
        if dlg.exec() != QDialog.Accepted:
            return

        new_width = dlg.get_width()
        if not new_width or new_width <= 0:
            return

        aspect = image.height() / image.width()
        new_height = int(new_width * aspect)

        new_fmt = QTextImageFormat()
        new_fmt.setName(path)
        new_fmt.setWidth(new_width)
        new_fmt.setHeight(new_height)

        cursor.deleteChar()
        cursor.insertImage(new_fmt)

        self.on_note_changed()

    # ---------------- Context Menu ---------------- #

    def open_context_menu(self, pos):
        menu = self.text_edit.createStandardContextMenu()

        insert_action = QAction("Insert Image…", self)
        insert_action.triggered.connect(self.insert_image_dialog)
        menu.addAction(insert_action)

        cursor = self.text_edit.cursorForPosition(pos)
        fmt = cursor.charFormat()

        if fmt.isImageFormat():
            resize_action = QAction("Resize Image…", self)
            resize_action.triggered.connect(lambda: self.resize_image_at_cursor(cursor))
            menu.addAction(resize_action)

        menu.exec(self.text_edit.mapToGlobal(pos))

# ------------------------- Topic Tracker ------------------------- #
# ---------------------- Topic model ---------------------- #

class Topic:
    def __init__(
        self,
        question,
        asked_to,
        asked_at=None,
        deadline=None,
        status="open",          # open, waiting, blocked, answered
        category="",
        priority="medium",      # low, medium, high
        channel="",
        reminder_date=None,
        tags="",
        answer="",
        history="",
        attachments=None,       # list of file paths or URLs (optional)
        created_at=None,
        answered_at=None,
    ):
        self.question = question
        self.asked_to = asked_to
        self.asked_at = asked_at or datetime.now().isoformat()
        self.deadline = deadline
        self.status = status
        self.category = category
        self.priority = priority
        self.channel = channel
        self.reminder_date = reminder_date
        self.tags = tags
        self.answer = answer
        self.history = history
        self.attachments = attachments or []
        self.created_at = created_at or datetime.now().isoformat()
        self.answered_at = answered_at

    def to_dict(self):
        return {
            "question": self.question,
            "asked_to": self.asked_to,
            "asked_at": self.asked_at,
            "deadline": self.deadline,
            "status": self.status,
            "category": self.category,
            "priority": self.priority,
            "channel": self.channel,
            "reminder_date": self.reminder_date,
            "tags": self.tags,
            "answer": self.answer,
            "history": self.history,
            "attachments": self.attachments,
            "created_at": self.created_at,
            "answered_at": self.answered_at,
        }

    @staticmethod
    def from_dict(d):
        return Topic(
            question=d.get("question", ""),
            asked_to=d.get("asked_to", ""),
            asked_at=d.get("asked_at"),
            deadline=d.get("deadline"),
            status=d.get("status", "open"),
            category=d.get("category", ""),
            priority=d.get("priority", "medium"),
            channel=d.get("channel", ""),
            reminder_date=d.get("reminder_date"),
            tags=d.get("tags", ""),
            answer=d.get("answer", ""),
            history=d.get("history", ""),
            attachments=d.get("attachments", []),
            created_at=d.get("created_at"),
            answered_at=d.get("answered_at"),
        )

# ---------------------- Topic Manager ---------------------- #

class TopicManager:
    def __init__(self):
        self.topics: list[Topic] = []
        self.load()

    def load(self):
        if os.path.exists(TOPICS_FILE):
            try:
                with open(TOPICS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.topics = [Topic.from_dict(t) for t in data]
            except Exception:
                self.topics = []
        else:
            self.topics = []

    def save(self):
        with open(TOPICS_FILE, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.topics], f, indent=2)

    def add_topic(self, topic: Topic):
        self.topics.append(topic)
        self.save()

    def delete_topic(self, topic: Topic):
        """Remove a topic and save immediately."""
        if topic in self.topics:
            self.topics.remove(topic)
            self.save()

    def all_topics(self):
        return self.topics

    def open_topics(self):
        return [t for t in self.topics if t.status != "answered"]

    def closed_topics(self):
        return [t for t in self.topics if t.status == "answered"]

# ---------------------- Topic Dialog ---------------------- #

class TopicDialog(QDialog):
    def __init__(self, manager: TopicManager, topic: Topic | None = None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.topic = topic
        self.setWindowTitle("Edit Topic" if topic else "New Topic")
        self.setMinimumWidth(520)
        self.init_ui()

    # ---------------------- DATE PICKER FACTORY ---------------------- #
    def make_date_picker(self, initial_iso=None):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        edit = QDateEdit()
        edit.setDisplayFormat("dd.MM.yyyy")
        edit.setCalendarPopup(False)
        edit.setMinimumHeight(28)

        # Set initial date
        if initial_iso:
            try:
                dt = datetime.fromisoformat(initial_iso)
                edit.setDate(QDate(dt.year, dt.month, dt.day))
            except Exception:
                edit.setDate(QDate.currentDate())
        else:
            edit.setDate(QDate.currentDate())

        btn = QPushButton("📅")
        btn.setFixedWidth(32)

        def open_calendar():
            dlg = CalendarDialog(self, edit.date())
            if dlg.exec() == QDialog.Accepted:
                edit.setDate(dlg.selected_date())

        btn.clicked.connect(open_calendar)

        layout.addWidget(edit)
        layout.addWidget(btn)

        return container, edit

    # ---------------------- UI SETUP ---------------------- #
    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Question
        self.question_edit = QTextEdit()
        self.question_edit.setFixedHeight(60)
        form.addRow("Question:", self.question_edit)

        # Asked to
        self.asked_to_edit = QLineEdit()
        form.addRow("Asked to:", self.asked_to_edit)

        # Asked at
        self.asked_at_container, self.asked_at_edit = self.make_date_picker()
        form.addRow("Asked at:", self.asked_at_container)

        # Deadline
        self.deadline_container, self.deadline_edit = self.make_date_picker()
        form.addRow("Deadline:", self.deadline_container)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(["open", "waiting", "blocked", "answered"])
        form.addRow("Status:", self.status_combo)

        # Category
        self.category_edit = QLineEdit()
        form.addRow("Category:", self.category_edit)

        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["low", "medium", "high"])
        form.addRow("Priority:", self.priority_combo)

        # Channel
        self.channel_edit = QLineEdit()
        form.addRow("Channel:", self.channel_edit)

        # Reminder
        self.reminder_container, self.reminder_edit = self.make_date_picker()
        form.addRow("Reminder:", self.reminder_container)

        # Answer
        self.answer_edit = QTextEdit()
        self.answer_edit.setFixedHeight(80)
        form.addRow("Answer:", self.answer_edit)

        # History
        self.history_edit = QTextEdit()
        self.history_edit.setFixedHeight(80)
        form.addRow("History:", self.history_edit)

        layout.addLayout(form)

        # Buttons
        btns = QHBoxLayout()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_and_close)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btns.addStretch()
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        # Load existing topic
        if self.topic:
            self.load_topic()

    # ---------------------- LOAD EXISTING TOPIC ---------------------- #
    def load_topic(self):
        t = self.topic
        self.question_edit.setPlainText(t.question)
        self.asked_to_edit.setText(t.asked_to)

        # Set dates
        def set_date(edit: QDateEdit, iso):
            if not iso:
                return
            try:
                dt = datetime.fromisoformat(iso)
                edit.setDate(QDate(dt.year, dt.month, dt.day))
            except Exception:
                pass

        set_date(self.asked_at_edit, t.asked_at)
        set_date(self.deadline_edit, t.deadline)
        set_date(self.reminder_edit, t.reminder_date)

        self.status_combo.setCurrentText(t.status)
        self.category_edit.setText(t.category)
        self.priority_combo.setCurrentText(t.priority)
        self.channel_edit.setText(t.channel)
        self.answer_edit.setPlainText(t.answer)
        self.history_edit.setPlainText(t.history)

    # ---------------------- SAVE ---------------------- #
    def save_and_close(self):
        question = self.question_edit.toPlainText().strip()
        asked_to = self.asked_to_edit.text().strip()

        if not question or not asked_to:
            QMessageBox.warning(self, "Missing data", "Please fill at least question and 'asked to'.")
            return

        def to_iso(edit: QDateEdit):
            d = edit.date()
            return datetime(d.year(), d.month(), d.day()).isoformat()

        asked_at_iso = to_iso(self.asked_at_edit)
        deadline_iso = to_iso(self.deadline_edit)
        reminder_iso = to_iso(self.reminder_edit)

        if self.topic is None:
            # Create new topic
            self.topic = Topic(
                question=question,
                asked_to=asked_to,
                asked_at=asked_at_iso,
                deadline=deadline_iso,
                status=self.status_combo.currentText(),
                category=self.category_edit.text().strip(),
                priority=self.priority_combo.currentText(),
                channel=self.channel_edit.text().strip(),
                reminder_date=reminder_iso,
                answer=self.answer_edit.toPlainText().strip(),
                history=self.history_edit.toPlainText().strip(),
            )
            if self.topic.status == "answered":
                self.topic.answered_at = datetime.now().isoformat()
            self.manager.add_topic(self.topic)

        else:
            # Update existing topic
            t = self.topic
            t.question = question
            t.asked_to = asked_to
            t.asked_at = asked_at_iso
            t.deadline = deadline_iso
            t.status = self.status_combo.currentText()
            t.category = self.category_edit.text().strip()
            t.priority = self.priority_combo.currentText()
            t.channel = self.channel_edit.text().strip()
            t.reminder_date = reminder_iso
            t.answer = self.answer_edit.toPlainText().strip()
            t.history = self.history_edit.toPlainText().strip()

            if t.status == "answered" and not t.answered_at:
                t.answered_at = datetime.now().isoformat()

            self.manager.save()

        self.accept()


# ---------------------- Topics View ---------------------- #

class TopicsView(QWidget):
    def __init__(self, manager: TopicManager):
        super().__init__()
        self.manager = manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Topics")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2980b9; margin-bottom: 6px;")
        layout.addWidget(title)

        # ---------------------- ACTION BAR ---------------------- #
        action_bar = QHBoxLayout()

        self.new_btn = QPushButton("➕ New Topic")
        self.new_btn.clicked.connect(self.new_topic)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh)

        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self.delete_selected_topic)

        action_bar.addWidget(self.new_btn)
        action_bar.addWidget(self.refresh_btn)
        action_bar.addWidget(self.delete_btn)
        action_bar.addStretch()

        layout.addLayout(action_bar)

        # ---------------------- FILTER BAR (WITH LABELS) ---------------------- #
        filter_frame = QFrame()
        filter_frame.setFrameShape(QFrame.StyledPanel)
        filter_frame.setStyleSheet("background-color: #f7f7f7; border: 1px solid #d0d0d0; border-radius: 6px;")

        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 6, 8, 6)
        filter_layout.setSpacing(12)

        # Status
        status_label = QLabel("Status:")
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "open", "waiting", "blocked", "answered"])
        self.status_filter.setFixedWidth(120)

        # Category
        category_label = QLabel("Category:")
        self.category_filter = QLineEdit()
        self.category_filter.setPlaceholderText("e.g. Finance")

        # Priority
        priority_label = QLabel("Priority:")
        self.priority_filter = QComboBox()
        self.priority_filter.addItems(["All", "low", "medium", "high"])
        self.priority_filter.setFixedWidth(100)

        # Asked to
        person_label = QLabel("Asked to:")
        self.person_filter = QLineEdit()
        self.person_filter.setPlaceholderText("Name")

        # Search
        search_label = QLabel("Search:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Question or answer…")

        apply_btn = QPushButton("Filter")
        apply_btn.clicked.connect(self.refresh)

        # Add widgets to filter bar
        filter_layout.addWidget(status_label)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addWidget(category_label)
        filter_layout.addWidget(self.category_filter)

        filter_layout.addWidget(priority_label)
        filter_layout.addWidget(self.priority_filter)

        filter_layout.addWidget(person_label)
        filter_layout.addWidget(self.person_filter)

        filter_layout.addWidget(search_label)
        filter_layout.addWidget(self.search_edit)

        filter_layout.addWidget(apply_btn)

        layout.addWidget(filter_frame)

        # ---------------------- TABLE ---------------------- #
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Question",
            "Asked to",
            "Asked at",
            "Deadline",
            "Status",
            "Category",
            "Priority",
            "Channel",
            "Reminder",
            "Answer",
        ])

        # Better selection highlight
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #cce5ff;
                color: black;
            }
        """)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.edit_selected_topic)

        layout.addWidget(self.table)

        self.refresh()

    # ---------------------- FILTERING ---------------------- #
    def filtered_topics(self):
        status = self.status_filter.currentText()
        category = self.category_filter.text().strip().lower()
        priority = self.priority_filter.currentText()
        person = self.person_filter.text().strip().lower()
        search = self.search_edit.text().strip().lower()

        result = []
        for t in self.manager.all_topics():
            if status != "All" and t.status != status:
                continue
            if priority != "All" and t.priority != priority:
                continue
            if category and category not in (t.category or "").lower():
                continue
            if person and person not in (t.asked_to or "").lower():
                continue

            haystack = " ".join([
                t.question or "",
                t.answer or "",
            ]).lower()
            if search and search not in haystack:
                continue

            result.append(t)
        return result

    # ---------------------- REFRESH TABLE ---------------------- #
    def refresh(self):
        topics = self.filtered_topics()
        self.table.setRowCount(len(topics))

        for row, t in enumerate(topics):
            def fmt_date(iso_str):
                if not iso_str:
                    return ""
                try:
                    dt = datetime.fromisoformat(iso_str)
                    return dt.strftime("%d.%m.%Y")
                except Exception:
                    return iso_str

            values = [
                t.question,
                t.asked_to,
                fmt_date(t.asked_at),
                fmt_date(t.deadline),
                t.status,
                t.category,
                t.priority,
                t.channel,
                fmt_date(t.reminder_date),
                t.answer,
            ]

            for col, val in enumerate(values):
                item = QTableWidgetItem(val or "")

                # Overdue highlighting
                if col == 3 and t.deadline:
                    try:
                        due = datetime.fromisoformat(t.deadline)
                        if due.date() < datetime.now().date() and t.status != "answered":
                            item.setForeground(Qt.red)
                        elif due.date() <= datetime.now().date() and t.status != "answered":
                            item.setForeground(QColor("#e67e22"))
                    except Exception:
                        pass

                self.table.setItem(row, col, item)

            # Store topic reference
            self.table.item(row, 0).setData(Qt.UserRole, t)
            self.table.setRowHeight(row, 26)

        self.table.resizeColumnsToContents()

    # ---------------------- GET CURRENT TOPIC ---------------------- #
    def current_topic(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        return item.data(Qt.UserRole)

    # ---------------------- NEW TOPIC ---------------------- #
    def new_topic(self):
        dlg = TopicDialog(self.manager, None, self)
        if dlg.exec():
            self.refresh()

    # ---------------------- EDIT TOPIC ---------------------- #
    def edit_selected_topic(self):
        t = self.current_topic()
        if not t:
            return
        dlg = TopicDialog(self.manager, t, self)
        if dlg.exec():
            self.refresh()

    # ---------------------- DELETE TOPIC ---------------------- #
    def delete_selected_topic(self):
        topic = self.current_topic()
        if not topic:
            QMessageBox.warning(self, "No selection", "Please select a topic to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Topic",
            "Are you sure you want to delete this topic?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if confirm == QMessageBox.Yes:
            self.manager.delete_topic(topic)
            self.table.clearSelection()
            self.refresh()


# ---------------------- Main window ---------------------- #

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = TaskManager()
        self.topic_manager = TopicManager()     # NEW
        self.setWindowTitle("Task Command Center")
        self.setMinimumSize(1100, 700)
        self.init_ui()

    def init_ui(self):
        self.stack = QStackedWidget()

        # --- Views --- #
        self.matrix_view = MatrixView(self.manager, self.refresh_all_views)
        self.timeline_view = TimelineView(self.manager, self.refresh_all_views)
        self.archive_view = ArchiveView(self.manager)
        self.stats_view = StatisticsView(self.manager)
        self.notes_view = NotesView()
        self.topics_view = TopicsView(self.topic_manager)   

        self.stack.addWidget(self.matrix_view)     # index 0
        self.stack.addWidget(self.timeline_view)   # index 1
        self.stack.addWidget(self.archive_view)    # index 2
        self.stack.addWidget(self.stats_view)      # index 3
        self.stack.addWidget(self.notes_view)      # index 4
        self.stack.addWidget(self.topics_view)     # index 5   

        self.setCentralWidget(self.stack)

        # ---------------- Toolbar ---------------- #
        toolbar = QToolBar("Navigation")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.LeftToolBarArea, toolbar)

        # Create Task
        create_act = QAction("+ Create Task", self)
        create_act.triggered.connect(self.open_create_task_dialog)
        toolbar.addAction(create_act)
        toolbar.addSeparator()

        # Navigation buttons
        def add_nav_action(text, index):
            act = QAction(text, self)
            act.triggered.connect(lambda _, i=index: self.stack.setCurrentIndex(i))
            toolbar.addAction(act)

        add_nav_action("Matrix", 0)
        add_nav_action("Timeline", 1)
        add_nav_action("Archive", 2)
        add_nav_action("Statistics", 3)
        add_nav_action("Notes", 4)
        add_nav_action("Topics", 5)   

        self.statusBar().showMessage("Ready")
        self.refresh_all_views()

    def open_create_task_dialog(self):
        dlg = CreateTaskDialog(self.manager, self)
        if dlg.exec():
            self.refresh_all_views()

    def refresh_all_views(self):
        self.matrix_view.refresh()
        self.timeline_view.refresh()
        self.archive_view.refresh()
        self.stats_view.refresh()
        self.topics_view.refresh()     
        self.manager.save()
        self.topic_manager.save()      


# ---------------------- Entry point ---------------------- #

def main():
    app = QApplication(sys.argv)

    palette = app.palette()
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.Text, QColor("#000000"))
    palette.setColor(QPalette.Window, QColor("#ffffff"))
    palette.setColor(QPalette.WindowText, QColor("#000000"))
    app.setPalette(palette)

    app.setStyleSheet("""
        QPushButton {
            background-color: #e0e0e0;
            color: #000000;
            border: 1px solid #888;
            padding: 6px 10px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #d5d5d5;
        }
        QPushButton:pressed {
            background-color: #c8c8c8;
        }

        QLabel {
            color: #000000;
        }

        QToolBar QToolButton {
            color: #000000;
        }

        QMessageBox {
            background-color: #ffffff;
        }

        QComboBox {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #888;
            padding: 4px;
            border-radius: 4px;
        }

        QComboBox QAbstractItemView {
            background-color: #ffffff;
            color: #000000;
            selection-background-color: #d0d0d0;
            selection-color: #000000;
        }

        QToolBar {
            background: #f7f7f7;
            border-right: 1px solid #d0d0d0;
            padding: 6px;
        }

        QToolButton {
            background: transparent;
            border-radius: 6px;
            padding: 8px 10px;
            margin: 4px;
            color: #333;
            font-weight: 500;
        }

        QToolButton:hover {
            background: #e6e6e6;
        }

        QToolButton:pressed {
            background: #dcdcdc;
        }

        QToolButton:checked {
            background: #d0d0d0;
            border: 1px solid #b0b0b0;
        }
        
        QMenu {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #888;
        }

        QMenu::item:selected {
            background-color: #e6f0ff;
            color: #000000;
        }

    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
