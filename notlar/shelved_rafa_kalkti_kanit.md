# Shelved / Rafa Kalktı — kanıt sınırı

## Arşivde bulunan

Tweet `2065351367544181110`, 2.200 setup içindeki “Diğer Sonuçlar” bölümünde
`34 Kayıt → Rafa Kalktı` bilgisini verir. Arşiv taramasında bu statüyü üreten
sayısal, teknik veya zamansal koşul açıklanmamıştır.

## BigE davranışı

- Shelved kalıcı ve TP/STOP dışı bir Result Journal sonucudur.
- Yalnız entry gerçekleşmemiş `Aday/Bekliyor` setup açık bir çağrıyla rafa
  kaldırılabilir.
- İşlem açıldıktan sonra Shelved geriye dönük uygulanmaz.
- Kararın nedeni `durum_nedeni` alanında, lifecycle olayı da zaman çizelgesinde
  saklanır.
- Otomatik Shelved sınıflandırması kapalıdır; arşivde olmayan eşik üretilmez.
