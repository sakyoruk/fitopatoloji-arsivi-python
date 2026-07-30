# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import os
import datetime as dt
import traceback

from fitopatoloji.common import APP_NAME, APP_VERSION, AppPaths, resource_path, tk, messagebox
from fitopatoloji.database import Database
from fitopatoloji.main_window import MainWindow
from fitopatoloji.selftest import self_test
from fitopatoloji.rc_shell import SplashScreen


def install_exception_handler(root, paths):
    def report(exc_type, exc_value, exc_tb):
        try:
            log_dir = os.path.join(paths.data, "Logs")
            if not os.path.isdir(log_dir):
                os.makedirs(log_dir)
            log_path = os.path.join(log_dir, "error_{}.log".format(dt.datetime.now().strftime("%Y%m%d_%H%M%S")))
            with open(log_path, "w", encoding="utf-8") as handle:
                handle.write("{} {}\n{}\n\n".format(APP_NAME, APP_VERSION, dt.datetime.now()))
                traceback.print_exception(exc_type, exc_value, exc_tb, file=handle)
            messagebox.showerror(APP_NAME, "İşlem sırasında beklenmeyen bir hata oluştu.\n\nVerileriniz korunmuştur. Tanılama kaydı:\n{}".format(log_path), parent=root)
        except Exception:
            traceback.print_exception(exc_type, exc_value, exc_tb)
    root.report_callback_exception = report


def main():
    if "--self-test" in sys.argv:
        return self_test()

    paths = AppPaths()
    seed = resource_path("seed", "diseases.csv")
    try:
        db = Database(paths.database, seed)
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            APP_NAME,
            "Veritabanı açılamadı:\n{}\n\n"
            "Uygulama klasörünün yazılabilir olduğundan emin olun.".format(exc),
        )
        root.destroy()
        return 1

    app = MainWindow(paths, db)
    install_exception_handler(app, paths)
    try:
        app.withdraw()
        splash = SplashScreen(app)
        def finish_startup():
            try:
                splash.progress.stop()
                splash.destroy()
            except Exception:
                pass
            app.deiconify()
            app.lift()
        app.after(1150, finish_startup)
    except Exception:
        app.deiconify()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
