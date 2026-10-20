

def func(x):
    return x + 1

def test_answer():
    assert func(4) == 5


# 2-qadam: Xavfsizlik (Chekka holatlar)
# Tasavvur qiling, all_stops bo'sh ro'yxat [] bo'lib keldi.
# Agar siz to'g'ridan-to'g'ri stops_list[0] ga murojaat qilsangiz,
# dastur qulaydi (IndexError). Shuning uchun avval ro'yxat bo'sh emasligini tekshirish shart.