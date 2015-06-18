import sys
import os.path
import subprocess
from collections import defaultdict
import re
import traceback
import json

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
    QPixmap,
)
import patricia
import polytaxis_monitor.common as ptcommon
import appdirs

from .qtwrapper import *
from .common import *
from .settings import res

# TODO
# element types to vars
# order element
# save queries

# tag editor
# launcher editor

one_file = '{one-file}'
all_files = '{all-files}'

icon_size = QSize(24, 24)
icon_remove = None
icons = {}

eltype_labels = {
    'inc': 'include',
    'exc': 'exclude',
    'sort_asc': 'sort ascending',
    'sort_desc': 'sort descending',
    'sort_rand': 'randomize',
    'col': 'show column',
}

long_ext_regex = re.compile(r'\.[^/]+$')
short_ext_regex = re.compile(r'\.[^.]+$')

known_columns = patricia.trie()

elements = []

def to_gen(outer):
    return outer()

unwrap_root = os.path.join(
    appdirs.user_data_dir('polytaxis-unwrap', 'zarbosoft'),
    'mount',
)

def unwrap(path):
    return os.path.join(unwrap_root, path[1:])

def collapse(callback):
    timer = QTimer()
    timer.setSingleShot(True)
    timer.setInterval(200)
    def out(*maybe_self):
        out._maybe_self = maybe_self[:1]
        timer.start()
    out.stop = lambda: timer.stop()
    timer.timeout.connect(lambda: callback(*out._maybe_self))
    return out

class ElementBuilder(QObject):
    worker_result = pyqtSignal(int, list)

    def __init__(self):
        super(ElementBuilder, self).__init__()
        self.element = None
        self.worker = None

        self.query_unique = 0
        self.text = None
        self.label = QLabel(tags=['builder-label'])
        self.entry = QLineEdit(tags=['builder-entry'])
        self.entry_layout = QHBoxLayout(tags=['builder-head-layout'])
        self.entry_layout.addWidget(self.label)
        self.entry_layout.addWidget(self.entry)
        self.results = QListWidget(tags=['builder-list'])
        layout = QVBoxLayout(tags=['builder-layout'])
        layout.addLayout(self.entry_layout)
        layout.addWidget(self.results)
        self.outer_widget = QFrame(tags=['builder-widget'])
        self.outer_widget.setLayout(layout)
        
        suppress_row_select = [False]

        @self.entry.textEdited.connect
        def edited(text):
            self.element.set_value(text)
            self.element.last_query = self.text
            self.change_query()

        @self.results.currentTextChanged.connect
        def selected(text):
            if suppress_row_select[0]:
                return
            if not text:
                return
            self.element.set_value(text)
            self.entry.setText(text)

        @self.worker_result.connect
        def handle_result(unique, values):
            if unique != self.query_unique:
                return
            for row, value in enumerate(values):
                self.results.addItem(value)
                if value == self.text:
                    suppress_row_select[0] = True
                    self.results.setCurrentRow(row)
                    suppress_row_select[0] = False
    
    @collapse
    def _reset_query(self):
        self.query_unique += 1
        self.text = self.entry.text()
        if self.element.type in ('sort_asc', 'sort_desc', 'sort_rand', 'col'):
            for row, column in enumerate(known_columns.iter(self.element.last_query)):
                self.results.addItem(column)
                if column == self.text:
                    self.results.setCurrentRow(row)
        elif self.element.type in ('inc', 'exc'):
            self.worker.build_query.emit(self.query_unique, self.element.last_query)

    def change_query(self):
        self.worker.build_query.emit(-1, '')
        self.results.clear()
        self._reset_query()

    def set_element(self, element):
        if element == self.element:
            return
        if self.element:
            self.element.auto_deselect()
        self.element = element
        if element is None:
            self.worker.build_query.emit(-1, '')
            self.outer_widget.hide()
        else:
            self.label.setPixmap(icons[element.type])
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

        self.launchers = []

        context_menu = QMenu()
        open_menu = QMenu()
        self.results = MouseLMRTreeWidget(tags=['display-tree'])
        self.results.setSelectionMode(QTreeWidget.ExtendedSelection)
        @self.results.customContextMenuRequested.connect
        def callback(point):
            context_menu.exec(point)
        self.results.header().hide()
        actions = QToolBar(tags=['display-toolbar'])
        tool_open = actions.addAction('Open')
        tool_open.setMenu(open_menu)
        layout = QVBoxLayout(tags=['display-layout'])
        layout.addWidget(self.results)
        layout.addWidget(actions)
        self.outer_widget = QFrame(tags=['display-widget'])
        self.outer_widget.setLayout(layout)

        def spawn(command):
            print('spawning {}'.format(command))
            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            proc.stdin.close()
            proc.stdout.close()
            proc.stderr.close()

        def do_open(option):
            print('callin open')
            rows = [
                self.raw[index.row()] 
                for index in self.results.selectedIndexes()
                if index.column() == 0
            ]
            if not rows:
                rows = self.raw
            if not rows:
                return
            paths = [
                unwrap(path) if option.get('unwrap', True) else path
                for path in [
                    next(iter(row['tags']['path'])) 
                    for row in rows
                ]
            ]
            if one_file in option['command']:
                for path in paths:
                    spawn([
                        path if arg == one_file else arg
                        for arg in option['command']
                    ])
            else:
                if all_files not in option['command']:
                    raise RuntimeError('Option {} doesn\'t have any filepath arguments.'.format(option['name']))
                args = []
                for arg in option['command']:
                    if arg == all_files:
                        args.extend(paths)
                    else:
                        args.append(arg)
                spawn(args)
        
        @collapse
        def update_launch_concensus():
            launch_sums = defaultdict(lambda: 0)
            rows = [
                self.raw[index.row()] 
                for index in self.results.selectedIndexes()
            ]
            if not rows:
                rows = self.raw
            for data in rows:
                for key in data['tags']['launch_keys']:
                    launch_sums[key] += 1
            self.launchers = []
            for top in sorted(launch_sums.items(), key=lambda x: x[1]):
                if len(self.launchers) > 5:
                    break
                launcher_bunch = keyed_launchers.get(top[0])
                if not launcher_bunch:
                    continue
                self.launchers.extend(launcher_bunch)
            self.launchers.extend(
                wildcard_launchers
            )

            for menu in [open_menu, context_menu]:
                menu.clear()
                for launcher in self.launchers:
                    action = menu.addAction(launcher['name'])
                    def launch():
                        do_open(launch.launcher)
                    launch.launcher = launcher
                    action.triggered.connect(launch)
            if self.launchers:
                tool_open.setText('Open with ' + self.launchers[0]['name'])
        
        @self.worker_result.connect
        def handle_result(unique, rows):
            if unique != self.query_unique:
                return
            for row in rows:
                for key in row['tags'].keys():
                    known_columns[key] = None
            self.raw.extend(rows)
            self._redisplay()
            update_launch_concensus()

        @self.results.m_clicked_anywhere.connect
        def handle_m_clicked():
            self.results.clearSelection()
        
        @self.results.itemSelectionChanged.connect
        def callback():
            update_launch_concensus()

        @self.results.r_clicked_anywhere.connect
        def handle_r_clicked(position):
            context_menu.exec(position)

        @self.results.doubleClicked.connect
        def handle_clicked(index):
            if not self.launchers:
                return
            do_open(self.launchers[0])

        @tool_open.triggered.connect
        def handle_clicked(index):
            if not self.launchers:
                return
            do_open(self.launchers[0])
        
    @collapse
    def _reset_query(self):
        self.worker.display_query.emit(
                self.query_unique, self.includes, self.excludes)
    
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
        cleared = [False]
        def clear():
            if not cleared[0]:
                cleared[0] = True
            self.results.clear()

        includes = {
            element.value for element in elements if element.type == 'inc'}
        excludes = {
            element.value for element in elements if element.type == 'exc'}
        columns = []
        sort = []
        for element in elements:
            if element.type in ('col', 'sort_asc', 'sort_desc', 'sort_rand') and element.value:
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
            clear()
            self._reset_query()

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
            clear()
            self._redisplay()

wildcard_launchers = []
keyed_launchers = defaultdict(lambda: [])
def main():
    launchers_path = os.path.join(
        appdirs.user_config_dir('polytaxis-adventure'),
        'launchers.json',
    )
    try:
        with open(launchers_path, 'r') as launchers_file:
            launchers = json.load(launchers_file)
        for launcher in launchers:
            for key in launcher['keys']:
                if key == '*':
                    wildcard_launchers.append(launcher)
                else:
                    keyed_launchers[key].append(launcher)
    except:
        print('Failed to load {}:\n{}'.format(
            launchers_path, 
            traceback.format_exc())
        )

    app = QApplication(sys.argv)

    global icon_remove
    icon_remove = QPixmap(res('icon_remove.png'))
    global icons
    icons = {
        key: QPixmap(res('icon_{}.png'.format(key)))
        for key in [
            'exc',
            'inc',
            'col',
            'sort_asc',
            'sort_desc',
            'sort_rand',
        ]
    }
    icons['logo'] = QPixmap(res('logo.png'))
    for icon in icons.values():
        if not icon:
            raise RuntimeError('Unable to load icon {}'.format(icon))

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
                        for row in rows:
                            path = next(iter(row['tags']['path']))
                            long_ext = long_ext_regex.findall(path)
                            short_ext = short_ext_regex.findall(path)
                            launch_keys = set()
                            if long_ext:
                                launch_keys.add(long_ext[0])
                            if short_ext:
                                launch_keys.add(short_ext[0])
                            row['tags']['launch_keys'] = launch_keys
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
    appicon = QToolButton(tags=['appicon'])
    appicon.setIcon(QIcon(icons['logo']))
    appicon.setIconSize(QSize(48, 48))

    query = FlowLayout(tags=['query-layout'])
    query_toolbar = QToolBar(tags=['query-toolbar'])
    query_toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    def create_query_element_action(eltype):
        ellabel = eltype_labels[eltype]
        action = QAction(QIcon(icons[eltype]), ellabel, query_toolbar, tags=['query-tool', eltype])
        query_toolbar.addAction(action)
        def create(ign1):
            layout = QHBoxLayout(tags=['element-layout', eltype])
            icon = QLabel(tags=['element-icon', eltype])
            icon.setPixmap(icons[eltype])
            layout.addWidget(icon)
            text = QLabel(tags=['element-text', eltype])
            layout.addWidget(text)
            delete = QToolButton(tags=['element-remove', eltype])
            delete.setIcon(QIcon(icon_remove))
            layout.addWidget(delete)
            toggle = LayoutPushButton(tags=['element-toggle', eltype])
            toggle.setLayout(layout)
            query.addWidget(toggle)
            delete.hide()

            class Element():
                type = eltype
                value = ''
                last_query = ''

                def set_value(self, value):
                    self.value = value
                    text.setText(value)
                    display.change_query()

                def auto_deselect(self):
                    toggle.setChecked(False)
                    delete.hide()

                def deselect(self):
                    build.set_element(None)
                    delete.hide()

                def select(self):
                    build.set_element(self)
                    toggle.setChecked(True)
                    delete.show()

                def destroy(self):
                    self.deselect()
                    elements.remove(self)
                    display.change_query()
                    query.removeWidget(toggle)

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

            element.select()
            elements.append(element)

        action.triggered.connect(create)
    create_query_element_action('inc')
    create_query_element_action('exc')
    create_query_element_action('sort_asc')
    create_query_element_action('sort_desc')
    create_query_element_action('sort_rand')
    create_query_element_action('col')
    query_layout = QVBoxLayout(tags=['outer-query-layout'])
    query_layout.addLayout(query, 1)
    query_layout.addWidget(query_toolbar)
    
    total_query_layout = QHBoxLayout(tags=['top-layout'])
    total_query_layout.addWidget(appicon)
    total_query_layout.addLayout(query_layout, 1)

    # Assemblage
    bottom_splitter = QSplitter(Qt.Horizontal, tags=['bottom-splitter'])
    bottom_splitter.addWidget(build.outer_widget)
    bottom_splitter.addWidget(display.outer_widget)

    total_layout = QVBoxLayout(tags=['window-layout'])
    total_layout.addLayout(total_query_layout)
    total_layout.addWidget(bottom_splitter, 1)

    window = QFrame(tags=['window'])
    window.setObjectName('window')
    window.setLayout(total_layout)
    window.show()

    build.outer_widget.hide()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
