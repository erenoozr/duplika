# Duplika

Klasördeki birebir aynı dosyaları içerik (SHA-256) ile bulur. Varsayılan olarak **yalnızca rapor verir**;
`--tasi` ile kopyaları silmek yerine bir karantina klasörüne taşır. Hiçbir dosyayı silmez.

## Kullanım

Python 3.8+ yeterli, ek paket gerekmez.

```
python duplika.py C:\Users\ben\Masaüstü
python duplika.py C:\Users\ben\Masaüstü --tasi C:\karantina
python duplika.py D:\Fotoğraflar --min-boyut 100000 --tasi D:\karantina
```

| Seçenek | Açıklama |
|---|---|
| `--tasi KLASOR` | Kopyaları bu klasöre, göreli yollarını koruyarak taşır. Verilmezse yalnızca rapor. |
| `--min-boyut N` | N bayttan küçük dosyaları atlar (varsayılan 1, yani boş dosyalar atlanır). |
| `--hepsi` | `.git`, `.venv`, `node_modules` gibi klasörleri de tarar (varsayılan: atlanır). |
| `--bulut-dahil` | OneDrive'da yalnızca bulutta duran dosyaları da tarar; bu dosyaları indirir. |

## Nasıl karar verir?

- Önce boyuta göre eler, yalnızca aynı boyuttaki dosyaları hashler.
- Her grupta **en eski** dosya saklanır (eşitse en kısa yol).
- Karantina klasörü taranan klasörün içindeyse taramaya katılmaz; tekrar çalıştırmak güvenlidir.
- Karantinada aynı adlı dosya varsa üzerine yazmaz, `ad (2).uzantı` olarak taşır.
- Sanal ortamlar ve sürüm kontrol klasörleri varsayılan olarak atlanır, çünkü içlerindeki "kopyaları" taşımak onları bozar.

## Sınırlar

- Yalnızca birebir aynı dosyaları bulur; benzer fotoğrafları veya farklı kodlanmış aynı şarkıyı bulmaz.
- Sembolik bağlantılar atlanır.

## Geliştirme

```
pip install pytest
python -m pytest tests
```

Lisans: MIT
