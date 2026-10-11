"""browser-own-profile: drive your own logged-in Chrome through browser-harness, safely.

Lower layer: client.Browser (talks to worker.py in a separate process).
Upper layer: guard.Kit (stops on verification pages, asks before risky clicks) and the recipes.
"""
