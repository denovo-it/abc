#!/usr/bin/env python
# Copyright Axelera AI, 2025

import os
import threading
import time

try:
    import wx
except ImportError:
    print(
        "[ERROR] The 'wxPython' module is not installed.\n"
        "Please install it using pip.\n"
        "First ensure libgtk-3-dev is installed. Run: sudo apt install libgtk-3-dev\n"
        "Run: pip install wxpython\n"
        "Exiting."
    )
    exit(1)
# Try to import CLIP, install if missing
try:
    import clip
except ImportError:
    print("Installing CLIP...")
    os.system("pip install git+https://github.com/openai/CLIP.git")
    import clip

import numpy as np
import torch

from axelera import types
from axelera.app import config, display, inf_tracers, logging_utils
from axelera.app.meta.segmentation import InstanceSegmentationMeta
from axelera.app.stream import create_inference_stream

W = 1280
H = 720
SURFACE_SIZE = (W, H)

SURFACE_REFRESH_INTERVAL = 1000 // 30  # ~30 FPS

print("Loading CLIP model...")
model, preprocess = clip.load('RN50x4')
print("CLIP model loaded.")


def _update_prompt(model, prompt):
    text_input = clip.tokenize(prompt)
    text_features = model.encode_text(text_input)
    text_features /= text_features.norm(dim=-1, keepdim=True)
    return text_features


DEFAULT_PROMPT = 'fruits and vegetables'
print(f"Initializing with prompt: '{DEFAULT_PROMPT}'")
DEFAULT_FEATURES = _update_prompt(model, DEFAULT_PROMPT)
print("Prompt initialized.")

tracers = inf_tracers.create_tracers('core_temp', 'cpu_usage', 'end_to_end_fps')
stream = create_inference_stream(
    network="fastsams-rn50x4-onnx",
    sources=[config.env.framework / "media/bowl-of-fruit.mp4@auto"],
    pipe_type='gst',
    log_level=logging_utils.INFO,  # INFO, DEBUG, TRACE
    hardware_caps=config.HardwareCaps(
        vaapi=config.HardwareEnable.detect,
        opencl=config.HardwareEnable.detect,
        opengl=config.HardwareEnable.detect,
    ),
    tracers=tracers,
    specified_frame_rate=7,
)


class WxViewer(wx.Frame):
    def __init__(self, app: display.App, size, stop: threading.Event, surface: display.Surface):
        super().__init__(parent=None, title="FastSAM demo", size=size)
        self._app = app
        self._stop = stop
        self._surface = surface
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self._prompt = DEFAULT_PROMPT
        self._topk = 1

        self._bitmap_panel = wx.Panel(self)
        self._bitmap_sizer = wx.BoxSizer(wx.VERTICAL)
        self._bmp_ctrl = wx.StaticBitmap(self._bitmap_panel, -1, size=SURFACE_SIZE)
        self._bitmap_sizer.Add(self._bmp_ctrl, 0, wx.ALIGN_CENTER)
        self._bitmap_panel.SetSizer(self._bitmap_sizer)
        black = wx.Bitmap.FromBuffer(W, H, np.zeros((H, W, 3), dtype=np.uint8))
        self._bmp_ctrl.SetBitmap(black)

        self._sizer.Add(self._bitmap_panel, 1, wx.ALL | wx.EXPAND, 5)

        controls = wx.BoxSizer(wx.HORIZONTAL)

        prompt_label = wx.StaticText(self, label="Text prompt:")
        controls.Add(prompt_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.prompt_entry = wx.TextCtrl(self, value=self._prompt)
        controls.Add(self.prompt_entry, 3, wx.ALL | wx.EXPAND, 5)

        topk_label = wx.StaticText(self, label="Top-K:")
        controls.Add(topk_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.topk_entry = wx.TextCtrl(self, value=str(self._topk))
        controls.Add(self.topk_entry, 1, wx.ALL | wx.EXPAND, 5)

        update_btn = wx.Button(self, label="Update")
        update_btn.Bind(wx.EVT_BUTTON, self.on_update)
        controls.Add(update_btn, 0, wx.ALL, 5)

        self._sizer.Add(controls, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(self._sizer)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_SIZE, self._on_resize)
        wx.CallAfter(self._on_timer, None)

        self.Fit()
        self.Show()

    def _get_bitmap_size(self):
        client_size = self.GetClientSize()
        controls_height = 0
        if self._sizer.GetItemCount() > 1:
            controls_item = self._sizer.GetItem(1)
            if controls_item:
                controls_height = controls_item.GetMinSize().height

        w = max(1, client_size.width)
        h = max(1, client_size.height - controls_height)

        return w, h

    def _on_resize(self, event):
        self._bitmap_panel.Layout()
        event.Skip()

    def _on_timer(self, _):
        start = time.time()
        if self._stop.is_set():
            self._on_close(wx.CloseEvent())
            return

        if new := self._surface.pop_latest():
            np_img = new.asarray(types.ColorFormat.RGB).astype(np.uint8)
            buf = np_img.tobytes()
            bmp = wx.Image(new.width, new.height, buf).ConvertToBitmap()
            self._bmp_ctrl.SetBitmap(bmp)
        delay = max(1, SURFACE_REFRESH_INTERVAL - int((time.time() - start) * 1000))
        wx.CallLater(delay, self._on_timer, None)

    def _on_close(self, evt):
        self._stop.set()
        self.Destroy()

    def on_update(self, event):
        self._prompt = self.prompt_entry.GetValue()
        self._topk = self.topk_entry.GetValue()
        try:
            self._topk = int(self.topk_entry.GetValue())
        except ValueError:
            print("[Warning] Invalid topk value, must be integer.")
        print(f"[Prompt Updated] -> {self._prompt} | topk = {self._topk}")

    @property
    def prompt(self) -> str:
        return self._prompt

    @property
    def topk(self) -> int:
        return self._topk


def _main(stream, stop, surface: display.Surface, window: WxViewer):
    nr_boxes_to_process = 15
    last_prompt = DEFAULT_PROMPT
    text_features = DEFAULT_FEATURES
    update_msg = surface.text(
        "50%, 50%", "Updating...", font_size=24, anchor_x="center", anchor_y="center"
    )
    update_msg.hide()

    surface.options(0, bbox_label_format="{scorep:.0f}{scoreunit}")

    update_at_end = False
    for frame_result in stream:
        if stop.is_set():
            return
        current_prompt = window.prompt

        if current_prompt != last_prompt:
            # show msg here - but update after the frame updates so the message
            # is actually visible during the slow op...
            update_msg.show()
            last_prompt = current_prompt
            update_at_end = True

        meta = frame_result.meta['master_detections']
        nr_boxes = meta.boxes.shape[0]
        nr_boxes = min(nr_boxes, nr_boxes_to_process)

        topk = window.topk

        det_idxs = meta.secondary_frame_indices.get('detections', [])
        no_det_idxs = len(det_idxs)

        topk = min(no_det_idxs, topk)

        if no_det_idxs > 1:
            emb_tensors = []
            for idx in det_idxs:
                emb = meta.get_secondary_meta('detections', idx).embedding
                emb_tensor = torch.tensor(emb)
                emb_tensors.append(emb_tensor.squeeze())

            img_features = torch.stack(emb_tensors)
            img_features /= img_features.norm(dim=-1, keepdim=True)
            similarity = 100.0 * img_features @ text_features.T

            idxs = torch.argsort(similarity.squeeze(), descending=True)
            top_idxs = idxs[0:topk]

            newmasks = [meta.masks[idx] for idx in top_idxs]
            newboxes = [meta.boxes[idx] for idx in top_idxs]
            newids = top_idxs
            newscores = [0] * topk

        elif no_det_idxs == 0:  # No detections
            newmasks = newboxes = newids = newscores = []

        else:  # Single detection, no filtering needed
            newmasks = [meta.masks[0]]
            newboxes = [meta.boxes[0]]
            newids = [0]
            newscores = [0]

        filtered_meta = InstanceSegmentationMeta(seg_shape=meta.seg_shape, labels=meta.labels)
        filtered_meta.add_results(
            newmasks,
            np.array(newboxes) if len(newboxes) else np.array([]).reshape(0, 4),
            np.array(newids),
            np.array(newscores),
        )
        frame_result.meta.delete_instance('master_detections')
        frame_result.meta.add_instance('master_detections', filtered_meta)

        surface.push(frame_result.image, frame_result.meta)
        if update_at_end:
            text_features = _update_prompt(model, current_prompt)
            update_msg.hide()
            update_at_end = False


def main(stream, stop: threading.Event, surface: display.Surface, window: WxViewer):
    try:
        _main(stream, stop, surface, window)
    finally:
        stop.set()


with display.App(renderer='opencv') as app:
    surface = app.create_surface(SURFACE_SIZE)
    stop = threading.Event()
    wx_app = wx.App(False)
    wx_wnd = WxViewer(app, (W, H), stop, surface)
    app.start_thread(main, (stream, stop, surface, wx_wnd), name="InferenceThread")
    wx_app.MainLoop()
stream.stop()
