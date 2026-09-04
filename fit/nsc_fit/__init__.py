"""Fitting the Neural Space Cap to a head.

Turns three tape-measure numbers into electrode positions, a printable
marking template, and dimensions for the printed parts.

The problem this solves: electrode position moving between sessions is
indistinguishable from the subject's physiology changing. A cap that puts the
electrodes somewhere slightly different every time cannot produce comparable
recordings, and the difference will be blamed on the signal chain.
"""

__all__ = ["head", "ten_twenty", "template"]
