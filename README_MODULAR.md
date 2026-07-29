# Fitopatoloji Arşivi 1.1.0

Bu sürümde uygulama tek dosyalı yapıdan modüler Python paketine ayrıldı.

## Dosyalar

- `app.py`: giriş noktası
- `fitopatoloji/common.py`: ortak ayarlar, bağımlılıklar ve yollar
- `fitopatoloji/database.py`: SQLite ve veri işlemleri
- `fitopatoloji/richtext.py`: zengin metin düzenleyici
- `fitopatoloji/editor.py`: hastalık kayıt düzenleyicisi
- `fitopatoloji/gallery.py`: fotoğraf galerisi
- `fitopatoloji/main_window.py`: ana kullanıcı arayüzü
- `fitopatoloji/selftest.py`: otomatik testler
- `build.yml`: GitHub Actions derleme dosyası

Mevcut `seed` klasörünüzü ve `README.md` dosyanızı koruyun.
GitHub'da `.github/workflows/build.yml` yerine bu klasördeki `build.yml` içeriğini kullanın.
