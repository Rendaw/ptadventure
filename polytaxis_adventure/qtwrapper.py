import itertools
import collections
import hashlib

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
    QPainter,
)
from PyQt5.QtWidgets import (
    QApplication,
    QLabel as _QLabel,
    QPushButton as _QPushButton,
    QAction as _QAction,
    QToolButton as _QToolButton,
    QLayout,
    QHBoxLayout as _QHBoxLayout,
    QVBoxLayout as _QVBoxLayout,
    QMenu,
    QLineEdit as _QLineEdit,
    QListWidget as _QListWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFrame as _QFrame,
    QToolBar as _QToolBar,
    QSplitter as _QSplitter,
    QStyleOptionButton,
    QStyle,
)

from .flowlayout import FlowLayout as _FlowLayout
from .common import *
from .settings import style_settings

def _tag_keys(tags):
    for sublen in range(len(tags)):
        for subset in itertools.combinations(tags, sublen + 1):
            yield frozenset(subset)

def trym(dest, method, *pargs, **kwargs):
    if hasattr(dest, method):
        getattr(dest, method)(*pargs, **kwargs)

def rupdate(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            r = rupdate(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d

def stylable(cls):
    class new_cls(cls):
        def __init__(self, *pargs, **kwargs):
            tags = kwargs.pop('tags', [])
            cls.__init__(self, *pargs, **kwargs)
            tags.append(cls.__name__)
            use_name = getattr(self, '_style_name', cls.__name__)
            style = {}
            rupdate(style, {'styleSheet': getattr(self, '_default_style', {})})
            for key in limit(100, _tag_keys(tags)):
                substyle = dict(style_settings.get(key, {}))
                rupdate(style, substyle)
            stylesheet = style.pop('styleSheet', None)
            if stylesheet:
                selectors = []
                for key, values in stylesheet.items():
                    key = key.split(',')
                    if not key:
                        key = ['']
                    selectors.append(
                        '{} {{ {} }}'.format(
                            ', '.join([
                                '{}{}'.format(
                                    use_name,
                                    subkey,
                                ) for subkey in key
                            ]),
                            '; '.join([
                                '{}: {}'.format(key, value) 
                                for key, value in values.items()
                            ])
                        )
                    )
                stylesheet = ' '.join(selectors)
                if not hasattr(self, 'setStyleSheet'):
                    print('no setStyleSheet! {}'.format(cls.__name__))
                else:
                    print('using ss {}'.format(stylesheet))
                    self.setStyleSheet(stylesheet)
            trym(self, 'setMinimumWidth', style.pop('min-width', 0))
            trym(self, 'setMinimumHeight', style.pop('min-height', 0))
            trym(self, '__style_init__', style)
            if style:
                print('Unknown style settings for {}: {}'.format(cls.__name__, style))
    return new_cls

@stylable
class MouseLMRTreeWidget(QTreeWidget):
    l_clicked_anywhere = pyqtSignal(QPoint)
    m_clicked_anywhere = pyqtSignal(QPoint)
    r_clicked_anywhere = pyqtSignal(QPoint)

    def mousePressEvent(self, event):
        done = False
        if (
                QApplication.mouseButtons() & Qt.LeftButton and 
                self.receivers(self.l_clicked_anywhere) > 0):
            self.l_clicked_anywhere.emit(event.globalPos())
            done = True
        if (
                QApplication.mouseButtons() & Qt.MidButton and 
                self.receivers(self.m_clicked_anywhere) > 0):
            self.m_clicked_anywhere.emit(event.globalPos())
            done = True
        if (
                QApplication.mouseButtons() & Qt.RightButton and 
                self.receivers(self.r_clicked_anywhere) > 0):
            self.r_clicked_anywhere.emit(event.globalPos())
            done = True
        if not done:
            QTreeWidget.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        done = False
        if (
                QApplication.mouseButtons() & Qt.LeftButton and 
                self.receivers(self.l_clicked_anywhere) > 0):
            done = True
        if (
                QApplication.mouseButtons() & Qt.MidButton and 
                self.receivers(self.m_clicked_anywhere) > 0):
            done = True
        if (
                QApplication.mouseButtons() & Qt.RightButton and 
                self.receivers(self.r_clicked_anywhere) > 0):
            done = True
        if not done:
            QTreeWidget.mouseReleaseEvent(self, event)

@stylable
class QVBoxLayout(_QVBoxLayout):
    def __style_init__(self, style):
        self.setSpacing(float(style.pop('spacing', 0)))
        self.setContentsMargins(*style.pop('contentsMargins', [0, 0, 0, 0]))

@stylable
class QHBoxLayout(_QHBoxLayout):
    def __style_init__(self, style):
        self.setSpacing(float(style.pop('spacing', 0)))
        self.setContentsMargins(*style.pop('contentsMargins', [0, 0, 0, 0]))

@stylable
class FlowLayout(_FlowLayout):
    def __style_init__(self, style):
        self.setSpacing(float(style.pop('spacing', 0)))
        self.setContentsMargins(*style.pop('contentsMargins', [0, 0, 0, 0]))

@stylable
class QLabel(_QLabel):
    pass

@stylable
class QPushButton(_QPushButton):
    pass

_state_up = 0
_state_pressing = 1
_state_down = 2
@stylable
class LayoutPushButton(_QFrame):
    _style_name = 'QFrame'
    _default_style = {
        '': {
            'padding': '2px',
        }
    }
    toggled = pyqtSignal(bool)
    state = _state_up
    hover = False

    def paintEvent(self, event):
        opt = QStyleOptionButton()
        if self.state == _state_up:
            opt.state = QStyle.State_Active | QStyle.State_Enabled
        elif self.state in [_state_pressing, _state_down]:
            opt.state = QStyle.State_Active | QStyle.State_Enabled | QStyle.State_Sunken
        else:
            assert(False)
        if self.hover:
            opt.state |= QStyle.State_MouseOver
        opt.rect = self.frameRect()
        self.style().drawControl(QStyle.CE_PushButton, opt, QPainter(self));
        _QFrame.paintEvent(self, event)

    def setChecked(self, state):
        if state and self.state != _state_down:
            self.state = _state_down
            self.update()
        elif not state and self.state != _state_up:
            self.state = _state_up
            self.update()

    def mousePressEvent(self, event):
        if self.state == _state_up:
            self.state = _state_pressing
            self.update()
        self.grabMouse
        event.accept()

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            if self.state == _state_pressing:
                self.state = _state_down
                self.update()
                self.toggled.emit(True)
            else:
                self.state = _state_up
                self.update()
                self.toggled.emit(False)
            event.accept()
        else:
            self.state = _state_up
            self.update()
            event.ignore()

    def enterEvent(self, event):
        if self.hover:
            return
        self.hover = True
        self.update()
    
    def leaveEvent(self, event):
        if not self.hover:
            return
        self.hover = False
        self.update()

@stylable
class QToolButton(_QToolButton):
    pass

@stylable
class QAction(_QAction):
    pass

@stylable
class QLineEdit(_QLineEdit):
    pass

@stylable
class QListWidget(_QListWidget):
    pass

@stylable
class QFrame(_QFrame):
    pass

@stylable
class QToolBar(_QToolBar):
    pass

@stylable
class QSplitter(_QSplitter):
    pass

