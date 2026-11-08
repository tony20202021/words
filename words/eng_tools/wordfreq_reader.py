"""Читает частотный список wordfreq без установки пакета.

Данные wordfreq лежат как msgpack.gz: [заголовок, [слова корзины 0], ...].
Корзины идут от самых частых к редким, внутри корзины — по алфавиту. Нам нужен
не точный ранг, а порядок, поэтому корзины дают его с достаточной точностью.

Свой разборщик вместо pip install msgpack: нужное подмножество формата —
строки, массивы, словари, целые — укладывается в сорок строк, а боевое
окружение остаётся нетронутым.
"""
import gzip
import struct
import sys


def unpack(buf, i=0):
    b = buf[i]; i += 1
    if b < 0x80:
        return b, i
    if b >= 0xe0:
        return b - 0x100, i
    if 0xa0 <= b <= 0xbf:
        n = b & 0x1f
        return buf[i:i + n].decode("utf-8"), i + n
    if 0x90 <= b <= 0x9f:
        return _arr(buf, i, b & 0x0f)
    if 0x80 <= b <= 0x8f:
        return _map(buf, i, b & 0x0f)
    if b == 0xc0:
        return None, i
    if b == 0xc2:
        return False, i
    if b == 0xc3:
        return True, i
    if b in (0xd9, 0xda, 0xdb):
        w = {0xd9: 1, 0xda: 2, 0xdb: 4}[b]
        n = int.from_bytes(buf[i:i + w], "big"); i += w
        return buf[i:i + n].decode("utf-8"), i + n
    if b in (0xdc, 0xdd):
        w = 2 if b == 0xdc else 4
        n = int.from_bytes(buf[i:i + w], "big")
        return _arr(buf, i + w, n)
    if b in (0xde, 0xdf):
        w = 2 if b == 0xde else 4
        n = int.from_bytes(buf[i:i + w], "big")
        return _map(buf, i + w, n)
    if b in (0xcc, 0xcd, 0xce, 0xcf):
        w = 1 << (b - 0xcc)
        return int.from_bytes(buf[i:i + w], "big"), i + w
    if b in (0xd0, 0xd1, 0xd2, 0xd3):
        w = 1 << (b - 0xd0)
        return int.from_bytes(buf[i:i + w], "big", signed=True), i + w
    if b == 0xca:
        return struct.unpack_from(">f", buf, i)[0], i + 4
    if b == 0xcb:
        return struct.unpack_from(">d", buf, i)[0], i + 8
    raise ValueError(f"не разобран байт 0x{b:02x} на позиции {i - 1}")


def _arr(buf, i, n):
    out = []
    for _ in range(n):
        v, i = unpack(buf, i)
        out.append(v)
    return out, i


def _map(buf, i, n):
    out = {}
    for _ in range(n):
        k, i = unpack(buf, i)
        v, i = unpack(buf, i)
        out[k] = v
    return out, i


def buckets(path):
    with gzip.open(path, "rb") as f:
        data = f.read()
    value, _ = unpack(data)
    return value


if __name__ == "__main__":
    v = buckets(sys.argv[1])
    print("заголовок:", v[0])
    print("корзин:", len(v) - 1)
    print("слов всего:", sum(len(b) for b in v[1:]))
    for n, b in enumerate(v[1:6], 1):
        print(f"корзина {n}: {len(b)} слов — {b[:12]}")
