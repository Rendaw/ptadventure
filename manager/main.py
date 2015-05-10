import sys
import os.path
import subprocess

from PyQt5.QtCore import (
    QObject,
    QThread,
    QTimer,
    QPoint,
    QRect,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QIcon,
)
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QListWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QWidget,
    QToolBar,
    QSplitter,
)
import patricia
import polytaxis_monitor.common as ptcommon
import appdirs

from flowlayout import FlowLayout

# TODO
# enable/disable path expansion
# element types to vars
# order element
# element labels to images

# open
# tag editor

icon_remove = QIcon('/home/fsandrew/downloads/material-design-icons/action/svg/design/ic_highlight_remove_24px.svg')

eltype_labels = {
    'inc': '',
    'exc': '^',
    'sort_asc': 'sort+:',
    'sort_desc': 'sort-:',
    'sort_rand': 'sort?:',
    'col': 'col:',
}

known_columns = patricia.trie()

elements = []

def limit(maxcount, generator):                                                 
    count = 0                                                                   
    for x in generator:                                                         
        if count >= maxcount:                                                   
            break                                                               
        count += 1                                                              
        yield x 

def to_gen(outer):
    return outer()

unwrap_root = os.path.join(
    appdirs.user_data_dir('polytaxis-unwrap', 'zarbosoft'),
    'mount',
)

def default_open(paths):
    # TODO reimplement with configured apps, based on majority extension
    # + configured unwrap
    for path in paths:
        path = os.path.join(unwrap_root, path[1:])
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', path))
        elif os.name == 'nt':
            os.startfile(path)
        elif os.name == 'posix':
            subprocess.call(('xdg-open', path))

class ElementBuilder(QObject):
    worker_result = pyqtSignal(int, list)
    def __init__(self):
        super(ElementBuilder, self).__init__()
        self.element = None
        self.worker = None

        self.query_unique = 0
        self.text = None
        self.refresh_timer = QTimer()
        self.label = QLabel()
        self.entry = QLineEdit()
        self.entry_layout = QHBoxLayout()
        self.entry_layout.addWidget(self.label)
        self.entry_layout.addWidget(self.entry)
        self.results = QListWidget()
        layout = QVBoxLayout()
        layout.addLayout(self.entry_layout)
        layout.addWidget(self.results)
        self.outer_widget = QWidget()
        self.outer_widget.setLayout(layout)
        
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(200)
        @self.refresh_timer.timeout.connect
        def change_query_():
            self.query_unique += 1
            self.text = self.entry.text()
            if self.element.type in ('sort_asc', 'sort_desc', 'sort_rand', 'col'):
                for row, column in enumerate(known_columns.iter(self.text)):
                    self.results.addItem(column)
                    if column == self.text:
                        self.results.setCurrentRow(row)
            elif self.element.type in ('inc', 'exc'):
                self.worker.build_query.emit(self.query_unique, self.text)

        @self.entry.textEdited.connect
        def edited(text):
            self.element.set_value(text)
            self.change_query()

        @self.results.currentTextChanged.connect
        def selected(text):
            self.element.set_value(text)

        @self.worker_result.connect
        def handle_result(unique, values):
            if unique != self.query_unique:
                return
            for row, value in enumerate(values):
                self.results.addItem(value)
                if value == self.text:
                    self.results.setCurrentRow(row)

    def change_query(self):
        self.worker.build_query.emit(-1, '')
        self.results.clear()
        self.refresh_timer.start()

    def set_element(self, element):
        if self.element:
            self.element.auto_deselect()
        self.element = element
        if element is None:
            self.worker.build_query.emit(-1, '')
            self.outer_widget.hide()
        else:
            self.label.setText(eltype_labels[element.type])
            self.entry.setText(element.value)
            self.change_query()
            self.outer_widget.show()
            self.entry.setFocus()

class Display(QObject):
    worker_result = pyqtSignal(int, list)
    def __init__(self):
        super(Display, self).__init__()
        
        self.worker = None

        self.query_unique = 0
        self.columns = None
        self.sort = None
        self.filters = None
        self.includes = None
        self.excludes = None
        self.raw = []

        self.results = QTreeWidget()
        self.results.header().hide()
        actions = QToolBar()
        tool_open = actions.addAction('Open')
        layout = QVBoxLayout()
        layout.addWidget(self.results)
        layout.addWidget(actions)
        self.outer_widget = QWidget()
        self.outer_widget.setLayout(layout)
        
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(200)
        @self.refresh_timer.timeout.connect
        def change_query_():
            self.worker.display_query.emit(
                    self.query_unique, self.includes, self.excludes)

        @self.worker_result.connect
        def handle_result(unique, rows):
            if unique != self.query_unique:
                return
            for row in rows:
                for key in row['tags'].keys():
                    known_columns[key] = None
            self.raw.extend(rows)
            self._redisplay()

        @self.results.doubleClicked.connect
        def handle_clicked(index):
            default_open([next(iter(self.raw[index.row()]['tags']['path']))])
    
    def _redisplay(self):
        self.raw = ptcommon.sort(self.sort, self.raw)
        self.results.clear()
        #self.results.setRowCount(0)
        for row in self.raw:
            self.results.addTopLevelItem(QTreeWidgetItem([
                ', '.join(list(row['tags'].get(column, [])))
                for column in self.columns]))
        self.results.header().resizeSections(QHeaderView.ResizeToContents)

    def change_query(self):
        self.worker.display_query.emit(-1, set(), set())
        self.results.clear()

        includes = {
            element.value for element in elements if element.type == 'inc'}
        excludes = {
            element.value for element in elements if element.type == 'exc'}
        columns = []
        sort = []
        for element in elements:
            if element.type in ('col', 'sort_asc', 'sort_desc', 'sort_rand'):
                columns.append(element.value)
            if element.type == 'sort_asc':
                sort.append(('asc', element.value))
            elif element.type == 'sort_desc':
                sort.append(('desc', element.value))
            elif element.type == 'sort_rand':
                sort.append(('rand', element.value))

        if includes != self.includes or excludes != self.excludes:
            self.query_unique += 1
            known_columns = patricia.trie()
            self.raw = []
            self.includes = includes
            self.excludes = excludes
            self.refresh_timer.start()

        if columns != self.columns or sort != self.sort:
            self.columns = columns
            self.sort = sort
            if self.columns:
                self.results.setColumnCount(len(self.columns))
                self.results.setHeaderLabels(self.columns)
                self.results.header().show()
            else:
                self.results.header().hide()
                self.results.setColumnCount(1)
                self.columns = ['path']
            self._redisplay()

def main():
    app = QApplication(sys.argv)

    class Worker(QObject):
        build_query = pyqtSignal(int, str)
        display_query = pyqtSignal(int, set, set)
        def __init__(self):
            super(Worker, self).__init__()

            self.build = None
            self.display = None

            self.current_build_query = None
            self.current_display_query = None
            self.db = ptcommon.QueryDB()
            self.queue = []
            self.idle = QTimer()
            self.idle.setInterval(0)
            @self.idle.timeout.connect
            def idle():
                if not self.queue:
                    self.idle.stop()
                    return
                work = self.queue.pop()
                try:
                    next(work)
                except StopIteration:
                    return
                self.queue.append(work)
            self.idle.start()

            @self.build_query.connect
            def build_query_handler(unique, arg):
                try:
                    self.queue.remove(self.current_build_query)
                except ValueError:
                    pass
                if unique == -1:
                    self.current_build_query = None
                    return
                @to_gen
                def work():
                    count = 0
                    work = self.db.query_tags('prefix', arg)
                    while True:
                        rows = list(limit(100, work))
                        if not rows:
                            raise StopIteration()
                        count += len(rows)
                        self.build.worker_result.emit(unique, rows)
                        if count >= 1000:
                            break
                        yield
                self.queue.append(work)
                self.current_build_query = work
                self.idle.start()
            
            @self.display_query.connect
            def display_query_handler(unique, includes, excludes):
                try:
                    self.queue.remove(self.current_display_query)
                except ValueError:
                    pass
                if unique == -1:
                    self.current_display_query = None
                    self.db.clear_cache()
                    return
                @to_gen
                def work():
                    count = 0
                    work = self.db.query(
                            includes, excludes,
                        add_path=True)
                    while True:
                        rows = list(limit(100, work))
                        if not rows:
                            raise StopIteration()
                        count += len(rows)
                        self.display.worker_result.emit(unique, rows)
                        if count >= 1000:
                            break
                        yield
                self.queue.append(work)
                self.current_display_query = work
                self.idle.start()

    worker_thread = QThread()
    worker_thread.start()

    worker = Worker()
    worker.moveToThread(worker_thread)
    
    # Query element specification
    build = ElementBuilder()
    build.worker = worker
    worker.build = build

    # Result display and interaction
    display = Display()
    display.worker = worker
    worker.display = display

    # Query bar
    query = FlowLayout()
    query_toolbar = QToolBar()
    def create_query_element_action(eltype):
        action = query_toolbar.addAction(eltype)
        def create(ign1):
            ellabel = eltype_labels[eltype]
            toggle = QPushButton(ellabel)
            toggle.setCheckable(True)
            toggle.setObjectName('button')
            delete = QPushButton(icon_remove, 'remove')
            delete.setObjectName('delete')
            layout = QHBoxLayout()
            layout.addWidget(toggle)
            layout.addWidget(delete)
            wrapper = QWidget()
            wrapper.setLayout(layout)
            wrapper.setProperty('class', 'element {}'.format(eltype))
            query.addWidget(wrapper)
            delete.hide()

            class Element():
                type = eltype
                value = ''

                def set_value(self, value):
                    self.value = value
                    toggle.setText(ellabel + value)
                    display.change_query()

                def auto_deselect(self):
                    toggle.setChecked(False)
                    delete.hide()

                def deselect(self):
                    build.set_element(None)
                    delete.hide()

                def select(self):
                    build.set_element(self)
                    delete.show()

                def destroy(self):
                    self.deselect()
                    elements.remove(self)
                    display.change_query()
                    query.removeWidget(wrapper)

            element = Element()
            
            @toggle.toggled.connect
            def click_action(checked):
                if checked:
                    element.select()
                else:
                    element.deselect()

            @delete.clicked.connect
            def delete_action(checked):
                element.destroy()

            toggle.setChecked(True)
            elements.append(element)

        action.triggered.connect(create)
    create_query_element_action('inc')
    create_query_element_action('exc')
    create_query_element_action('sort_asc')
    create_query_element_action('sort_desc')
    create_query_element_action('sort_rand')
    create_query_element_action('col')
    query_layout = QVBoxLayout()
    query_layout.addLayout(query)
    query_layout.addWidget(query_toolbar)

    # Assemblage
    bottom_splitter = QSplitter(Qt.Horizontal)
    bottom_splitter.addWidget(build.outer_widget)
    bottom_splitter.addWidget(display.outer_widget)

    total_layout = QVBoxLayout()
    total_layout.addLayout(query_layout)
    total_layout.addWidget(bottom_splitter, 1)

    window = QWidget()
    window.setLayout(total_layout)
    window.show()

    build.outer_widget.hide()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
