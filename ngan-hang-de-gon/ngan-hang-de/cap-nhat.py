#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cập nhật Ngân hàng đề (chỉ dùng thư viện có sẵn của Python 3, không cần cài thêm).

Việc script làm:
  1. Đổi mọi file đề viết bằng văn bản (.txt) thành file .json cùng tên.
  2. Kiểm tra mọi file .json hợp lệ.
  3. Tạo lại index.json, là danh mục mà trang web đọc để biết có những đề nào.

Cách chạy (trong thư mục gốc của dự án):   python ngan-hang-de/cap-nhat.py
"""
import json, os, re, sys, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
LOAI = {"kt15": "15 phút", "kt45": "45 phút", "thi": "90 phút"}
HEAD = {"tiêu đề": "tieu_de", "loại": "loai", "học kì": "hoc_ki", "học kỳ": "hoc_ki", "dạng": "dang",
        "thời gian": "thoi_gian", "điểm mỗi câu trắc nghiệm": "diem_moi_cau", "điểm mỗi câu": "diem_moi_cau"}
RE_CAU = re.compile(r"^Câu\s*\d+\s*[.:)]\s*(.*)$", re.I)
RE_BAI = re.compile(r"^Bài\s*\d+\b.*$", re.I)
RE_OPT = re.compile(r"^([A-Da-d])\s*[.)]\s*(.*)$")
RE_DAP = re.compile(r"^(?:Đáp án|Dap an)\s*[:：]\s*([A-Da-d])\b", re.I)
RE_GIAI = re.compile(r"^(?:Lời giải|Hướng dẫn|Đáp án)\s*[:：]\s*(.*)$", re.I)


def warn(path, msg):
    rel = os.path.relpath(path, os.path.dirname(ROOT)).replace("\\", "/")
    print("::warning file=%s::%s" % (rel, msg))
    print("CẢNH BÁO %s: %s" % (rel, msg))


def parse_txt(text):
    d = {"trac_nghiem": [], "tu_luan": []}
    cur, kind, field, mode = None, None, None, "head"

    def close():
        nonlocal cur, kind
        if cur is None:
            return
        if kind == "tn":
            n = len(d["trac_nghiem"]) + 1
            if len(cur["o"]) != 4:
                raise ValueError("Câu %d cần đúng 4 đáp án A, B, C, D (đang có %d)." % (n, len(cur["o"])))
            if cur["a"] is None:
                raise ValueError("Câu %d thiếu dòng 'Đáp án: ...'." % n)
            d["trac_nghiem"].append(cur)
        else:
            cur["giai"] = cur.get("giai", "").strip()
            d["tu_luan"].append(cur)
        cur = None

    for raw in text.replace("\ufeff", "").splitlines():
        l = raw.strip()
        if not l:
            continue
        m = RE_CAU.match(l)
        if m:
            close(); cur = {"q": m.group(1), "o": [], "a": None}; kind, field, mode = "tn", "q", "body"; continue
        if RE_BAI.match(l):
            close(); cur = {"de": l, "giai": ""}; kind, field, mode = "tl", "de", "body"; continue
        if mode == "head":
            if ":" in l:
                k, v = l.split(":", 1)
                key = HEAD.get(k.strip().lower())
                if key:
                    d[key] = v.strip()
            continue
        if kind == "tn":
            m = RE_DAP.match(l)
            if m:
                cur["a"] = "ABCD".index(m.group(1).upper()); field = None; continue
            m = RE_OPT.match(l)
            if m and len(cur["o"]) < 4:
                cur["o"].append(m.group(2)); field = "o"; continue
            if field == "q":
                cur["q"] += " " + l
            elif field == "o" and cur["o"]:
                cur["o"][-1] += " " + l
        elif kind == "tl":
            m = RE_GIAI.match(l)
            if m:
                cur["giai"] = m.group(1); field = "giai"; continue
            if field == "giai":
                cur["giai"] += "\n" + l
            else:
                cur["de"] += "\n" + l
    close()
    if "hoc_ki" in d:
        d["hoc_ki"] = int(re.sub(r"\D", "", str(d["hoc_ki"])) or 0)
    if "diem_moi_cau" in d:
        d["diem_moi_cau"] = float(str(d["diem_moi_cau"]).replace(",", "."))
    d.setdefault("dang", "Tổng hợp")
    if d.get("loai") in LOAI:
        d.setdefault("thoi_gian", LOAI[d["loai"]])
    if d["trac_nghiem"]:
        d.setdefault("diem_moi_cau", 0.25)
    return d


def validate(d):
    e = []
    if not str(d.get("tieu_de", "")).strip():
        e.append("thiếu 'Tiêu đề'")
    if d.get("loai") not in LOAI:
        e.append("'Loại' phải là kt15, kt45 hoặc thi")
    if d.get("hoc_ki") not in (1, 2):
        e.append("'Học kì' phải là 1 hoặc 2")
    tn, tl = d.get("trac_nghiem") or [], d.get("tu_luan") or []
    if not tn and not tl:
        e.append("đề chưa có câu hỏi nào")
    for i, x in enumerate(tn, 1):
        o = x.get("o")
        if not str(x.get("q", "")).strip() or not isinstance(o, list) or len(o) != 4 or not all(str(t).strip() for t in o):
            e.append("câu trắc nghiệm %d phải có nội dung và đúng 4 đáp án" % i)
        elif x.get("a") not in (0, 1, 2, 3):
            e.append("câu trắc nghiệm %d: đáp án đúng phải là 0, 1, 2 hoặc 3 (A đến D)" % i)
    for i, x in enumerate(tl, 1):
        if not str(x.get("de", "")).strip():
            e.append("bài tự luận %d chưa có đề" % i)
    pt = d.get("diem_moi_cau", 0.25)
    if tn and (not isinstance(pt, (int, float)) or pt <= 0 or pt * len(tn) > 10):
        e.append("'Điểm mỗi câu trắc nghiệm' không hợp lý (tổng trắc nghiệm vượt 10 điểm)")
    return e


def main():
    converted = 0
    for dp, _, fs in os.walk(ROOT):
        for f in sorted(fs):
            if f.lower().endswith(".txt") and not f.upper().startswith(("MAU", "README")):
                p = os.path.join(dp, f)
                try:
                    d = parse_txt(open(p, encoding="utf-8").read())
                    errs = validate(d)
                    if errs:
                        warn(p, "; ".join(errs)); continue
                    d["id"] = os.path.splitext(f)[0]
                    out = os.path.splitext(p)[0] + ".json"
                    open(out, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=1))
                    converted += 1
                except Exception as ex:
                    warn(p, str(ex))
    items, bad = [], 0
    for dp, _, fs in os.walk(ROOT):
        for f in sorted(fs):
            if f.lower().endswith(".json") and f != "index.json":
                p = os.path.join(dp, f)
                try:
                    d = json.load(open(p, encoding="utf-8"))
                    errs = validate(d)
                except Exception as ex:
                    errs = ["không đọc được file JSON: %s" % ex]
                if errs:
                    bad += 1; warn(p, "; ".join(errs)); continue
                items.append({"f": os.path.relpath(p, ROOT).replace("\\", "/"), "loai": d["loai"], "hoc_ki": d["hoc_ki"],
                              "dang": d.get("dang", "Tổng hợp"), "tieu_de": d["tieu_de"],
                              "tn": len(d.get("trac_nghiem") or []), "tl": len(d.get("tu_luan") or [])})
    items.sort(key=lambda x: (x["loai"], x["hoc_ki"], x["dang"], x["f"]))
    idx = {"cap_nhat": datetime.date.today().isoformat(), "so_de": len(items), "de": items}
    open(os.path.join(ROOT, "index.json"), "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=1))
    print("Đã đổi %d file .txt sang .json. Danh mục có %d đề hợp lệ, %d file lỗi bị bỏ qua." % (converted, len(items), bad))


if __name__ == "__main__":
    main()
