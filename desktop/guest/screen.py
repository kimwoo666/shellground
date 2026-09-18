"""Capture only the guest's Xvfb display, never the host desktop."""
import sys
from PIL import ImageGrab

ImageGrab.grab(xdisplay=':0').save(sys.stdout.buffer, format='PNG')
