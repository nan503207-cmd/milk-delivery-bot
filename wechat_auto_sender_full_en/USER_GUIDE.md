# USER GUIDE — WeChat Auto Sender

... (内容同上，省略这里的预览以节省篇幅) ...

## Setting the input box position

The script clicks the chat input box before pasting messages.  Different screen
resolutions mean the coordinates vary from machine to machine.  You can measure
the coordinates in a Python shell:

```python
>>> import pyautogui as gui
>>> gui.position()  # move your mouse to the input box first
```

Take the returned `(x, y)` and set it in `config.py`:

```python
INPUT_BOX_POS = (x, y)
```

After saving, the sender will use your customised position instead of the
built‑in default.
