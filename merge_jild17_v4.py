#!/usr/bin/env python3
"""Merge Fatawa Razviya Jild 17 easy-Urdu tashreeh v4 chunks into jild-17.json.

Reads the 17 leaf chunk files listed in chunks-manifest-v4-jild17.json,
concatenates them in order 01 -> 02 -> 03 -> 04 -> 05 -> 06 -> 07 ->
08a -> 08b -> 08c -> 09 -> 09b -> 10a -> 10 -> 11 -> 12 -> 13, JOINS
the three masala-217 parts (leaves 08a+08b+08c) and the two
masala-219 parts (leaves 09b+10a) into single items, derives
start_page = min(pages) where the field is absent, normalises page
markers, validates, and writes {"masail": [...]} to jild-17.json.

ORDER -- chunk order is the order:
  The v3 merged file ~/workspace/fatawa-app/content/tashreeh/jild-17.json
  has ID order == concatenation order of the v4 leaf chunks (verified
  locally by the coordinator: all 252 ids match the v3 sequence exactly
  after the two joins). Do NOT sort or reorder. Within each chunk,
  items keep file order. CHUNK_ORDER is an explicit 17-leaf list
  because 08a/08b/08c, 09b and 10a break the numeric range pattern.

GENERIC CONSECUTIVE-DUPLICATE JOIN (the joins in this merge, earlier-jild
  pattern): two masail were written in multiple leaves because they
  are too big for one worker, so concatenation gives the same id 2-3
  times consecutively. Each group is joined into ONE item: pages =
  sorted union, sawal = the single non-empty one IF ANY (at most one,
  and it must be in the FIRST part — masala-219 has NO non-empty
  sawal in any part, merged v3 sawal is empty), jawab = parts
  concatenated with a single space, notes = concatenated in order,
  title / volume_id / start_page from the FIRST part. All parts of
  both joins carry the merged-v3 title (instructed in the worker
  briefs; title_must_match=True for both).
  masala-217 (3 parts): leaves 08a (pp.395-420, FULL sawal 1,695ch,
    notes 1-8) + 08b (pp.421-470, kasir-6..11 joined in the leaf,
    sawal EMPTY, notes 9-29) + 08c (pp.471-502, p471+p483+p486+
    masala-12 joined in the leaf, sawal EMPTY, notes 30-43) -> 1
    item, 108 pages, notes 8+21+14 = 43.
  masala-219 (2 parts): leaf 09b (pp.505-520, masala-219+p506+p514
    joined in the leaf, sawal EMPTY, notes 1-12) + leaf 10a
    (pp.521-560, 17 p-items joined in the leaf, sawal EMPTY, notes
    13-52) -> 1 item, 56 pages, notes 12+40 = 52. Joined sawal is
    EMPTY (all parts empty, as in v3).
  After the joins there are 252 items and 252 unique ids — the
  duplicate-id assertion runs AFTER the joins, not before.
  NO rename quirk in Jild 17's merge: the v3 merged file has 252
  UNIQUE ids.

BOUNDARY DEDUP / FOLD (5 masail — the Jild 10/11/12/13/14/16
  pattern): the v3 chunk files overlap at 5 boundaries; the merged
  v3 has each ONCE with combined pages + combined notes. Each is
  written ONCE, in the EARLIER leaf, combining both halves' tashreeh
  into one flowing passage with ALL notes from both halves; the later
  leaf EXCLUDES the folded item:
  masala-33 (leaf 01, [119-121] — folds in chunk-02's
    jild17-masala-33 [121]; chunk-01's own half is id jild17-33),
  masala-141 (leaf 05, [320-322] — folds in chunk-06's
    jild17-masala-141 [321,322]; chunk-05's own half is id jild17-141;
    sawal = chunk-05's 342ch, chunk-06's 325ch sawal dropped),
  masala-198 (leaf 06, [370-374] — folds in chunk-07's
    jild17-masala-198 [371-374]; sawal = chunk-06's 1,902ch,
    chunk-07's 1,841ch sawal dropped; jawab = chunk-07's 4,386ch,
    chunk-06's half has EMPTY jawab),
  masala-255 (leaf 11, [610-613] — folds in chunk-12's jild17-255
    [612,613]; title keeps "(جاری)" verbatim, v3's own wording),
  masala-280 (leaf 12, [657-670] — folds in chunk-13's jild17-280
    [661-670]).
  The 6 fold-boundary pages (121, 322, 374, 502, 613, 670) are each
  present in two leaves (fold/join item's last page = next leaf's
  first item's first page); per-leaf present pages sum to 636 while
  unique pages are 630.

START_PAGE: every one of the 17 v4 leaf chunks carries start_page ==
  min(pages) for all its items (verified by the coordinator). The
  derivation code below stays as a safety net; it is expected to
  derive 0 items.

MARKER NORMALISATION (the only text transformation): page markers, if
  present, are normalised to the single form [safha N] written with the
  Urdu word for page:
  - lenticular-bracket form (U+3010/U+3011 around the Urdu word for
    page + number) -> [safha N]
  - [short form] -> [safha N]
  - [safha N] stays as-is
  Applied to every string field of every item (jawab, sawal, title,
  notes). The 17 v4 chunks are expected to contain ZERO markers of
  any form (verified locally); the code stays so the merge is robust
  and the "none remain" assertions still run. No other text is
  touched and no markers are invented.
  NOTE: the literal lenticular-bracket characters are written here only
  as U+3010/U+3011 escapes, never as literal characters in this file.

VALIDATION (fails loudly on any violation):
  252 items; ID sequence EXACTLY == the v3 merged file's ID sequence
  (embedded below as V3_IDS, copied verbatim from
  ~/workspace/fatawa-app/content/tashreeh/jild-17.json); pages per item
  identical to v3 (embedded as V3_PAGES, same source, verified against
  the v3 file before pushing); 630 unique pages (min 6, max 715);
  volume_ids == {53}; start_page == min(pages) for every item (after
  derivation); zero empty tashreeh_jawab; no lenticular / short markers
  remain; first id jild17-pesh-lafz, last id jild17-khatima.
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = "chunks-manifest-v4-jild17.json"

# Concatenation order: chunk files 01 -> 18, in order.
CHUNK_ORDER = ["jild-17-chunk-01.json", "jild-17-chunk-02.json", "jild-17-chunk-03.json", "jild-17-chunk-04.json", "jild-17-chunk-05.json", "jild-17-chunk-06.json", "jild-17-chunk-07.json", "jild-17-chunk-08a.json", "jild-17-chunk-08b.json", "jild-17-chunk-08c.json", "jild-17-chunk-09.json", "jild-17-chunk-09b.json", "jild-17-chunk-10a.json", "jild-17-chunk-10.json", "jild-17-chunk-11.json", "jild-17-chunk-12.json", "jild-17-chunk-13.json"]

EXPECTED_ITEMS = 252
EXPECTED_PAGES = 630
EXPECTED_MIN_PAGE = 6
EXPECTED_MAX_PAGE = 715
EXPECTED_VOLUME_IDS = {53}
EXPECTED_FIRST_ID = "jild17-pesh-lafz"
EXPECTED_LAST_ID = "jild17-khatima"

# v3 ID sequence, verbatim from content/tashreeh/jild-17.json.
V3_IDS = ["jild17-pesh-lafz", "jild17-1", "jild17-2", "jild17-3", "jild17-4", "jild17-5", "jild17-6-16", "jild17-17", "jild17-18", "jild17-19", "jild17-20", "jild17-21", "jild17-22", "jild17-23", "jild17-24", "jild17-25", "jild17-26", "jild17-27", "jild17-28", "jild17-29", "jild17-30", "jild17-31", "jild17-32", "jild17-masala-33", "jild17-masala-34-35", "jild17-masala-36", "jild17-masala-37", "jild17-masala-38", "jild17-masala-39", "jild17-masala-40", "jild17-masala-41", "jild17-masala-42", "jild17-masala-43", "jild17-masala-44-45", "jild17-masala-46", "jild17-masala-47", "jild17-masala-48", "jild17-masala-49", "jild17-masala-50", "jild17-masala-51", "jild17-masala-52", "jild17-masala-53", "jild17-masala-54", "jild17-masala-55", "jild17-masala-56", "jild17-masala-57", "jild17-masala-58", "jild17-masala-59", "jild17-masala-60", "jild17-masala-61", "jild17-masala-62", "jild17-masala-63", "jild17-masala-64", "jild17-masala-65", "jild17-masala-66", "jild17-masala-67-68", "jild17-masala-69", "jild17-masala-70-71", "jild17-masala-72", "jild17-masala-73", "jild17-masala-74", "jild17-masala-75", "jild17-masala-76", "jild17-masala-77", "jild17-masala-78", "jild17-masala-79", "jild17-masala-80", "jild17-masala-81", "jild17-masala-82-84", "jild17-p173", "jild17-masala-86", "jild17-masala-87", "jild17-masala-88", "jild17-masala-89", "jild17-masala-90", "jild17-masala-91-92", "jild17-masala-93", "jild17-masala-94", "jild17-masala-95", "jild17-masala-96", "jild17-masala-97", "jild17-masala-98", "jild17-masala-99", "jild17-masala-100", "jild17-masala-101", "jild17-masala-102", "jild17-masala-103", "jild17-masala-104", "jild17-masala-105", "jild17-masala-106", "jild17-masala-107", "jild17-masala-108", "jild17-masala-109", "jild17-masala-110", "jild17-masala-111", "jild17-masala-112", "jild17-masala-113", "jild17-masala-114", "jild17-115", "jild17-116", "jild17-117", "jild17-118", "jild17-119", "jild17-120", "jild17-122", "jild17-123-124", "jild17-125", "jild17-126", "jild17-127", "jild17-128", "jild17-129", "jild17-130", "jild17-131", "jild17-132", "jild17-133-138", "jild17-139", "jild17-140", "jild17-masala-141", "jild17-masala-142-144", "jild17-masala-145", "jild17-masala-146", "jild17-masala-147", "jild17-masala-148", "jild17-masala-149", "jild17-masala-150", "jild17-masala-151", "jild17-masala-152", "jild17-masala-153", "jild17-masala-154-155", "jild17-masala-156", "jild17-masala-157", "jild17-masala-158-159", "jild17-masala-160", "jild17-masala-161", "jild17-masala-162", "jild17-masala-163", "jild17-masala-164", "jild17-masala-165", "jild17-masala-166", "jild17-masala-167-170", "jild17-masala-171", "jild17-masala-172", "jild17-masala-173", "jild17-masala-174", "jild17-masala-175-176", "jild17-masala-177", "jild17-masala-178", "jild17-masala-179", "jild17-masala-180", "jild17-masala-181-182", "jild17-masala-183-184", "jild17-masala-185-186", "jild17-masala-187", "jild17-masala-188", "jild17-masala-189", "jild17-masala-190", "jild17-masala-191", "jild17-masala-192", "jild17-masala-193", "jild17-masala-194", "jild17-masala-195", "jild17-masala-196", "jild17-masala-197", "jild17-masala-198", "jild17-masala-199", "jild17-masala-200", "jild17-masala-201", "jild17-masala-202", "jild17-masala-203", "jild17-masala-204", "jild17-masala-205", "jild17-masala-206", "jild17-masala-207", "jild17-masala-208", "jild17-masala-209", "jild17-masala-210", "jild17-masala-211", "jild17-masala-212", "jild17-masala-213", "jild17-masala-214", "jild17-masala-215", "jild17-masala-216", "jild17-masala-217", "jild17-masala-218", "jild17-masala-219", "jild17-masala-220", "jild17-masala-221", "jild17-masala-222", "jild17-masala-223", "jild17-masala-224", "jild17-masala-225", "jild17-masala-226", "jild17-masala-227", "jild17-masala-228", "jild17-masala-229", "jild17-masala-230", "jild17-masala-231", "jild17-masala-232", "jild17-masala-233", "jild17-masala-234-235", "jild17-masala-236", "jild17-masala-237-239", "jild17-masala-240", "jild17-masala-241", "jild17-masala-242", "jild17-masala-243", "jild17-masala-244", "jild17-masala-245", "jild17-masala-246", "jild17-masala-247", "jild17-masala-248", "jild17-masala-249", "jild17-masala-250", "jild17-masala-251", "jild17-masala-252", "jild17-masala-253-254", "jild17-masala-255", "jild17-256", "jild17-257", "jild17-p615", "jild17-259", "jild17-260", "jild17-261", "jild17-262", "jild17-263", "jild17-266", "jild17-267", "jild17-268", "jild17-269", "jild17-270", "jild17-271", "jild17-272", "jild17-273", "jild17-274", "jild17-275", "jild17-276", "jild17-277", "jild17-278", "jild17-279", "jild17-280", "jild17-281", "jild17-282", "jild17-283-286", "jild17-287", "jild17-288", "jild17-289", "jild17-290", "jild17-291", "jild17-292", "jild17-293-297", "jild17-298", "jild17-khatima"]

# v3 pages per item id, verbatim from content/tashreeh/jild-17.json.
V3_PAGES = {
"jild17-pesh-lafz": [6, 7, 8],
"jild17-1": [81, 82],
"jild17-2": [82, 83, 84, 85, 86, 87],
"jild17-3": [87, 88],
"jild17-4": [88, 89],
"jild17-5": [89, 90],
"jild17-6-16": [90, 91, 92],
"jild17-17": [92, 93],
"jild17-18": [93, 94],
"jild17-19": [94, 95],
"jild17-20": [95],
"jild17-21": [95, 96],
"jild17-22": [96],
"jild17-23": [96, 97],
"jild17-24": [97, 98],
"jild17-25": [98, 99, 100, 101, 102, 103],
"jild17-26": [103, 104, 105, 106, 107],
"jild17-27": [107, 109],
"jild17-28": [109, 110],
"jild17-29": [110, 111, 112, 113, 114, 115, 116],
"jild17-30": [116, 117],
"jild17-31": [117, 118],
"jild17-32": [118, 119],
"jild17-masala-33": [119, 120, 121],
"jild17-masala-34-35": [121, 122, 123, 124],
"jild17-masala-36": [124, 125, 126, 127],
"jild17-masala-37": [127],
"jild17-masala-38": [128],
"jild17-masala-39": [128, 129],
"jild17-masala-40": [129],
"jild17-masala-41": [129, 130],
"jild17-masala-42": [130],
"jild17-masala-43": [130, 131],
"jild17-masala-44-45": [131, 132],
"jild17-masala-46": [132, 133, 134, 135, 136, 137],
"jild17-masala-47": [137],
"jild17-masala-48": [137, 138],
"jild17-masala-49": [138],
"jild17-masala-50": [138, 139],
"jild17-masala-51": [139, 140],
"jild17-masala-52": [141, 142, 143],
"jild17-masala-53": [144, 145, 146, 147, 148, 149],
"jild17-masala-54": [149, 150, 151],
"jild17-masala-55": [151, 152, 153],
"jild17-masala-56": [153, 154],
"jild17-masala-57": [154, 155],
"jild17-masala-58": [155, 156],
"jild17-masala-59": [156],
"jild17-masala-60": [156, 157],
"jild17-masala-61": [157, 158, 159],
"jild17-masala-62": [159, 160],
"jild17-masala-63": [160, 161],
"jild17-masala-64": [161],
"jild17-masala-65": [161, 162],
"jild17-masala-66": [162],
"jild17-masala-67-68": [162, 163, 164],
"jild17-masala-69": [165],
"jild17-masala-70-71": [165],
"jild17-masala-72": [166, 167],
"jild17-masala-73": [167, 168],
"jild17-masala-74": [168],
"jild17-masala-75": [168, 169],
"jild17-masala-76": [168, 169],
"jild17-masala-77": [169, 170],
"jild17-masala-78": [170],
"jild17-masala-79": [170, 171],
"jild17-masala-80": [171],
"jild17-masala-81": [171, 172],
"jild17-masala-82-84": [172, 173],
"jild17-p173": [173, 174],
"jild17-masala-86": [174, 175],
"jild17-masala-87": [175, 176, 177],
"jild17-masala-88": [177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188],
"jild17-masala-89": [189, 190],
"jild17-masala-90": [190, 191],
"jild17-masala-91-92": [190, 191],
"jild17-masala-93": [191, 192],
"jild17-masala-94": [192],
"jild17-masala-95": [193, 194],
"jild17-masala-96": [194],
"jild17-masala-97": [194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204],
"jild17-masala-98": [205, 206, 207, 208, 209],
"jild17-masala-99": [209],
"jild17-masala-100": [209, 210],
"jild17-masala-101": [210, 211, 212, 213, 214, 215, 216],
"jild17-masala-102": [217, 218],
"jild17-masala-103": [219],
"jild17-masala-104": [220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241],
"jild17-masala-105": [243, 244, 245, 246],
"jild17-masala-106": [246, 247],
"jild17-masala-107": [248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260],
"jild17-masala-108": [260, 261, 262],
"jild17-masala-109": [262],
"jild17-masala-110": [263],
"jild17-masala-111": [263],
"jild17-masala-112": [263, 264],
"jild17-masala-113": [264, 265, 266],
"jild17-masala-114": [266, 267],
"jild17-115": [269],
"jild17-116": [270, 271, 272, 273],
"jild17-117": [273],
"jild17-118": [273, 274],
"jild17-119": [274],
"jild17-120": [274, 275, 276],
"jild17-122": [276],
"jild17-123-124": [277],
"jild17-125": [278, 279, 280, 281],
"jild17-126": [281, 282, 283, 284, 285, 286, 287, 288, 289],
"jild17-127": [289, 290],
"jild17-128": [290],
"jild17-129": [291, 292, 293],
"jild17-130": [293, 294, 295, 296, 297, 298],
"jild17-131": [298, 299, 300, 301, 302, 303, 304],
"jild17-132": [304],
"jild17-133-138": [304, 305, 306, 307, 308],
"jild17-139": [308],
"jild17-140": [308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320],
"jild17-masala-141": [320, 321, 322],
"jild17-masala-142-144": [322, 323],
"jild17-masala-145": [322, 323],
"jild17-masala-146": [323],
"jild17-masala-147": [323],
"jild17-masala-148": [323, 324],
"jild17-masala-149": [324, 325],
"jild17-masala-150": [325, 326],
"jild17-masala-151": [326],
"jild17-masala-152": [326],
"jild17-masala-153": [326],
"jild17-masala-154-155": [326, 327],
"jild17-masala-156": [327],
"jild17-masala-157": [327, 328, 329, 330, 331, 332, 333],
"jild17-masala-158-159": [333, 334],
"jild17-masala-160": [334, 335],
"jild17-masala-161": [335],
"jild17-masala-162": [335, 336],
"jild17-masala-163": [336, 337],
"jild17-masala-164": [337],
"jild17-masala-165": [337],
"jild17-masala-166": [337, 338],
"jild17-masala-167-170": [338],
"jild17-masala-171": [338, 339],
"jild17-masala-172": [339, 340],
"jild17-masala-173": [340, 341],
"jild17-masala-174": [341, 342],
"jild17-masala-175-176": [342, 343, 344],
"jild17-masala-177": [344, 345],
"jild17-masala-178": [345],
"jild17-masala-179": [345, 346],
"jild17-masala-180": [346, 347],
"jild17-masala-181-182": [347, 348],
"jild17-masala-183-184": [348, 349],
"jild17-masala-185-186": [349, 350, 351],
"jild17-masala-187": [351, 352],
"jild17-masala-188": [353],
"jild17-masala-189": [353, 354, 355],
"jild17-masala-190": [355, 356, 357],
"jild17-masala-191": [357, 358, 359, 360, 361],
"jild17-masala-192": [361, 362],
"jild17-masala-193": [362, 363, 364],
"jild17-masala-194": [364, 365],
"jild17-masala-195": [366, 367],
"jild17-masala-196": [367, 368],
"jild17-masala-197": [368, 369, 370],
"jild17-masala-198": [370, 371, 372, 373, 374],
"jild17-masala-199": [374, 375],
"jild17-masala-200": [375, 376],
"jild17-masala-201": [376],
"jild17-masala-202": [376, 377, 378],
"jild17-masala-203": [378, 379, 380],
"jild17-masala-204": [380, 381],
"jild17-masala-205": [381],
"jild17-masala-206": [381],
"jild17-masala-207": [381, 382],
"jild17-masala-208": [382, 383],
"jild17-masala-209": [383, 384],
"jild17-masala-210": [384, 385],
"jild17-masala-211": [385, 386],
"jild17-masala-212": [386, 387, 388],
"jild17-masala-213": [388, 389],
"jild17-masala-214": [389],
"jild17-masala-215": [390, 391, 392],
"jild17-masala-216": [392, 393, 394],
"jild17-masala-217": [395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502],
"jild17-masala-218": [502, 503, 504],
"jild17-masala-219": [505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560],
"jild17-masala-220": [561, 562, 563],
"jild17-masala-221": [563],
"jild17-masala-222": [563, 564, 565, 566, 567],
"jild17-masala-223": [569, 570, 571, 572, 573],
"jild17-masala-224": [573],
"jild17-masala-225": [573, 574],
"jild17-masala-226": [574],
"jild17-masala-227": [574, 575, 576],
"jild17-masala-228": [576],
"jild17-masala-229": [576, 577, 578],
"jild17-masala-230": [578],
"jild17-masala-231": [578],
"jild17-masala-232": [578, 579],
"jild17-masala-233": [579, 580],
"jild17-masala-234-235": [580],
"jild17-masala-236": [581],
"jild17-masala-237-239": [581, 582, 583],
"jild17-masala-240": [583, 584],
"jild17-masala-241": [584, 585],
"jild17-masala-242": [585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595],
"jild17-masala-243": [595],
"jild17-masala-244": [597, 598, 599, 600],
"jild17-masala-245": [600],
"jild17-masala-246": [601, 602, 603, 604],
"jild17-masala-247": [604, 605],
"jild17-masala-248": [605],
"jild17-masala-249": [605, 606],
"jild17-masala-250": [606],
"jild17-masala-251": [606, 607],
"jild17-masala-252": [607, 608],
"jild17-masala-253-254": [608, 609, 610],
"jild17-masala-255": [610, 611, 612, 613],
"jild17-256": [613, 614],
"jild17-257": [614],
"jild17-p615": [615],
"jild17-259": [616],
"jild17-260": [616, 617],
"jild17-261": [617, 618, 619],
"jild17-262": [619, 620],
"jild17-263": [620, 621, 622, 623, 624, 625, 626, 627],
"jild17-266": [627, 628, 629, 630, 631, 632],
"jild17-267": [632, 633, 634, 635, 636, 637],
"jild17-268": [638],
"jild17-269": [639, 640, 641],
"jild17-270": [641],
"jild17-271": [643, 644, 645],
"jild17-272": [645],
"jild17-273": [645, 646, 647],
"jild17-274": [649],
"jild17-275": [649, 650],
"jild17-276": [650, 651],
"jild17-277": [651],
"jild17-278": [653, 654, 655],
"jild17-279": [655, 656, 657],
"jild17-280": [657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670],
"jild17-281": [670, 671],
"jild17-282": [671, 672, 673, 674, 675, 676],
"jild17-283-286": [676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686],
"jild17-287": [686, 687],
"jild17-288": [687, 688, 689, 690, 691, 692, 693, 694, 695, 696],
"jild17-289": [696, 697],
"jild17-290": [697, 698, 699, 700, 701, 702],
"jild17-291": [703, 704, 705],
"jild17-292": [705, 706, 707, 708, 709, 710, 711],
"jild17-293-297": [712, 713, 714, 715],
"jild17-298": [715],
"jild17-khatima": [715],
}

# The Urdu word for "page" is safha; the canonical marker is [safha N].
# Lenticular brackets are U+3010 (open) and U+3011 (close); the short
# form is "[safha-initial N]" with the single-letter abbreviation.
# All three patterns are built from escapes so this file never contains
# a literal lenticular-bracket pair.
SAFHA = "\u0635\u0641\u062d\u06c1"  # the Urdu word for page
RE_LENTICULAR = re.compile("\u3010" + SAFHA + " (\\d+)\u3011")
RE_SHORT = re.compile("\\[\u0635 (\\d+)\\]")
RE_FULL = re.compile("\\[" + SAFHA + " \\d+\\]")
LENTICULAR_PREFIX = "\u3010" + SAFHA  # for the "none remain" check
SHORT_PREFIX_RE = re.compile("\\[\u0635 \\d+\\]")

# Canonical output key order for every item (the JSON contract).
ITEM_KEYS = ["id", "title", "volume_id", "pages", "start_page",
             "tashreeh_sawal", "tashreeh_jawab", "notes"]


def normalise_markers(text):
    """Normalise page markers in one string. Returns (new_text, counts)."""
    counts = {"lenticular": 0, "short": 0, "full_before": 0}
    counts["full_before"] = len(RE_FULL.findall(text))
    text, n1 = RE_LENTICULAR.subn("[" + SAFHA + " \\1]", text)
    counts["lenticular"] = n1
    text, n2 = RE_SHORT.subn("[" + SAFHA + " \\1]", text)
    counts["short"] = n2
    return text, counts


def normalise_item(item):
    """Normalise markers in every string field of one item (recursively
    through lists/dicts). Returns per-form counts for this item."""
    totals = {"lenticular": 0, "short": 0, "full_before": 0}

    def walk(value):
        if isinstance(value, str):
            new, c = normalise_markers(value)
            for k in totals:
                totals[k] += c[k]
            return new
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        return value

    for key in list(item.keys()):
        item[key] = walk(item[key])
    return totals


def main():
    assert len(V3_IDS) == EXPECTED_ITEMS, "embedded V3_IDS length mismatch"
    assert set(V3_PAGES) == set(V3_IDS), "embedded V3_PAGES keys != V3_IDS"
    assert sum(len(v) for v in V3_PAGES.values()) >= EXPECTED_PAGES

    manifest = json.load(open(os.path.join(BASE, MANIFEST), encoding="utf-8"))
    entries = manifest["chunks"]
    assert len(entries) == 17, f"expected 17 manifest entries, got {len(entries)}"
    assert all(e.get("status") == "done" for e in entries), "not all chunks done"
    by_file = {e["file"]: e for e in entries}
    assert set(by_file) == set(CHUNK_ORDER), (
        f"manifest files != CHUNK_ORDER: "
        f"missing={set(CHUNK_ORDER) - set(by_file)} "
        f"extra={set(by_file) - set(CHUNK_ORDER)}"
    )

    all_items = []
    derived = []
    for fname in CHUNK_ORDER:
        path = os.path.join(BASE, fname)
        d = json.load(open(path, encoding="utf-8"))
        items = d["masail"]
        entry = by_file[fname]
        assert len(items) == entry["items"], (
            f"{fname}: {len(items)} items, manifest says {entry['items']}"
        )
        # Marker normalisation, with before/after counts per chunk.
        before = {"lenticular": 0, "short": 0, "full_before": 0}
        for it in items:
            c = normalise_item(it)
            for k in before:
                before[k] += c[k]
        after_full = sum(
            len(RE_FULL.findall(json.dumps(it, ensure_ascii=False)))
            for it in items
        )
        print(
            f"{fname}: {len(items)} items | markers before: "
            f"lenticular={before['lenticular']} short={before['short']} "
            f"full={before['full_before']} | after: full={after_full}"
        )
        assert after_full == (
            before["lenticular"] + before["short"] + before["full_before"]
        ), f"{fname}: marker count changed by normalisation!"
        # Derive start_page = min(pages) where absent (none expected: all chunks carry start_page).
        for it in items:
            if "start_page" not in it:
                it["start_page"] = min(it["pages"])
                derived.append(it["id"])
        all_items.extend(items)

    # GENERIC CONSECUTIVE-DUPLICATE JOIN (earlier-jild pattern): two
    # masail were written in multiple leaves because they are too big
    # for one worker, so concatenation gives the same id 2-3 times
    # consecutively. Each group is joined into ONE item: pages =
    # sorted union, sawal = the single non-empty one IF ANY (at most
    # one, and it must be in the FIRST part — masala-219 has NO
    # non-empty sawal in any part, merged v3 sawal is empty),
    # jawab = parts concatenated with a single space, notes =
    # concatenated in order, title / volume_id / start_page from the
    # FIRST part. All parts of both joins carry the merged-v3 title
    # (instructed in the worker briefs; title_must_match=True).
    #   masala-217 (3 parts): leaves 08a (pp.395-420, FULL sawal
    #     1,695ch, notes 1-8) + 08b (pp.421-470, kasir-6..11 joined in
    #     the leaf, sawal EMPTY, notes 9-29) + 08c (pp.471-502,
    #     p471+p483+p486+masala-12 joined in the leaf, sawal EMPTY,
    #     notes 30-43) -> 1 item, 108 pages, notes 8+21+14 = 43.
    #   masala-219 (2 parts): leaf 09b (pp.505-520, masala-219+p506+
    #     p514 joined in the leaf, sawal EMPTY, notes 1-12) + leaf 10a
    #     (pp.521-560, 17 p-items joined in the leaf, sawal EMPTY,
    #     notes 13-52) -> 1 item, 56 pages, notes 12+40 = 52. Joined
    #     sawal is EMPTY (all parts empty, as in v3).
    # After the joins there are 252 items and 252 unique ids — the
    # duplicate-id assertion runs AFTER the joins, not before.
    # NO rename quirk in Jild 17's merge: the v3 merged file has 252
    # UNIQUE ids.
    def join_consecutive(item_id, expected_parts, seam_checks, title_must_match=True):
        idxs = [i for i, it in enumerate(all_items) if it["id"] == item_id]
        assert len(idxs) == expected_parts, (
            f"expected exactly {expected_parts} {item_id} parts, got {len(idxs)}"
        )
        assert all(idxs[k + 1] == idxs[k] + 1 for k in range(len(idxs) - 1)), (
            f"{item_id} parts are not consecutive"
        )
        parts = [all_items[i] for i in idxs]
        vols = {p.get("volume_id") for p in parts}
        assert vols == {53}, f"{item_id} volume mismatch: {vols}"
        non_empty_sawal = [p for p in parts if p.get("tashreeh_sawal")]
        assert len(non_empty_sawal) <= 1, (
            f"{item_id}: expected at most 1 non-empty sawal, got {len(non_empty_sawal)}"
        )
        if non_empty_sawal:
            assert non_empty_sawal[0] is parts[0], (
                f"{item_id}: the non-empty sawal must be in the FIRST part"
            )
        if title_must_match:
            assert all(p["title"] == parts[0]["title"] for p in parts), (
                f"{item_id} part titles differ"
            )
        for (part_no, which, needle) in seam_checks:
            txt = parts[part_no]["tashreeh_jawab"]
            if which == "end":
                assert txt.rstrip().endswith(needle), (
                    f"{item_id} part {part_no + 1} jawab does not end at the verified seam: {needle!r}"
                )
            else:
                assert txt.lstrip().startswith(needle), (
                    f"{item_id} part {part_no + 1} jawab does not start at the verified seam: {needle!r}"
                )
        joined = {
            "id": item_id,
            "title": parts[0]["title"],
            "volume_id": parts[0]["volume_id"],
            "pages": sorted(set().union(*[set(p["pages"]) for p in parts])),
            "start_page": min(min(p["pages"]) for p in parts),
            "tashreeh_sawal": parts[0]["tashreeh_sawal"],
            "tashreeh_jawab": " ".join(
                p["tashreeh_jawab"].strip() for p in parts
            ),
            "notes": sum((p.get("notes") or [] for p in parts), []),
        }
        all_items[idxs[0]:idxs[-1] + 1] = [joined]
        print(
            f"{item_id} joined: "
            + " + ".join(
                f"part {k + 1} ({len(p['pages'])}pp, "
                f"sawal {'EMPTY' if not p.get('tashreeh_sawal') else str(len(p['tashreeh_sawal'])) + 'ch'}, "
                f"jawab {len(p['tashreeh_jawab'])}ch, notes {len(p.get('notes') or [])})"
                for k, p in enumerate(parts)
            )
            + f" -> 1 item, {len(joined['pages'])} pages, "
              f"jawab {len(joined['tashreeh_jawab'])}ch, notes {len(joined['notes'])}"
        )
        return joined

    join_consecutive(
        "jild17-masala-217", 3,
        [
            (0, "end", "یعنی مگر یہ کہ کوئی سودا ہو تمہاری آپس کی خوشی سے۔"),
            (1, "start", "اعلیٰ حضرت رحمۃ اللہ علیہ فرماتے ہیں کہ بیع کو شریعت نے اسی لیے جائز"),
            (1, "end", "جائز اور ثواب کا کام ہے، اس لیے کہ اس میں حرام سے بھاگنا ہے۔"),
            (2, "start", "دلیل کا سلسلہ آگے بڑھتا ہے کہ حرام سے بچنے کے لیے حیلہ کرنا مستحب ہے،"),
        ],
        title_must_match=True,
    )
    join_consecutive(
        "jild17-masala-219", 2,
        [
            (0, "end", "تصویب کا مطلب ہے قول کے ہو جانے کے بعد اسے درست بتانا۔"),
            (1, "start", "یہ صفحہ پچھلے حصے کی بحث کا تتمہ"),
        ],
        title_must_match=True,
    )
    # Joined titles (part 1's) must equal the merged-v3 titles.
    m217 = next(it for it in all_items if it["id"] == "jild17-masala-217")
    assert m217["title"] == "مسئلہ ۲۱۷: رسالہ کاسر السفیہ الواہم (الذیل المنوط لرسالۃ النوط) — کاغذی نوٹ کی حقیقت اور اس کے بارہ سوالات", (
        f"masala-217 joined title != merged-v3 title: {m217['title']!r}"
    )
    m219 = next(it for it in all_items if it["id"] == "jild17-masala-219")
    assert m219["title"] == "مسئلہ ۲۱۹ — رسالہ کاسر السفیہ الواہم فی ابدال قرطاس الدراہم کا دیباچہ", (
        f"masala-219 joined title != merged-v3 title: {m219['title']!r}"
    )
    assert len(all_items) == len({it["id"] for it in all_items}), (
        f"DUPLICATE IDS after joins: "
        f"{[i for i in [it['id'] for it in all_items] if [it['id'] for it in all_items].count(i) > 1]}"
    )
    print("renames applied: [] (no duplicate masala numbers in Jild 17's merge; masala-217 and masala-219 are joins, not renames)")

    print(f"after joins: {len(all_items)} items (255 concatenated)")
    print(f"start_page derived for {len(derived)} items (expected 0: all chunks carry start_page)")
    assert len(all_items) == EXPECTED_ITEMS, (
        f"expected {EXPECTED_ITEMS} items, got {len(all_items)}"
    )

    # Rebuild each item in the canonical key order (the JSON contract).
    canonical = []
    for it in all_items:
        assert set(it.keys()) == set(ITEM_KEYS), (
            f"{it.get('id')}: keys {sorted(it.keys())} != {sorted(ITEM_KEYS)}"
        )
        canonical.append({k: it[k] for k in ITEM_KEYS})
    all_items = canonical

    # Validation.
    ids = [it["id"] for it in all_items]
    assert ids == V3_IDS, (
        f"ID sequence != v3: first diff at "
        f"{next((i for i, (a, b) in enumerate(zip(ids, V3_IDS)) if a != b), min(len(ids), len(V3_IDS)))}"
    )
    assert len(ids) == len(set(ids)), (
        f"DUPLICATE IDS: {[i for i in ids if ids.count(i) > 1]}"
    )
    empty = [it["id"] for it in all_items if not it.get("tashreeh_jawab")]
    assert not empty, f"EMPTY JAWAB: {empty}"
    vols = set(it.get("volume_id") for it in all_items)
    assert vols == EXPECTED_VOLUME_IDS, f"volume_ids {vols} != {EXPECTED_VOLUME_IDS}"
    pages = set()
    for it in all_items:
        assert it["pages"] == V3_PAGES[it["id"]], (
            f"{it['id']}: pages {it['pages']} != v3 {V3_PAGES[it['id']]}"
        )
        pages.update(it["pages"])
    assert len(pages) == EXPECTED_PAGES, (
        f"expected {EXPECTED_PAGES} unique pages, got {len(pages)}"
    )
    assert min(pages) == EXPECTED_MIN_PAGE, f"min page {min(pages)}"
    assert max(pages) == EXPECTED_MAX_PAGE, f"max page {max(pages)}"
    exceptions = {
        it["id"] for it in all_items if it["start_page"] != min(it["pages"])
    }
    assert not exceptions, f"start_page != min(pages): {sorted(exceptions)}"
    assert ids[0] == EXPECTED_FIRST_ID, f"first id {ids[0]}"
    assert ids[-1] == EXPECTED_LAST_ID, f"last id {ids[-1]}"

    out = {"masail": all_items}
    out_text = json.dumps(out, ensure_ascii=False, indent=1)
    assert LENTICULAR_PREFIX not in out_text, "lenticular markers remain in output!"
    assert not SHORT_PREFIX_RE.search(out_text), "short markers remain in output!"
    total_markers = len(RE_FULL.findall(out_text))
    print(
        f"VALIDATION PASSED: {len(all_items)} items, {len(pages)} unique pages "
        f"(min {min(pages)}, max {max(pages)}), volume_ids {sorted(vols)}, "
        f"first {ids[0]}, last {ids[-1]}, start_page == min(pages) for all, "
        f"derived start_page for {len(derived)} items, markers {total_markers}"
    )

    with open(os.path.join(BASE, "jild-17.json"), "w", encoding="utf-8") as f:
        f.write(out_text)
    print(f"WROTE jild-17.json: {len(out_text.encode('utf-8'))} bytes")


if __name__ == "__main__":
    main()
