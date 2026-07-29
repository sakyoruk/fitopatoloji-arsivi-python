# -*- coding: utf-8 -*-
from __future__ import print_function

import sys

from fitopatoloji.common import APP_NAME, AppPaths, resource_path, tk, messagebox
from fitopatoloji.database import Database
from fitopatoloji.main_window import MainWindow
from fitopatoloji.selftest import self_test


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
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
