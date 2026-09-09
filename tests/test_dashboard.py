import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest


class DashboardTests(unittest.TestCase):
    def test_all_pages_render(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'), default_timeout=20).run()
        self.assertFalse(app.exception)
        for page in ['Try a message','Case inspector','Label customer messages','Review replies','Judge audit','Evidence stress test']:
            app.sidebar.radio[0].set_value(page).run()
            self.assertFalse(app.exception, page)

    def test_interactive_baseline(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=20).run()
        app.sidebar.radio[0].set_value('Try a message').run()
        app.text_area[0].set_value('My phone battery drains very quickly after an update.')
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.info)
