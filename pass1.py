import sys
from opcode_table import OPTAB

Symbol_table = {}
pool_table = {}
intermediate = []
VALID_BLOCKS = {"DEFAULT", "DEFAULTB", "CDATA", "CBLKS"}
block = {
    "DEFAULT":  {"lc": 0x000000, "start": 0x000000},
    "DEFAULTB": {"lc": 0x000000, "start": 0x000000},
    "CDATA":    {"lc": 0x000000, "start": 0x000000},
    "CBLKS":    {"lc": 0x000000, "start": 0x000000},
    "POOL":     {"lc": 0x000000, "start": 0x000000},
}
current_block = "DEFAULT"

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
            if symbol != "":
                Symbol_table[symbol] = f"{start:06X}"
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
                "lc": f"{block[current_block]['lc']:04X}",
                "symbol": "",
                "instruction": instruction,
                "reference": reference
            })
            if reference == "":
                current_block = "DEFAULT"
            elif reference in VALID_BLOCKS:
                current_block = reference
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
                Symbol_table[symbol] = f"{block[current_block]['lc']:06X}"

            if reference.startswith("&"):
                if not pool_table:
                    block["POOL"]["lc"] = block[current_block]["lc"]
                    block["POOL"]["start"] = block[current_block]["lc"]
                if reference not in pool_table:
                    pool_table[reference] = f"{block['POOL']['lc']:06X}"
                    block["POOL"]["lc"] += 3

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
    f.write(f"{'OPERAND':<14} {'ADDRESS'}\n")
    f.write("-" * 24 + "\n")
    for operand, addr in pool_table.items():
        f.write(f"{operand:<14} {addr}\n")

print("\nPOOL TABLE:")
for k, v in pool_table.items():
    print(f"  {k:<14} {v}")

print("SYMBOL TABLE:")
for k, v in Symbol_table.items():
    print(f"{k}\t{v}")

print("\nBLOCK COUNTERS:")
for name, data in block.items():
    size = data["lc"] - data["start"]
    print(f"  {name:<12} start={data['start']:06X}  end={data['lc']:06X}  size={size}")