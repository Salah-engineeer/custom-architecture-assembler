import sys
import json

with open("pass1_data.json", "r") as f:
    data = json.load(f)

Symbol_table = data["Symbol_table"]
pool_table = data["pool_table"]
intermediate = data["intermediate"]
block_order = data["block_order"]
block = data["block"]
total_length = data["total_length"]

from opcode_table import OPTAB

REGISTERS = {
    "A": 0, "X": 1, "L": 2, "B": 3, "S": 4, "T": 5, "F": 6, "PC": 8, "SW": 9
}

base_register = None
program_name = ""
start_address = 0
first_exec_addr = 0

object_code_lines = []
text_records = []
mod_records = []
current_t_start = None
current_t_bytes = []

current_block_p2 = "DEFAULT"


def handle_error(error_name, pc_value):
    with open("error.txt", "w") as ef:
        ef.write(f"Error: {error_name}\n")
        ef.write(f"PC: {pc_value:06X}\n")
    print(f"[ERROR] {error_name} at PC={pc_value:06X}")
    sys.exit(1)


def resolve(reference):
    ref = reference
    if reference.startswith("#") or reference.startswith("@"):
        ref = reference[1:]
    if "," in ref:
        ref = ref[:ref.index(",")]
    if ref in Symbol_table:
        return int(Symbol_table[ref], 16)
    try:
        return int(ref)
    except:
        return None


def compute_format3_4(instruction, reference, lc_abs, is_format4):

    if reference == "":
        base_instr = instruction.lstrip("+")
        opcode_val = OPTAB[base_instr]["opcode"]
        opcode_ni = (opcode_val & 0xFC) | (1 << 1) | 1  # n=1, i=1
        return f"{opcode_ni:02X}0000"


    if reference.startswith("#"):
        n, i = 0, 1
        ref_clean = reference[1:]
    elif reference.startswith("@"):
        n, i = 1, 0
        ref_clean = reference[1:]
    else:
        n, i = 1, 1
        ref_clean = reference

    x = 0
    if ref_clean.endswith(",X"):
        x = 1
        ref_clean = ref_clean[:-2]

    base_instr = instruction.lstrip("+")
    opcode_val = OPTAB[base_instr]["opcode"]
    opcode_ni = (opcode_val & 0xFC) | (n << 1) | i

    is_pool_ref = ref_clean.startswith("&")

    if not is_pool_ref and ref_clean not in Symbol_table:
        try:
            literal_val = int(ref_clean)
            if is_format4:
                e = 1;
                b = 0;
                p = 0
                nixbpe = (n << 5) | (i << 4) | (x << 3) | (b << 2) | (p << 1) | e
                word = (opcode_ni << 24) | (nixbpe << 20) | (literal_val & 0xFFFFF)
                return f"{word:08X}"
            else:
                b = 0;
                p = 0;
                e = 0
                disp = literal_val & 0xFFF
                nixbpe = (n << 5) | (i << 4) | (x << 3) | (b << 2) | (p << 1) | e
                byte2 = (x << 7) | (b << 6) | (p << 5) | (e << 4) | ((disp >> 8) & 0xF)
                byte3 = disp & 0xFF
                return f"{opcode_ni:02X}{byte2:02X}{byte3:02X}"
        except ValueError:
            pass
    if is_pool_ref:
        if ref_clean not in pool_table:
            handle_error(f"Unidentified Symbol: {ref_clean}", lc_abs)
        target = pool_table[ref_clean]["abs_addr"]
    else:
        target = resolve(ref_clean)
        if target is None:
            handle_error(f"Unidentified Symbol: {ref_clean}", lc_abs)


    if is_format4:
        e = 1;
        b = 0;
        p = 0
        nixbpe = (n << 5) | (i << 4) | (x << 3) | (b << 2) | (p << 1) | e
        word = (opcode_ni << 24) | (nixbpe << 20) | (target & 0xFFFFF)
        obj_code = f"{word:08X}"
        mod_records.append(f"M.{lc_abs + 1:06X}.05")
        return obj_code

    e = 0
    pc_next = lc_abs + 3

    if -2048 <= (target - pc_next) <= 2047:
        disp = (target - pc_next) & 0xFFF
        b, p = 0, 1

    elif base_register is not None and 0 <= (target - base_register) <= 4095:
        disp = target - base_register
        b, p = 1, 0

    else:
        if is_pool_ref:
            handle_error("POOLVAR error", lc_abs)
        else:
            handle_error(f"Cannot address symbol: {ref_clean}", lc_abs)

    nixbpe = (n << 5) | (i << 4) | (x << 3) | (b << 2) | (p << 1) | e
    byte2 = (x << 7) | (b << 6) | (p << 5) | (e << 4) | ((disp >> 8) & 0xF)
    byte3 = disp & 0xFF
    return f"{opcode_ni:02X}{byte2:02X}{byte3:02X}"


def compute_byte(reference):
    content = reference[2:-1]
    if reference.upper().startswith("X"):
        return content.upper()
    elif reference.upper().startswith("C"):
        return "".join(f"{ord(c):02X}" for c in content)
    return ""


def compute_format2(instruction, reference):
    opcode_val = OPTAB[instruction]["opcode"]
    parts = [p.strip() for p in reference.split(",")]
    reg1 = REGISTERS.get(parts[0], 0)
    reg2 = REGISTERS.get(parts[1], 0) if len(parts) > 1 else 0
    return f"{opcode_val:02X}{reg1:01X}{reg2:01X}"


def flush_t_record():
    global current_t_start, current_t_bytes
    if current_t_bytes:
        byte_length = sum(len(c) // 2 for c in current_t_bytes)
        codes = ".".join(current_t_bytes)
        text_records.append(f"T.{current_t_start:06X}.{byte_length:02X}.{codes}")
    current_t_start = None
    current_t_bytes = []


def add_to_t_record(abs_addr, obj_code):
    global current_t_start, current_t_bytes
    byte_count = len(obj_code) // 2
    if current_t_start is None:
        current_t_start = abs_addr
        current_t_bytes = []
    current_byte_count = sum(len(c) // 2 for c in current_t_bytes)
    if current_byte_count + byte_count > 30:
        flush_t_record()
        current_t_start = abs_addr
        current_t_bytes = []
    current_t_bytes.append(obj_code)


for entry in intermediate:
    lc_str = entry["lc"]
    symbol = entry["symbol"]
    instruction = entry["instruction"]
    reference = entry["reference"]
    obj_code = ""

    rel_lc = int(lc_str, 16) if lc_str else 0
    if current_block_p2 in block:
        lc_abs = block[current_block_p2]["address"] + (rel_lc - block[current_block_p2]["start"])
    else:
        lc_abs = rel_lc

    if instruction == "START":
        program_name = symbol if symbol else "PROG"
        start_address = lc_abs
        obj_code = "No object code"

    elif instruction == "END":
        flush_t_record()
        if pool_table:
            pool_start = None
            pool_codes = []
            for operand, pdata in pool_table.items():
                if pool_start is None:
                    pool_start = pdata["abs_addr"]
                pool_codes.append(pdata["obj_code"])
            if pool_codes:
                byte_length = sum(len(c) // 2 for c in pool_codes)
                codes = ".".join(pool_codes)
                text_records.append(f"T.{pool_start:06X}.{byte_length:02X}.{codes}")
        # find first executable address from END operand
        if reference in Symbol_table:
            first_exec_addr = int(Symbol_table[reference], 16)
        else:
            first_exec_addr = start_address
        obj_code = "No object code"

    elif instruction == "USE":
        flush_t_record()
        if reference == "" or reference == "DEFAULT":
            current_block_p2 = "DEFAULT"
        elif reference in block:
            current_block_p2 = reference
        obj_code = "No object code"

    elif instruction == "BASE":
        if reference in Symbol_table:
            base_register = int(Symbol_table[reference], 16)
        else:
            try:
                base_register = int(reference, 16)
            except:
                pass
        obj_code = "No object code"

    elif instruction == "NOBASE":
        base_register = None
        obj_code = "No object code"

    elif instruction in ("RESW", "RESB"):
        flush_t_record()
        obj_code = "No object code"

    elif instruction == "WORD":
        obj_code = f"{int(reference):06X}"
        add_to_t_record(lc_abs, obj_code)

    elif instruction == "BYTE":
        obj_code = compute_byte(reference)
        add_to_t_record(lc_abs, obj_code)

    elif instruction == "EQU":
        obj_code = "No object code"

    elif instruction.startswith("+"):
        obj_code = compute_format3_4(instruction, reference, lc_abs, is_format4=True)
        add_to_t_record(lc_abs, obj_code)

    elif instruction in OPTAB:
        fmt = OPTAB[instruction]["format"]
        if fmt == 1:
            obj_code = f"{OPTAB[instruction]['opcode']:02X}"
            add_to_t_record(lc_abs, obj_code)
        elif fmt == 2:
            obj_code = compute_format2(instruction, reference)
            add_to_t_record(lc_abs, obj_code)
        elif fmt == 3:
            obj_code = compute_format3_4(instruction, reference, lc_abs, is_format4=False)
            add_to_t_record(lc_abs, obj_code)

    object_code_lines.append({
        "lc": lc_str,
        "symbol": symbol,
        "instruction": instruction,
        "reference": reference,
        "obj_code": obj_code
    })


with open("out_pass2.txt", "w") as f:
    f.write(f"{'Location counter':<18} {'Symbol':<10} {'Instructions':<14} {'Reference':<14} {'Obj. code'}\n")
    f.write("-" * 16 + " " + "-" * 8 + " " + "-" * 12 + " " + "-" * 10 + " " + "-" * 14 + "\n")
    for entry in object_code_lines:
        f.write(
            f"{entry['lc']:<18} {entry['symbol']:<10} {entry['instruction']:<14} {entry['reference']:<14} {entry['obj_code']}\n")

with open("HTME.txt", "w") as f:
    f.write(f"H.{program_name}.{start_address:06X}.{total_length:06X}\n")
    for t in text_records:
        f.write(t + "\n")
    for m in mod_records:
        f.write(m + "\n")
    f.write(f"E.{first_exec_addr:06X}\n")

print("Pass 2 complete.")
print("Output files: out_pass2.txt, HTME.txt")