import sys, os, api, re, threading, time
import datetime as dt
from dateutil.relativedelta import relativedelta, FR, MO

use_qt5 = True
if not "--qt5" in sys.argv:
    use_qt5 = False
    try:
        from PyQt6.QtCore import Qt, QDate, QSettings, pyqtSignal, QTimer
        from PyQt6 import QtCore
        from PyQt6.QtGui import QShortcut, QKeySequence, QIcon, QBrush, QColor
        from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QDialog, QFrame, QAbstractItemView, QMessageBox, QTableWidgetItem, QSizePolicy, QSpacerItem, QToolButton, QDateEdit, QTableWidget, QStatusBar, QTabWidget, QComboBox
    except ImportError:
        use_qt5 = True
if use_qt5:
    from PyQt5.QtCore import Qt, QDate, QSettings, pyqtSignal, QTimer
    from PyQt5 import QtCore
    from PyQt5.QtGui import QIcon, QBrush, QColor, QKeySequence
    from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QDialog, QFrame, QAbstractItemView, QMessageBox, QTableWidgetItem, QShortcut, QSizePolicy, QSpacerItem, QToolButton, QDateEdit, QTableWidget, QStatusBar,  QTabWidget, QComboBox

class QFrame_click(QFrame):
    clicked = pyqtSignal()
    def mousePressEvent(self, ev):
        self.clicked.emit()

def size_policy():
    if use_qt5:
        return QSizePolicy
    else:
        return QSizePolicy.Policy

class LoginPopup(QDialog):
    def save(self):                
        self.settings.setValue('server', self.server)
        self.settings.setValue('school', self.school)
        self.settings.setValue('user', self.user_le.text())
        self.settings.setValue('password', self.password_le.text())
        self.close()
    
    def cb_change(self):
        if self.old_text == self.school_le.text():
            return
        self.old_text = self.school_le.text()
        
        results = api.school_search(self.school_le.text())
        entries = [i[0] for i in results]
        self.school_cb.clear()

        if len(results) == 2 and results[1] == "ERR":
            self.school_cb.addItem(results[0])
            self.err_backed = True
        elif len(results) == 0:
            self.school_cb.addItem("No Results")
            self.err_backed = True
        else:
            self.school_cb.addItems(entries)
            self.err_backed = False
            
    def cb_sel(self):
        if self.err_backed:
            return
        data = api.school_search(self.school_cb.currentText())
        if len(data) == 0 or (len(data) == 2 and data[1] == "ERR"):
            return
        self.server = api.school_search(self.school_cb.currentText())[0][1]
        self.school = self.school_cb.currentText()
        
    def __init__(self, settings):
        QWidget.__init__(self)
        self.old_text = ""
        self.err_backed = True
        self.search_timer = QTimer()
        self.search_timer.timeout.connect(self.cb_change)
        self.search_timer.start(1000) # only search once a second at most
        self.vlayout = QVBoxLayout(self)
        
        self.setWindowTitle("Edit Credentials")
        self.resize(172, 244)

        self.school_lbl = QLabel()
        self.vlayout.addWidget(self.school_lbl)
        self.school_lbl.setText("School:")
        
        self.school_le = QLineEdit()
        self.vlayout.addWidget(self.school_le)

        self.school_cb = QComboBox()
        self.vlayout.addWidget(self.school_cb)
        self.school_cb.currentIndexChanged.connect(self.cb_sel)
        
        self.user_lbl = QLabel()
        self.vlayout.addWidget(self.user_lbl)
        self.user_lbl.setText("Username:")
        self.user_le = QLineEdit()
        self.vlayout.addWidget(self.user_le)

        self.password_lbl = QLabel()
        self.vlayout.addWidget(self.password_lbl)

        self.password_lbl.setText("Password:")
        self.password_le = QLineEdit()
        self.vlayout.addWidget(self.password_le)
        
        self.btn_layout = QHBoxLayout()
        self.vlayout.addLayout(self.btn_layout)

        self.btn_ok = QPushButton()
        self.btn_ok.setText("Save")
        self.btn_layout.addWidget(self.btn_ok)
        self.btn_cc = QPushButton()
        self.btn_cc.setText("Cancel")
        self.btn_layout.addWidget(self.btn_cc)
        
        self.btn_ok.pressed.connect(self.save) # type: ignore
        self.btn_cc.pressed.connect(self.close) # type: ignore
        
        self.settings = settings
        
        self.server = self.settings.value('server') or ''
        
        self.school_le.setText(self.settings.value('school') or '')
        self.school = self.settings.value('school') or ''
        self.user_le.setText(self.settings.value('user') or '')
        self.password_le.setText(self.settings.value('password') or '')

class InfoPopup(QDialog):
    def __init__(self, parent):        
        QWidget.__init__(self)
        self.setWindowTitle("Lesson Info")
        self.vlayout = QVBoxLayout(self)
        self.close_btn = QPushButton()
        self.close_btn.setText("Close")
        self.close_btn.pressed.connect(self.close)
        self.lesson_tab = QTabWidget()
        self.vlayout.addWidget(self.lesson_tab)
        self.lesson_tab.setCurrentIndex(1)
        
        col = parent.timetable.currentColumn()
        row = parent.timetable.currentRow()
        parent.timetable.selectionModel().clear()
        self.close_btn.pressed.connect(self.close)
        # richtext info about the lesson
        try:
            hour_data = parent.data[row][col]
        except:
            hour_data = [None]
            
        for i in range(len(hour_data)):
            if hour_data == [None]:
                self.content = QLabel(self)
                self.content.setText("<h2>No Lesson planned!</h2>")
                self.content.setWordWrap(True)
                continue

            lesson = hour_data[i]
            full_repl = lesson[-1]

            if full_repl.activityType != "Unterricht": # why is it localized qwq
                status_str = full_repl.activityType
            elif full_repl.code == "cancelled":
                status_str = "Cancelled"
            elif full_repl.code == "irregular":
                status_str = "Substitution"
            elif full_repl.type == "ls":
                status_str = "Regular"
            elif full_repl.type == "oh":
                status_str = "Office Hour"
            elif full_repl.type == "sb":
                status_str = "Standby"
            elif full_repl.type == "bs":
                status_str = "Break Supervision"
            elif full_repl.type == "ex":
                status_str = "Examination"
            else:
                status_str = "unknown/report error"

            rt_info = f"<h4>{full_repl.long_name}</h4>"
            rt_info += f"<br>Start: {full_repl.starttime}"
            rt_info += f"<br>End: {full_repl.endtime}"
            if status_str:
                rt_info += f"<br>Type: {status_str}"
            rt_info += f"<br>Room: {full_repl.room_str}"
            if full_repl.klassen_str:
                rt_info += f"<br>Classes: {full_repl.klassen_str}"
            if lesson[2]:
                rt_info += f"<br>Info: {lesson[2]}"
            title = f"{i+1}: {lesson[0]}"
            info_lbl = QLabel(f"{rt_info}")
            info_lbl.setWordWrap(True)
            self.lesson_tab.addTab(info_lbl, title)
        self.vlayout.addWidget(self.close_btn)
        self.close_btn.pressed.connect(self.close)

class MainWindow(QMainWindow):
    def setupUi(self, MainWindow):
        MainWindow.setWindowTitle("Untis")
        MainWindow.resize(1116, 674)
        sizePolicy = QSizePolicy(size_policy().Expanding, size_policy().Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.centralwidget = QWidget(MainWindow)
        sizePolicy = QSizePolicy(size_policy().Expanding, size_policy().Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setAutoFillBackground(True)
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        spacerItem = QSpacerItem(20, 5, size_policy().Minimum, size_policy().Fixed)
        self.verticalLayout.addItem(spacerItem)
        self.top_bar_qhb = QHBoxLayout()
        spacerItem1 = QSpacerItem(10, 20, size_policy().Fixed, size_policy().Minimum)
        self.top_bar_qhb.addItem(spacerItem1)
        self.prev_btn = QToolButton(self.centralwidget)
        self.prev_btn.setText("")
        self.top_bar_qhb.addWidget(self.prev_btn)
        spacerItem2 = QSpacerItem(100, 20, size_policy().Maximum, size_policy().Minimum)
        self.top_bar_qhb.addItem(spacerItem2)
        self.login_btn = QPushButton(self.centralwidget)
        self.login_btn.setText("Login")
        self.top_bar_qhb.addWidget(self.login_btn)
        spacerItem3 = QSpacerItem(100, 20, size_policy().Maximum, size_policy().Minimum)
        self.top_bar_qhb.addItem(spacerItem3)
        self.reload_btn = QPushButton(self.centralwidget)
        self.reload_btn.setText("Reload")
        self.top_bar_qhb.addWidget(self.reload_btn)
        spacerItem4 = QSpacerItem(100, 20, size_policy().Maximum, size_policy().Minimum)
        self.top_bar_qhb.addItem(spacerItem4)
        self.date_edit = QDateEdit(self.centralwidget)
        self.date_edit.setDateTime(QtCore.QDateTime(QtCore.QDate(2024, 2, 16), QtCore.QTime(0, 0, 0)))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setCurrentSectionIndex(2)
        self.top_bar_qhb.addWidget(self.date_edit)
        spacerItem5 = QSpacerItem(100, 20, size_policy().Maximum, size_policy().Minimum)
        self.top_bar_qhb.addItem(spacerItem5)
        self.next_btn = QToolButton(self.centralwidget)

        self.top_bar_qhb.addWidget(self.next_btn)
        spacerItem6 = QSpacerItem(10, 20, size_policy().Fixed, size_policy().Minimum)
        self.top_bar_qhb.addItem(spacerItem6)
        self.verticalLayout.addLayout(self.top_bar_qhb)
        self.timetable = QTableWidget(self.centralwidget)
        sizePolicy = QSizePolicy(size_policy().Expanding, size_policy().Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.timetable.sizePolicy().hasHeightForWidth())
        self.timetable.setSizePolicy(sizePolicy)
        self.timetable.setAutoFillBackground(True)
        self.timetable.setAlternatingRowColors(True)
        self.timetable.setShowGrid(False)
        self.timetable.setRowCount(8)
        self.timetable.setColumnCount(5)
        self.timetable.horizontalHeader().setCascadingSectionResizes(False)
        self.timetable.horizontalHeader().setDefaultSectionSize(220)
        self.timetable.horizontalHeader().setMinimumSectionSize(210)
        self.timetable.verticalHeader().setVisible(False)
        self.timetable.verticalHeader().setDefaultSectionSize(70)
        self.timetable.verticalHeader().setMinimumSectionSize(70)
        self.verticalLayout.addWidget(self.timetable)
        if use_qt5:
            self.next_btn.setArrowType(QtCore.Qt.RightArrow)
            self.prev_btn.setArrowType(QtCore.Qt.LeftArrow)
            self.date_edit.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
            self.timetable.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
            self.timetable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        else:
            self.next_btn.setArrowType(QtCore.Qt.ArrowType.RightArrow)
            self.prev_btn.setArrowType(QtCore.Qt.ArrowType.LeftArrow)
            self.date_edit.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
            self.timetable.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
            self.timetable.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)
        self.prev_btn.setShortcut("Left")
        self.reload_btn.setShortcut("Up, Ctrl+R")
        self.next_btn.setShortcut("Right")
        
    current_date = QDate.currentDate()
    def date_changed(self):
        new_date = self.date_edit.date()
        if self.current_date.weekNumber() != new_date.weekNumber():
            self.fetch_week()
        self.current_date = new_date

    def load_settings(self, no_set_credentials):
        if not no_set_credentials:
            self.server   = self.settings.value('server')
            self.school   = self.settings.value('school')
            self.user     = self.settings.value('user')
            self.password = self.settings.value('password')
        if not "--no-cache" in sys.argv:
            self.ref_cache = self.settings.value('cached_timetable') or []
        else:
            self.ref_cache = []

    def delete_settings(self):
        self.settings.clear()

    def login_popup(self):
        popup = LoginPopup(self.settings)
        popup.exec()
        self.load_settings(False)
        # try to start a new session
        credentials = [self.server, self.school, self.user, self.password]
        if None not in credentials and '' not in credentials:
            self.session = api.API(credentials, self.ref_cache)
            if type(self.session) != list: # if login successful
                self.fetch_week()
            else:
                QMessageBox.critical(
                    self,
                    self.session[0],
                    self.session[1]
                )
                self.session = None

    def info_popup(self):
        if self.is_interactive:
            popup = InfoPopup(self)
            popup.exec()
    
    def draw_week(self):
        selected_day = self.date_edit.date().toPyDate()
        week_number = selected_day.isocalendar()[1]
        monday = dt.date.fromisocalendar(selected_day.year, week_number, 1)
        
        self.is_interactive = False

        self.timetable.setRowCount(len(self.data))

        if not self.week_is_cached:
            self.verticalLayout.removeWidget(self.cache_warning[1])
            self.resize(self.width(), self.cache_warning[0])

        for row in range(len(self.data)):
            for col in range(len(self.data[row])):
                widget = QFrame_click()
                try:
                    entry_data = self.data[row][col]
                    # add the on-click function for lesson info. dont change the lambda it barely works as-is
                    if (len(entry_data) != 0):
                        fn = lambda row=row, col=col: f"{self.timetable.setCurrentCell(row, col)}\n{self.info_popup()}"
                        widget.clicked.connect(fn)
                except IndexError:
                    entry_data = []
                layout = QHBoxLayout()
                layout.setContentsMargins(0, 0, 0, 0);
                
                if (col != 0):
                    line = QFrame()
                    line.setFrameShape(QFrame.Shape.VLine)
                    line.setStyleSheet("background-color:white;")
                    line.setMaximumWidth(1)
                    layout.addWidget(line)
                else:
                    layout.addSpacing(6)

                entry_data.sort()
                for i in range(len(entry_data)):
                    lesson = entry_data[i]
                    lesson_widget = QLabel()
                    lesson_widget.setTextFormat(Qt.TextFormat.RichText)
                    richtext = f"<b>{lesson[0]}</b><br>{lesson[1]}"
                    stylesheet = f"padding-right:4px; padding-left:4px; margin-top: 4px; margin-bottom:4px; border-radius:4px;"
                    if lesson[3] != "white":
                         stylesheet+=f"background-color:{lesson[3]};"
                    if lesson[2] != '':
                        richtext += f"<br><small>{lesson[2]}</small>"
                    lesson_widget.setStyleSheet(stylesheet)
                    lesson_widget.setText(richtext)
                    layout.addWidget(lesson_widget)
                    if len(entry_data) != 1 and i+1 != len(entry_data):
                        # add separator
                        line = QFrame()
                        line.setFrameShape(QFrame.Shape.VLine)
                        line.setStyleSheet("background-color:gray;margin-top:7px;margin-bottom:7px;border-radius:5px")
                        layout.addWidget(line)
                
                if (len(entry_data) == 0):
                   layout.addWidget(QWidget())
                
                
                if (col != len(self.data[row])-1):
                    line = QFrame()
                    line.setFrameShape(QFrame.Shape.VLine)
                    line.setStyleSheet("background-color:white;")
                    line.setMaximumWidth(1)
                    layout.addWidget(line)
                else:
                    layout.addSpacing(6)
                
                widget.setLayout(layout)
                
                self.timetable.setCellWidget(row, col, widget)
                
        # highlight the current day, if it is within the week
        current_date = QDate.currentDate()
        default_brush = QTableWidgetItem().background()
        for i in range(5):
            ref_tm = QDate(monday).addDays(i)
            if (monday == current_date.addDays((i)*-1)):
                brush = QBrush(QColor(0x30, 0xA5, 0x30))
                self.timetable.horizontalHeaderItem(i).setBackground(brush)
            else:
                self.timetable.horizontalHeaderItem(i).setBackground(default_brush)
            # https://doc.qt.io/qt-6/qdate.html#toString-1
            self.timetable.horizontalHeaderItem(i).setText(ref_tm.toString("dddd (d.M)"))
        self.is_interactive = True

    def fetch_week(self, replace_cache=False, silent=False, skip_cache=False):
        selected_day = self.date_edit.date().toPyDate()
        week_number = selected_day.isocalendar()[1]
        monday = dt.date.fromisocalendar(selected_day.year, week_number, 1)
        friday = dt.date.fromisocalendar(selected_day.year, week_number, 5)

        if "--fake-data" in sys.argv:
            self.data = [[[['mo 1', 'regular lesson', '', 'white', None]], [['tu 1', 'regular lesson', '', 'white', None]]], [[['mo 2', 'single, red', '', 'red', None]], [['tu 2', 'single, orange', '', 'orange', None]]], [[['mo 3', 'half, white', '', 'white', None], ['mo 3', 'second half', '', 'white', None]], [['hello', 'half, red', '', 'red', None], ['world', 'other half', '', 'white', None]]]]
            self.week_is_cached = False
            self.draw_week()
            return

        if not (replace_cache or skip_cache):
            self.week_is_cached = True
            # quickly load some cache data
            self.data = api.get_cached(self.ref_cache, monday)
            if self.force_cache:
                if self.data != [] and self.data[0] == "err":
                    if not silent:
                        QMessageBox.critical(
                            self,
                            self.data[1],
                            self.data[2]
                        )
                    return
                self.data = self.data[1]
                self.draw_week()
                return
            if self.data != [] and self.data[0] != "err":
                self.data = self.data[1]
                self.draw_week()
        # properly fetch data
        if replace_cache:
            self.data = self.session.get_table(monday, friday, (replace_cache or skip_cache))
            if self.data != [] and self.data[0] == "err":
                if not silent:
                    QMessageBox.critical(
                        self,
                        self.data[1],
                        self.data[2]
                    )
                return
            self.week_is_cached = self.data[0]
            self.data = self.data[1]
            return

        def cache_refresh(parent, monday, friday):
            data = parent.session.get_table(monday, friday, True)
            if (data[0] == "err"):
                QMessageBox.critical(
                    parent,
                    data[1],
                    data[2]
                )
                return
            else:
                parent.data = data[1]
            parent.week_is_cached = False
            parent.redraw_trip = True
        
        # if our results were from cache, asynchronously refresh that
        if (self.week_is_cached and not self.force_cache and not replace_cache):
            # async start a thread with api.get_table
            api_thread = threading.Thread(target=cache_refresh, args = (self, monday, friday,))
            api_thread.start()
    
    def prev_week(self):
        self.date_edit.setDate(self.date_edit.date().addDays(-7))

    def next_week(self):
        self.date_edit.setDate(self.date_edit.date().addDays(7))

    def current_week(self):
        self.date_edit.setDate(QDate.currentDate())

    def reload_all(self):
        self.ref_cache = []
        # delete all rows and draw empty table to make the reload visible
        self.timetable.setRowCount(0)
        self.timetable.repaint()
        self.session = api.API([self.server, self.school, self.user, self.password], self.ref_cache)
        self.fetch_week()
        self.is_interactive = True

    def test_trip_redraw(self):
        if self.redraw_trip != False:
            self.redraw_trip = False
            self.draw_week()
    
    def login_thread(self):
        if not self.session_trip:
            return

        credentials = [self.server, self.school, self.user, self.password]
        if None not in credentials and '' not in credentials and '--fake-data' not in sys.argv and '--force-cache' not in sys.argv:
            if self.session.error_state == None: # if login successful (already tried pre-trip)
                self.fetch_week(skip_cache=True)
            else:
                box = QMessageBox (
                    QMessageBox.Icon.Critical,
                    "Login Failed!",
                    f"<h3>Login Failed!</h3><b>Details:</b><br>{self.session.error_state}<h4>Use cached data only?</h4>",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                self.force_cache = (box.exec() == QMessageBox.StandardButton.Yes)
                self.session = None
        elif '--fake-data' in sys.argv:
            self.fetch_week()
        elif '--force-cache' in sys.argv:
            self.force_cache = True
            self.session = None
        else:
            self.session = None
        
        if self.force_cache:
            if (self.cache_warning):
                self.verticalLayout.removeWidget(self.cache_warning[1])
                self.cache_warning = None
            cache_warning = QLabel("<span style='color:#F44;'>Cache-only mode active, restart to disable!</span>")
            self.verticalLayout.addWidget(cache_warning)
            # resize to just-enough-to-fit unless it is already big enough
            self.resize(self.width(), max(self.height(), 698))
            self.fetch_week()
        
        # stop trying this, its useless
        self.session_timer.stop()

    def login_thread_defer(parent):
        credentials = [parent.server, parent.school, parent.user, parent.password]
        if None not in credentials and '' not in credentials and '--fake-data' not in sys.argv and '--force-cache' not in sys.argv:
            # this part can take forever in theory
            parent.session = api.API(credentials, parent.ref_cache)

        # trip in any case, to ensure the fairly frequent login timer doesn't run forever
        parent.session_trip = True

    def __init__(self):
        super().__init__()
        self.settings = QSettings('l-koehler', 'untis-py')
        self.is_interactive = False
        self.redraw_trip = False # tripped by thread whenever the data was asynchronously refreshed
        self.redraw_timer = QTimer()
        self.redraw_timer.timeout.connect(self.test_trip_redraw)
        self.redraw_timer.start(500) # twice a second
        self.session_trip = False
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self.login_thread)
        self.session_timer.start(100) # ten times a second, but deleted after use
        
        self.load_settings('--credentials' in sys.argv) # don't overwrite credentials true/false
        
        if "--delete-settings" in sys.argv:
            self.delete_settings()
        if getattr(sys, 'frozen', False):
            ico_path = os.path.join(sys._MEIPASS, "icon.ico")
        else:
            ico_path = "./icon.ico"
        self.setupUi(self)
        # workaround to set icon on windows
        # how did this mess of an OS ever succeed
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('l-koehler.untis-py')
        # set application icon
        self.setWindowIcon(QIcon(ico_path))
        for index in range(len(sys.argv)):
            if sys.argv[index] == '--credentials':
                if len(sys.argv) < index+5:
                    print(f"--credentials takes 4 arguments, {len(sys.argv)-index-1} were passed!")
                    print("use --credentials <server> <school> <username> <password>")
                    exit(1)
                self.server   = sys.argv[index+1]
                self.school   = sys.argv[index+2]
                self.user     = sys.argv[index+3]
                self.password = sys.argv[index+4]
        self.date_edit.setDate(QDate.currentDate())
        self.shortcut_current_week = QShortcut(QKeySequence('Down'), self)
        self.shortcut_current_week.activated.connect(self.current_week)
        self.timetable.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.date_edit.dateChanged.connect(self.date_changed)
        self.login_btn.pressed.connect(self.login_popup)
        self.timetable.cellClicked.connect(self.info_popup)
        self.prev_btn.pressed.connect(self.prev_week)
        self.next_btn.pressed.connect(self.next_week)
        self.reload_btn.pressed.connect(self.reload_all)
        self.timetable.setHorizontalHeaderLabels([""]*5)
        self.force_cache = False
        self.cache_warning = None
        self.data = None
        self.session = None
        self.week_is_cached = False
        self.show()
        
        # try loading cached data to display at-least-something during login/fetch (unless that'll happen anyways)
        if not '--force-cache' in sys.argv:
            self.cache_warning = (self.height(), QLabel("Not yet logged in, data might be outdated!"))
            self.verticalLayout.addWidget(self.cache_warning[1])
            # resize to just-enough-to-fit unless it is already big enough
            self.resize(self.width(), max(self.height(), 698))
            self.force_cache = True
            self.fetch_week(silent=True)
            self.force_cache = False
        
        # if the credentials are already all set, log in asynchronously
        self.session_thread = threading.Thread(target=self.login_thread_defer)
        self.session_thread.start()

    def closeEvent(self, event):
        # save the new cache before closing
        if not "--no-cache" in sys.argv and self.session != None:
            self.settings.setValue('cached_timetable', self.session.cache)
        event.accept()
        # cause a AssertionError to kill the login thread
        if self.session_thread.is_alive():
            # causes a RuntimeError in login_thread_defer by starting the already-started thread.
            # this is fully intentional, as we no longer need to login as we are already closing
            # and if a login thread returns neither result nor timeout it could get stuck for ages, leaving the program unable to close
            self.session_thread.start()
