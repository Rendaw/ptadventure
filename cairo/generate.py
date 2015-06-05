import math

import cairo
from gi.repository import Pango, PangoCairo

def draw_rect(context, linewidth, color, left, right, top, bottom):
    ctx = context.cairo
    x = context.x
    off_x = context.off_x
    y = context.y
    off_y = context.off_y
    if linewidth is not None:
        ctx.set_line_width(linewidth)
    ctx.set_source_rgb(*color)
    ctx.move_to(off_x + left * x, off_y + top * y)
    ctx.line_to(off_x + left * x, off_y + bottom * y)
    ctx.line_to(off_x + right * x, off_y + bottom * y)
    ctx.line_to(off_x + right * x, off_y + top * y)
    ctx.close_path()
    if linewidth is not None:
        ctx.stroke()
    else:
        ctx.fill()

def draw_line(context, linewidth, color, x1, y1, x2, y2):
    ctx = context.cairo
    x = context.x
    off_x = context.off_x
    y = context.y
    off_y = context.off_y
    ctx.set_line_width(linewidth)
    ctx.set_source_rgb(*color)
    ctx.move_to(off_x + x1 * x, off_y + y1 * y)
    ctx.line_to(off_x + x2 * x, off_y + y2 * y)
    ctx.stroke()

def transform(context, x, y, angle):
    c = context.cairo
    c.identity_matrix()
    c.translate(context.off_x + x * context.x, context.off_y + y * context.y)
    c.rotate(math.radians(angle))

def untransform(context):
    c = context.cairo
    c.identity_matrix()

def draw_text(context, fsize, color, x1, y1, text):
    c = context.cairo
    layout = PangoCairo.create_layout(c)
    font = Pango.FontDescription('sans {}'.format(fsize))
    layout.set_font_description(font)
    layout.set_text(text, -1)
    c.set_source_rgb(*color)
    transform(context, x1, y1, 0)
    PangoCairo.update_layout(c, layout)
    PangoCairo.show_layout(c, layout)
    untransform(context)

def create(fname, x, y):
    class Context:
        x = None
        y = None
        off_x = None
        off_y = None
        surf = None
        cairo = None

        _fname = None
        def done(self):
            self.surf.write_to_png(self._fname + '.png')
            self.surf.finish()
    context = Context()
    context._fname = fname
    context.x = x
    context.off_x = 2
    context.y = y
    context.off_y = 2
    context.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, x + 4, y + 4)
    #context.surf = cairo.SVGSurface(fname + '.svg', x, y)
    #context.surf = cairo.SVGSurface(fname, x, y)
    context.cairo = cairo.Context(context.surf)
    return context

# prep
thick1 = 1
thickb1 = 1
thick2 = 1
fsize1 = 12

purp1 = (0.5, 0.1, 0.7)
purp2 = (0.6, 0.3, 0.75)
yello1 = (0.2, 1, 0)
black1 = (0, 0, 0)
black2 = (0.1, 0.1, 0.1)
green1 = (0.2, 0.6, 0.35)
red1 = (0.5, 0.2, 0.1)

# logo
def logo():
    portion = 2/5
    logo = create('logo', 45, 50)
    xp = portion
    yp = logo.x / logo.y * xp
    size = logo.x * portion
    draw_rect(logo, None, purp1, xp, 1, 0, 1 - yp)
    draw_rect(logo, None, purp1, 0, 1 - xp, yp, 1)
    draw_rect(logo, None, yello1, xp, 1 - xp, yp, 1 - yp)
    draw_rect(logo, thick1, purp2, xp, 1, 0, 1 - yp)
    draw_rect(logo, thick1, purp2, 0, 1 - xp, yp, 1)
    draw_rect(logo, thickb1, black1, 0, 1, 0, 1)
    logo.done()
logo()

def icon_inc(icon):
    draw_line(icon, thick2, green1, 2/7, 1/2, 5/7, 1/2)
    draw_line(icon, thick2, green1, 1/2, 2/7, 1/2, 5/7)

def icon_exc(icon):
    transform(icon, 1/2, 1/2, 45)
    draw_line(icon, thick2, red1, -1.5/7, 0, 1.5/7, 0)
    draw_line(icon, thick2, red1, 0, -1.5/7, 0, 1.5/7)
    untransform(icon)

def icon_sort_asc(icon):
    draw_text(icon, fsize1, black2, 3/4, 1/4, 'a')
    draw_text(icon, fsize1, black2, 3/4, 3/4, 'z')

def icon_sort_desc(icon):
    draw_text(icon, fsize1, black2, 3/4, 1/4, 'z')
    draw_text(icon, fsize1, black2, 3/4, 3/4, 'a')

def icon_sort_rand(icon):
    draw_text(icon, fsize1, black2, 3/4, 1/4, '?')
    draw_text(icon, fsize1, black2, 3/4, 3/4, '?')

def icon_col(icon):
    draw_line(icon, thick2, black2, 2/5, 0, 2/5, 1)
    draw_line(icon, thick2, black2, 3/5, 0, 3/5, 1)

for method in [
        icon_inc, icon_exc, 
        icon_sort_asc, icon_sort_desc, icon_sort_rand, 
        icon_col,
        ]:
    icon = create(method.__name__, 24, 24)
    method(icon)
    draw_rect(icon, thickb1, black1, 0, 1, 0, 1)
    icon.done()
