# Fitopatoloji Arşivi 2.0 RC1

Windows 7 SP1 64 bit hedefli, tamamen yerel çalışan fitopatoloji kayıt ve bilimsel çalışma uygulaması.

Teknoloji: Python 3.8, Tkinter, SQLite ve PyInstaller. Hedef bilgisayarda Python veya SQLite kurulumu gerekmez.

## 2.0 RC1 yenilikleri

- DOSYA, KAYIT, FOTOĞRAF, ANALİZ ve YARDIM sekmeli yeni komut şeridi
- Seçili kayıt için kayıt bütünlüğü ve eksik bilgi önerileri
- Yeni açılış ekranı ve Hakkında penceresi
- Mevcut fotoğraf, rapor, monografi, çalışma alanı, bilgi ağı ve bakım araçlarıyla bütünleşik kullanım

## GitHub Actions ile derleme

GitHub deposunda **Actions** sekmesine girin, **Fitopatoloji Arsivi 2.0 RC1 derle** iş akışını seçin ve **Run workflow** düğmesine basın. Başarılı çalışmanın artifact bölümünden `FitopatolojiArsivi-2.0-RC1-Windows` paketini indirin.

İş akışı önce bütün Python modüllerini derleme kontrolünden geçirir, ardından veritabanı CRUD, gelişmiş arama, teşhis ve SQLite yedekleme self-testlerini çalıştırır.

> Bu sürüm Release Candidate niteliğindedir. Gerçek arşivle kullanmadan önce mevcut `Data`, `Images`, `Documents` ve `Backups` klasörlerinizi yedekleyin.
