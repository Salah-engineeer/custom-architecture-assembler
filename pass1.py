import sys
from opcode_table import OPTAB

Symbol_table = {}
pool_table = {}
intermediate = []
block_order=[]
VALID_BLOCKS = {"DEFAULT", "DEFAULTB", "CDATA", "CBLKS"}
block = {
    "DEFAULT":  {"lc": 0x000000, "start": 0x000000, "num": -1, "address": 0},
    "DEFAULTB": {"lc": 0x000000, "start": 0x000000, "num": -1, "address": 0},
    "CDATA":    {"lc": 0x000000, "start": 0x000000, "num": -1, "address": 0},
    "CBLKS":    {"lc": 0x000000, "start": 0x000000, "num": -1, "address": 0},
    "POOL":    {"lc": 0x000000, "start": 0x000000, "num": -1, "address": 0}
}
current_block = "DEFAULT"
block_counter=0

with open('in.txt', 'r') as file:
    for line in file:
        words = line.split()
        if not words or words[0].startswith('.'):
            continue

        symbol = ""
        instruction = ""
        reference = ""
        if len(words) >= 3:
            symbol = words[0]
            instruction = words[1]
            reference = words[2]
        elif len(words) == 2:
            instruction = words[0]
            reference = words[1]
        elif len(words) == 1:
            instruction = words[0]

        if instruction == "START":
            start = int(reference, 16)
            block["DEFAULT"]["lc"] = start
            block["DEFAULT"]["start"] = start
            block["DEFAULT"]["num"] = 0
            block["DEFAULT"]["address"] = start
            block_counter=1
            block_order.append("DEFAULT")
            if symbol != "":
                Symbol_table[symbol] = {
                    "rel_addr": start,
                    "block": "DEFAULT"
                }
            intermediate.append({
                "lc": f"{start:04X}",
                "symbol": symbol,
                "instruction": instruction,
                "reference": reference
            })
            continue

        elif instruction == "END":
            intermediate.append({
                "lc": f"{block[current_block]['lc']:04X}",
                "symbol": "",
                "instruction": instruction,
                "reference": reference
            })
            break

        elif instruction == "USE":
            intermediate.append({
                 "lc": "",
                "symbol": "",
                "instruction": instruction,
                "reference": reference
            })
            if reference == "":
                current_block = "DEFAULT"
            elif reference in VALID_BLOCKS:
                current_block = reference
                if block[current_block]["num"] == -1:
                    block[current_block]["num"] = block_counter
                    block_counter += 1
                    block_order.append(current_block)
            else:
                with open("error.txt", "w") as ef:
                    ef.write(f"Unidentified Block Name: {reference}\n")
                    ef.write(f"PC: {block[current_block]['lc']:06X}\n")
                sys.exit(1)
            continue

        elif instruction in ("BASE", "NOBASE"):
            intermediate.append({
                "lc": f"{block[current_block]['lc']:04X}",
                "symbol": "",
                "instruction": instruction,
                "reference": reference
            })
            continue

        else:
            current_lc = f"{block[current_block]['lc']:04X}"

            if symbol != "" and instruction != "EQU":
                if symbol in Symbol_table:
                    with open("error.txt", "w") as ef:
                        ef.write(f"Duplicate Symbol: {symbol}\n")
                        ef.write(f"PC: {block[current_block]['lc']:06X}\n")
                    sys.exit(1)
                Symbol_table[symbol] = {
                    "rel_addr": block[current_block]["lc"],
                    "block": current_block
                }

            if reference.startswith("&"):
                if not pool_table:
                    block["POOL"]["lc"] = block[current_block]["lc"]
                    block["POOL"]["start"] = block[current_block]["lc"]
                    if block["POOL"]["num"] == -1:
                        block["POOL"]["num"] = block_counter
                        block_counter += 1
                        block_order.append("POOL")
                if reference not in pool_table:
                    pool_addr = block["POOL"]["lc"]
                    val = reference[1:]
                    if val.upper().startswith("X'"):
                        content = val[2:-1]
                        obj_code = content.upper()
                        length = len(content) // 2
                    elif val.upper().startswith("C'"):
                        content = val[2:-1]
                        obj_code = "".join(f"{ord(c):02X}" for c in content)
                        length = len(content)
                    else:
                        obj_code = f"{int(val):06X}"
                        length = 3
                    pool_table[reference] = {
                        "rel_addr": pool_addr,
                        "length": length,
                        "obj_code": obj_code
                    }
                    block["POOL"]["lc"] += length
                    
            if instruction == "RESW":
                block[current_block]["lc"] += int(reference) * 3
            elif instruction == "RESB":
                block[current_block]["lc"] += int(reference)
            elif instruction == "WORD":
                block[current_block]["lc"] += 3
            elif instruction == "BYTE":
                content = reference[2:-1]
                if reference.startswith("X"):
                    block[current_block]["lc"] += len(content) // 2
                elif reference.startswith("C"):
                    block[current_block]["lc"] += len(content)
            elif instruction.startswith("+"):
                block[current_block]["lc"] += 4
            elif instruction in OPTAB:
                f_size = OPTAB[instruction]["format"]
                if f_size == 1:
                    block[current_block]["lc"] += 1
                elif f_size == 2:
                    block[current_block]["lc"] += 2
                elif f_size == 3:
                    block[current_block]["lc"] += 3

            intermediate.append({
                "lc": current_lc,
                "symbol": symbol,
                "instruction": instruction,
                "reference": reference
            })
current_address = block["DEFAULT"]["start"]
for name in block_order:
    block[name]["address"] = current_address
    size = block[name]["lc"] - block[name]["start"]
    current_address += size
total_length = current_address - block["DEFAULT"]["start"]
for sym in Symbol_table:
        rel = Symbol_table[sym]["rel_addr"]
        blk = Symbol_table[sym]["block"]
        abs_addr = block[blk]["address"] + (rel - block[blk]["start"])
        Symbol_table[sym] = f"{abs_addr:04X}"

for operand in pool_table:
        rel = pool_table[operand]["rel_addr"]
        abs_addr = block["POOL"]["address"] + (rel - block["POOL"]["start"])
        pool_table[operand]["abs_addr"] = abs_addr

with open("intermediate.txt", "w") as f:
    f.write(f"{'Location counter':<18} {'Symbol':<10} {'Instructions':<14} {'Reference'}\n")
    f.write("-"*16 + " " + "-"*8 + " " + "-"*12 + " " + "-"*10 + "\n")
    for entry in intermediate:
        f.write(f"{entry['lc']:<18} {entry['symbol']:<10} {entry['instruction']:<14} {entry['reference']}\n")

with open("symbTable.txt", "w") as f:
    f.write(f"{'SYMBOL':<12} {'ADDRESS'}\n")
    f.write("-" * 22 + "\n")
    for sym, addr in Symbol_table.items():
        f.write(f"{sym:<12} {addr}\n")

with open("PoolTable.txt", "w") as f:
    f.write(f"{'POOL NAME':<14} {'ADDRESS':<10} {'LENGTH':<8} {'OBJECT CODE'}\n")
    f.write("-" * 44 + "\n")
    for operand, data in pool_table.items():
        f.write(f"{operand:<14} {data['abs_addr']:04X}      {data['length']:<8} {data['obj_code']}\n")

with open("blockTable.txt", "w") as f:
    f.write(f"{'BLOCK NAME':<14} {'BLOCK NUMBER':<14} {'ADDRESS':<10} {'SIZE'}\n")
    f.write("-" * 50 + "\n")
    for name in block_order:
        size = block[name]["lc"] - block[name]["start"]
        f.write(f"{name:<14} {block[name]['num']:<14} {block[name]['address']:04X}      {size:04X}\n")
    f.write(f"\nTotal program length: {total_length:04X}\n")

print("\nPOOL TABLE:")
for k, v in pool_table.items():
    print(f"  {k:<14} addr={v['abs_addr']:04X} len={v['length']} obj={v['obj_code']}")


print("\nSYMBOL TABLE:")
for k, v in Symbol_table.items():
    print(f"  {k:<12} {v}")

print("\nBLOCK TABLE:")
for name in block_order:
    size = block[name]["lc"] - block[name]["start"]
    print(f"  {name:<12} num={block[name]['num']} address={block[name]['address']:04X} size={size:04X}")
print(f"\nTotal program length: {total_length:04X}")
