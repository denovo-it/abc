# Copyright Axelera AI, 2025
from __future__ import annotations

import collections
import contextlib
import ctypes
from dataclasses import dataclass
import functools
import math
import operator
import os
import queue
import sys
import time
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence, Tuple
import uuid
import weakref

import numpy as np
import pyglet

from axelera import types

from . import config, display, logging_utils, meta
from .utils import catchtime, get_backend_opengl_version

if TYPE_CHECKING:
    from . import inf_tracers

_GL_API, _GL_MAJOR, _GL_MINOR = get_backend_opengl_version(config.env.opengl_backend)
# If using gles, shadow_window must be disabled before any pyglet imports other than
# `import pyglet`. Otherwise, importing pyglet.gl (either by us or by pyglet) will
# cause an error. Hence, all pyglet.* imports should be below here.
if _GL_API == "gles":
    pyglet.options.shadow_window = False


LOG = logging_utils.getLogger(__name__)
KEYPOINT_6 = np.array([[0, 0, 1], [0, 1, 1], [1, 1, 1]], np.float64)
KEYPOINT_4 = np.array([[0, 1], [1, 1]], np.float64)
KEYPOINT_2 = np.full((4, 4), 1, np.float64)

# some env based configs for tweaking performance
_LOW_LATENCY_STREAMS = config.env.render_low_latency_streams
_RENDER_FONT_SCALE = config.env.render_font_scale
_RENDER_LINE_WIDTH = config.env.render_line_width
_RENDER_FPS = config.env.render_fps
_SHOW_BUFFER_STATUS = config.env.render_show_buffer_status
_SHOW_RENDER_FPS = config.env.render_show_fps
_STREAM_QUEUE_SIZE = config.env.render_queue_size

# Soft as won't fail, but may have visual glitches if exceeded
SOFT_MAX_STREAMS = 100

# Offsets for OpenGL groups used for rendering - higher groups
# are rendered on top of lower groups.
GR_BACK_OFFSET = 0  # Bottom
GR_FORE_OFFSET = GR_BACK_OFFSET + SOFT_MAX_STREAMS
GR_SPEEDO_OFFSET = GR_FORE_OFFSET + SOFT_MAX_STREAMS
GR_LAYER_OFFSET = GR_SPEEDO_OFFSET + SOFT_MAX_STREAMS
GR_PROG_OFFSET = GR_LAYER_OFFSET + SOFT_MAX_STREAMS  # Top


class Box(pyglet.shapes.MultiLine):
    def __init__(self, x, y, width, height, **kwargs):
        x1, y1 = x + width, y + height
        pts = [(x, y), (x1, y), (x1, y1), (x, y1)]
        super().__init__(*pts, closed=True, **kwargs)


@contextlib.contextmanager
def _render_to_texture(width, height):
    fb = pyglet.image.Framebuffer()
    t = pyglet.image.Texture.create(width, height)
    fb.attach_texture(t)
    fb.bind()
    try:
        yield t
    finally:
        fb.unbind()


class _SpriteProxy:
    def __init__(self, sprite: pyglet.sprite.Sprite):
        super().__setattr__("sprite", sprite)

    def __getattr__(self, x):
        return getattr(self.sprite, x)

    def __setattr__(self, x, v):
        setattr(self.sprite, x, v)


_label_argnames = (
    "text",
    "font_name",
    "font_size",
    "weight",
    "italic",
    "stretch",
    "color",
    "align",
    "multiline",
    "dpi",
    "back_color",
)


grayscale_fragment_source: str = """#version 150 core
    in vec4 vertex_colors;
    in vec3 texture_coords;
    out vec4 final_colors;
    uniform sampler2D sprite_texture;
    void main()
    {{
        vec4 color = texture(sprite_texture, texture_coords.xy) * vertex_colors;
        float grey = dot(color.rgb, vec3(0.299, 0.587, 0.114));
        vec4 grey_color = vec4(grey, grey, grey, color.a);
        final_colors = mix(color, grey_color, {grayness}); // 1.0 totally grayscale, 0.0 original color
    }}
"""


@functools.lru_cache(maxsize=10)
def _get_grayscale_shader(grayness: float, area: str) -> pyglet.program.ShaderProgram:
    """Create and return a grayscale sprite shader."""
    if grayness == 0.0:
        return None
    expr = {
        'all': grayness,
        'left': f'texture_coords.x < 0.5 ? {grayness} : 0.0',
        'right': f'texture_coords.x > 0.5 ? {grayness} : 0.0',
        'top': f'texture_coords.y < 0.5 ? {grayness} : 0.0',
        'bottom': f'texture_coords.y > 0.5 ? {grayness} : 0.0',
    }[area]

    return pyglet.gl.current_context.create_program(
        (pyglet.sprite.vertex_source, 'vertex'),
        (grayscale_fragment_source.format(grayness=expr), 'fragment'),
    )


class SpritePool:
    def __init__(self):
        self._pool = []

    def create_sprite(self, image, x, y, z, rotation=None, batch=None, group=None, opacity=255):
        try:
            # TODO possible opt is to select sprites based on t.owner
            s = self._pool.pop()
            s.image = image
            s.batch = batch
            s.group = group
            s.visible = True
            s.opacity = opacity
            s.update(x=x, y=y, z=z, rotation=rotation)
        except IndexError:
            s = pyglet.sprite.Sprite(image, x, y, z, batch=batch, group=group)
            s.opacity = opacity
            if rotation is not None:
                s.rotation = rotation
        proxy = _SpriteProxy(s)
        weakref.finalize(proxy, self._remove, s)
        return proxy

    def _remove(self, s):
        self._pool.append(s)
        s.visible = False


_ANCHOR_ADJUST_X = dict(left=0, center=0.5, right=1.0)
_ANCHOR_ADJUST_Y = dict(top=1.0, center=0.5, baseline=0.2, bottom=0.0)


class LabelPool:
    def __init__(self, pixel_ratio):
        self._texture_bin = pyglet.image.atlas.TextureBin()
        self._textures = {}
        self._sprites = SpritePool()
        # 1.0 for normal DPI, 2.0 for retina/HiDPI.  On HiDPI we need to create
        # a sprite twice as big and scale it to normal size because the rendering
        # of text (and other line primitives) is effectively done at 2x resolution.
        self._pixel_ratio = pixel_ratio

    def create_label(
        self,
        text="",
        font_name=None,
        font_size=None,
        weight='normal',
        italic=False,
        stretch=False,
        color=(255, 255, 255, 255),
        x=0,
        y=0,
        z=0,
        width=None,
        height=None,
        anchor_x="left",
        anchor_y="baseline",
        align="left",
        multiline=False,
        dpi=None,
        rotation=0,
        batch=None,
        group=None,
        back_color=None,
        opacity=255,
    ):
        all_args = locals()
        args = tuple(all_args[k] for k in _label_argnames)
        try:
            t = self._textures[args]
        except KeyError:
            t = self._textures[args] = self._new_texture(args)
        x -= _ANCHOR_ADJUST_X[anchor_x] * t.width
        y -= _ANCHOR_ADJUST_Y[anchor_y] * t.height
        s = self._sprites.create_sprite(t, x, y, z, rotation, batch, group, opacity)
        # for HiDPI scale the texture on rendering
        s.scale = _RENDER_FONT_SCALE / self._pixel_ratio
        return s

    def _new_texture(self, args):
        kwargs = dict(zip(_label_argnames, args))
        back_color = kwargs.pop("back_color")
        BORDER = 1
        label = pyglet.text.Label(x=BORDER, y=BORDER, **kwargs, anchor_y="bottom")
        width, height = label.content_width, label.content_height
        # for HiDPI create a texture x2 size
        width = math.ceil((width + BORDER * 2) * self._pixel_ratio)
        height = math.ceil((height + BORDER * 2) * self._pixel_ratio)
        with _render_to_texture(width, height) as texture:
            if back_color is not None:
                pyglet.shapes.Rectangle(0, 0, width, height, back_color).draw()
            label.draw()
        t = self._texture_bin.add(texture.get_image_data())
        return t


@functools.lru_cache(maxsize=1)
def _load_fonts():
    # Barlow Regular:
    pyglet.font.add_file(os.path.join(os.path.dirname(__file__), "axelera-sans.ttf"))


@functools.lru_cache(maxsize=10000)
def _textsize(text, name, pts):
    label = pyglet.text.Label(text, font_name=name, font_size=pts)
    return label.content_width, label.content_height


def _determine_font_params(font: display.Font()) -> Tuple[str, float]:
    '''Convert font.name/size (in pixels high) to font_name/font_size (in points)'''
    _load_fonts()
    name = "Barlow Regular" if font.family == display.FontFamily.sans_serif else "Times"
    pts = font.size * 96 / 72
    _, height = _textsize('Iy', name, pts)
    while abs(font.size - height) > 0.5:
        pts += (font.size - height) / 4
        _, height = _textsize('Iy', name, pts)
    return (name, pts)


def _add_alpha(c):
    if c is not None:
        r, g, b, *a = c
        c = r, g, b, a[0] if a else 255
    return c


@dataclass
class GLCanvas(display.Canvas):
    '''
    GLCanvas uses the information from display.Canvas to scale and position
    image coordinates correctly in the OpenGL GL coordinate system. GL Y direction
    is inverted (0 is the bottom of the screen).

    A bounding box of (100, 100, 200, 200) in the image space will be drawn as a rectangle in the
    GL space at
    (0 + 100*0.5859, 475 - 100*0.5859, 200*0.5859, 200*0.5859) = (59, 416, 117, 117)
    Given a scale factor of 0.5859, and rounding to integer pixel values.
    '''

    def glp(self, p: Tuple[int, int]) -> Tuple[int, int]:
        '''Convert a logical point to a gl point.'''
        return (
            round(self.left + p[0] * self.scale),
            round(self.window_height - self.bottom - p[1] * self.scale),
        )


class ProgressDraw:
    def __init__(self, stream_id, num_streams, window_size):
        self._source_id = stream_id
        self._canvas = _create_canvas(self._source_id, num_streams, window_size, window_size)
        self._p = ProgressBar(
            *self._canvas.glp((window_size[0] / 2, window_size[1] - 14)),
            100,
            10,
            (255, 255, 255, 255),
            (0, 0, 0, 255),
        )

    def resize(self, num_streams: int, window_size: Tuple[int, int]):
        self._canvas = _create_canvas(self._source_id, num_streams, window_size, window_size)
        self._p.move(*self._canvas.glp((window_size[0] / 2, window_size[1] - 14)))

    def set_position(self, value):
        self._p.set_position(value)

    def draw(self):
        self._p.draw()


def _new_sprite_from_image(
    image: types.Image,
    canvas: GLCanvas,
    batch=None,
    group=None,
    grayscale=False,
    grayscale_area='all',
):
    w, h = image.size
    fmt = image.color_format.name
    with image.as_c_void_p() as ptr:
        glimg = pyglet.image.ImageData(w, h, fmt, ptr, pitch=image.pitch)
        pt = canvas.glp((0, 0))
        pr = _get_grayscale_shader(grayscale, grayscale_area)
        sprite = pyglet.sprite.Sprite(glimg, *pt, batch=batch, group=group, program=pr)
        sprite.scale_x = canvas.scale
        sprite.scale_y = -canvas.scale
        return sprite


def _move_sprite(sprite: pyglet.sprite.Sprite, canvas: GLCanvas):
    sprite.scale_x = canvas.scale
    sprite.scale_y = -canvas.scale
    sprite.x, sprite.y = canvas.glp((0, 0))


@functools.lru_cache(maxsize=128)
def _load_image_from_file(filename: str):
    return pyglet.image.load(filename)


def _load_sprite_from_file(
    filename: str, scale, canvas_size, batch, group
) -> pyglet.sprite.Sprite:
    i = _load_image_from_file(filename)
    s = pyglet.sprite.Sprite(i, 0, 0, batch=batch, group=group)
    s.scale = display.canvas_scale_to_img_scale(scale, (s.width, s.height), canvas_size)
    return s


def _create_canvas(
    source_id: int, num_sources: int, image_size: Tuple[int, int], window_size: Tuple[int, int]
):
    (x, y, w, h) = display.pane_position(source_id, num_sources, image_size, window_size)
    return GLCanvas(x, y, w, h, w / image_size[0], *window_size)


class MasterDraw:
    def __init__(self, window: pyglet.window.Window, label_pool: LabelPool):
        self._label_pool = label_pool
        self._batch = pyglet.graphics.Batch()
        self._keypoint_cache = functools.cache(_keypoint_image)
        self._window = window
        self._draws = {}
        self._progresses = {}
        self._meta_cache = display.MetaCache()
        self._speedometer_smoothing = display.SpeedometerSmoothing()
        self._options: dict[int, GLOptions] = collections.defaultdict(GLOptions)
        self._layers: dict[uuid.UUID, display._Layer] = collections.defaultdict()

    def _num_sources(self, new_source_id: int) -> int:
        return (
            max(
                max(self._draws.keys(), default=0),
                max(self._progresses.keys(), default=0),
                new_source_id,
            )
            + 1
        )

    def has_anything_to_draw(self):
        return bool(self._draws) or bool(self._progresses)

    def draw(self):
        for d in self._draws.values():
            d.draw()
        for p in self._progresses.values():
            p.draw()

    def pop_source(self, source_id: int):
        self._draws.pop(source_id, None)
        self._progresses.pop(source_id, None)

    def new_frame(
        self, stream_id: int, image: types.Image, axmeta: Optional[meta.AxMeta], buf_state: float
    ):
        cached, meta_map = self._meta_cache.get(stream_id, axmeta)
        cached  # TODO we should optimise by updating the image and leaving the rest of the draw
        layers = display.get_layers(self._layers, stream_id)
        speedometer_smoothing = (
            self._speedometer_smoothing if self._options[-1].speedometer_smoothing else None
        )

        self._draws[stream_id] = GLDraw(
            stream_id,
            self._num_sources(stream_id),
            self._window.size,
            self._label_pool,
            self._batch,
            self._keypoint_cache,
            image,
            meta_map,
            self._options[stream_id],
            self._options[-1],  # window options is stream_id -1
            layers,
            speedometer_smoothing=speedometer_smoothing,
        )
        if _SHOW_BUFFER_STATUS:
            self.set_buffering(stream_id, buf_state)
        else:
            self._progresses.pop(stream_id, None)

    def options(self, stream_id: int, options: dict[str, Any]) -> None:
        self._options[stream_id].update(**options)

    def layer(self, msg: display._Text):
        self._layers[msg.id] = msg

    def set_buffering(self, stream_id: int, buf_state: float):
        try:
            p = self._progresses[stream_id]
            p.resize(self._num_sources(stream_id), self._window.size)
        except KeyError:
            p = self._progresses[stream_id] = ProgressDraw(
                stream_id, self._num_sources(stream_id), self._window.size
            )
        p.set_position(buf_state)

    def on_resize(self, width: int, height: int):
        num_sources = self._num_sources(0)
        window_size = (width, height)
        for draw in self._draws.values():
            draw.resize(num_sources, window_size)
        for p in self._progresses.values():
            p.resize(num_sources, window_size)

    def new_label_pool(self, label_pool: LabelPool):
        self._label_pool = label_pool
        for draw in self._draws.values():
            draw.new_label_pool(label_pool)


class GLDraw(display.Draw):
    def __init__(
        self,
        stream_id: int,
        num_streams: int,
        window_size: tuple[int, int],
        label_pool: LabelPool,
        batch: pyglet.graphics.Batch,
        keypoint_cache,
        image: types.Image,
        meta_map: Mapping[str, meta.AxTaskMeta],
        options: GLOptions,
        window_options: GLOptions,
        layers: list[display._Layer],
        speedometer_smoothing: display.SpeedometerSmoothing = None,
    ):
        self._source_id = stream_id
        self._window_size = window_size
        self._label_pool = label_pool
        self._batch = batch
        self._keypoint_cache = keypoint_cache
        self._shapes = []
        self._canvas = _create_canvas(self._source_id, num_streams, image.size, window_size)
        self._back = pyglet.graphics.Group(GR_BACK_OFFSET + self._source_id)
        self._fore = pyglet.graphics.Group(GR_FORE_OFFSET + self._source_id)
        self._speedo0 = pyglet.graphics.Group(GR_SPEEDO_OFFSET + 0)
        self._speedo1 = pyglet.graphics.Group(GR_SPEEDO_OFFSET + 1)
        self._layer_gr = pyglet.graphics.Group(GR_LAYER_OFFSET + self._source_id)
        self._sprite = _new_sprite_from_image(
            image, self._canvas, self._batch, self._back, options.grayscale, options.grayscale_area
        )
        self._speedometer_index = 0
        self._meta_map = meta_map
        self._speedometer_smoothing = speedometer_smoothing
        self._options = options
        self._image_size = image.size
        self._render_meta()

        if options.title:
            layers.append(display.gen_title_message(self._source_id, options))
        if window_options.title and self._source_id == 0:
            layers.append(display.gen_title_message(-1, window_options))

        for x in layers:
            if x.stream_id == -1:
                pt_transform = lambda pt: (pt[0], window_size[1] - pt[1])
                canvas_size = window_size
            else:
                pt_transform = self._canvas.glp
                canvas_size = image.size
            opacity = int(255 * x.visibility)  # TODO: 255 should be x.opacity once added
            if isinstance(x, display._Text):
                self._text(
                    pt_transform(x.position.as_px(canvas_size)),
                    x.text,
                    self._layer_gr,
                    x.color,
                    x.bgcolor,
                    display.Font(size=x.font_size),
                    x.anchor_x,
                    x.anchor_y,
                    opacity,
                )
            elif isinstance(x, display._Image):
                s = _load_sprite_from_file(
                    x.path, x.scale, canvas_size, self._batch, self._layer_gr
                )
                s.x, s.y = pt_transform(x.position.as_px(canvas_size))
                s.opacity = opacity
                if x.anchor_x == 'center':
                    s.x -= s.width / 2
                elif x.anchor_x == 'right':
                    s.x -= s.width
                if x.anchor_y == 'center':
                    s.y -= s.height / 2
                elif x.anchor_y == 'top':
                    s.y -= s.height
                self._shapes.append(s)
            else:
                LOG.debug(f"Unknown layer type {x.__class__.__name__} ignoring...")

    @property
    def options(self) -> GLOptions:
        return self._options

    def _render_meta(self):
        self._shapes.clear()
        if self._meta_map:
            for m in self._meta_map.values():
                m.visit(lambda m: m.draw(self))

    def resize(self, num_streams: int, window_size: Tuple[int, int]):
        self._window_size = window_size
        tex = self._sprite.image
        self._canvas = _create_canvas(
            self._source_id, num_streams, (tex.width, tex.height), window_size
        )
        _move_sprite(self._sprite, self._canvas)
        self._render_meta()

    def new_label_pool(self, label_pool: LabelPool):
        self._label_pool = label_pool
        self._render_meta()

    @property
    def canvas_size(self) -> display.Point:
        return self._canvas.size

    @property
    def image_size(self) -> display.Point:
        '''Return the original, unscaled size of the input image'''
        return self._image_size

    def polylines(
        self,
        lines: Sequence[Sequence[display.Point]],
        closed: bool = False,
        color: display.Color = (255, 255, 255, 255),
        width: int = 0,
    ) -> None:
        # though width is given here, it is ignored because glLineWidth is not portable, and
        # since the lines are drawn with Screen width of 1 this is usually sufficient.
        # the reason that width is provided is that in CV drawing the line is given in image pixels
        del width
        converted = [[self._canvas.glp(p) for p in pts] for pts in lines]
        for pts in converted:
            self._shapes.append(
                pyglet.shapes.MultiLine(
                    *pts, closed=closed, color=color, batch=self._batch, group=self._fore
                )
            )

    def rectangle(self, p1, p2, fill=None, outline=None, width=1):
        x0, y0 = self._canvas.glp(p1)
        x1, y1 = self._canvas.glp(p2)
        w, h = x1 - x0, y1 - y0
        if fill and outline:
            kwargs = dict(border=width, color=fill, border_color=outline)
            cls = pyglet.shapes.BorderedRectangle
        elif fill:
            kwargs = dict(color=fill)
            cls = pyglet.shapes.Rectangle
        elif outline:
            kwargs = dict(color=outline)
            cls = Box
        self._shapes.append(cls(x0, y0, w, h, **kwargs, batch=self._batch, group=self._fore))

    def keypoint(
        self, p: display.Point, color: display.Color = (255, 255, 255, 255), size=2
    ) -> None:
        size = round(size * self._canvas.scale)
        image = self._keypoint_cache(size, *color)
        x, y = self._canvas.glp(p)
        o = image.width // 2
        spr = pyglet.sprite.Sprite(image, x - o, y - o, batch=self._batch, group=self._fore)
        self._shapes.append(spr)

    def textsize(self, text, font=display.Font()):
        w, h = _textsize(text, *_determine_font_params(font))
        return w / self._canvas.scale, h / self._canvas.scale

    def text(
        self,
        p,
        text,
        txt_color,
        back_color: display.OptionalColor = None,
        font=display.Font(),
    ):
        self._text(self._canvas.glp(p), text, self._fore, txt_color, back_color, font)

    def _text(
        self,
        p,
        text,
        group,
        txt_color,
        back_color: display.OptionalColor = None,
        font=display.Font(),
        anchor_x='left',
        anchor_y='top',
        opacity=255,
    ):
        txt_color = _add_alpha(txt_color)
        back_color = _add_alpha(back_color)
        name, size = _determine_font_params(font)
        self._shapes.append(
            self._label_pool.create_label(
                text,
                name,
                size,
                weight=font.weight,
                italic=font.italic,
                color=txt_color,
                back_color=back_color,
                x=p[0],
                y=p[1],
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                batch=self._batch,
                group=group,
                opacity=opacity,
            )
        )

    def draw_speedometer(self, metric: inf_tracers.TraceMetric):
        if self._speedometer_smoothing:
            self._speedometer_smoothing.update(metric)
        text = display.calculate_speedometer_text(metric, self._speedometer_smoothing)
        needle_pos = display.calculate_speedometer_needle_pos(metric, self._speedometer_smoothing)
        m = display.SpeedometerMetrics(self._window_size, self._speedometer_index)

        image = _get_speedometer()
        top_left = (m.top_left[0], self._window_size[1] - m.bottom_left[1])
        sprite = pyglet.sprite.Sprite(image, *top_left, batch=self._batch, group=self._speedo0)
        sprite.anchor_y = -image.height
        sprite.scale = m.diameter / image.width
        self._shapes.append(sprite)

        C = (m.center[0], self._window_size[1] - m.center[1])
        x1 = round(C[0] + math.cos(_to_radians(needle_pos)) * m.needle_radius)
        y1 = round(C[1] - math.sin(_to_radians(needle_pos)) * m.needle_radius)
        self._shapes.append(
            pyglet.shapes.Line(
                *C,
                x1,
                y1,
                thickness=3,
                color=m.needle_color,
                batch=self._batch,
                group=self._speedo1,
            )
        )
        self._shapes.append(
            pyglet.text.Label(
                text,
                x=C[0],
                y=C[1] - m.text_offset,
                anchor_x='center',
                anchor_y='center',
                color=m.text_color,
                batch=self._batch,
                group=self._speedo1,
                font_size=m.text_size * 0.7,
            )
        )
        self._shapes.append(
            pyglet.text.Label(
                metric.title,
                x=C[0],
                y=C[1] - m.text_offset * 1.75,
                anchor_x='center',
                anchor_y='center',
                color=m.text_color,
                batch=self._batch,
                group=self._speedo1,
                font_size=m.text_size * 0.5,
            )
        )
        self._speedometer_index += 1

    def draw(self):
        self._batch.draw()

    def heatmap(self, data: np.ndarray, color_map: np.ndarray) -> None:
        indices = np.clip((data * len(color_map) - 1).astype(int), 0, len(color_map) - 1)
        rgba_mask = color_map[indices]
        image = pyglet.image.ImageData(data.shape[1], data.shape[0], 'RGBA', rgba_mask.tobytes())
        sprite = pyglet.sprite.Sprite(
            image, *self._canvas.glp((0, 0)), batch=self._batch, group=self._fore
        )
        sprite.anchor_y = -image.height
        sprite.scale_x = self._canvas.scale
        sprite.scale_y = -self._canvas.scale
        self._shapes.append(sprite)

    def segmentation_mask(self, mask_data, color: Tuple[int]) -> None:
        mask, mbox = mask_data[-1], mask_data[4:8]
        mid_point = np.iinfo(np.uint8).max // 2
        bool_array = mask > mid_point

        colored_mask = np.zeros((*bool_array.shape, 4), dtype=np.uint8)
        colored_mask[bool_array] = color
        buf = colored_mask.ctypes.data_as(ctypes.c_void_p)

        img_size = (mbox[2] - mbox[0], mbox[3] - mbox[1])
        image = pyglet.image.ImageData(mask.shape[1], mask.shape[0], 'RGBA', buf)
        scale_x = img_size[0] / mask.shape[1] * self._canvas.scale
        scale_y = img_size[1] / mask.shape[0] * self._canvas.scale
        sprite = pyglet.sprite.Sprite(
            image, *self._canvas.glp(mbox[:2]), batch=self._batch, group=self._fore
        )

        sprite.anchor_y = -image.height
        sprite.scale_x = scale_x
        sprite.scale_y = -scale_y
        self._shapes.append(sprite)

    def class_map_mask(self, class_map: np.ndarray, color_map: np.ndarray) -> None:
        colored_mask = color_map[class_map]
        image = pyglet.image.ImageData(
            class_map.shape[1], class_map.shape[0], 'RGBA', colored_mask.tobytes()
        )
        sprite = pyglet.sprite.Sprite(
            image, *self._canvas.glp((0, 0)), batch=self._batch, group=self._fore
        )
        sprite.anchor_y = -image.height
        sprite.scale_x = self._canvas.width / image.width
        sprite.scale_y = -(self._canvas.height / image.height)
        self._shapes.append(sprite)

    def draw_image(self, image: np.ndarray) -> None:
        # TODO: Implement the draw_image method. Refer to SDK-5801 ticket for details.
        pass


def _keypoint_image(size, r, g, b, alpha=255):
    if size >= 6:
        corner = KEYPOINT_6
    elif size >= 4:
        corner = KEYPOINT_4
    else:
        corner = KEYPOINT_2
    left = np.concatenate((corner, np.flipud(corner)))
    mask = np.concatenate((left, np.fliplr(left)), axis=1)
    h, w = mask.shape
    i = np.full((h, w, 4), (r, g, b, 0), np.uint8)
    i[:, :, 3] = (mask * alpha).astype(np.uint8)
    return pyglet.image.ImageData(w, h, "RGBA", i.ctypes.data_as(ctypes.c_void_p))


@functools.lru_cache
def _get_speedometer():
    here = os.path.dirname(__file__)
    return pyglet.image.load(f'{here}/speedo-alpha-transparent.png')


_to_radians = functools.partial(operator.mul, math.pi / 180)


class ProgressBar:
    def __init__(self, x, y, w, h, color, back_color):
        self._width = w
        b = self._border = 2
        assert h > self._border * 2, "Border is too small"
        g0 = pyglet.graphics.Group(GR_PROG_OFFSET + 0)
        g1 = pyglet.graphics.Group(GR_PROG_OFFSET + 1)
        self._outer = pyglet.shapes.BorderedRectangle(
            x, y, w, h, border=1, color=back_color, border_color=color, group=g0
        )
        self._outer.anchor_position = (w // 2, h // 2)
        self._inner = pyglet.shapes.Rectangle(
            x + b, y + b, w - b * 2, h - b * 2, color=color, group=g1
        )
        self._inner.anchor_position = (w // 2 - b, h // 2)
        self.set_position(0.0)

    def move(self, x, y):
        self._outer.position = x, y
        self._inner.position = x + 2, y + 2

    def set_position(self, value):
        value = min(1.0, max(0.0, value))
        self._inner.width = int((self._width - self._border * 3) * value)

    def draw(self):
        self._outer.draw()
        self._inner.draw()


class HighLowQueue(collections.deque):
    def __init__(self, *, maxlen):
        super().__init__(maxlen=maxlen)
        self.low = maxlen // 3
        self.high = max(1, 2 * self.low)
        self.low_water_reached = False


def noexcept(f):
    '''Decorator to catch all exceptions and log them, suitable for event handlers'''

    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            LOG.report_recoverable_exception(e)

    return wrapper


@dataclass
class GLOptions(display.Options):
    grayscale_area: str = 'all'
    '''When grayscale is enabled this specifies the area to grayscale.

    One of 'all' for the entire image, or 'left', 'right', 'top', 'bottom' for
    the respective half of the image. This is useful when tiling only part of
    the screen for example.
    '''


class GLWindow(pyglet.window.Window):
    def __init__(self, q: queue.Queue, title, size, buffering, frame_sink):
        self._master = None
        self._gles = False
        self._frame_sink = frame_sink
        w, h = (None, None) if size == display.FULL_SCREEN else size

        _display = pyglet.display.get_display()
        screen = _display.get_default_screen()
        gl_config = screen.get_best_config()
        gl_config.opengl_api = _GL_API
        gl_config.major_version = _GL_MAJOR
        gl_config.minor_version = _GL_MINOR
        if gl_config.opengl_api == "gles":
            self._gles = True

        super().__init__(
            w,
            h,
            caption=title,
            fullscreen=size == display.FULL_SCREEN,
            resizable=True,
            config=gl_config,
            visible=bool(title),
        )
        w = w or self.width
        h = h or self.height
        icons = [pyglet.image.load(i) for i in display.ICONS.values()]
        icons[-1].anchor_x = icons[-1].width // 2
        icons[-1].anchor_y = icons[-1].height // 2
        self._start_time = time.time()
        self._logo = pyglet.sprite.Sprite(icons[-1], 0, 0)
        self._progress = ProgressBar(
            w // 2, h // 2 - icons[-1].height, 200, 20, (255, 255, 255, 255), (0, 0, 0, 255)
        )
        self.set_icon(*icons)
        self._queue = q
        self._old_pixel_ratio = self.get_pixel_ratio()
        self._pool = LabelPool(self._old_pixel_ratio)
        self._master = MasterDraw(self, self._pool)
        self._stream_queues = {}
        # during initial logo spin have redraws at 30fps. Once we are going drop to 10
        pyglet.clock.schedule_interval(self._redraw, 1 / 30)
        pyglet.clock.schedule_interval(self.on_update, 1 / _RENDER_FPS)
        self._fps_counter = pyglet.window.FPSDisplay(self)
        self.buffering = buffering
        self._closed_sources = set()
        self._pending_blocking_capture = False

    def on_key_press(self, symbol, modifiers):
        del modifiers
        if symbol in (pyglet.window.key.Q, pyglet.window.key.ESCAPE, pyglet.window.key.SPACE):
            pyglet.app.platform_event_loop.post_event(self, "on_close")

    @noexcept
    def on_update(self, dt):
        del dt

        with catchtime('update', LOG.trace):
            try:
                while True:
                    msg = self._queue.get(block=False)
                    if msg is display.SHUTDOWN:
                        self._queue.clear()
                        pyglet.app.platform_event_loop.post_event(self, "on_close")
                        return
                    if msg is display.THREAD_COMPLETED:
                        continue  # ignore, just wait for user to close
                    if isinstance(msg, display._OpenSource):
                        self._closed_sources.discard(msg.stream_id)
                        continue
                    blocking = isinstance(msg, display._BlockingFrame)
                    if (
                        isinstance(msg, display._StreamMessage)
                        and msg.stream_id in self._closed_sources
                    ):
                        if blocking:
                            LOG.error(
                                f"Received blocking frame from closed source {msg.stream_id}"
                            )
                        continue  # ignore messages from closed sources
                    if isinstance(msg, display._CloseSource):
                        if not msg.reopen:
                            self._closed_sources.add(msg.stream_id)
                        self._stream_queues.pop(msg.stream_id, None)
                        self._master.pop_source(msg.stream_id)
                    elif isinstance(msg, display._SetOptions):
                        self._master.options(msg.stream_id, msg.options)
                    elif isinstance(msg, display._Layer):
                        self._master.layer(msg)
                    elif isinstance(msg, display._Frame):
                        pyglet.clock.unschedule(self._redraw)
                        try:
                            q = self._stream_queues[msg.stream_id]
                        except KeyError:
                            maxlen = (
                                2
                                if msg.stream_id in _LOW_LATENCY_STREAMS or not self.buffering
                                else _STREAM_QUEUE_SIZE
                            )
                            q = self._stream_queues[msg.stream_id] = HighLowQueue(maxlen=maxlen)
                        q.append((msg.image, msg.meta, blocking))
                    else:
                        LOG.debug(f"Unexpected render message {msg}")
            except queue.Empty:
                pass

            self.invalid = False
            for source_id, q in self._stream_queues.items():
                self.invalid = True
                if q.low_water_reached or len(q) > q.low:
                    q.low_water_reached = True
                    if len(q) > q.high:
                        # we're falling behind, drop an extra frame
                        image, axmeta, blocking_flag = q.popleft()
                        if blocking_flag:
                            # never drop a blocking frame
                            self._pending_blocking_capture = True
                            self._master.new_frame(source_id, image, axmeta, len(q) / q.maxlen)
                    if len(q):
                        image, axmeta, blocking_flag = q.popleft()
                        if blocking_flag:
                            self._pending_blocking_capture = True
                        self._master.new_frame(source_id, image, axmeta, len(q) / q.maxlen)
                else:
                    # still buffering don't pop anything but do redraw progress
                    self._master.set_buffering(source_id, len(q) / q.maxlen)

            self._redraw()

    def _redraw(self, dt=None):
        self.dispatch_event('on_draw')
        self.flip()

    def on_resize(self, width, height):
        # on a resize we need to redo all the scale calculations
        if self._master:
            self._master.on_resize(width, height)
        return super().on_resize(width, height)

    def on_move(self, x, y):
        new_pixel_ratio = self.get_pixel_ratio()
        if self._old_pixel_ratio != new_pixel_ratio:
            # If HiDPI setting has changed in some way then dump the label xfipool
            self._old_pixel_ratio = new_pixel_ratio
            self._pool = LabelPool(new_pixel_ratio)
            self._master.new_label_pool(self._pool)

    @noexcept
    def on_draw(self):
        self.clear()
        if _RENDER_LINE_WIDTH > 1 and not self._gles:
            pyglet.gl.glLineWidth(_RENDER_LINE_WIDTH)
        if self._master.has_anything_to_draw():
            if not self._gles:
                pyglet.gl.glEnable(pyglet.gl.GL_LINE_SMOOTH)
            with catchtime('draw', LOG.trace):
                self._master.draw()
            self.invalid = False
        else:
            self._show_logo()
        if _SHOW_RENDER_FPS:
            self._fps_counter.draw()
        if self._frame_sink:
            color_buf = pyglet.image.get_buffer_manager().get_color_buffer()
            img_data = color_buf.get_image_data()
            row_stride = self.width * 4
            raw = img_data.get_data('RGBA', row_stride)
            arr = np.frombuffer(raw, dtype=np.uint8).reshape(self.height, self.width, 4)
            arr = np.flipud(arr)
            rgb = arr[:, :, :3]
            try:
                self._frame_sink.push(
                    types.Image.fromarray(rgb), block=self._pending_blocking_capture
                )
            except RuntimeError as e:
                LOG.error(f"Blocking frame sink not updated: {e}")
            finally:
                self._pending_blocking_capture = False

    def _show_logo(self):
        # silly bit of code to make the logo pulsate during startup whilst we warm up pipelines
        self._logo.position = self.width // 2, self.height // 2, 0.0
        elapsed = time.time() - self._start_time
        if elapsed < 1.0:
            self._logo.scale = 1.5 * math.sin(math.pi * elapsed)
        else:
            elapsed -= 1.0
            startup_time = 10.0
            # pulsate the logo whilst we show a progress bar counting to arbitrary 10s
            self._logo.opacity = int(180 + 75 * math.sin(math.pi * elapsed * 1.1))
            if elapsed < startup_time:
                self._progress.set_position(elapsed / startup_time)
                self._progress.draw()
        self._logo.draw()


class GLApp(display.App):
    SupportedOptions = GLOptions

    def __init__(self, *args, **kwargs):
        self.buffering = kwargs.pop('buffering', True)
        super().__init__(*args, **kwargs)

    def _idle(self, dt):
        del dt
        self._create_new_windows()
        if self.has_thread_completed:
            pyglet.app.exit()

    def _create_new_window(self, q, frame_sink, title, size):
        return GLWindow(q, title, size, self.buffering, frame_sink)

    def _run_background(self, interval=1 / 30):
        del interval
        if self._running_in_main:
            return
        raise RuntimeError(
            "Implicit OpenGL rendering in the background is not supported. Either: "
            "1. Start the renderer in your application with `display.App.run()` or "
            "2. Use OpenCV rendering with `display.App(renderer='opencv')`"
        )

    def _run(self, interval=1 / 60):
        pyglet.clock.schedule_interval(self._idle, 0.3)
        pyglet.app.run(interval=None if not sys.platform == 'darwin' else 1 / 10)

    def _destroy_all_windows(self):
        pyglet.app.exit()
